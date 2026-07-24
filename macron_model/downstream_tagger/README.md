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
