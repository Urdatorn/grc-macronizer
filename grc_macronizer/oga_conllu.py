"""
Converter: Opera Graeca Adnotata (OGA) CoNLL-U annotation files -> spaCy Doc / DocBin.

OGA ships its own state-of-the-art (96.4% POS accuracy) lemma/POS/morphology
annotation for ~40M tokens of Ancient Greek, using the AGDT/Perseus Treebank
tagging scheme (NOT standard Universal Dependencies). grc_macronizer's rule
modules (nominal_forms.py, verbal_forms.py, class_text.py) expect spaCy-style
UD tags/values (as actually produced by grc_odycy_joint_trf). This module
bridges the two: it parses OGA's CoNLL-U files and builds spaCy Doc objects
with `token.lemma_`, `token.pos_`, and `token.morph` set to the UD-style
values grc_macronizer's rules understand -- entirely without running odyCy's
neural pipeline. Only `grc_odycy_joint_trf.load().vocab` is needed (for its
Vocab/StringStore), never a forward pass.

The resulting Doc objects can be serialized into a DocBin and fed straight
into `grc_macronizer.Macronizer(...).macronize(text, custom_doc=<path>)`.

--------------------------------------------------------------------------
CoNLL-U column layout actually used by OGA (verified empirically against
~2000 files / several million tokens; NOT standard UD, no comment lines):

    1  ID       per-sentence token index (1-based)
    2  FORM     surface token
    3  LEMMA
    4  UPOS     single lowercase AGDT letter (see AGDT_POS below)
    5  XPOS     9-position AGDT positional tag string, e.g. "n-s---mv-"
    6  FEATS    partial subset of the above already spelled out as
                 Key=value pairs (e.g. "Case=g|Gender=f|Number=s"), but
                 values are STILL the single-letter AGDT codes, not UD
                 words. Can be "_".
    7  HEAD     dependency head index (ignored here)
    8  DEPREL   AGDT relation label (ignored here)
    9  DEPS     always "_" (ignored here)
    10 MISC     original PAULA token id, e.g. "t_1" (real token) or
                 "e_1" (editorial marker / gap -- NOT a real word)

Empirically confirmed facts that matter for the mapping below (see the
task's validation transcript for the full derivation):

  * Participles are NOT tagged with a separate 't' UPOS letter in the real
    data (that letter essentially never occurs). They are tagged 'v' with
    Mood=p in FEATS/XPOS position 5. odyCy's real output represents
    participles as pos_=VERB, VerbForm=Part, with Case/Gender/Number set
    like a nominal and NO Mood key.
  * 'e' (exclamation) as a UPOS letter is vanishingly rare (5 hits in the
    entire ~40M-token corpus) and in every observed instance was actually
    punctuation (":"), not an interjection. Mapped to PUNCT.
  * AGDT Voice codes 'e' (medio-passive/deponent) and 'm' (real middle) BOTH
    surface as UD Voice=Mid in real odyCy output; 'p' -> Voice=Pass,
    'a' -> Voice=Act. Confirmed against real odyCy inference on deponent
    (γίγνομαι, βούλομαι), true-middle (aorist -σατο/-όμην), and true-passive
    (aorist -θη-) verb forms.
  * Real odyCy's Tense value space is only {Pres, Past, Fut} -- Imperfect,
    Aorist, Perfect and Pluperfect all collapse onto Tense=Past, optionally
    with an extra Aspect=Imp / Aspect=Perf key (itself applied
    inconsistently by odyCy). morph_disambiguator.py's spaCy_tenses dict
    (which lists "Imp"/"Perf"/"Plup" as if they were Tense values) does NOT
    match actual odyCy output and appears to be aspirational/unused dead
    code -- none of nominal_forms.py / verbal_forms.py's *working* code
    paths branch on Tense at all, so this mapping choice has no effect on
    current macronization behaviour; it is chosen purely for fidelity to
    real odyCy output in case future rules consult it.
  * Rows with UPOS '-' are almost always (>99.99%) the OGA editorial
    markers whose MISC id starts with "e_" (e.g. "[0]", "[1]"); a small
    residue (~0.006%) have a real "t_" id but are junk (bare numerals used
    as apparatus/page markers, or literally empty FORM "-"). Both kinds are
    dropped entirely, per the task brief.
  * Only spaCy_cases/spaCy_tenses in morph_disambiguator.py and the actual
    rule-checking code (`'X' in morph.get('Key')`) were used to confirm the
    vocabulary; real odyCy inference (see task transcript) is the ultimate
    ground truth and takes precedence wherever the two disagree.
--------------------------------------------------------------------------
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, NamedTuple

# ---------------------------------------------------------------------------
# AGDT -> UD/odyCy mapping tables
# ---------------------------------------------------------------------------

# Column-4 UPOS single-letter code -> spaCy/UD pos_ string.
# 't' (participle) is included defensively even though it was never observed
# in practice (participles come through as 'v' + Mood=p); if OGA ever emits
# it for some sub-corpus, treat it the same as a verbal participle.
AGDT_POS = {
    "n": "NOUN",
    "v": "VERB",
    "t": "VERB",
    "a": "ADJ",
    "d": "ADV",
    "l": "DET",
    "g": "PART",
    "c": "CCONJ",
    "r": "ADP",
    "p": "PRON",
    "m": "NUM",
    "i": "INTJ",
    "e": "PUNCT",  # observed only as stray ":" tokens (5 hits/corpus)
    "u": "PUNCT",
    "x": "X",
    # "-" (undefined) is NOT mapped -- such rows are dropped by the parser.
}

AGDT_CASE = {"n": "Nom", "g": "Gen", "d": "Dat", "a": "Acc", "v": "Voc"}
AGDT_NUMBER = {"s": "Sing", "p": "Plur", "d": "Dual"}
AGDT_GENDER = {"m": "Masc", "f": "Fem", "n": "Neut", "c": "Com"}
AGDT_DEGREE = {"c": "Cmp", "s": "Sup"}
AGDT_VOICE = {"a": "Act", "m": "Mid", "p": "Pass", "e": "Mid"}  # e = deponent -> Mid
AGDT_PERSON = {"1": "1", "2": "2", "3": "3"}

# Mood: AGDT letter -> (UD Mood value or None, UD VerbForm value)
# i=Ind,s=Sub,o=Opt,m=Imp -> finite moods (VerbForm=Fin, Mood set)
# n=Inf -> VerbForm=Inf, no Mood key (matches real odyCy: infinitives never
#          carry a Mood feature)
# p=Part -> VerbForm=Part, no Mood key (participles are declined like
#           nominals; Case/Gender/Number come from the same FEATS string)
# g=Gerundive/verbal-adjective (-τέος/-τέον). Extremely rare (~0.0004% of
#          tokens). odyCy has no real equivalent; we deliberately do NOT
#          set Mood or VerbForm for these so no rule misfires on a
#          fabricated value -- Case/Gender/Number (present in FEATS
#          whenever the token is adjectival) still come through normally.
AGDT_MOOD = {
    "i": ("Ind", "Fin"),
    "s": ("Sub", "Fin"),
    "o": ("Opt", "Fin"),
    "m": ("Imp", "Fin"),
    "n": (None, "Inf"),
    "p": (None, "Part"),
    "g": (None, None),
}

# Tense: AGDT letter -> (UD Tense value, UD Aspect value or None)
# See module docstring: real odyCy collapses Impf/Aor/Perf/Plup all onto
# Tense=Past, distinguished only (and inconsistently) by an Aspect key.
AGDT_TENSE = {
    "p": ("Pres", None),
    "i": ("Past", "Imp"),
    "f": ("Fut", None),
    "a": ("Past", "Perf"),
    "r": ("Past", "Perf"),
    "l": ("Past", "Perf"),  # pluperfect: no clean real-odyCy signal found;
                            # best-effort, closest aspectually to Perf.
    "t": ("Fut", "Perf"),   # future-perfect: vanishingly rare (~0.0006%)
}

# Punctuation forms that should NOT be preceded by a space when
# reconstructing sentence surface text from CoNLL-U tokens (heuristic only
# -- CoNLL-U carries no original whitespace).
NO_SPACE_BEFORE = set(",.;··;!?·)]}»”’’›")
NO_SPACE_AFTER = set("([{«“‘‘‹")


class OgaToken(NamedTuple):
    form: str
    lemma: str
    upos: str        # single AGDT letter, e.g. "n"
    xpos: str        # 9-char positional string
    feats: dict       # {"Case": "g", "Gender": "f", ...} (AGDT letter values)


def parse_conllu(path: str | Path) -> list[list[OgaToken]]:
    """
    Parse one OGA CoNLL-U file into a list of sentences, each a list of
    OgaToken. Editorial markers (MISC starting with "e_") and rows with
    undefined UPOS ("-") are dropped entirely, as are blank-FORM rows.
    """
    sentences: list[list[OgaToken]] = []
    current: list[OgaToken] = []

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line:
                if current:
                    sentences.append(current)
                    current = []
                continue
            if line.startswith("#"):
                continue  # defensive; OGA files have none, but just in case

            cols = line.split("\t")
            if len(cols) != 10:
                logging.warning(f"{path}: malformed line (not 10 cols): {line!r}")
                continue

            _id, form, lemma, upos, xpos, feats_str, _head, _deprel, _deps, misc = cols

            if misc.startswith("e_"):
                continue  # editorial marker (gap, [0], [1], ...)
            if upos == "-":
                continue  # undefined POS -- junk row (see module docstring)
            if not form or form == "-":
                continue  # empty/placeholder surface form

            feats = {}
            if feats_str != "_":
                for kv in feats_str.split("|"):
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        feats[k] = v

            current.append(OgaToken(form=form, lemma=lemma, upos=upos, xpos=xpos, feats=feats))

    if current:
        sentences.append(current)

    return sentences


def _build_morph_string(tok: OgaToken) -> tuple[str, str]:
    """
    Returns (pos, ufeats_string) for a single OgaToken, using the AGDT->UD
    mapping tables above. pos is "" if the AGDT UPOS letter is unmapped
    (should not happen after parse_conllu's filtering, but defensive).
    """
    pos = AGDT_POS.get(tok.upos, "")
    feats = tok.feats
    parts: dict[str, str] = {}

    if "Case" in feats and feats["Case"] in AGDT_CASE:
        parts["Case"] = AGDT_CASE[feats["Case"]]
    if "Number" in feats and feats["Number"] in AGDT_NUMBER:
        parts["Number"] = AGDT_NUMBER[feats["Number"]]
    if "Gender" in feats and feats["Gender"] in AGDT_GENDER:
        parts["Gender"] = AGDT_GENDER[feats["Gender"]]
    if "Degree" in feats and feats["Degree"] in AGDT_DEGREE:
        parts["Degree"] = AGDT_DEGREE[feats["Degree"]]
    if "Person" in feats and feats["Person"] in AGDT_PERSON:
        parts["Person"] = AGDT_PERSON[feats["Person"]]

    if pos == "VERB":
        mood_letter = feats.get("Mood")
        if mood_letter in AGDT_MOOD:
            ud_mood, ud_verbform = AGDT_MOOD[mood_letter]
            if ud_mood:
                parts["Mood"] = ud_mood
            if ud_verbform:
                parts["VerbForm"] = ud_verbform

        tense_letter = feats.get("Tense")
        if tense_letter in AGDT_TENSE:
            ud_tense, ud_aspect = AGDT_TENSE[tense_letter]
            parts["Tense"] = ud_tense
            if ud_aspect:
                parts["Aspect"] = ud_aspect

        voice_letter = feats.get("Voice")
        if voice_letter in AGDT_VOICE:
            parts["Voice"] = AGDT_VOICE[voice_letter]

    # UFEATS requires alphabetical order by key for canonical form; spaCy
    # doesn't strictly require it but it's good hygiene and matches odyCy.
    ufeats = "|".join(f"{k}={parts[k]}" for k in sorted(parts))
    return pos, ufeats


def reconstruct_words_and_spaces(tokens: list[OgaToken]) -> tuple[list[str], list[bool]]:
    """
    Heuristic sentence-surface reconstruction from CoNLL-U tokens (no
    original whitespace is available). Joins tokens with a single space,
    except no space before closing punctuation and no space after opening
    punctuation/quotes.
    """
    words = [t.form for t in tokens]
    spaces = [True] * len(words)
    for i, w in enumerate(words):
        if i == len(words) - 1:
            spaces[i] = False
            continue
        nxt = words[i + 1]
        if nxt and nxt[0] in NO_SPACE_BEFORE:
            spaces[i] = False
        if w and w[-1] in NO_SPACE_AFTER:
            spaces[i] = False
    return words, spaces


def build_doc(vocab, tokens: list[OgaToken]):
    """
    Build a single spaCy Doc from one parsed OGA sentence (list of
    OgaToken), setting lemma_/pos_/morph on every token per the AGDT->UD
    mapping. `vocab` should be `grc_odycy_joint_trf.load().vocab` (load
    once per process and reuse -- expensive to reload).
    """
    from spacy.tokens import Doc  # local import: keep spaCy off the import path
                                   # for callers that only want parse_conllu()

    words, spaces = reconstruct_words_and_spaces(tokens)
    doc = Doc(vocab, words=words, spaces=spaces)

    for i, tok in enumerate(tokens):
        pos, ufeats = _build_morph_string(tok)
        doc[i].lemma_ = tok.lemma if tok.lemma else tok.form
        doc[i].pos_ = pos
        doc[i].set_morph(ufeats)

    return doc


def iter_docs_from_file(vocab, path: str | Path) -> Iterator[tuple]:
    """
    Yields (doc, surface_text) pairs for every sentence in an OGA CoNLL-U
    file. `surface_text` is the reconstructed plain-text string
    (doc.text) that must be passed as the `text` argument to
    `Macronizer.macronize()` alongside `custom_doc=<path-to-docbin>` --
    the Text class still cleans/matches against this string for the
    final macron-integration step, even when tokens/lemma/pos/morph come
    from a custom Doc.
    """
    sentences = parse_conllu(path)
    for sent in sentences:
        if not sent:
            continue
        doc = build_doc(vocab, sent)
        yield doc, doc.text


def convert_file_to_docbin(vocab, conllu_path: str | Path, docbin_path: str | Path) -> int:
    """
    Converts one OGA CoNLL-U file into a DocBin on disk. Returns the number
    of sentences (Docs) written.
    """
    from spacy.tokens import DocBin

    doc_bin = DocBin(store_user_data=False)
    n = 0
    for doc, _text in iter_docs_from_file(vocab, conllu_path):
        doc_bin.add(doc)
        n += 1
    doc_bin.to_disk(docbin_path)
    return n
