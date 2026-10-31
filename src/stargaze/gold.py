"""Gold layer: model-ready table. IDs dropped; redshift kept only for the upper-bound baseline.

Run: uv run python -m stargaze.gold   (after stargaze.silver)
"""

import pandas as pd

from stargaze.silver import OUT as SILVER
from stargaze.validate import validate

OUT = SILVER.parent / "gold"
BANDS = "ugriz"
MAGS = [f"psfMag_{b}" for b in BANDS]
COLORS = [f"{a}-{b}" for a, b in zip(BANDS, BANDS[1:], strict=False)]
# PSF - model is ~0 for point sources (stars, QSOs), > 0 for galaxies (docs/decisions/0002).
PSF_MODEL = [f"psf-model_{b}" for b in BANDS]
FEATURES = MAGS + COLORS + PSF_MODEL  # never add z or IDs here
MODEL_MAGS = [f"modelMag_{b}" for b in BANDS]
# For noise augmentation, not features.
ERRS = [f"psfMagErr_{b}" for b in BANDS] + [f"modelMagErr_{b}" for b in BANDS]
# Real errors reach ~1.8M mag; above 1 mag a band is effectively undetected anyway.
ERR_CAP = 1.0


def add_colors(df: pd.DataFrame) -> pd.DataFrame:
    """PSF colors u-g, g-r, r-i, i-z and PSF - model per band; NaN if an input is missing."""
    df = df.copy()
    for a, b in zip(BANDS, BANDS[1:], strict=False):
        df[f"{a}-{b}"] = df[f"psfMag_{a}"] - df[f"psfMag_{b}"]
    for b in BANDS:
        df[f"psf-model_{b}"] = df[f"psfMag_{b}"] - df[f"modelMag_{b}"]
    return df


def to_gold(df: pd.DataFrame) -> pd.DataFrame:
    df = add_colors(validate(df)[0])
    df[ERRS] = df[ERRS].clip(upper=ERR_CAP)
    return df[FEATURES + ERRS + MODEL_MAGS + ["class", "z"]]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("clean", "messy"):
        gold = to_gold(pd.read_parquet(SILVER / f"sdss_dr17_{name}.parquet"))
        gold.to_parquet(OUT / f"sdss_dr17_{name}.parquet", index=False)
        print(f"gold {name}: {len(gold):,} rows, {len(FEATURES)} features")


if __name__ == "__main__":
    main()
