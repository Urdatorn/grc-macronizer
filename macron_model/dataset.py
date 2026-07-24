'''
Dataset/collation for the macron-tagging model.

Training data is just macronized Ancient Greek sentences -- either one per line, or a
grc_macronizer-style TSV where column 2 is the macronized version (column 1, the plain
form, is ignored: it's redundant with the macronized column since stripping ^/_ recovers it).
'''

import glob
import random
from multiprocessing import Pool

import torch
from torch.utils.data import Dataset

from tokenizer import (
    DiacriticVocab,
    encode_macronized,
    mask_diacritics,
    PLANE1_STOI,
    LABEL_IGNORE_INDEX,
)

PAD_ID = 0

_pool_vocab = None
_pool_max_len = None


def _pool_init(vocab, max_len):
    global _pool_vocab, _pool_max_len
    _pool_vocab = vocab
    _pool_max_len = max_len


def _encode_one_line(line):
    '''Top-level (picklable) worker fn for parallel dataset construction.
    Returns a list of chunk dicts (usually 0 or 1, >1 only for lines longer
    than max_len) -- same logic as the sequential path in MacronDataset.'''
    enc = encode_macronized(line, _pool_vocab, fit=False)
    if not enc["plane1"]:
        return []
    if all(l == LABEL_IGNORE_INDEX for l in enc["labels"]):
        return []
    chunks = []
    for start in range(0, len(enc["plane1"]), _pool_max_len):
        chunk = {k: v[start:start + _pool_max_len] for k, v in enc.items()}
        if any(l != LABEL_IGNORE_INDEX for l in chunk["labels"]):
            chunks.append(chunk)
    return chunks


def iter_macronized_lines(path_or_glob):
    paths = sorted(glob.glob(path_or_glob)) if any(ch in path_or_glob for ch in "*?[") else [path_or_glob]
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line.strip():
                    continue
                if "\t" in line:
                    parts = line.split("\t")
                    line = parts[1] if len(parts) > 1 else parts[0]
                yield line


def build_vocab(lines, max_lines_for_fit=None):
    vocab = DiacriticVocab()
    for i, line in enumerate(lines):
        if max_lines_for_fit is not None and i >= max_lines_for_fit:
            break
        encode_macronized(line, vocab, fit=True)
    vocab.freeze()
    return vocab


class MacronDataset(Dataset):
    def __init__(self, lines, diacritic_vocab, max_len=384, diacritic_mask_p=0.0,
                 training=True, num_workers=0):
        self.vocab = diacritic_vocab
        self.max_len = max_len
        self.diacritic_mask_p = diacritic_mask_p
        self.training = training
        self.examples = []

        if num_workers and len(lines) > 10_000:
            with Pool(num_workers, initializer=_pool_init, initargs=(diacritic_vocab, max_len)) as pool:
                for chunks in pool.imap(_encode_one_line, lines, chunksize=2000):
                    self.examples.extend(chunks)
        else:
            for line in lines:
                enc = encode_macronized(line, diacritic_vocab, fit=False)
                if not enc["plane1"]:
                    continue
                if all(l == LABEL_IGNORE_INDEX for l in enc["labels"]):
                    continue  # no supervision signal at all in this line -- skip
                for start in range(0, len(enc["plane1"]), max_len):
                    chunk = {k: v[start:start + max_len] for k, v in enc.items()}
                    if any(l != LABEL_IGNORE_INDEX for l in chunk["labels"]):
                        self.examples.append(chunk)

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex = self.examples[idx]
        plane2 = ex["plane2"]
        if self.training and self.diacritic_mask_p > 0:
            plane2 = mask_diacritics(plane2, none_id=self.vocab.NONE, p=self.diacritic_mask_p)
        return {
            "plane1": ex["plane1"],
            "plane2": plane2,
            "labels": ex["labels"],
        }


def collate_fn(batch):
    max_len = max(len(ex["plane1"]) for ex in batch)
    plane1 = torch.full((len(batch), max_len), PAD_ID, dtype=torch.long)
    plane2 = torch.full((len(batch), max_len), PAD_ID, dtype=torch.long)
    labels = torch.full((len(batch), max_len), LABEL_IGNORE_INDEX, dtype=torch.long)
    attention_mask = torch.zeros((len(batch), max_len), dtype=torch.long)

    for i, ex in enumerate(batch):
        n = len(ex["plane1"])
        plane1[i, :n] = torch.tensor(ex["plane1"], dtype=torch.long)
        plane2[i, :n] = torch.tensor(ex["plane2"], dtype=torch.long)
        labels[i, :n] = torch.tensor(ex["labels"], dtype=torch.long)
        attention_mask[i, :n] = 1

    return {
        "plane1_ids": plane1,
        "plane2_ids": plane2,
        "attention_mask": attention_mask,
        "labels": labels,
    }


def train_val_split(lines, val_fraction=0.02, seed=13):
    lines = list(lines)
    rng = random.Random(seed)
    idx = list(range(len(lines)))
    rng.shuffle(idx)
    n_val = max(1, int(len(idx) * val_fraction))
    val_idx = set(idx[:n_val])
    train_lines = [l for i, l in enumerate(lines) if i not in val_idx]
    val_lines = [l for i, l in enumerate(lines) if i in val_idx]
    return train_lines, val_lines


if __name__ == "__main__":
    import sys
    lines = list(iter_macronized_lines(sys.argv[1] if len(sys.argv) > 1 else "diagnostic_output.txt"))
    print(f"{len(lines)} lines")
    vocab = build_vocab(lines)
    print(f"diacritic vocab size: {len(vocab)}")
    train_lines, val_lines = train_val_split(lines)
    ds = MacronDataset(train_lines, vocab, diacritic_mask_p=0.3, training=True)
    print(f"{len(ds)} training examples (chunks)")
    from torch.utils.data import DataLoader
    dl = DataLoader(ds, batch_size=4, shuffle=True, collate_fn=collate_fn)
    batch = next(iter(dl))
    for k, v in batch.items():
        print(k, v.shape, v.dtype)
