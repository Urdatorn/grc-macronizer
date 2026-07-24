'''
Training loop for the char-level macron-tagging model.

Usage:
    python train.py --data '/path/to/macronized_oga/*.tsv' --output_dir runs/v1

Submit via Slurm, e.g.:
    sbatch -A <account> -p cpu -c 16 --mem=64G -t 12:00:00 --wrap "source .venv/bin/activate && python train.py --data ... --output_dir ..."
'''

import argparse
import json
import math
import os
import random
import time

import torch
from torch.utils.data import DataLoader

from dataset import build_vocab, collate_fn, iter_macronized_lines, MacronDataset, train_val_split
from model import MacronizerConfig, MacronizerModel
from tokenizer import MACRON_LABEL_NAMES, LABEL_IGNORE_INDEX


def evaluate(model, loader, device):
    model.eval()
    total_loss, total_correct, total_count = 0.0, 0, 0
    per_class_correct = [0, 0, 0]
    per_class_total = [0, 0, 0]
    n_batches = 0
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            out = model(**batch)
            total_loss += out.loss.item()
            n_batches += 1
            preds = out.logits.argmax(-1)
            labels = batch["labels"]
            mask = labels != LABEL_IGNORE_INDEX
            total_correct += (preds[mask] == labels[mask]).sum().item()
            total_count += mask.sum().item()
            for c in range(3):
                cmask = mask & (labels == c)
                per_class_total[c] += cmask.sum().item()
                per_class_correct[c] += (preds[cmask] == labels[cmask]).sum().item()
    model.train()
    acc = total_correct / total_count if total_count else 0.0
    per_class_acc = [
        (per_class_correct[c] / per_class_total[c] if per_class_total[c] else None)
        for c in range(3)
    ]
    return {
        "loss": total_loss / max(n_batches, 1),
        "accuracy": acc,
        "n_positions": total_count,
        "per_class_accuracy": dict(zip(MACRON_LABEL_NAMES, per_class_acc)),
        "per_class_n": dict(zip(MACRON_LABEL_NAMES, per_class_total)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="Glob or path to macronized sentence file(s)/TSV(s)")
    ap.add_argument("--output_dir", required=True)
    ap.add_argument("--max_lines", type=int, default=None,
                     help="Randomly subsample to this many lines before splitting -- CPU training "
                          "throughput is ~8ms/example for this model, so the full multi-million-line "
                          "corpus is unnecessary; a few hundred thousand lines is plenty for a model "
                          "this size and keeps wall-clock reasonable.")
    ap.add_argument("--max_len", type=int, default=384)
    ap.add_argument("--batch_size", type=int, default=64)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--weight_decay", type=float, default=0.01)
    ap.add_argument("--diacritic_mask_p", type=float, default=0.3,
                     help="Probability of stripping a character's diacritics during training, "
                          "so the model also learns to macronize unaccented input.")
    ap.add_argument("--val_fraction", type=float, default=0.10)
    ap.add_argument("--hidden_size", type=int, default=128)
    ap.add_argument("--num_hidden_layers", type=int, default=4)
    ap.add_argument("--num_attention_heads", type=int, default=4)
    ap.add_argument("--intermediate_size", type=int, default=512)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--eval_every_steps", type=int, default=1000)
    ap.add_argument("--log_every_steps", type=int, default=100)
    ap.add_argument("--patience", type=int, default=5,
                     help="Stop after this many consecutive evals with no improvement in val "
                          "accuracy over the best-so-far. Set to 0 to disable early stopping.")
    ap.add_argument("--num_workers", type=int, default=4)
    ap.add_argument("--encode_workers", type=int, default=8,
                     help="parallel workers for the one-off dataset-encoding pass")
    ap.add_argument("--vocab_fit_lines", type=int, default=200_000,
                     help="diacritic vocab is a small closed set -- fitting on a sample is enough")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--num_threads", type=int, default=4,
                     help="torch intra-op thread cap -- avoids oversubscribing shared/busy nodes")
    args = ap.parse_args()

    torch.set_num_threads(args.num_threads)
    torch.manual_seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Loading data from {args.data} ...")
    lines = list(iter_macronized_lines(args.data))
    print(f"{len(lines)} lines loaded")

    if args.max_lines is not None and len(lines) > args.max_lines:
        rng = random.Random(args.seed)
        lines = rng.sample(lines, args.max_lines)
        print(f"Subsampled to {len(lines)} lines")

    print(f"Fitting diacritic vocab (sample of up to {args.vocab_fit_lines} lines) ...")
    vocab = build_vocab(lines, max_lines_for_fit=args.vocab_fit_lines)
    print(f"diacritic vocab size: {len(vocab)}")
    with open(os.path.join(args.output_dir, "diacritic_vocab.json"), "w", encoding="utf-8") as f:
        json.dump(vocab.to_dict(), f, ensure_ascii=False, indent=2)

    train_lines, val_lines = train_val_split(lines, val_fraction=args.val_fraction, seed=args.seed)
    print(f"train lines: {len(train_lines)}, val lines: {len(val_lines)}")

    print(f"Encoding dataset ({args.encode_workers} workers) ...")
    train_ds = MacronDataset(train_lines, vocab, max_len=args.max_len,
                              diacritic_mask_p=args.diacritic_mask_p, training=True,
                              num_workers=args.encode_workers)
    val_ds = MacronDataset(val_lines, vocab, max_len=args.max_len, diacritic_mask_p=0.0,
                            training=False, num_workers=args.encode_workers)
    print(f"train examples: {len(train_ds)}, val examples: {len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                               collate_fn=collate_fn, num_workers=args.num_workers, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False,
                             collate_fn=collate_fn, num_workers=args.num_workers)

    config = MacronizerConfig(
        plane2_vocab_size=len(vocab),
        hidden_size=args.hidden_size,
        num_hidden_layers=args.num_hidden_layers,
        num_attention_heads=args.num_attention_heads,
        intermediate_size=args.intermediate_size,
        max_position_embeddings=max(args.max_len + 8, 512),
        dropout=args.dropout,
    )
    model = MacronizerModel(config).to(args.device)
    print(f"Model: {model.num_parameters_readable()} parameters on {args.device}")

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
        metrics = evaluate(model, val_loader, args.device)
        print(f"  [eval @ {step_label}] loss {metrics['loss']:.4f} acc {metrics['accuracy']:.4%} "
              f"per_class {metrics['per_class_accuracy']} n={metrics['per_class_n']}")
        if metrics["accuracy"] > best_val_acc:
            best_val_acc = metrics["accuracy"]
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
            batch = {k: v.to(args.device) for k, v in batch.items()}
            out = model(**batch)
            loss = out.loss
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
    print(f"Done. Best val accuracy: {best_val_acc:.4%}. Final model saved to {args.output_dir}/final")


if __name__ == "__main__":
    main()
