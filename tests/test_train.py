import numpy as np
import pandas as pd

from stargaze.gold import FEATURES
from stargaze.train import MODELS, evaluate, fit


def test_baseline_has_no_redshift_and_models_learn():
    assert "z" not in MODELS["baseline"] and MODELS["upper_bound"] == FEATURES + ["z"]
    rng = np.random.default_rng(0)
    y = np.repeat(["GALAXY", "QSO", "STAR"], 100)
    df = pd.DataFrame(rng.normal(size=(300, len(FEATURES))), columns=FEATURES)
    df["u-g"] += pd.Series(y).map({"GALAXY": 0, "QSO": 5, "STAR": 10})  # separable signal
    df.loc[0, "psfMag_u"] = np.nan  # NaN must be accepted
    df["class"], df["z"] = y, 0.0
    r = evaluate(fit(df, MODELS["baseline"], df), df, MODELS["baseline"])
    assert r["macro_f1"] > 0.9 and len(r["confusion"]) == 3
