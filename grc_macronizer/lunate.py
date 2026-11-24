'''
Lunate sigma (ϲ U+03F2, Ϲ U+03F9) support.

Some editions in OGA (e.g. the Suda and Aelius Herodianus in First1KGreek) are printed with
the lunate sigma. The lexicons (custom, Wiktionary, LSJ, hypotactic) and the rules spell
σ/ς, so lunate tokens missed almost every lookup: in the OGA run of 2026-11-24, 82.6% of the
lunate tokens sent to the modules kept an unmarked dichronon, against 21.1% overall.

Tokens are therefore looked up with ordinary sigmas, and the marks are put back on the
original spelling, so the text keeps its lunate sigmas. The replacement is one character for
one character, so the positions of the ^/_ marks carry over unchanged.
'''

import re

_FINAL = re.compile(r"ϲ(?=$|[^\w])")  # word-final: end of token, or before an apostrophe etc.


def has_lunate(word):
    return "ϲ" in word or "Ϲ" in word


def normalize_lunate(word):
    '''
    >>> normalize_lunate('πόλιϲ')
    'πόλις'
    >>> normalize_lunate('Ἀριϲτοφάνηϲ')
    'Ἀριστοφάνης'
    >>> normalize_lunate('Ϲωκράτηϲ')
    'Σωκράτης'
    '''
    if not has_lunate(word):
        return word
    word = word.replace("Ϲ", "Σ")
    word = _FINAL.sub("ς", word)
    return word.replace("ϲ", "σ")


def restore_spelling(macronized, original):
    '''
    Put the lunate sigmas of the original token back into the macronized normalized token:
    every letter position that is ϲ/Ϲ in the original and σ/ς/Σ in the macronized token gets
    the original character back; marks and all other letters are kept as the cascade
    returned them (as for any token without lunate sigmas).

    >>> restore_spelling('πό^λις', 'πόλιϲ')
    'πό^λιϲ'
    >>> restore_spelling('Ἀ^ρι^στοφά_νης', 'Ἀριϲτοφάνηϲ')
    'Ἀ^ρι^ϲτοφά_νηϲ'

    Returns None if the letter counts differ, i.e. the positions cannot be aligned.
    '''
    if sum(1 for c in macronized if c not in "^_") != len(original):
        return None
    out, i = [], 0
    for c in macronized:
        if c in "^_":
            out.append(c)
            continue
        o = original[i]
        out.append(o if o in "ϲϹ" and c in "σςΣ" else c)
        i += 1
    return "".join(out)
