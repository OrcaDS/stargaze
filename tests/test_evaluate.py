import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import f1_score

from stargaze.augment import mask, perturb
from stargaze.evaluate import (
    bootstrap,
    codes,
    corruption,
    macro_f1,
    met,
    noise_auc,
    random_bands,
)
from stargaze.gold import ERRS, FEATURES, MAGS, MODEL_MAGS, add_colors


def test_random_bands_masks_exactly_k_per_row():
    hide = random_bands(1000, 2, np.random.default_rng(0))
    assert (hide.sum(axis=1) == 2).all()
    assert hide.mean(axis=0).min() > 0.3  # every band gets picked, roughly 2/5 each


def test_mask_hides_psf_and_model_and_recomputes_colors():
    df = pd.DataFrame(20.0, index=range(2), columns=MAGS + MODEL_MAGS)
    hide = np.zeros((2, 5), dtype=bool)
    hide[0, 1] = True  # g band of row 0
    out = mask(df, hide)
    assert out.loc[0, ["psfMag_g", "modelMag_g", "u-g", "g-r", "psf-model_g"]].isna().all()
    assert out.loc[1].notna().all()


def test_macro_f1_matches_sklearn_including_a_never_predicted_class():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 3, 500)
    for pred in (rng.integers(0, 3, 500), np.where(y == 2, 0, y)):  # second: STAR never predicted
        assert abs(macro_f1(y, pred) - f1_score(y, pred, average="macro", zero_division=0)) < 1e-12


def test_bootstrap_interval_brackets_value_and_separates_a_real_difference():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 3, 300)
    noisy = np.where(rng.random(300) < 0.3, rng.integers(0, 3, 300), y)  # ~80% accurate

    def diff(i):
        return macro_f1(y[i], y[i]) - macro_f1(y[i], noisy[i])

    b = bootstrap(diff, 300, np.random.default_rng(2))
    lo, hi = b["ci95"]
    assert 0 < lo <= b["value"] <= hi < 0.5


def test_macro_f1_averages_over_all_three_classes_even_if_one_is_absent():
    y, pred = np.array([0, 0, 1, 1]), np.array([0, 1, 1, 1])  # STAR in neither
    expected = f1_score(y, pred, labels=[0, 1, 2], average="macro", zero_division=0)
    assert abs(macro_f1(y, pred) - expected) < 1e-12
    assert abs(macro_f1(y, pred) - (2 / 3 + 0.8) / 3) < 1e-12  # by hand: F1 = 2/3, 4/5, 0


def test_bootstrap_rejects_non_finite_statistic():
    y = np.array([0] * 10 + [1])  # most resamples miss the single class-1 row
    with pytest.raises(ValueError):
        bootstrap(lambda i: (y[i] == 1).sum() / (y[i] == 1).sum(), 11, np.random.default_rng(0))


def test_codes_maps_classes_and_rejects_abstain_labels():
    assert codes(["GALAXY", "QSO", "STAR"]).tolist() == [0, 1, 2]
    with pytest.raises(ValueError):
        codes(["QSO", "uncertain"])


def test_noise_auc_is_mean_f1_over_the_range():
    assert noise_auc([1.0] * 6) == 1.0
    # F1 = 1 only at 8x: area of the last trapezoid, (8 - 5) * 1 / 2, over the width 8.
    assert noise_auc([0, 0, 0, 0, 0, 1]) == 1.5 / 8


def test_met_needs_the_whole_interval_on_the_right_side():
    assert met("<=", 0.07, [0.06, 0.07]) and not met("<=", 0.07, [0.06, 0.071])
    assert met(">=", 0.85, [0.85, 0.9]) and not met(">=", 0.85, [0.849, 0.9])
    assert met(">", 0.0, [0.001, 0.1]) and not met(">", 0.0, [0.0, 0.1])


class _Trust:
    """Always answers GALAXY with confidence 1, never an outlier."""

    classes_ = np.array(["GALAXY", "QSO", "STAR"])

    def predict_proba(self, X):
        return np.tile([1.0, 0.0, 0.0], (len(X), 1))

    def score_samples(self, X):
        return np.zeros(len(X))


def test_corruption_counts_injected_rows_and_validation_flags_all_of_them():
    df = pd.DataFrame(20.0, index=range(400), columns=MAGS + MODEL_MAGS)
    df[ERRS] = 0.1
    df.loc[:9, "psfMag_u"] = np.nan  # already missing: an injection here must still count
    df = add_colors(df)
    raw = perturb(df, np.random.default_rng(0), 0, 0, 0.3)
    trust = {"cal": _Trust(), "iso": _Trust(), "tau": 0.5, "cutoff": -1.0, "blocked": []}
    r = corruption(trust, df, raw)
    assert 0.2 < r["injected_share"] < 0.4
    assert r["flagged_share_of_injected"] == 1.0 and r["flagged_share_of_others"] == 0.0
    assert r["abstained_on_injected"] == 0.0  # this stub never abstains
    assert set(FEATURES) <= set(raw.columns)
