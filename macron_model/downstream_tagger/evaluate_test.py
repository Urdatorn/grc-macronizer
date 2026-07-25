'''
Final held-out evaluation: load a trained tagger checkpoint + the shared vocabs,
score it on the (untouched) test split. Run once per ablation arm.

Usage:
    python evaluate_test.py --checkpoint runs/no_macron/best --vocab_dir runs/vocabs \
        --test_conllu data/test.conllu
    python evaluate_test.py --checkpoint runs/with_macron/best --vocab_dir runs/vocabs \
        --test_conllu data/test.macronized.conllu --use_macron_plane
'''

import argparse
import json
import os
import sys

import torch
from torch.utils.data import DataLoader

from tagger_dataset import ClosedVocab, load_sentences, make_collate_fn, TaggerDataset
from tagger_model import TaggerModel
from edit_script import EditScriptVocab
from train_tagger import evaluate

sys.path.insert(0, "..")  # macron_model/ for tokenizer.py
from tokenizer import DiacriticVocab  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True, help="e.g. runs/no_macron/best")
    ap.add_argument("--vocab_dir", required=True)
    ap.add_argument("--test_conllu", required=True)
    ap.add_argument("--use_macron_plane", action="store_true")
    ap.add_argument("--macron_plane_mode", choices=["real", "random", "constant"], default="real",
                     help="Must match whatever the checkpoint was trained with -- evaluating a "
                          "random/constant-trained model with 'real' input (or vice versa) is a "
                          "train/test mismatch, not a meaningful number.")
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--max_len", type=int, default=384)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    with open(os.path.join(args.vocab_dir, "diacritic_vocab.json"), encoding="utf-8") as f:
        diacritic_vocab = DiacriticVocab.from_dict(json.load(f))
    with open(os.path.join(args.vocab_dir, "xpos_vocab.json"), encoding="utf-8") as f:
        xpos_vocab = ClosedVocab.from_dict(json.load(f))
    with open(os.path.join(args.vocab_dir, "lemma_vocab.json"), encoding="utf-8") as f:
        lemma_vocab = EditScriptVocab.from_dict(json.load(f))

    print(f"Loading {args.test_conllu} ...")
    test_sentences = load_sentences(args.test_conllu)
    test_ds = TaggerDataset(test_sentences, diacritic_vocab, xpos_vocab, lemma_vocab,
                             macronized=args.use_macron_plane, max_len=args.max_len)
    print(f"test examples: {len(test_ds)}")

    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False,
                              collate_fn=make_collate_fn(args.use_macron_plane, macron_plane_mode=args.macron_plane_mode))

    model = TaggerModel.from_pretrained(args.checkpoint).to(args.device)
    print(f"Loaded {args.checkpoint} ({model.num_parameters_readable()} params, "
          f"use_macron_plane={model.config.use_macron_plane}, macron_plane_mode={args.macron_plane_mode})")

    metrics = evaluate(model, test_loader, args.device)
    print(f"\nTest set results ({args.test_conllu}):")
    print(f"  xpos_accuracy:  {metrics['xpos_accuracy']:.4%}")
    print(f"  lemma_accuracy: {metrics['lemma_accuracy']:.4%}")
    print(f"  combined:       {metrics['combined']:.4%}")
    print(f"  n_tokens:       {metrics['n_tokens']}")


if __name__ == "__main__":
    main()
