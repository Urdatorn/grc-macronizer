# Downstream tagger ablation

Tests RQ3 from the paper: does adding macron information as an input feature
improve a lemma/XPOS tagger, all else held equal?

## Data

`data/train0.conllu`, `data/dev0.conllu`, `data/test.conllu` are a manually
annotated (gold) morphosyntactic treebank for Ancient Greek, developed by
Giuseppe Celano for training/evaluating his own OGA parser
(https://git.informatik.uni-leipzig.de/celano/morphosyntactic_parser_for_oga,
see also Celano 2024, arXiv:2410.12055). AGDT-style annotation: single-letter
POS, 9-slot positional XPOS, pipe-separated FEATS -- the same scheme
`grc_macronizer/oga_conllu.py` already parses for OGA.

Some documents overlap with OGA's source collections (First1KGreek,
PatristicTextArchive, Perseus canonical-greekLit), so this is not a
zero-shot generalization test. That doesn't invalidate the ablation itself:
both the with-macron and without-macron tagger see identical macronizer
output either way, so the *comparison* between them is still fair -- it only
means any observed benefit shouldn't be read as a claim about unseen text.

## Method

1. Macronize the FORM column of all three splits with our trained
   transformer (`Ericu950/oga-macronizer-char`).
2. Train two taggers to convergence, identical in every respect except
   input: one sees plain text, the other sees macronized text via an extra
   embedding plane. Both predict XPOS (closed-set classification over the
   AGDT tag string) and lemma (via edit-script classification).
3. Compare tagging accuracy on the (untouched) test split.

The macron plane is derived from `tokenizer.encode_macronized`'s own label
convention: at a genuinely ambiguous dichronon our transformer marked, the
plane carries short/long; everywhere else (non-dichrona, or a dichronon our
model abstained on) it carries `none` -- so "no macron plane" and "macron
plane, always none" are exactly the same input, and the only thing that can
possibly help the ablation arm is a *real* long/short prediction.

## Usage on the cluster

```bash
source .venv/bin/activate
cd macron_model/downstream_tagger

# 1. Macronize all three splits (GPU recommended, CPU works too)
for split in train0 dev0 test; do
    python macronize_conllu.py --input data/$split.conllu \
        --output data/$split.macronized.conllu --device cuda
done

# 2. Train both arms to convergence -- run order doesn't matter, the first
#    run builds runs/vocabs/, the second reuses it (see README "Method" above
#    for why sharing vocabs across arms is required for a fair comparison).
CUDA_VISIBLE_DEVICES=0 python train_tagger.py \
    --train_conllu data/train0.conllu --dev_conllu data/dev0.conllu \
    --vocab_dir runs/vocabs --output_dir runs/no_macron \
    --epochs 30 --patience 8 --device cuda

CUDA_VISIBLE_DEVICES=0 python train_tagger.py \
    --train_conllu data/train0.macronized.conllu --dev_conllu data/dev0.macronized.conllu \
    --vocab_dir runs/vocabs --output_dir runs/with_macron --use_macron_plane \
    --epochs 30 --patience 8 --device cuda

# 3. Score both on the held-out test split
python evaluate_test.py --checkpoint runs/no_macron/best --vocab_dir runs/vocabs \
    --test_conllu data/test.conllu
python evaluate_test.py --checkpoint runs/with_macron/best --vocab_dir runs/vocabs \
    --test_conllu data/test.macronized.conllu --use_macron_plane
```

On the login node (no Slurm GPU allocation held), set `CUDA_VISIBLE_DEVICES=""`
even for `--device cpu` runs -- torch's AdamW probes the CUDA device on
`.step()` regardless, and the login node's GPU is in "prohibited" compute mode
outside a job allocation, so it errors rather than silently falling back.
