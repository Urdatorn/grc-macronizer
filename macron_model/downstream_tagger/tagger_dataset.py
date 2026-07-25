'''
Dataset/collation for the downstream tagger ablation. Reads CoNLL-U (AGDT
scheme), builds per-sentence char sequences via tagger_tokenizer.encode_sentence
plus per-token XPOS/lemma-edit-script labels.

The plain-text file (data/train0.conllu) and its macronized counterpart
(data/train0.macronized.conllu, produced by macronize_conllu.py) have identical
LEMMA/XPOS columns -- only FORM differs -- so both ablation arms train on the
same sentences/labels, differing only in which file's FORM column (and hence
whether plane3 carries real macron predictions or stays all-MACRON_NONE) feeds
the model.
'''

import sys

import torch
from torch.utils.data import Dataset

sys.path.insert(0, "..")  # macron_model/ for tokenizer.py
from tokenizer import DiacriticVocab, encode_plain, LABEL_IGNORE_INDEX  # noqa: E402

from tagger_tokenizer import encode_sentence
from edit_script import EditScriptVocab, compute_edit_script
from conllu_io import iter_sentences, FORM, LEMMA, XPOS

PAD_ID = 0


class ClosedVocab:
    '''Generic closed-set vocab (used for XPOS tags -- the AGDT tag string is
    already a closed set, no decomposition needed).'''

    PAD, UNK = 0, 1

    def __init__(self, unk_token="<unk>"):
        self.itos = ["<pad>", unk_token]
        self.stoi = {"<pad>": self.PAD, unk_token: self.UNK}
        self.frozen = False

    def fit(self, items):
        for it in items:
            self._get_or_add(it)

    def freeze(self):
        self.frozen = True

    def _get_or_add(self, item):
        if item in self.stoi:
            return self.stoi[item]
        if self.frozen:
            return self.UNK
        idx = len(self.itos)
        self.itos.append(item)
        self.stoi[item] = idx
        return idx

    def encode(self, item):
        return self.stoi.get(item, self.UNK)

    def decode(self, idx):
        return self.itos[idx]

    def __len__(self):
        return len(self.itos)

    def to_dict(self):
        return {"itos": self.itos}

    @classmethod
    def from_dict(cls, d):
        v = cls()
        v.itos = list(d["itos"])
        v.stoi = {s: i for i, s in enumerate(v.itos)}
        v.frozen = True
        return v


def load_sentences(path):
    '''Returns list of (forms, lemmas, xpos_tags) per sentence.'''
    out = []
    for _, tokens in iter_sentences(path):
        forms = [row[FORM] for row in tokens]
        lemmas = [row[LEMMA] for row in tokens]
        xpos_tags = [row[XPOS] for row in tokens]
        out.append((forms, lemmas, xpos_tags))
    return out


def build_vocabs(train_sentences):
    '''Fit diacritic/xpos/lemma-script vocabs on the training split only.
    Works the same whether `train_sentences` came from the plain or macronized
    file: the diacritic plane only encodes accent/breathing/diaeresis, which is
    identical in both (macron ^/_ marks are parsed out separately, see
    tokenizer.encode_macronized), and LEMMA/XPOS columns never change.'''
    diacritic_vocab = DiacriticVocab()
    xpos_vocab = ClosedVocab()
    lemma_vocab = EditScriptVocab()

    for forms, lemmas, xpos_tags in train_sentences:
        for form in forms:
            encode_plain(form, diacritic_vocab, fit=True)
        for tag in xpos_tags:
            xpos_vocab._get_or_add(tag)
        for form, lemma in zip(forms, lemmas):
            lemma_vocab._get_or_add(compute_edit_script(form, lemma))

    diacritic_vocab.freeze()
    xpos_vocab.freeze()
    lemma_vocab.freeze()
    return diacritic_vocab, xpos_vocab, lemma_vocab


class TaggerDataset(Dataset):
    def __init__(self, sentences, diacritic_vocab, xpos_vocab, lemma_vocab,
                 macronized=False, max_len=384):
        self.examples = []
        n_dropped = 0
        for forms, lemmas, xpos_tags in sentences:
            enc = encode_sentence(forms, diacritic_vocab, macronized=macronized, fit=False)
            if len(enc["plane1"]) > max_len:
                n_dropped += 1
                continue  # rare over-length sentence -- drop rather than truncate mid-token
            xpos_ids = [xpos_vocab.encode(t) for t in xpos_tags]
            lemma_ids = [lemma_vocab.encode(compute_edit_script(f, lm)) for f, lm in zip(forms, lemmas)]
            self.examples.append({
                "plane1": enc["plane1"],
                "plane2": enc["plane2"],
                "plane3": enc["plane3"],
                "spans": enc["spans"],
                "xpos_labels": xpos_ids,
                "lemma_labels": lemma_ids,
            })
        if n_dropped:
            print(f"  dropped {n_dropped} sentences longer than max_len={max_len} chars")

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        return self.examples[idx]


def make_collate_fn(use_macron_plane, macron_plane_mode="real"):
    '''macron_plane_mode (only matters when use_macron_plane=True):
      - "real": plane3 carries the transformer's actual macron predictions (default)
      - "random": plane3 is independently randomized (uniform over none/short/long)
        at every real character position -- same architecture, same parameter count,
        zero mutual information with true macron status. Confound control for
        "is the gain from the extra capacity, or from the macron information?"
      - "constant": plane3 is always MACRON_NONE (id 0) at every real position --
        the weaker of the two controls suggested in review (the embedding row can
        still be learned as a bias, but carries no per-position information at all).
    '''
    assert macron_plane_mode in ("real", "random", "constant")

    def collate_fn(batch):
        max_len = max(len(ex["plane1"]) for ex in batch)
        max_tokens = max(len(ex["spans"]) for ex in batch)
        bsz = len(batch)

        plane1 = torch.full((bsz, max_len), PAD_ID, dtype=torch.long)
        plane2 = torch.full((bsz, max_len), PAD_ID, dtype=torch.long)
        plane3 = torch.full((bsz, max_len), PAD_ID, dtype=torch.long) if use_macron_plane else None
        attention_mask = torch.zeros((bsz, max_len), dtype=torch.long)
        # trash bucket = max_tokens, for separator/padding char positions (belong to no token)
        token_id_per_char = torch.full((bsz, max_len), max_tokens, dtype=torch.long)
        xpos_labels = torch.full((bsz, max_tokens), LABEL_IGNORE_INDEX, dtype=torch.long)
        lemma_labels = torch.full((bsz, max_tokens), LABEL_IGNORE_INDEX, dtype=torch.long)

        for i, ex in enumerate(batch):
            n = len(ex["plane1"])
            plane1[i, :n] = torch.tensor(ex["plane1"], dtype=torch.long)
            plane2[i, :n] = torch.tensor(ex["plane2"], dtype=torch.long)
            if use_macron_plane:
                plane3[i, :n] = torch.tensor(ex["plane3"], dtype=torch.long)
            attention_mask[i, :n] = 1

            for t, (start, end) in enumerate(ex["spans"]):
                token_id_per_char[i, start:end] = t
            nt = len(ex["spans"])
            xpos_labels[i, :nt] = torch.tensor(ex["xpos_labels"], dtype=torch.long)
            lemma_labels[i, :nt] = torch.tensor(ex["lemma_labels"], dtype=torch.long)

        if use_macron_plane and macron_plane_mode == "random":
            real_positions = attention_mask.bool()
            plane3[real_positions] = torch.randint(0, 3, (int(real_positions.sum()),))
        elif use_macron_plane and macron_plane_mode == "constant":
            plane3[attention_mask.bool()] = 0

        out = {
            "plane1_ids": plane1,
            "plane2_ids": plane2,
            "attention_mask": attention_mask,
            "token_id_per_char": token_id_per_char,
            "num_tokens": max_tokens,
            "xpos_labels": xpos_labels,
            "lemma_labels": lemma_labels,
        }
        if use_macron_plane:
            out["plane3_ids"] = plane3
        return out

    return collate_fn


if __name__ == "__main__":
    sents = load_sentences(sys.argv[1] if len(sys.argv) > 1 else "data/dev0.conllu")
    print(f"{len(sents)} sentences")
    dvocab, xvocab, lvocab = build_vocabs(sents[:2000])
    print(f"diacritic vocab: {len(dvocab)}, xpos vocab: {len(xvocab)}, lemma-script vocab: {len(lvocab)}")
    ds = TaggerDataset(sents[:2000], dvocab, xvocab, lvocab, macronized=False)
    print(f"{len(ds)} examples")
    from torch.utils.data import DataLoader
    dl = DataLoader(ds, batch_size=4, shuffle=True, collate_fn=make_collate_fn(use_macron_plane=False))
    batch = next(iter(dl))
    for k, v in batch.items():
        print(k, v.shape if torch.is_tensor(v) else v, v.dtype if torch.is_tensor(v) else "")
