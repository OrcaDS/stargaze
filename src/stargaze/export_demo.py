"""Precompute the web demo's answers: 21 sample objects x every damage the page offers.

Run: uv run python -m stargaze.export_demo   (needs the shipped models/ and models/samples.parquet)
Writes web/src/generated/answers.json. The page then shows the shipped models' real answers with no
server. It reads the test scores from reports/test/metrics.json and never rescores anything.

Damage matches streamlit_app.py: noise drawn with the object's row number as seed (so the guided
stories reproduce the hand-picked examples), a lost colour hides its PSF and model mag, and a typo
is the clean PSF mag x 10. Everything goes through validate -> add_colors, for both models, as in
stargaze.api.predict.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import shap

from stargaze import trust
from stargaze.api import SAMPLES, load_models
from stargaze.augment import perturb
from stargaze.explain import NAME, describe
from stargaze.gold import FEATURES, MAGS, MODEL_MAGS, add_colors
from stargaze.validate import validate

ROOT = Path(__file__).parents[2]
OUT = ROOT / "web" / "src" / "generated" / "answers.json"
REPORT = ROOT / "reports" / "test" / "metrics.json"
# Rows of models/samples.parquet, seven of each class. 42, 4 and 22 are the guided stories
# (streamlit_app.SCENARIOS); 11, 1 and 48 are bright, clean extra objects for free play. The
# other 15 are the first five per class in file order with all ten mags in 10-30 and model r
# brighter than 18.5 (so the photo shows something), picked by that rule, not by model answers.
OBJECTS = [42, 22, 4, 11, 1, 48]
OBJECTS += [6, 7, 12, 14, 17, 10, 13, 20, 52, 58, 114, 272, 344, 403, 447]
NOISE = [0, 1, 2, 3, 5, 8]
LABELS = ["Star", "Galaxy", "Quasar", "Not sure"]
STORIES = [  # (object index in OBJECTS, noise, lost bands bitmask, typo band or -1)
    {"title": "Lose two colours", "obj": 0, "noise": 0, "mask": 0b00110, "typo": -1},
    {"title": "Make it very noisy", "obj": 2, "noise": 8, "mask": 0, "typo": -1},
    {"title": "Add a typo", "obj": 1, "noise": 0, "mask": 0, "typo": 3},
]


def key(obj: int, noise: int, mask: int, typo: int) -> str:
    return f"{obj}|{noise}|{mask}|{typo}"


def jname(ra: float, dec: float) -> str:
    """Official SDSS designation, SDSS Jhhmmss.ss+ddmmss.s (digits truncated, not rounded)."""
    h = int(ra / 15 * 360000)  # hundredths of a second of time
    d = int(abs(dec) * 36000)  # tenths of an arcsecond
    sign = "-" if dec < 0 else "+"
    return (
        f"SDSS J{h // 360000:02d}{h // 6000 % 60:02d}{h % 6000 // 100:02d}.{h % 100:02d}"
        f"{sign}{d // 36000:02d}{d // 600 % 60:02d}{d % 600 // 10:02d}.{d % 10}"
    )


def damaged(samples: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[dict]]:
    """Every (object, noise, lost bands, typo) case as raw rows, before validation."""
    rows, keys, objects = [], [], []
    for o, i in enumerate(OBJECTS):
        base = samples.iloc[[i]].reset_index(drop=True)
        kind = NAME[base["class"].iloc[0]]
        base[MAGS] = base[MAGS].clip(10.0, 30.0)
        noisy_by_level = {}
        for n in NOISE:
            # display-only seed = row number, matches streamlit_app.py SCENARIOS
            noisy = perturb(base, np.random.default_rng(i), float(n), mask_p=0.0)
            noisy_by_level[str(n)] = [round(float(v), 3) for v in noisy[MAGS].iloc[0]]
            for mask in range(32):
                for typo in [-1, *(b for b in range(5) if not mask >> b & 1)]:
                    r = noisy[MAGS + MODEL_MAGS].iloc[0].copy()
                    for b in range(5):
                        if mask >> b & 1:
                            r[[MAGS[b], MODEL_MAGS[b]]] = np.nan
                    if typo >= 0:  # a misplaced decimal point: 19.2 -> 192
                        r[MAGS[typo]] = base[MAGS[typo]].iloc[0] * 10
                    rows.append(r)
                    keys.append(key(o, n, mask, typo))
        objects.append(
            {
                "tag": jname(base["ra"].iloc[0], base["dec"].iloc[0]),
                "type": kind,
                "ra": round(float(base["ra"].iloc[0]), 3),
                "dec": round(float(base["dec"].iloc[0]), 3),
                "mags": [round(float(v), 3) for v in base[MAGS].iloc[0]],
                "err": [round(float(base[m.replace("Mag_", "MagErr_")].iloc[0]), 3) for m in MAGS],
                "noisy": noisy_by_level,
            }
        )
    return pd.DataFrame(rows).reset_index(drop=True), keys, objects


def reasons(explainer, classes, X: pd.DataFrame, lean: np.ndarray, typical) -> list[str]:
    """Per row, the strongest clue (SHAP) pushing toward the class the model leans to."""
    values = explainer(X[FEATURES].astype(float)).values  # (rows, features, classes)
    out = []
    for k in range(len(X)):
        row = X.iloc[k]
        c = lean[k]
        pushes = pd.Series(values[k, :, c]).groupby([describe(f, row, typical) for f in FEATURES])
        text, push = pushes.sum().sort_values().index[-1], pushes.sum().max()
        name = NAME[classes[c]].lower()
        clue = text[0].lower() + text[1:]
        if push > 0:
            out.append(f"Strongest clue: {clue}. That points to {name}.")
        else:  # nothing pushes toward the class it picked; it wins by being argued against least
            out.append(f"No clue points clearly to {name}; the others were ruled out harder.")
    return out


def scores() -> dict:
    s = json.loads(REPORT.read_text())["suites"]

    def scores_for(name: str) -> list[int]:
        """Ordinary, Stargaze forced to answer all, Stargaze on what it answers, % it answers."""
        t = s[name]["trust"]
        values = [
            s[name]["baseline_f1"],
            s[name]["robust_f1"],
            t["macro_f1_answered"],
            t["coverage"],
        ]
        return [round(v * 100) for v in values]

    return {
        "noise": {str(n): scores_for(f"noise_{n}x") for n in NOISE},
        "missing": [scores_for(f"random_{k}_bands") for k in range(5)],
        "corrupt": scores_for("corrupt_5pct"),
        "objects": json.loads(REPORT.read_text())["rows"],
    }


def build() -> dict:
    models = load_models()
    samples = pd.read_parquet(SAMPLES)
    typical = add_colors(samples)[FEATURES].median()
    raw, keys, objects = damaged(samples)
    checked, corrupted = validate(raw)
    X = add_colors(checked)

    base = models["baseline"]
    b_proba = base.predict_proba(X[FEATURES])
    b_lean = b_proba.argmax(axis=1)
    b_why = reasons(shap.TreeExplainer(base), base.classes_, X, b_lean, typical)

    t = models["robust"]
    r_proba = t["cal"].predict_proba(X[FEATURES])
    r_lean = r_proba.argmax(axis=1)
    r_label = trust.predict(t, X)["label"].to_numpy()
    r_why = reasons(
        shap.TreeExplainer(t["cal"].estimator.estimator), t["cal"].classes_, X, r_lean, typical
    )

    texts: dict[str, int] = {}

    def text_id(s: str) -> int:
        return texts.setdefault(s, len(texts))

    answers = {}
    for k in range(len(X)):
        leaned = NAME[t["cal"].classes_[r_lean[k]]].lower()
        if r_label[k] == "unusual_input":
            sg_why = (
                "This doesn't look like anything it learned from. "
                f"It leaned {leaned}, but won't guess."
            )
        elif r_label[k] == "uncertain":
            sg_why = f"The clues left aren't enough to decide. It leaned {leaned}, but won't guess."
        else:
            sg_why = r_why[k]
        sg_ans = "Not sure" if r_label[k] in trust.ABSTAIN else NAME[r_label[k]]
        answers[keys[k]] = [
            LABELS.index(NAME[base.classes_[b_lean[k]]]),
            round(float(b_proba[k].max()), 3),
            text_id(b_why[k]),
            LABELS.index(sg_ans),
            round(float(r_proba[k].max()), 3),
            text_id(sg_why),
            1 if r_label[k] == "unusual_input" else 0,
            1 if corrupted.iloc[k] else 0,
        ]
    return {
        "note": "Generated by python -m stargaze.export_demo from the shipped models; do not edit.",
        "labels": LABELS,
        "fields": [
            "ordinary",
            "ordinary_conf",
            "ordinary_why",
            "stargaze",
            "stargaze_conf",
            "stargaze_why",
            "unusual",
            "corrected",
        ],
        "noise": NOISE,
        "objects": objects,
        "stories": STORIES,
        "texts": list(texts),
        "answers": answers,
        "scores": scores(),
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print(f"{len(data['answers'])} cases -> {OUT} ({OUT.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
