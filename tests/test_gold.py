import math

import pandas as pd

from stargaze.gold import ERR_CAP, ERRS, FEATURES, MODEL_MAGS, to_gold


def test_gold_colors_nan_and_no_leaky_columns():
    row = {f"psfMag_{b}": m for b, m in zip("ugriz", [20.0, 19.0, None, 18.0, 17.5], strict=False)}
    row |= {e: 0.1 for e in ERRS} | {f"modelMag_{b}": 18.0 for b in "ugriz"}
    row |= {"psfMagErr_u": 1.8e6, "modelMagErr_g": math.nan}
    row |= {"class": "QSO", "z": 1.2, "objID": 7, "specObjID": 9, "ra": 1.0, "dec": 2.0}
    gold = to_gold(pd.DataFrame([row]))
    assert gold.loc[0, "u-g"] == 1.0
    assert math.isnan(gold.loc[0, "g-r"]) and math.isnan(gold.loc[0, "r-i"])
    assert gold.loc[0, "i-z"] == 0.5
    assert gold.loc[0, "psf-model_u"] == 2.0 and math.isnan(gold.loc[0, "psf-model_r"])
    assert gold.loc[0, "psfMagErr_u"] == ERR_CAP and math.isnan(gold.loc[0, "modelMagErr_g"])
    # Pinned so any new (possibly leaky) column fails here first.
    assert list(gold.columns) == FEATURES + ERRS + MODEL_MAGS + ["class", "z"]
    assert len(FEATURES) == 14 and not {"z", "objID", "specObjID", "ra", "dec"} & set(FEATURES)
