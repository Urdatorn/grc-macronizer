---
language: grc
license: gpl-3.0
tags:
- ancient-greek
- vowel-length
- macronization
- token-classification
- char-level
---

# grc-macronizer-char: a small char-level model for Ancient Greek vowel-length annotation

This model predicts the phonemic length (long/short/undetermined) of the three
Ancient Greek "dichrona" -- alpha (α), iota (ι), and upsilon (υ) -- whose length
is not disambiguated by the standard Greek script. It was trained on Ancient
Greek text automatically macronized by the rule-based
[grc-macronizer](https://github.com/Urdatorn/grc-macronizer), applied to the
[Opera Graeca Adnotata](https://doi.org/10.5281/zenodo.14206061) corpus
(Celano 2024), and is intended as a complementary, corpus-general alternative
to that rule-based system.

## Architecture

A small transformer encoder (~0.9M parameters) operating over three character-level
"planes" per input position:

- **plane 1 (letter)**: which of the 24 Greek letters (final/medial sigma
  folded together), or space, or "other" (punctuation/digits/foreign chars)
- **plane 2 (diacritic)**: the combination of accent/breathing/diaeresis marks
  on that letter, if any (a small vocabulary fit from the training data)
- **target (macron)**: none / short / long -- predicted only at positions
  that are genuine ambiguous dichrona (diphthong members and circumflexed
  vowels are excluded, matching the rule-based system's own definition)

During training, the diacritic plane is randomly masked (accents stripped)
for a fraction of characters, so the model also learns to macronize
unaccented input.

## Training data

Training labels come directly from the rule-based macronizer's own output:
wherever it marks a dichronon (it does not guess -- see the
[macronizer paper](https://github.com/Urdatorn/grc-macronizer)), that becomes
a training label; dichrona it left unmarked are excluded from the loss
entirely (never treated as a negative "short" or "long" example), since the
rule-based system is known to be incomplete rather than wrong where it commits.

## Evaluation

Evaluated on [Norma Syllabarum Graecarum](https://huggingface.co/datasets/Urdatorn/norma),
a manually-annotated benchmark spanning 15 works (prose and verse; two further
works are held out of this HF version specifically to avoid overlap with a
separate training corpus). Scored with the identical harness
(`macron_model/eval_norma.py`) against the bundled rule-based macronizer,
counting a left-unmarked dichronon as an implicit "short" guess for both
systems (`default_short_accuracy` below) so abstention isn't unfairly
penalized either way:

| system | accuracy (unmarked defaults to short) | raw accuracy | unmarked / total |
|---|---|---|---|
| rule-based grc-macronizer | 89.46% | 57.57% | 769 / 1916 |
| **this model** | **90.66%** | **90.55%** | **6 / 1916** |

The model modestly outperforms the rule-based system on the fair metric while
resolving essentially every position (99.7% coverage vs. 60%), since it
learned to generalize past the cases the rule-based system couldn't commit to.

## Usage

```python
import sys
sys.path.insert(0, "path/to/grc-macronizer/macron_model")  # for predict.py
from predict import MacronPredictor

predictor = MacronPredictor("path/to/downloaded/checkpoint")
macronized = predictor.macronize("ανθρωπος ανηρ")
# -> "α^νθρωπος α_νηρ"
```

`MacronPredictor` expects the checkpoint directory (containing
`config.json`/`model.safetensors`) plus a sibling or parent `diacritic_vocab.json`
(see `predict.py` for the exact lookup logic). The `predict.py`/`tokenizer.py`
source lives in [grc-macronizer/macron_model](https://github.com/Urdatorn/grc-macronizer/tree/oga-macronization-improvements/macron_model).

## Citation

If you use this model, please cite:

> Thörn Cleland, Albin and Eric Cullhed (forthcoming). Automatic Annotation of Ancient Greek Vowel Length.

## License

GNU GPL v3, matching [grc-macronizer](https://github.com/Urdatorn/grc-macronizer)
(the training-data generator this model's code ships alongside).
