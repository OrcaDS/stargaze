"""Trust layer (pipeline stages 3 and 5): outlier check, calibration, abstention.

Run: uv run python -m stargaze.trust   (after stargaze.train)
Calibration fits on the early-stopping rows (held out of training); tau and the outlier cutoff
are tuned on val only; the test split is never read.
"""

import json

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import IsolationForest
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import f1_score

from stargaze.augment import augment, mask
from stargaze.gold import FEATURES
from stargaze.gold import MAGS as PSF
from stargaze.split import OUT as SPLITS
from stargaze.split import SEED
from stargaze.train import CLASSES, OUT, degraded_val, split_stop

ABSTAIN_RATE = 0.05  # share of clean val answered "uncertain" (spec: about 5-10%)
OUTLIER_RATE = 0.01  # share of clean val flagged unusual_input
# A pattern of available bands whose answered rows are right less often than this on val is
# answered "uncertain" (the u band alone: confident and mostly wrong).
MIN_PATTERN_ACC = 0.80
ABSTAIN = ("uncertain", "unusual_input")


def bands_present(df: pd.DataFrame) -> np.ndarray:
    """Per row, which PSF bands have a value, as a bitmask: bit i set = band i of ugriz present."""
    return df[PSF].notna().to_numpy() @ (1 << np.arange(5))


def blocked_patterns(cal, tau: float, val: pd.DataFrame) -> list[int]:
    """Band patterns (bitmasks) to answer "uncertain", tuned on val.

    Each of the 32 patterns is scored by hiding its missing bands on every val row. A pattern is
    blocked when, among rows the confidence rule answers (conf >= tau), the share predicted right
    is below MIN_PATTERN_ACC, or when it answers no row at all. No bands (0) is always blocked.
    """
    blocked = []
    for pattern in range(32):
        present = (pattern >> np.arange(5)) & 1 == 1
        d = mask(val, np.tile(~present, (len(val), 1)))
        proba = cal.predict_proba(d[FEATURES])
        answered = proba.max(axis=1) >= tau
        right = cal.classes_[proba.argmax(axis=1)] == d["class"].to_numpy()
        if pattern == 0 or not answered.any() or right[answered].mean() < MIN_PATTERN_ACC:
            blocked.append(pattern)
    return blocked


def fit_trust(model, train: pd.DataFrame, stop: pd.DataFrame, val: pd.DataFrame) -> dict:
    # Calibrate on held-out rows plus degraded copies: the mix the robust model is used on.
    cal_rows = augment(stop, SEED + 2)
    cal = CalibratedClassifierCV(FrozenEstimator(model), method="temperature")
    cal.fit(cal_rows[FEATURES], cal_rows["class"])
    iso = IsolationForest(random_state=SEED).fit(train[FEATURES])
    tau = float(np.quantile(cal.predict_proba(val[FEATURES]).max(axis=1), ABSTAIN_RATE))
    return {
        "cal": cal,
        "iso": iso,
        "tau": tau,
        "cutoff": float(np.quantile(iso.score_samples(val[FEATURES]), OUTLIER_RATE)),
        "blocked": blocked_patterns(cal, tau, val),
    }


def predict(trust: dict, df: pd.DataFrame) -> pd.DataFrame:
    """Rows after validate + add_colors -> label (class, uncertain, unusual_input), confidence."""
    proba = trust["cal"].predict_proba(df[FEATURES])
    conf = proba.max(axis=1)
    label = trust["cal"].classes_[proba.argmax(axis=1)]
    label = np.where(conf < trust["tau"], "uncertain", label)
    label = np.where(np.isin(bands_present(df), trust["blocked"]), "uncertain", label)
    label = np.where(
        trust["iso"].score_samples(df[FEATURES]) < trust["cutoff"], "unusual_input", label
    )
    return pd.DataFrame({"label": label, "confidence": conf}, index=df.index)


def conf_bins(conf: np.ndarray, bins: int = 15) -> np.ndarray:
    """Equal-width bin index of each confidence; conf = 1.0 goes in the top bin."""
    return np.minimum((conf * bins).astype(int), bins - 1)


def ece(conf: np.ndarray, correct: np.ndarray, bins: int = 15) -> float:
    """Expected calibration error of the top-class probability, equal-width bins."""
    idx = conf_bins(conf, bins)
    return float(
        sum(
            abs(correct[idx == b].mean() - conf[idx == b].mean()) * (idx == b).mean()
            for b in np.unique(idx)
        )
    )


def score(trust: dict, df: pd.DataFrame) -> dict:
    out = predict(trust, df)
    proba = trust["cal"].predict_proba(df[FEATURES])
    raw = trust["cal"].estimator.predict_proba(df[FEATURES])
    answered = ~out["label"].isin(ABSTAIN)
    y, pred = df["class"].to_numpy(), trust["cal"].classes_[proba.argmax(axis=1)]
    y_ans, label_ans = y[answered], out["label"][answered].to_numpy()
    return {
        "coverage": float(answered.mean()),
        # Abstained rows are never counted as correct: scores are on answered rows, next to
        # coverage; None when nothing is answered. Accuracy too: macro F1 on answered rows
        # swings with which classes happen to be answered.
        "macro_f1_answered": f1_score(y_ans, label_ans, labels=CLASSES, average="macro")
        if answered.any()
        else None,
        "accuracy_answered": float((y_ans == label_ans).mean()) if answered.any() else None,
        "macro_f1_all": f1_score(y, pred, labels=CLASSES, average="macro"),
        "uncertain": float((out["label"] == "uncertain").mean()),
        "unusual_input": float((out["label"] == "unusual_input").mean()),
        "ece_raw": ece(
            raw.max(axis=1), raw.argmax(axis=1) == np.searchsorted(trust["cal"].classes_, y)
        ),
        "ece_calibrated": ece(proba.max(axis=1), pred == y),
    }


def main() -> None:
    train, stop = split_stop(pd.read_parquet(SPLITS / "train.parquet"))
    val = pd.read_parquet(SPLITS / "val.parquet")
    trust = fit_trust(joblib.load(OUT / "robust.joblib"), train, stop, val)
    joblib.dump(trust, OUT / "robust_trust.joblib")
    results = {"tau": trust["tau"], "outlier_cutoff": trust["cutoff"], "seed": SEED}
    for name, df in ({"clean": val} | degraded_val(val)).items():
        results[name] = r = score(trust, df)
        f1_answered = r["macro_f1_answered"] if r["coverage"] else np.nan  # None: none answered
        print(
            f"{name}: coverage {r['coverage']:.3f}, F1 answered {f1_answered:.4f} "
            f"(all {r['macro_f1_all']:.4f}), unusual {r['unusual_input']:.3f}, "
            f"ECE {r['ece_raw']:.3f} -> {r['ece_calibrated']:.3f}"
        )
    (OUT / "trust_val_metrics.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
