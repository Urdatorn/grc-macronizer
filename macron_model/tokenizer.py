'''
Char-level tokenizer for the macron-tagging model.

Every input character position is encoded as two small categorical "planes":
  - plane 1 (letter):     which of the 24 Greek letters (sigma/final-sigma folded together)
                          it is, or SPACE, or OTHER (punctuation, digits, digamma, Latin, ...)
  - plane 2 (diacritic):  which combination of accent/breathing/diaeresis/subscript-iota
                          it carries (built dynamically from data; OTHER-plane positions
                          always get the "none" diacritic)

The target is a third plane, macron status, but that's never fed in as an input feature —
it is only ever the training label (NONE / SHORT / LONG), used at positions whose plane-1
letter is alpha, iota or upsilon and which grc_utils considers a "real" (ambiguous) dichronon.

Training text comes from grc_macronizer output, e.g. "νεα_νί^α_ς", where an ^ or _
immediately follows a disambiguated dichronon's base letter + any diacritics
(see grc_macronizer/format_macrons.py). A macronized sentence alone is enough to build
one training example: the plain form (marks stripped) is the model input, and the
mark positions give the labels.
'''

import unicodedata

from grc_utils import DICHRONA
from grc_utils.filter_dichrona import is_diphthong, has_iota_adscriptum

PAD, SPACE, OTHER = 0, 1, 2
GREEK_LETTERS = "αβγδεζηθικλμνξοπρστυφχψω"  # 24 letters, sigma covers both σ and ς
LETTER_VOCAB = [None, ' ', None] + list(GREEK_LETTERS)  # index 0/2 are placeholders, see below
PLANE1_ITOS = ["<pad>", "<space>", "<other>"] + list(GREEK_LETTERS)
PLANE1_STOI = {ch: i for i, ch in enumerate(PLANE1_ITOS)}
PLANE1_VOCAB_SIZE = len(PLANE1_ITOS)

DICHRONA_LETTERS = {"α", "ι", "υ"}

MACRON_NONE, MACRON_SHORT, MACRON_LONG = 0, 1, 2
MACRON_LABEL_NAMES = ["none", "short", "long"]

LABEL_IGNORE_INDEX = -100  # standard HF convention: loss ignores these positions

SHORT_MARK, LONG_MARK = "^", "_"

FINAL_SIGMA = "ς"
SIGMA = "σ"


def _base_letter(nfd_char):
    '''Fold final sigma to sigma; return None if not a lowercase Greek letter a-w.'''
    if nfd_char == FINAL_SIGMA:
        return SIGMA
    if nfd_char in GREEK_LETTERS:
        return nfd_char
    return None


def is_dichronon(base_letter):
    return base_letter in DICHRONA_LETTERS


def real_dichrona_mask(chars):
    '''
    True eligibility mask: char is a genuine ambiguous dichronon (in grc_utils.DICHRONA --
    i.e. not circumflexed, not iota-subscript, not a bare unaccented capital) AND does not
    form a diphthong or iota-adscriptum with its immediate neighbour. Mirrors
    grc_utils.filter_dichrona.word_with_real_dichrona but returns a per-position mask
    instead of a single bool, so training/inference eligibility exactly matches what the
    rule-based macronizer (and the Norma benchmark) consider markable.

    `chars` should be the NFC-composed grapheme-cluster list produced by encode_plain /
    encode_macronized. Falls back to a context-free DICHRONA-membership check if any
    cluster didn't collapse to a single codepoint under NFC (rare combining-mark combo).
    '''
    joined = "".join(chars)
    if len(joined) != len(chars):
        return [c in DICHRONA for c in chars]
    n = len(joined)
    mask = []
    for i, ch in enumerate(joined):
        if ch not in DICHRONA:
            mask.append(False)
            continue
        prev_pair = joined[i - 1:i + 1] if i > 0 else ''
        next_pair = joined[i:i + 2] if i < n - 1 else ''
        if (prev_pair and (is_diphthong(prev_pair) or has_iota_adscriptum(prev_pair))) or \
           (next_pair and (is_diphthong(next_pair) or has_iota_adscriptum(next_pair))):
            mask.append(False)
        else:
            mask.append(True)
    return mask


class DiacriticVocab:
    '''
    Built from data: maps a (sorted) combining-mark-string -> small integer id.
    id 0 is reserved for "<pad>", id 1 for "<none>" (no diacritics -- also what
    positions get when diacritics are masked out during training), id 2 for "<unk>"
    (an unseen combination at inference time).
    '''

    PAD, NONE, UNK = 0, 1, 2

    def __init__(self):
        self.itos = ["<pad>", "<none>", "<unk>"]
        self.stoi = {"<pad>": self.PAD, "<none>": self.NONE, "<unk>": self.UNK}
        self.frozen = False

    def fit(self, marks_iterable):
        for marks in marks_iterable:
            self._get_or_add(marks)

    def freeze(self):
        self.frozen = True

    def _get_or_add(self, marks):
        if marks == "":
            return self.NONE
        if marks in self.stoi:
            return self.stoi[marks]
        if self.frozen:
            return self.UNK
        idx = len(self.itos)
        self.itos.append(marks)
        self.stoi[marks] = idx
        return idx

    def encode(self, marks):
        if marks == "":
            return self.NONE
        return self.stoi.get(marks, self.UNK if self.frozen else self._get_or_add(marks))

    def __len__(self):
        return len(self.itos)

    def to_dict(self):
        return {"itos": self.itos}

    @classmethod
    def from_dict(cls, d):
        v = cls()
        v.itos = list(d["itos"])
        v.stoi = {s: i for i, s in enumerate(v.itos)}
        v.frozen = True
        return v


def _decompose(text):
    '''NFD-decompose, then walk it grouping each base letter with its trailing combining marks.
    Returns a list of (base_char, combining_marks_str, is_mark_char) -- non-letters are their
    own "cluster" with empty marks.
    '''
    nfd = unicodedata.normalize("NFD", text)
    clusters = []
    i = 0
    n = len(nfd)
    while i < n:
        ch = nfd[i]
        if unicodedata.category(ch).startswith("M"):
            # Stray combining mark with no preceding base in this cluster view (shouldn't
            # normally happen at the start of a cluster) -- attach to previous cluster if any.
            if clusters:
                base, marks = clusters[-1]
                clusters[-1] = (base, marks + ch)
            i += 1
            continue
        marks = ""
        i += 1
        while i < n and unicodedata.category(nfd[i]).startswith("M"):
            marks += nfd[i]
            i += 1
        clusters.append((ch, marks))
    return clusters


def encode_plain(text, diacritic_vocab, fit=False):
    '''
    Encode a PLAIN (no ^/_ marks) macronized-or-not string into parallel arrays.

    Returns dict with:
      chars:       list[str]  -- the base+diacritics grapheme cluster as it should be rendered
                                  (NFC), one per position -- used to reconstruct output text
      plane1:      list[int]  -- letter-plane ids
      plane2:      list[int]  -- diacritic-plane ids
      dichrona_mask: list[bool] -- True where plane1 letter is alpha/iota/upsilon (candidate
                                  positions; caller further filters "real" dichrona if desired)
    '''
    clusters = _decompose(text)
    chars, plane1, plane2 = [], [], []
    for base, marks in clusters:
        lower = base.lower()
        letter = _base_letter(lower)
        if letter is not None:
            plane1.append(PLANE1_STOI[letter])
            did = diacritic_vocab._get_or_add(marks) if fit else diacritic_vocab.encode(marks)
            plane2.append(did)
        elif base == " " or base == "\n" or base == "\t":
            plane1.append(PLANE1_STOI["<space>"])
            plane2.append(diacritic_vocab.NONE)
        else:
            plane1.append(PLANE1_STOI["<other>"])
            plane2.append(diacritic_vocab.NONE)
        chars.append(unicodedata.normalize("NFC", base + marks))
    return {
        "chars": chars,
        "plane1": plane1,
        "plane2": plane2,
        "dichrona_mask": real_dichrona_mask(chars),
    }


def strip_marks(text):
    return text.replace(SHORT_MARK, "").replace(LONG_MARK, "")


def encode_macronized(text, diacritic_vocab, fit=False):
    '''
    Encode a MACRONIZED string (base letters with trailing ^/_ markup, cf.
    grc_macronizer/format_macrons.py's macron_unicode_to_markup convention) into the
    same per-position arrays as encode_plain, PLUS a macron_label array (NONE/SHORT/LONG,
    LABEL_IGNORE_INDEX at non-dichrona positions and at dichrona positions with no mark).
    '''
    nfd = unicodedata.normalize("NFD", text)
    clusters = []
    i, n = 0, len(nfd)
    while i < n:
        ch = nfd[i]
        if unicodedata.category(ch).startswith("M"):
            if clusters:
                base, marks, mark_sym = clusters[-1]
                clusters[-1] = (base, marks + ch, mark_sym)
            i += 1
            continue
        marks = ""
        i += 1
        while i < n and unicodedata.category(nfd[i]).startswith("M"):
            marks += nfd[i]
            i += 1
        mark_sym = ""
        if i < n and nfd[i] in (SHORT_MARK, LONG_MARK):
            mark_sym = nfd[i]
            i += 1
        clusters.append((ch, marks, mark_sym))

    chars, plane1, plane2, mark_syms = [], [], [], []
    for base, marks, mark_sym in clusters:
        lower = base.lower()
        letter = _base_letter(lower)
        if letter is not None:
            plane1.append(PLANE1_STOI[letter])
            did = diacritic_vocab._get_or_add(marks) if fit else diacritic_vocab.encode(marks)
            plane2.append(did)
        elif base == " " or base == "\n" or base == "\t":
            plane1.append(PLANE1_STOI["<space>"])
            plane2.append(diacritic_vocab.NONE)
        else:
            plane1.append(PLANE1_STOI["<other>"])
            plane2.append(diacritic_vocab.NONE)
        chars.append(unicodedata.normalize("NFC", base + marks))
        mark_syms.append(mark_sym)

    eligible = real_dichrona_mask(chars)
    labels = []
    for eligible_i, mark_sym in zip(eligible, mark_syms):
        if not eligible_i:
            labels.append(LABEL_IGNORE_INDEX)
        elif mark_sym == SHORT_MARK:
            labels.append(MACRON_SHORT)
        elif mark_sym == LONG_MARK:
            labels.append(MACRON_LONG)
        else:
            labels.append(LABEL_IGNORE_INDEX)  # dichronon left unmarked -> ignore in loss

    return {
        "chars": chars,
        "plane1": plane1,
        "plane2": plane2,
        "labels": labels,
        "dichrona_mask": eligible,
    }


def decode(chars, pred_labels):
    '''Rebuild a macronized string from rendered chars + predicted label per position.'''
    out = []
    for ch, lab in zip(chars, pred_labels):
        out.append(ch)
        if lab == MACRON_SHORT:
            out.append(SHORT_MARK)
        elif lab == MACRON_LONG:
            out.append(LONG_MARK)
    return "".join(out)


def mask_diacritics(plane2_ids, none_id, p):
    '''Return a copy of plane2_ids with each entry replaced by `none_id` independently
    with probability p (a lightweight stand-in for "input lacks accentuation").'''
    import random
    return [none_id if (v != none_id and random.random() < p) else v for v in plane2_ids]
