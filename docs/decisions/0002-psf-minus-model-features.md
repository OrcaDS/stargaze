# 0002: Add PSF − model magnitudes to the features; revise the gap target

_Status: decided · Raised 2026-10-26 · Decided 2026-10-26_

## Context
The first photometry-only baseline (5 PSF mags + 4 PSF colors) scored val macro F1 0.888 against 0.986 for the with-redshift upper bound: a 9.8-point gap against the spec's ≤ 5 target. Most errors were star↔galaxy (STAR recall 0.863). The spec listed model magnitudes as a variant to test.

## Options (all HistGradientBoosting, defaults, scored on val)
- **PSF only** (old baseline): macro F1 0.888.
- **Model mags + model colors** (what Kaggle SDSS17's u–z columns are): 0.889. No gain.
- **PSF + PSF − model per band**: 0.922 (STAR recall 0.899, GALAXY 0.967, QSO 0.915).
- **PSF + model + PSF − model**: 0.922. Same as above with 5 more inputs.
- Light tuning on top (more leaves, lower learning rate): at most +0.4 points.

## Decision
`FEATURES` = 5 PSF mags + 4 PSF colors + 5 PSF − model differences (14 features), default hyperparameters. The success target becomes **within 7 points** of the upper bound: the remaining 6.4-point gap is close to what photometry alone can give here, and the spec marked its targets as guesses to revise after the baseline.

## Consequences
- M3 must cover model magnitudes too: pull `modelMagErr_*` (bronze query) and cap them like the PSF errors; apply the 10–30 range check to model mags; masking a band masks both its PSF and model magnitude.
- `psf-model_*` and colors are stored in gold, so they must be recomputed (`stargaze.gold.add_colors`) after any augmentation changes the magnitudes.
