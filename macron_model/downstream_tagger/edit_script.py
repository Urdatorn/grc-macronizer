'''
Lemma-as-edit-script: instead of generating the lemma string, represent it as a
transformation relative to the surface form (UDPipe/Straka-style edit trees), then
classify which of a closed set of scripts applies. Standard approach for
morphologically rich languages -- Greek needs both suffix change (regular
inflection) and prefix change (augment: ἔλυσα vs lemma λύω), so the script is
anchored on the longest common substring rather than assuming a shared prefix.
'''

from difflib import SequenceMatcher

UNK_SCRIPT = "<unk>"
IDENTITY_SCRIPT = "0|0|"  # strip 0 front, strip 0 back, no replacement wrapper


def compute_edit_script(form, lemma):
    '''
    Returns a script string "<strip_front>|<strip_back>|<prefix_lemma><SEP><suffix_lemma>"
    meaning: strip `strip_front` chars from the start and `strip_back` chars from the
    end of (lowercased) form, then wrap the remaining core in prefix_lemma/suffix_lemma
    to get (lowercased) lemma.
    '''
    form_l, lemma_l = form.lower(), lemma.lower()
    sm = SequenceMatcher(None, form_l, lemma_l, autojunk=False)
    match = sm.find_longest_match(0, len(form_l), 0, len(lemma_l))
    if match.size == 0:
        # No overlap at all (e.g. suppletive forms) -- encode as a literal replacement.
        return f"L|{lemma_l}"
    strip_front = match.a
    strip_back = len(form_l) - (match.a + match.size)
    prefix_lemma = lemma_l[:match.b]
    suffix_lemma = lemma_l[match.b + match.size:]
    return f"{strip_front}|{strip_back}|{prefix_lemma}\x1f{suffix_lemma}"


def apply_edit_script(form, script):
    '''Reconstruct a lemma guess from a surface form + script string. Best-effort:
    if the script's strip counts don't fit the given form, falls back to the form
    itself unchanged. Preserves capitalization of the original form's first letter.'''
    form_l = form.lower()
    out = form_l
    if script.startswith("L|"):
        out = script[2:]
    elif "|" in script:
        try:
            strip_front_s, strip_back_s, wrap = script.split("|", 2)
            strip_front, strip_back = int(strip_front_s), int(strip_back_s)
            prefix_lemma, suffix_lemma = wrap.split("\x1f")
            core = form_l[strip_front: len(form_l) - strip_back] if strip_back else form_l[strip_front:]
            if len(form_l) - strip_front - strip_back < 0:
                out = form_l
            else:
                out = prefix_lemma + core + suffix_lemma
        except (ValueError, IndexError):
            out = form_l
    if form[:1].isupper():
        out = out[:1].upper() + out[1:]
    return out


class EditScriptVocab:
    '''Closed vocabulary of edit scripts, built from training data only (like
    tokenizer.DiacriticVocab). id 0 = <pad>, id 1 = <unk> (unseen script at eval time).'''

    PAD, UNK = 0, 1

    def __init__(self):
        self.itos = ["<pad>", UNK_SCRIPT]
        self.stoi = {"<pad>": self.PAD, UNK_SCRIPT: self.UNK}
        self.frozen = False

    def fit(self, scripts_iterable):
        for s in scripts_iterable:
            self._get_or_add(s)

    def freeze(self):
        self.frozen = True

    def _get_or_add(self, script):
        if script in self.stoi:
            return self.stoi[script]
        if self.frozen:
            return self.UNK
        idx = len(self.itos)
        self.itos.append(script)
        self.stoi[script] = idx
        return idx

    def encode(self, script):
        return self.stoi.get(script, self.UNK)

    def decode(self, idx):
        return self.itos[idx]

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


if __name__ == "__main__":
    tests = [
        ("ἀνήρ", "ἀνήρ"),
        ("ἀνθρώπων", "ἄνθρωπος"),
        ("ἐκμάθοις", "ἐκμανθάνω"),
        ("ἠνείχετο", "ἀνέχω"),
        ("ἐστʼ", "εἰμί"),
    ]
    for form, lemma in tests:
        script = compute_edit_script(form, lemma)
        recon = apply_edit_script(form, script)
        status = "OK" if recon == lemma.lower() else "MISS"
        print(f"{status:4s} {form!r:15s} -> script={script!r:30s} recon={recon!r} gold={lemma.lower()!r}")
