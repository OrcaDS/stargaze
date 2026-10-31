import math

import pandas as pd

from stargaze.validate import validate


def test_validate_range_sentinel_and_flag():
    df = pd.DataFrame(
        {
            "psfMag_u": [19.0, 2.1, -9999.0, math.nan],
            "modelMag_r": [18.0, 18.0, 18.0, 31.0],
            "psfMagErr_u": [50.0, 50.0, 50.0, 50.0],  # errors are not magnitudes
        }
    )
    out, flag = validate(df)
    assert out["psfMag_u"].iloc[0] == 19.0
    assert out["psfMag_u"].iloc[1:].isna().all() and math.isnan(out["modelMag_r"].iloc[3])
    assert (out["psfMagErr_u"] == 50.0).all()
    # A typo (2.1) and an out-of-range model mag flag; a sentinel or a plain NaN does not.
    assert flag.tolist() == [False, True, False, True]
