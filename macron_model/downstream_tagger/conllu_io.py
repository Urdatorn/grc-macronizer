'''Minimal CoNLL-U reader shared by macronize_conllu.py and tagger_dataset.py.
Fields, 0-indexed: ID=0 FORM=1 LEMMA=2 POS=3 XPOS=4 FEATS=5 HEAD=6 DEPREL=7 DEPS=8 MISC=9
(AGDT scheme -- POS is a single letter, XPOS is the 9-slot positional tag).'''

FORM, LEMMA, XPOS = 1, 2, 4


def iter_sentences(path):
    '''Yields (comment_lines, token_rows) per sentence. token_rows is list[list[str]],
    one tab-split row per token line (multiword/empty-node rows with non-integer ID
    are skipped, since they don't carry independent lemma/XPOS supervision).'''
    comments, tokens = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                if tokens:
                    yield comments, tokens
                comments, tokens = [], []
                continue
            if line.startswith("#"):
                comments.append(line)
                continue
            row = line.split("\t")
            if not row[0].isdigit():
                continue
            tokens.append(row)
    if tokens:
        yield comments, tokens
