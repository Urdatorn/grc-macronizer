'''
Sentence-level char encoding for the tagger: same letter/diacritic planes as
macron_model/tokenizer.py, reused per-token so we can track exact token->char
spans for pooling, plus a third "macron" plane recovered from our transformer's
own macronized output (MACRON_NONE everywhere when encoding plain/unmacronized
text, so the "without macron" ablation arm is just this same code with
macronized=False).
'''

import sys

sys.path.insert(0, "..")  # macron_model/ for tokenizer.py
from tokenizer import (  # noqa: E402
    PLANE1_STOI,
    encode_plain,
    encode_macronized,
    LABEL_IGNORE_INDEX,
    MACRON_NONE,
)

SPACE_ID = PLANE1_STOI["<space>"]
OTHER_ID = PLANE1_STOI["<other>"]


def encode_sentence(forms, diacritic_vocab, macronized=False, fit=False):
    '''
    forms: list[str] token FORM strings for one sentence (plain, or macronized
    with ^/_ markup if macronized=True).

    Returns chars/plane1/plane2/plane3 (whole-sentence, single space inserted
    between tokens) plus `spans`: one half-open (start, end) char-index range
    per token, for pooling token representations out of the char sequence.
    '''
    chars, plane1, plane2, plane3 = [], [], [], []
    spans = []
    encode_fn = encode_macronized if macronized else encode_plain

    for i, form in enumerate(forms):
        if i > 0:
            chars.append(" ")
            plane1.append(SPACE_ID)
            plane2.append(diacritic_vocab.NONE)
            plane3.append(MACRON_NONE)

        enc = encode_fn(form, diacritic_vocab, fit=fit)
        start = len(chars)
        if not enc["chars"]:
            # Degenerate empty FORM (shouldn't occur in valid CoNLL-U): placeholder
            # so every token still gets a non-empty span to pool over.
            chars.append("")
            plane1.append(OTHER_ID)
            plane2.append(diacritic_vocab.NONE)
            plane3.append(MACRON_NONE)
        else:
            chars.extend(enc["chars"])
            plane1.extend(enc["plane1"])
            plane2.extend(enc["plane2"])
            if macronized:
                plane3.extend(MACRON_NONE if lab == LABEL_IGNORE_INDEX else lab for lab in enc["labels"])
            else:
                plane3.extend([MACRON_NONE] * len(enc["chars"]))
        end = len(chars)
        spans.append((start, end))

    return {"chars": chars, "plane1": plane1, "plane2": plane2, "plane3": plane3, "spans": spans}
