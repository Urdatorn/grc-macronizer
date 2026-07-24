'''
Macronize the FORM column of a CoNLL-U file with our trained transformer, sentence
by sentence (for context), then realign the macronized text back onto per-token
FORM values. Everything else (LEMMA, POS, XPOS, FEATS, HEAD, DEPREL, ...) is copied
through unchanged -- only FORM changes.

Usage:
    python macronize_conllu.py --input data/train0.conllu --output data/train0.macronized.conllu
    python macronize_conllu.py --input data/train0.conllu --output data/train0.macronized.conllu \
        --model_dir Ericu950/oga-macronizer-char --device cuda
'''

import argparse
import sys

import torch

sys.path.insert(0, "..")  # macron_model/ for predict.py
from predict import MacronPredictor  # noqa: E402
from conllu_io import iter_sentences, FORM  # noqa: E402

DEFAULT_MODEL = "Ericu950/oga-macronizer-char"


def macronize_file(predictor, in_path, out_path):
    n_sent, n_mismatch = 0, 0
    with open(out_path, "w", encoding="utf-8") as out:
        for comments, tokens in iter_sentences(in_path):
            forms = [row[FORM] for row in tokens]
            joined = " ".join(forms)
            macronized = predictor.macronize(joined)
            parts = macronized.split(" ")
            if len(parts) != len(forms):
                # Rare: fall back to macronizing each token in isolation (loses
                # cross-word context but guarantees alignment).
                n_mismatch += 1
                parts = [predictor.macronize(f) for f in forms]

            for row, new_form in zip(tokens, parts):
                row[FORM] = new_form
            for c in comments:
                out.write(c + "\n")
            for row in tokens:
                out.write("\t".join(row) + "\n")
            out.write("\n")

            n_sent += 1
            if n_sent % 2000 == 0:
                print(f"  {n_sent} sentences ({n_mismatch} realign fallbacks)", file=sys.stderr)
    print(f"Done: {n_sent} sentences, {n_mismatch} realign fallbacks -> {out_path}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--model_dir", default=DEFAULT_MODEL)
    ap.add_argument("--device", default=None)
    ap.add_argument("--num_threads", type=int, default=4,
                     help="torch intra-op thread cap for CPU inference -- uncapped defaults to "
                          "all cores, which is dramatically SLOWER for this model's small matmuls "
                          "(OpenMP oversubscription), not faster.")
    args = ap.parse_args()

    if args.device in (None, "cpu"):
        torch.set_num_threads(args.num_threads)

    predictor = MacronPredictor(args.model_dir, device=args.device)
    macronize_file(predictor, args.input, args.output)


if __name__ == "__main__":
    main()
