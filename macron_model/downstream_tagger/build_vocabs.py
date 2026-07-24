'''
One-off vocab build, run BEFORE launching both training arms in parallel --
train_tagger.py builds vocabs lazily on first run and reuses them on the
second, which races if both arms start at the same time. Run this once first
so both `python train_tagger.py ...` invocations just load, never write.

Usage:
    python build_vocabs.py --train_conllu data/train0.conllu --vocab_dir runs/vocabs
'''

import argparse

from tagger_dataset import load_sentences
from train_tagger import load_or_build_vocabs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train_conllu", required=True)
    ap.add_argument("--vocab_dir", required=True)
    args = ap.parse_args()

    sentences = load_sentences(args.train_conllu)
    diacritic_vocab, xpos_vocab, lemma_vocab = load_or_build_vocabs(args.vocab_dir, sentences)
    print(f"diacritic vocab: {len(diacritic_vocab)}, xpos vocab: {len(xpos_vocab)}, "
          f"lemma-script vocab: {len(lemma_vocab)}")
    print(f"Saved to {args.vocab_dir}/")


if __name__ == "__main__":
    main()
