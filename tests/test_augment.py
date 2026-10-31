import numpy as np
import pandas as pd

from stargaze.augment import augment, degrade
from stargaze.gold import ERRS, FEATURES, MAGS, MODEL_MAGS, add_colors


def _gold(n: int) -> pd.DataFrame:
    df = pd.DataFrame({c: 18.0 for c in MAGS + MODEL_MAGS} | {e: 0.1 for e in ERRS}, index=range(n))
    df["class"], df["z"] = "STAR", 0.0
    return add_colors(df)


def test_degrade_noise_mask_corrupt():
    df = _gold(2000)
    rng = np.random.default_rng(0)
    # Noise only: spread matches error x multiplier, nothing masked.
    noisy = degrade(df, rng, 3.0, 0.0)
    assert abs(noisy["psfMag_r"].std() - 0.3) < 0.03 and noisy[MAGS].notna().all().all()
    assert noisy["u-g"].ne(0).all()  # colors recomputed from the noisy mags
    # Masking hides PSF and model of the same band together.
    masked = degrade(df, rng, 0.0, 0.5)
    for p, m in zip(MAGS, MODEL_MAGS, strict=True):
        assert masked[p].isna().equals(masked[m].isna())
    assert 0.45 < masked["psfMag_g"].isna().mean() < 0.55
    # Corrupted values never survive validation: every mag is NaN or in range.
    bad = degrade(df, rng, 0.0, 0.0, corrupt_p=1.0)
    assert (
        bad[MAGS].isna().sum(axis=1).eq(1).all()
        and bad[MAGS].stack().dropna().between(10, 30).all()
    )
    assert df.equals(_gold(2000))  # input untouched


def test_augment_keeps_clean_rows_and_adds_k_copies():
    df = _gold(100)
    out = augment(df, seed=0, k=2)
    assert len(out) == 300 and out.iloc[:100].equals(df)
    assert list(out.columns) == list(df.columns) and set(FEATURES) <= set(out)
