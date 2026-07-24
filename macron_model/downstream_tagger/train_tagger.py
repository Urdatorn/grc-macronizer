'''
Trains one arm of the RQ3 ablation: a char-level lemma+XPOS tagger, with or
without a macron input plane. Run this script TWICE with the same --vocab_dir
(build order doesn't matter, see tagger_dataset.build_vocabs) to get both arms:

    # baseline: plain text, no macron plane
    python train_tagger.py --train_conllu data/train0.conllu --dev_conllu data/dev0.conllu \
        --vocab_dir runs/vocabs --output_dir runs/no_macron --epochs 30 --patience 8

    # ablation: macronized text (our transformer's own output), macron plane on
    python train_tagger.py --train_conllu data/train0.macronized.conllu --dev_conllu data/dev0.macronized.conllu \
        --vocab_dir runs/vocabs --output_dir runs/with_macron --use_macron_plane --epochs 30 --patience 8

Submit via Slurm, e.g.:
    sbatch -A <account> -p gpu --gpus 1 -c 8 --mem=32G -t 24:00:00 --wrap "source .venv/bin/activate && python train_tagger.py ..."
'''

import argparse
import json
import os
import time

import torch
from torch.utils.data import DataLoader

from tagger_dataset import build_vocabs, ClosedVocab, load_sentences, make_collate_fn, TaggerDataset
from tagger_model import TaggerConfig, TaggerModel
from edit_script import EditScriptVocab

import sys
sys.path.insert(0, "..")  # macron_model/ for tokenizer.py
from tokenizer import DiacriticVocab, LABEL_IGNORE_INDEX  # noqa: E402


def load_or_build_vocabs(vocab_dir, train_sentences):
    paths = {
        "diacritic": os.path.join(vocab_dir, "diacritic_vocab.json"),
        "xpos": os.path.join(vocab_dir, "xpos_vocab.json"),
        "lemma": os.path.join(vocab_dir, "lemma_vocab.json"),
    }
    if all(os.path.exists(p) for p in paths.values()):
        print(f"Loading existing vocabs from {vocab_dir} (shared across both ablation arms) ...")
        with open(paths["diacritic"], encoding="utf-8") as f:
            diacritic_vocab = DiacriticVocab.from_dict(json.load(f))
        with open(paths["xpos"], encoding="utf-8") as f:
            xpos_vocab = ClosedVocab.from_dict(json.load(f))
        with open(paths["lemma"], encoding="utf-8") as f:
            lemma_vocab = EditScriptVocab.from_dict(json.load(f))
        return diacritic_vocab, xpos_vocab, lemma_vocab

    print("Building vocabs from this run's training split (first run creates them; "
          "the second arm will reuse these, so both see identical label spaces) ...")
    diacritic_vocab, xpos_vocab, lemma_vocab = build_vocabs(train_sentences)
    os.makedirs(vocab_dir, exist_ok=True)
    with open(paths["diacritic"], "w", encoding="utf-8") as f:
        json.dump(diacritic_vocab.to_dict(), f, ensure_ascii=False, indent=2)
    with open(paths["xpos"], "w", encoding="utf-8") as f:
        json.dump(xpos_vocab.to_dict(), f, ensure_ascii=False, indent=2)
    with open(paths["lemma"], "w", encoding="utf-8") as f:
        json.dump(lemma_vocab.to_dict(), f, ensure_ascii=False, indent=2)
    return diacritic_vocab, xpos_vocab, lemma_vocab


def evaluate(model, loader, device):
    model.eval()
    total_loss, n_batches = 0.0, 0
    xpos_correct, xpos_total = 0, 0
    lemma_correct, lemma_total = 0, 0
    with torch.no_grad():
        for batch in loader:
            batch = {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in batch.items()}
            out = model(**batch)
            total_loss += out["loss"].item()
            n_batches += 1

            xpos_preds = out["xpos_logits"].argmax(-1)
            xmask = batch["xpos_labels"] != LABEL_IGNORE_INDEX
            xpos_correct += (xpos_preds[xmask] == batch["xpos_labels"][xmask]).sum().item()
            xpos_total += xmask.sum().item()

            lemma_preds = out["lemma_logits"].argmax(-1)
            lmask = batch["lemma_labels"] != LABEL_IGNORE_INDEX
            lemma_correct += (lemma_preds[lmask] == batch["lemma_labels"][lmask]).sum().item()
            lemma_total += lmask.sum().item()
    model.train()
    xpos_acc = xpos_correct / xpos_total if xpos_total else 0.0
    lemma_acc = lemma_correct / lemma_total if lemma_total else 0.0
    return {
        "loss": total_loss / max(n_batches, 1),
        "xpos_accuracy": xpos_acc,
        "lemma_accuracy": lemma_acc,
        "combined": (xpos_acc + lemma_acc) / 2,
        "n_tokens": xpos_total,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train_conllu", required=True)
    ap.add_argument("--dev_conllu", required=True)
    ap.add_argument("--vocab_dir", required=True,
                     help="Shared between both ablation arms -- run order doesn't matter, "
                          "the first run creates these, the second reuses them.")
    ap.add_argument("--output_dir", required=True)
    ap.add_argument("--use_macron_plane", action="store_true")
    ap.add_argument("--max_len", type=int, default=384)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--weight_decay", type=float, default=0.01)
    ap.add_argument("--hidden_size", type=int, default=128)
    ap.add_argument("--num_hidden_layers", type=int, default=4)
    ap.add_argument("--num_attention_heads", type=int, default=4)
    ap.add_argument("--intermediate_size", type=int, default=512)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--eval_every_steps", type=int, default=500)
    ap.add_argument("--log_every_steps", type=int, default=100)
    ap.add_argument("--patience", type=int, default=8,
                     help="Stop after this many consecutive evals with no improvement in "
                          "combined (xpos+lemma)/2 val accuracy. 0 disables early stopping.")
    ap.add_argument("--num_workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--num_threads", type=int, default=4)
    args = ap.parse_args()

    torch.set_num_threads(args.num_threads)
    torch.manual_seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Loading {args.train_conllu} / {args.dev_conllu} ...")
    train_sentences = load_sentences(args.train_conllu)
    dev_sentences = load_sentences(args.dev_conllu)
    print(f"train sentences: {len(train_sentences)}, dev sentences: {len(dev_sentences)}")

    diacritic_vocab, xpos_vocab, lemma_vocab = load_or_build_vocabs(args.vocab_dir, train_sentences)
    print(f"diacritic vocab: {len(diacritic_vocab)}, xpos vocab: {len(xpos_vocab)}, "
          f"lemma-script vocab: {len(lemma_vocab)}")

    print("Encoding dataset ...")
    train_ds = TaggerDataset(train_sentences, diacritic_vocab, xpos_vocab, lemma_vocab,
                              macronized=args.use_macron_plane, max_len=args.max_len)
    dev_ds = TaggerDataset(dev_sentences, diacritic_vocab, xpos_vocab, lemma_vocab,
                            macronized=args.use_macron_plane, max_len=args.max_len)
    print(f"train examples: {len(train_ds)}, dev examples: {len(dev_ds)}")

    collate_fn = make_collate_fn(args.use_macron_plane)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                               collate_fn=collate_fn, num_workers=args.num_workers, drop_last=True)
    dev_loader = DataLoader(dev_ds, batch_size=args.batch_size, shuffle=False,
                             collate_fn=collate_fn, num_workers=args.num_workers)

    config = TaggerConfig(
        plane2_vocab_size=len(diacritic_vocab),
        use_macron_plane=args.use_macron_plane,
        num_xpos_labels=len(xpos_vocab),
        num_lemma_labels=len(lemma_vocab),
        hidden_size=args.hidden_size,
        num_hidden_layers=args.num_hidden_layers,
        num_attention_heads=args.num_attention_heads,
        intermediate_size=args.intermediate_size,
        max_position_embeddings=max(args.max_len + 8, 512),
        dropout=args.dropout,
    )
    model = TaggerModel(config).to(args.device)
    print(f"Model: {model.num_parameters_readable()} parameters on {args.device} "
          f"(use_macron_plane={args.use_macron_plane})")

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    total_steps = max(1, len(train_loader) * args.epochs)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=args.lr, total_steps=total_steps, pct_start=0.05
    )

    best_val_acc = -1.0
    evals_without_improvement = 0
    stop_early = False

    def run_eval(step_label):
        nonlocal best_val_acc, evals_without_improvement, stop_early
        metrics = evaluate(model, dev_loader, args.device)
        print(f"  [eval @ {step_label}] loss {metrics['loss']:.4f} "
              f"xpos_acc {metrics['xpos_accuracy']:.4%} lemma_acc {metrics['lemma_accuracy']:.4%} "
              f"combined {metrics['combined']:.4%} n={metrics['n_tokens']}")
        if metrics["combined"] > best_val_acc:
            best_val_acc = metrics["combined"]
            evals_without_improvement = 0
            model.save_pretrained(os.path.join(args.output_dir, "best"))
            print(f"  new best ({best_val_acc:.4%}), saved to {args.output_dir}/best")
        else:
            evals_without_improvement += 1
            if args.patience > 0 and evals_without_improvement >= args.patience:
                print(f"  no improvement for {evals_without_improvement} evals "
                      f"(patience={args.patience}) -- stopping early")
                stop_early = True

    step = 0
    t0 = time.time()
    for epoch in range(args.epochs):
        for batch in train_loader:
            batch = {k: (v.to(args.device) if torch.is_tensor(v) else v) for k, v in batch.items()}
            out = model(**batch)
            loss = out["loss"]
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            step += 1

            if step % args.log_every_steps == 0:
                elapsed = time.time() - t0
                print(f"epoch {epoch} step {step}/{total_steps} loss {loss.item():.4f} "
                      f"lr {scheduler.get_last_lr()[0]:.2e} ({elapsed:.0f}s)")

            if step % args.eval_every_steps == 0:
                run_eval(f"step {step}")
                if stop_early:
                    break
        if stop_early:
            break

        run_eval(f"epoch {epoch} end")
        if stop_early:
            break

    model.save_pretrained(os.path.join(args.output_dir, "final"))
    print(f"Done. Best val combined accuracy: {best_val_acc:.4%}. Final model saved to {args.output_dir}/final")


if __name__ == "__main__":
    main()
