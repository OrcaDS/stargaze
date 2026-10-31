"""M4 evaluation suites (spec, Evaluation plan): baseline vs robust (+ trust layer), fixed seeds.

Run: uv run python -m stargaze.evaluate          (val: build and check everything here first)
     uv run python -m stargaze.evaluate --test   (once, at the end: the headline result)
Writes reports/<split>/metrics.json and charts. The messy (clean = 0) set is scored with --test
only, so it stays an untouched held-out set like test.
"""

import argparse
import itertools
import json
import warnings

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.exceptions import UndefinedMetricWarning

from stargaze.augment import degrade, mask, perturb
from stargaze.gold import BANDS, FEATURES, add_colors
from stargaze.gold import MAGS as PSF
from stargaze.gold import OUT as GOLD
from stargaze.split import OUT as SPLITS
from stargaze.split import SEED
from stargaze.train import CLASSES, MODELS, OUT, evaluate
from stargaze.trust import ABSTAIN, conf_bins, ece, predict, score
from stargaze.validate import validate

NOISE = [0, 1, 2, 3, 5, 8]  # multipliers on the real SDSS errors
CORRUPT_P = 0.05
SEEDS = {"val": SEED + 1, "test": SEED + 3}  # test suites get their own seed
REPORTS = OUT.parent / "reports"
BOOT, BOOT_SEED = 1000, SEED + 4  # bootstrap resamples for the headline 95% intervals
SHAP_ROWS = 2000  # clean rows explained (TreeExplainer: ~1 s per 500)
# Spec targets; "met" only when the whole 95% interval is on the right side.
TARGETS = {
    "clean_f1_gap_to_upper_bound": ("<=", 0.07),
    "qso_recall_robust": (">=", 0.85),
    "two_missing_bands_gain": (">=", 0.10),
    "noise_auc_gain": (">", 0.0),
    "ece_calibrated": ("<=", 0.05),
}


def random_bands(n: int, k: int, rng: np.random.Generator) -> np.ndarray:
    """Exactly k distinct bands per row, each k-subset equally likely.

    argsort of iid uniforms is a uniformly random permutation; the k positions holding
    the values 0..k-1 are therefore a uniformly random k-subset.
    """
    return np.argsort(rng.random((n, 5)), axis=1) < k


def suites(
    df: pd.DataFrame, rng: np.random.Generator
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Degraded copies of df (same rows, same order), and the corruption suite before validation."""
    out = {f"noise_{m}x": degrade(df, rng, m, 0) for m in NOISE}
    out |= {f"random_{k}_bands": mask(df, random_bands(len(df), k, rng)) for k in range(5)}
    for k in range(1, 5):
        for combo in itertools.combinations(range(5), k):
            hide = np.zeros((len(df), 5), dtype=bool)
            hide[:, combo] = True
            out["mask_" + "".join(BANDS[i] for i in combo)] = mask(df, hide)
    raw = perturb(df, rng, 0, 0, CORRUPT_P)  # noise 0, no masking: only corruption changes values
    out["corrupt_5pct"] = add_colors(validate(raw)[0])  # what degrade(df, rng, 0, 0, ...) returns
    return out, raw


def run(models: dict, trust: dict, df: pd.DataFrame) -> dict:
    return {
        "baseline_f1": evaluate(models["baseline"], df, FEATURES)["macro_f1"],
        "robust_f1": evaluate(models["robust"], df, FEATURES)["macro_f1"],
        "trust": score(trust, df),
    }


def corruption(trust: dict, clean: pd.DataFrame, raw: pd.DataFrame) -> dict:
    """CORRUPT_P of rows get one impossible PSF value (spec suite 4).

    flagged_*: the validation layer's corrupted_input flag, returned with the answer as a warning.
    abstained_*: whether the trust layer also refused to answer (uncertain / unusual_input).
    """
    # raw = clean + 0 x noise, so a cell differs only where a bad value was written (also into
    # a band that was already missing, which the flag still catches).
    injected = ((raw[PSF] != clean[PSF]) & raw[PSF].notna()).any(axis=1).to_numpy()
    if not injected.any() or injected.all():
        raise ValueError("corruption suite needs both injected and untouched rows")
    bad, flag = validate(raw)
    flag = flag.to_numpy()
    abstained = predict(trust, add_colors(bad))["label"].isin(ABSTAIN).to_numpy()
    return {
        "injected_share": float(injected.mean()),
        "flagged_share_of_injected": float(flag[injected].mean()),
        "flagged_share_of_others": float(flag[~injected].mean()),
        "abstained_on_injected": float(abstained[injected].mean()),
        "abstained_on_others": float(abstained[~injected].mean()),
    }


def coverage_curve(trust: dict, df: pd.DataFrame) -> tuple[list[float], list[float]]:
    """Accuracy on the most confident share of rows, as the model abstains on more inputs.

    Accuracy (share of answered rows that are right), as the spec's "coverage vs accuracy" asks,
    not macro F1. Sweeps the confidence threshold only, band-pattern and outlier rules off: the tau
    trade-off, not the deployed policy (that one is the dashed line on the other charts).
    """
    proba = trust["cal"].predict_proba(df[FEATURES])
    order = np.argsort(-proba.max(axis=1), kind="stable")  # ties keep row order: reproducible
    correct = (trust["cal"].classes_[proba.argmax(axis=1)] == df["class"].to_numpy())[order]
    cov = np.linspace(0.5, 1, 11)
    return cov.tolist(), [float(correct[: int(c * len(df))].mean()) for c in cov]


def reliability(trust: dict, df: pd.DataFrame, bins: int = 15) -> dict:
    proba = trust["cal"].predict_proba(df[FEATURES])
    conf = proba.max(axis=1)
    correct = trust["cal"].classes_[proba.argmax(axis=1)] == df["class"].to_numpy()
    idx = conf_bins(conf, bins)  # same bins as the ECE
    used = np.unique(idx)
    return {
        "confidence": [float(conf[idx == b].mean()) for b in used],
        "accuracy": [float(correct[idx == b].mean()) for b in used],
        "count": [int((idx == b).sum()) for b in used],
    }


def codes(labels) -> np.ndarray:
    """Class labels -> 0, 1, 2 in CLASSES order (GALAXY, QSO, STAR); raises on any other label."""
    if CLASSES != sorted(CLASSES):
        raise ValueError("searchsorted needs CLASSES sorted")
    labels = np.asarray(labels)
    c = np.searchsorted(CLASSES, labels)
    if not (np.asarray(CLASSES)[c.clip(0, len(CLASSES) - 1)] == labels).all():
        raise ValueError("label outside CLASSES (abstain labels must not reach the metrics)")
    return c


def confusion(y: np.ndarray, pred: np.ndarray) -> np.ndarray:
    """3x3 counts, rows = true class, columns = predicted (integer codes)."""
    return np.bincount(3 * y + pred, minlength=9).reshape(3, 3)


def macro_f1(y: np.ndarray, pred: np.ndarray) -> float:
    """Mean over classes of F1 = 2TP / (2TP + FP + FN) = 2TP / (#true + #predicted).

    A class with no true and no predicted rows scores 0, as sklearn's f1_score does.
    Same value as sklearn (tested), fast enough for the bootstrap.
    """
    cm = confusion(y, pred)
    denom = cm.sum(axis=0) + cm.sum(axis=1)
    f1 = np.divide(2 * np.diag(cm), denom, out=np.zeros(3), where=denom > 0)
    return float(f1.mean())


def bootstrap(stat, n: int, rng: np.random.Generator) -> dict:
    """stat(rows) on all n rows, and its 95% percentile interval over BOOT resamples.

    Every suite is a degraded copy of the same rows in the same order, so one index draw
    pairs the models (and the suites): the interval is for the difference, not two margins.
    Scope: row sampling only. Each suite's noise / masking is one fixed draw, so that
    randomness is not in the interval.
    """
    draws = np.array([stat(rng.integers(0, n, n)) for _ in range(BOOT)])
    if not np.isfinite(draws).all():  # e.g. a resample with no QSO makes recall 0/0
        raise ValueError("bootstrap statistic was not finite on some resample")
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"value": stat(np.arange(n)), "ci95": [float(lo), float(hi)]}


def noise_auc(f1s: list[float]) -> float:
    """Mean macro F1 over noise multipliers 0-8x: trapezoid area / width of the range.

    On the uneven grid 0, 1, 2, 3, 5, 8 the trapezoid weights are .5, 1, 1, 1.5, 2.5, 1.5 (/8),
    so the 5x and 8x points carry half the score: it rewards holding up under heavy noise.
    """
    return float(np.trapezoid(f1s, NOISE) / NOISE[-1])


def met(op: str, target: float, ci95: list[float]) -> bool:
    """A target is met only if the whole 95% interval is on the right side of it."""
    lo, hi = ci95
    return {"<=": hi <= target, ">=": lo >= target, ">": lo > target}[op]


def headline(models: dict, trust: dict, df: pd.DataFrame, sets: dict) -> dict:
    """The spec's success metrics (Goals and success metrics table), with 95% intervals."""
    y = codes(df["class"])
    keys = [f"noise_{x}x" for x in NOISE] + ["random_2_bands"]
    pred = {
        m: {k: codes(models[m].predict(sets[k][FEATURES])) for k in keys}
        for m in ("baseline", "robust")
    }
    upper = codes(models["upper_bound"].predict(df[MODELS["upper_bound"]]))
    robust = pred["robust"]["noise_0x"]  # noise_0x equals df (checked in main)
    proba = trust["cal"].predict_proba(df[FEATURES])
    conf, correct = proba.max(axis=1), codes(trust["cal"].classes_[proba.argmax(axis=1)]) == y

    def auc(m: str, i: np.ndarray) -> float:
        return noise_auc([macro_f1(y[i], pred[m][f"noise_{x}x"][i]) for x in NOISE])

    def gain(k: str):
        rob, base = pred["robust"][k], pred["baseline"][k]
        return lambda i: macro_f1(y[i], rob[i]) - macro_f1(y[i], base[i])

    def qso_recall(i: np.ndarray) -> float:
        cm = confusion(y[i], robust[i])
        return float(cm[1, 1] / cm[1].sum())  # QSO is code 1; 0/0 is caught by bootstrap

    n, rng = len(y), np.random.default_rng(BOOT_SEED)
    h = {
        "clean_f1_gap_to_upper_bound": bootstrap(
            lambda i: macro_f1(y[i], upper[i]) - macro_f1(y[i], robust[i]), n, rng
        ),
        "qso_recall_robust": bootstrap(qso_recall, n, rng),
        "two_missing_bands_gain": bootstrap(gain("random_2_bands"), n, rng),
        "noise_auc_gain": bootstrap(lambda i: auc("robust", i) - auc("baseline", i), n, rng),
        "ece_calibrated": bootstrap(lambda i: ece(conf[i], correct[i]), n, rng),
    }
    for k, (op, target) in TARGETS.items():
        h[k] |= {"target": f"{op} {target}", "met": met(op, target, h[k]["ci95"])}
    h["noise_auc"] = {m: auc(m, np.arange(n)) for m in ("baseline", "robust")}
    return h


def shap_importance(model, df: pd.DataFrame) -> dict:
    """Mean |SHAP value| per feature and class for the robust model, on a sample of clean rows.

    Units: log-odds of the model's raw output for that class. Shows what the model leans on,
    to check against astrophysics (e.g. u-g should separate quasars from stars).
    """
    x = df[FEATURES].sample(min(SHAP_ROWS, len(df)), random_state=SEED)
    values = shap.TreeExplainer(model)(x).values  # (rows, features, classes), classes_ order
    imp = pd.DataFrame(np.abs(values).mean(axis=0), index=FEATURES, columns=model.classes_)
    return imp.to_dict(orient="index")


def charts(r: dict, out) -> None:
    plt.switch_backend("Agg")  # files only, no window
    s = r["suites"]
    for name, keys, x, xlabel in (
        ("noise", [f"noise_{m}x" for m in NOISE], NOISE, "noise multiplier × real SDSS error"),
        ("missing_bands", [f"random_{k}_bands" for k in range(5)], range(5), "bands masked"),
    ):
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(x, [s[k]["baseline_f1"] for k in keys], "o-", label="baseline")
        ax.plot(x, [s[k]["robust_f1"] for k in keys], "o-", label="robust")
        ax.plot(
            x,
            [
                s[k]["trust"]["macro_f1_answered"] if s[k]["trust"]["coverage"] else np.nan
                for k in keys
            ],
            "o--",
            label="robust, answered rows only",
        )
        for xi, k in zip(x, keys, strict=True):
            if not s[k]["trust"]["coverage"]:
                continue
            ax.annotate(
                f"{s[k]['trust']['coverage']:.0%}",
                (xi, s[k]["trust"]["macro_f1_answered"]),
                textcoords="offset points",
                xytext=(0, 6),
                ha="center",
                fontsize=7,
            )
        ax.set(xlabel=xlabel, ylabel="macro F1", ylim=(0, 1), title=f"{r['split']}: {name}")
        ax.set_xticks(list(x))
        ax.legend(title="labels on dashed line: coverage", fontsize=8, title_fontsize=7)
        fig.tight_layout()
        fig.savefig(out / f"{name}.png", dpi=120)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    rel = r["reliability"]
    ax.plot([0, 1], [0, 1], ":", color="grey")
    ax.plot(rel["confidence"], rel["accuracy"], "o-")
    ax.set(xlabel="confidence (calibrated)", ylabel="accuracy", title=f"{r['split']}: reliability")
    fig.tight_layout()
    fig.savefig(out / "reliability.png", dpi=120)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    for k, (cov, acc) in r["coverage_curve"].items():
        ax.plot(cov, acc, "o-", label=k)
    ax.set(
        xlabel="coverage (share answered)",
        ylabel="accuracy on answered rows",
        title=f"{r['split']}: coverage vs accuracy",
    )
    ax.invert_xaxis()
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "coverage.png", dpi=120)
    plt.close(fig)

    imp = pd.DataFrame(r["shap"]).T
    imp = imp.loc[imp.sum(axis=1).sort_values().index]  # most important on top
    ax = imp.plot.barh(stacked=True, figsize=(6, 5))
    ax.set(xlabel="mean |SHAP| (log-odds), stacked by class", title=f"{r['split']}: SHAP, robust")
    ax.figure.tight_layout()
    ax.figure.savefig(out / "shap.png", dpi=120)
    plt.close(ax.figure)


def main() -> None:
    # A model that never predicts a class gets precision 0 for it (sklearn's default): the
    # honest score under heavy masking, so the warning is expected noise here.
    warnings.filterwarnings("ignore", category=UndefinedMetricWarning)
    p = argparse.ArgumentParser()
    p.add_argument("--test", action="store_true", help="score the test split (run once)")
    split = "test" if p.parse_args().test else "val"
    out = REPORTS / split
    out.mkdir(parents=True, exist_ok=True)
    if split == "test":
        # Written before test is read, so even a crashed run counts as the one look (commit it).
        started = out / "STARTED"
        if started.exists():
            raise SystemExit(f"Test was already read once ({started}); not rerunning.")
        started.write_text("test split read; see metrics.json\n")

    df = pd.read_parquet(SPLITS / f"{split}.parquet")
    models = {m: joblib.load(OUT / f"{m}.joblib") for m in MODELS}
    trust = joblib.load(OUT / "robust_trust.joblib")
    sets, raw = suites(df, np.random.default_rng(SEEDS[split]))
    # Paired comparisons need every suite row-aligned with df; the 0x suite is df itself.
    if not all(d.index.equals(df.index) for d in sets.values()):
        raise ValueError("a suite reordered or dropped rows")
    pd.testing.assert_frame_equal(sets["noise_0x"][FEATURES], df[FEATURES])

    r = {
        "split": split,
        "rows": len(df),
        "seed": SEEDS[split],
        "scope": "clean and headline: all rows, no abstention; suites[*].trust: answered rows "
        "with coverage",
    }
    r["clean"] = {m: evaluate(models[m], df, cols) for m, cols in MODELS.items()}
    r["suites"] = {k: run(models, trust, d) for k, d in sets.items()}
    r["corruption"] = corruption(trust, df, raw)
    r["reliability"] = reliability(trust, df)
    r["coverage_curve"] = {
        k: coverage_curve(trust, sets[k]) for k in ("noise_0x", "noise_3x", "random_2_bands")
    }
    if split == "test":
        messy = pd.read_parquet(GOLD / "sdss_dr17_messy.parquet")
        r["messy"] = run(models, trust, messy) | {"rows": len(messy)}
    # Save the suites first: a crash in SHAP or the bootstrap must not lose the one test look.
    (out / "metrics.json").write_text(json.dumps(r, indent=2))
    r["shap"] = shap_importance(models["robust"], df)
    r["headline"] = headline(models, trust, df, sets)

    (out / "metrics.json").write_text(json.dumps(r, indent=2))
    charts(r, out)
    for k, v in (r["suites"] | ({"messy": r["messy"]} if "messy" in r else {})).items():
        t = v["trust"]
        answered = (
            f"F1 {t['macro_f1_answered']:.3f} acc {t['accuracy_answered']:.3f}"
            if t["coverage"]
            else "nothing answered"
        )
        print(
            f"{k:16} baseline {v['baseline_f1']:.3f}  robust {v['robust_f1']:.3f}  "
            f"answered {answered} @ {t['coverage']:.0%}"
        )
    print(json.dumps({"corruption": r["corruption"], "headline": r["headline"]}, indent=2))


if __name__ == "__main__":
    main()
