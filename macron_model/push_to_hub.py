'''
Push a trained macron_model checkpoint to the HuggingFace Hub: the model
weights/config (via MacronizerModel.push_to_hub, since it's a plain
transformers.PreTrainedModel subclass), the diacritic vocab it needs to
reconstruct the tokenizer, and this directory's MODEL_CARD.md as the repo's
README.

Usage:
    python push_to_hub.py --checkpoint_dir runs/v2_gpu/best --repo_id Ericu950/oga-macronizer-char
    python push_to_hub.py --checkpoint_dir runs/v2_gpu/best --repo_id Ericu950/oga-macronizer-char --private
'''

import argparse
import os

from huggingface_hub import HfApi

from model import MacronizerModel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint_dir", required=True, help="e.g. runs/v2_gpu/best")
    ap.add_argument("--repo_id", required=True, help="e.g. Ericu950/oga-macronizer-char")
    ap.add_argument("--private", action="store_true")
    args = ap.parse_args()

    print(f"Loading checkpoint from {args.checkpoint_dir} ...")
    model = MacronizerModel.from_pretrained(args.checkpoint_dir)

    print(f"Pushing model weights + config to {args.repo_id} ...")
    model.push_to_hub(args.repo_id, private=args.private)

    api = HfApi()

    # diacritic_vocab.json is saved once per training run, one level up from
    # the best/ or final/ checkpoint subdirectory -- see train.py.
    run_dir = os.path.dirname(os.path.normpath(args.checkpoint_dir))
    vocab_path = os.path.join(run_dir, "diacritic_vocab.json")
    if not os.path.exists(vocab_path):
        vocab_path = os.path.join(args.checkpoint_dir, "diacritic_vocab.json")

    if os.path.exists(vocab_path):
        print(f"Pushing {vocab_path} ...")
        api.upload_file(path_or_fileobj=vocab_path, path_in_repo="diacritic_vocab.json", repo_id=args.repo_id)
    else:
        print(f"WARNING: no diacritic_vocab.json found near {args.checkpoint_dir} -- "
              "push it manually. predict.py's MacronPredictor needs it to reconstruct the tokenizer.")

    model_card = os.path.join(os.path.dirname(os.path.abspath(__file__)), "MODEL_CARD.md")
    if os.path.exists(model_card):
        print(f"Pushing {model_card} as README.md ...")
        api.upload_file(path_or_fileobj=model_card, path_in_repo="README.md", repo_id=args.repo_id)

    print(f"\nDone: https://huggingface.co/{args.repo_id}")


if __name__ == "__main__":
    main()
