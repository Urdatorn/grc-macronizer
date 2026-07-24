'''
Inference wrapper around a trained MacronizerModel checkpoint, exposing the
same `str -> str` interface eval_norma.py expects from a macronize_fn: given
plain (unmarked) text, return the same text with ^/_ macron markup added.

Usage as a library:
    from predict import MacronPredictor
    predictor = MacronPredictor("runs/v1/best")
    macronized = predictor.macronize(plain_text)   # matches eval_norma's macronize_fn

CLI:
    python predict.py --model_dir runs/v1/best --text "ανθρωπος"
'''

import argparse
import json
import os

import torch
from huggingface_hub import hf_hub_download

from model import MacronizerModel
from tokenizer import (
    DiacriticVocab,
    decode,
    encode_plain,
    real_dichrona_mask,
    MACRON_SHORT,
    MACRON_LONG,
)

PAD_ID = 0


class MacronPredictor:
    def __init__(self, model_dir, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = MacronizerModel.from_pretrained(model_dir).to(self.device)
        self.model.eval()

        if os.path.isdir(model_dir):
            vocab_path = os.path.join(model_dir, "diacritic_vocab.json")
            if not os.path.exists(vocab_path):
                # checkpoints are saved under <output_dir>/best or /final; the vocab
                # is saved once at <output_dir>/diacritic_vocab.json
                vocab_path = os.path.join(os.path.dirname(os.path.normpath(model_dir)),
                                           "diacritic_vocab.json")
        else:
            # model_dir is a Hub repo id (e.g. "Ericu950/oga-macronizer-char")
            vocab_path = hf_hub_download(repo_id=model_dir, filename="diacritic_vocab.json")
        with open(vocab_path, encoding="utf-8") as f:
            self.vocab = DiacriticVocab.from_dict(json.load(f))

        self.max_len = self.model.config.max_position_embeddings

    @torch.no_grad()
    def macronize_line(self, line):
        if not line.strip():
            return line
        enc = encode_plain(line, self.vocab, fit=False)
        chars, plane1, plane2, eligible = enc["chars"], enc["plane1"], enc["plane2"], enc["dichrona_mask"]
        if not plane1:
            return line

        pred_labels = [0] * len(plane1)
        for start in range(0, len(plane1), self.max_len):
            p1 = torch.tensor([plane1[start:start + self.max_len]], dtype=torch.long, device=self.device)
            p2 = torch.tensor([plane2[start:start + self.max_len]], dtype=torch.long, device=self.device)
            out = self.model(plane1_ids=p1, plane2_ids=p2)
            chunk_preds = out.logits.argmax(-1)[0].tolist()
            pred_labels[start:start + self.max_len] = chunk_preds

        # Hard safety net: never emit a mark at a position that isn't a genuine
        # ambiguous dichronon (diphthong members, circumflexed vowels, etc. --
        # the model never saw supervision there and shouldn't be trusted there).
        final_labels = [
            lab if elig and lab in (MACRON_SHORT, MACRON_LONG) else 0
            for lab, elig in zip(pred_labels, eligible)
        ]
        return decode(chars, final_labels)

    def macronize(self, text):
        '''Line-preserving: splits on "\\n", predicts each line, rejoins -- so
        line count in == line count out (required for eval_norma's batched-call
        fast path).'''
        lines = text.split("\n")
        return "\n".join(self.macronize_line(line) for line in lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", required=True)
    ap.add_argument("--text", help="Text to macronize (or read stdin if omitted)")
    args = ap.parse_args()

    predictor = MacronPredictor(args.model_dir)
    if args.text:
        print(predictor.macronize(args.text))
    else:
        import sys
        print(predictor.macronize(sys.stdin.read()))


if __name__ == "__main__":
    main()
