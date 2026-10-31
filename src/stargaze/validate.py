"""Validation layer (pipeline stage 1): physical-range check on PSF and model magnitudes.

Sentinels become NaN silently; other out-of-range values become NaN and flag `corrupted_input`.
Run add_colors afterwards so colors and PSF - model see the cleaned magnitudes.
"""

import pandas as pd

from stargaze.silver import SENTINEL

MAG_RANGE = (10.0, 30.0)  # roughly the physical range for SDSS (spec, ML pipeline)


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Return (df with bad magnitudes as NaN, per-row corrupted_input flag)."""
    df = df.copy()
    cols = [c for c in df if c.startswith(("psfMag_", "modelMag_"))]  # not the *MagErr_ columns
    mags = df[cols]
    sentinel = mags <= SENTINEL
    bad = mags.notna() & ~sentinel & ~mags.apply(lambda c: c.between(*MAG_RANGE))
    df[cols] = mags.mask(sentinel | bad)
    return df, bad.any(axis=1).rename("corrupted_input")
