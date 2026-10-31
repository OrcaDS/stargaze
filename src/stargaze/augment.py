"""Degrade photometry: noise scaled by real SDSS errors, band masking, out-of-range corruption.

Training augmentation runs on the train split only; val and test degraded
copies are generated separately with their own fixed seeds.
"""

import numpy as np
import pandas as pd

from stargaze.gold import MAGS as PSF
from stargaze.gold import MODEL_MAGS as MODEL
from stargaze.gold import add_colors
from stargaze.validate import validate

K, MULT, MASK_P, CORRUPT_P = 2, (1.0, 5.0), 0.15, 0.02  # spec: training-time augmentation


def degrade(
    df: pd.DataFrame, rng: np.random.Generator, mult, mask_p: float, corrupt_p: float = 0.0
) -> pd.DataFrame:
    """mult: noise multiplier on the real errors, a scalar or one value per row."""
    return add_colors(validate(perturb(df, rng, mult, mask_p, corrupt_p))[0])


def perturb(
    df: pd.DataFrame, rng: np.random.Generator, mult, mask_p: float, corrupt_p: float = 0.0
) -> pd.DataFrame:
    """degrade before validation: corrupted values are still in place (evaluation needs them)."""
    df = df.copy()
    n = len(df)
    mult = np.broadcast_to(np.asarray(mult, dtype=float), n)[:, None]
    for cols in (PSF, MODEL):
        # shortcut: PSF and model noise are drawn independently (no covariance in SDSS);
        # revisit if psf-model features look too noisy on degraded val.
        sigma = df[[c.replace("Mag_", "MagErr_") for c in cols]].fillna(0).to_numpy()
        df[cols] = df[cols].to_numpy() + rng.normal(size=(n, 5)) * sigma * mult
    # A masked band hides both its PSF and model mag.
    hide = rng.random((n, 5)) < mask_p
    df[PSF] = df[PSF].mask(hide)
    df[MODEL] = df[MODEL].mask(hide)
    # Corruption: one PSF band gets an impossible value, which validation turns into NaN.
    rows = np.flatnonzero(rng.random(n) < corrupt_p)
    bad = np.where(
        rng.random(len(rows)) < 0.5, rng.uniform(0, 10, len(rows)), rng.uniform(30, 50, len(rows))
    )
    psf = df[PSF].to_numpy()
    psf[rows, rng.integers(0, 5, len(rows))] = bad
    df[PSF] = psf
    return df


def mask(df: pd.DataFrame, hide: np.ndarray) -> pd.DataFrame:
    """hide: (rows, 5) bool. A masked band hides both its PSF and model mag."""
    df = df.copy()
    df[PSF] = df[PSF].mask(hide)
    df[MODEL] = df[MODEL].mask(hide)
    return add_colors(df)


def augment(train: pd.DataFrame, seed: int, k: int = K) -> pd.DataFrame:
    """Clean train rows plus k degraded copies of each."""
    rng = np.random.default_rng(seed)
    copies = [
        degrade(train, rng, rng.uniform(*MULT, len(train)), MASK_P, CORRUPT_P) for _ in range(k)
    ]
    return pd.concat([train, *copies], ignore_index=True)
