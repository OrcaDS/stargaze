import numpy as np
import pandas as pd

from stargaze.gold import ERRS, FEATURES, MAGS, MODEL_MAGS, add_colors
from stargaze.trust import bands_present, blocked_patterns, ece, predict


class _Stub:
    """Stands in for the calibrated model and the outlier detector."""

    classes_ = np.array(["GALAXY", "QSO", "STAR"])

    def predict_proba(self, X):
        return np.array([[0.9, 0.05, 0.05], [0.4, 0.35, 0.25], [0.1, 0.1, 0.8]])

    def score_samples(self, X):
        return np.array([0.0, 0.0, -1.0])


def test_predict_abstains_below_tau_and_flags_outliers():
    df = pd.DataFrame(0.0, index=range(3), columns=FEATURES)
    trust = {"cal": _Stub(), "iso": _Stub(), "tau": 0.5, "cutoff": -0.5, "blocked": []}
    assert predict(trust, df)["label"].tolist() == ["GALAXY", "uncertain", "unusual_input"]


def test_ece():
    conf = np.array([0.9] * 10 + [0.6] * 10)
    assert ece(conf, np.array([1] * 9 + [0] + [1] * 6 + [0] * 4)) < 1e-9  # calibrated
    assert abs(ece(np.full(10, 0.9), np.zeros(10)) - 0.9) < 1e-9  # always wrong


def test_bands_present_bitmask():
    df = pd.DataFrame(20.0, index=range(2), columns=MAGS)
    df.loc[1, ["psfMag_g", "psfMag_z"]] = np.nan  # bits 1 and 4 cleared
    assert bands_present(df).tolist() == [0b11111, 0b01101]


class _NeedsG:
    """Right (GALAXY, conf 0.9) when the g band is present, wrong (QSO, conf 0.9) without it."""

    classes_ = np.array(["GALAXY", "QSO", "STAR"])

    def predict_proba(self, X):
        g = X["psfMag_g"].notna().to_numpy()[:, None]
        return np.where(g, [0.9, 0.05, 0.05], [0.05, 0.9, 0.05])


def test_blocked_patterns_are_exactly_those_missing_the_needed_band():
    val = pd.DataFrame(20.0, index=range(20), columns=MAGS + MODEL_MAGS)
    val[ERRS] = 0.1
    val = add_colors(val).assign(**{"class": "GALAXY"})
    blocked = blocked_patterns(_NeedsG(), 0.5, val)
    assert blocked == [p for p in range(32) if not p & 0b10]  # g is bit 1


def test_predict_answers_uncertain_for_a_blocked_band_pattern():
    class _Sure(_Stub):
        def predict_proba(self, X):
            return np.tile([0.9, 0.05, 0.05], (len(X), 1))

        def score_samples(self, X):
            return np.zeros(len(X))

    df = pd.DataFrame(20.0, index=range(2), columns=MAGS + MODEL_MAGS)
    df.loc[0, MAGS[1:]] = np.nan  # row 0: u band only (pattern 1)
    df = add_colors(df)
    trust = {"cal": _Sure(), "iso": _Sure(), "tau": 0.5, "cutoff": -1.0, "blocked": [0, 1]}
    assert predict(trust, df)["label"].tolist() == ["uncertain", "GALAXY"]
