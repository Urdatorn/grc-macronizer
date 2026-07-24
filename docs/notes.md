# NOTES

- Need a kind of ny-module which catches e.g. σατράπην or στρατηγὸν if σατράπη and στρατηγός is macronizable.

- i want stats (even a pie diagram) over which modules macronized how many dichrona and separate lists with these respective dichrona

- Possible next rule: 3rd-declension (consonant-stem) feminine accusative singular
  in bare -α, e.g. ἐλπίδα (ἐλπίς), ἀποφράδα (ἀποφράς), χάριτα (χάρις) -- should be
  short, same principle as the existing masc/neut rule in nominal_forms.py's
  masc_and_neutre_short_alpha, which currently excludes Fem gender. Confirmed
  high-frequency in OGA diagnostics (e.g. ἀποφράδα). NOT a safe drop-in
  extension though: bare final -α also occurs in 1st-declension (1D) feminine
  nominative/vocative singular, where length depends on the "pure vs impure
  alpha" distinction (Smyth 214-215) that first_declination()'s Ionic-counterpart
  heuristic only partially covers. Since 1D accusative singular always ends in
  -αν/-ην (never bare -α), a new rule gated on "lemma does NOT end in -α/-η"
  (to exclude 1D) should be safe from that particular conflict, but wants real
  odyCy-morphology validation across several lemmata before shipping, the same
  way macronize_ma_stem_neuters() was validated.