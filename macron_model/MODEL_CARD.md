---
language: grc
license: mit
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

Evaluated on [Norma Syllabarum Graecarum](https://github.com/Urdatorn/norma-syllabarum-graecarum),
a manually-annotated benchmark spanning 16 authors/works and both prose and verse.
See the accompanying paper for the comparison against the rule-based baseline.

## Usage

```python
from predict import MacronPredictor

predictor = MacronPredictor("path/to/checkpoint")
macronized = predictor.macronize("ανθρωπος ανηρ")
# -> "α^νθρωπος α^νηρ"
```

## Citation

If you use this model, please cite:

> Thörn Cleland, Albin and Eric Cullhed (forthcoming). Automatic Annotation of Ancient Greek Vowel Length.

## License

MIT, matching the underlying grc-macronizer training-data generator.
