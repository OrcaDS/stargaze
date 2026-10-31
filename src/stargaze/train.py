"""Train upper bound (with redshift), baseline and robust (clean + augmented train); score on val.

Run: uv run python -m stargaze.train   (after stargaze.split)
Scores are on validation: the test split is touched once, at the end.
"""

import json

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

from stargaze.augment import augment, degrade
from stargaze.gold import FEATURES
from stargaze.split import OUT as SPLITS
from stargaze.split import SEED

OUT = SPLITS.parents[2] / "models"
MODELS = {"upper_bound": FEATURES + ["z"], "baseline": FEATURES, "robust": FEATURES}
# Degraded val for development checks: (noise multiplier, mask probability). Not the M4 suites.
VAL_DEGRADED = {"noise_1x": (1, 0), "noise_3x": (3, 0), "noise_5x": (5, 0), "mask_30pct": (0, 0.3)}
CLASSES = ["GALAXY", "QSO", "STAR"]


def fit(train: pd.DataFrame, cols: list[str], stop: pd.DataFrame) -> HistGradientBoostingClassifier:
    """Early stopping scores on `stop`, rows held out of train before any augmentation."""
    model = HistGradientBoostingClassifier(
        class_weight="balanced", max_iter=500, early_stopping=True, random_state=SEED
    )
    return model.fit(train[cols], train["class"], X_val=stop[cols], y_val=stop["class"])


def split_stop(train: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hold out early-stopping rows by object, before any augmentation; also the calibration set."""
    return train_test_split(train, test_size=0.1, stratify=train["class"], random_state=SEED)


def degraded_val(val: pd.DataFrame) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(SEED + 1)  # own seed, separate from training augmentation
    return {k: degrade(val, rng, m, p) for k, (m, p) in VAL_DEGRADED.items()}


def evaluate(model, df: pd.DataFrame, cols: list[str]) -> dict:
    pred = model.predict(df[cols])
    report = classification_report(df["class"], pred, labels=CLASSES, output_dict=True)
    return {
        "macro_f1": f1_score(df["class"], pred, labels=CLASSES, average="macro"),
        "per_class": {c: {k: report[c][k] for k in ("precision", "recall")} for c in CLASSES},
        "confusion": confusion_matrix(df["class"], pred, labels=CLASSES).tolist(),
    }


def main() -> None:
    train = pd.read_parquet(SPLITS / "train.parquet")
    # Same early-stopping rows for every model (and for calibration in trust.py).
    train, stop = split_stop(train)
    val = pd.read_parquet(SPLITS / "val.parquet")
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    degraded = degraded_val(val)
    for name, cols in MODELS.items():
        data = augment(train, SEED) if name == "robust" else train
        model = fit(data, cols, stop)
        joblib.dump(model, OUT / f"{name}.joblib")
        results[name] = evaluate(model, val, cols) | {
            "seed": SEED,
            "train_rows": len(data),
            "stop_rows": len(stop),
            "val_rows": len(val),
            "n_iter": model.n_iter_,
            "sklearn": sklearn.__version__,
        }
        f1, qso = results[name]["macro_f1"], results[name]["per_class"]["QSO"]["recall"]
        print(f"{name}: macro F1 {f1:.4f}, QSO recall {qso:.4f}")
        if name != "upper_bound":  # its redshift is never degraded, so the comparison is moot
            for k, d in degraded.items():
                results[name][k] = evaluate(model, d, cols)
                print(f"  {k}: macro F1 {results[name][k]['macro_f1']:.4f}")
    (OUT / "val_metrics.json").write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
