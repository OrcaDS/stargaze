import pandas as pd

from stargaze.silver import to_silver


def test_silver_sentinels_dedupe_and_split():
    df = pd.DataFrame(
        {
            "specObjID": pd.array([30, 10, 20], dtype="uint64"),
            "objID": [1, 1, 2],
            "psfMag_u": [19.0, -9999.0, 18.0],
            "psfMagErr_u": [0.1, -9999.0, 0.2],
            "modelMag_u": [19.0, -9999.0, 18.0],
            "clean": [1, 1, None],
        }
    )
    clean, messy = to_silver(df)
    # objID 1 keeps the lowest specObjID (10), whose sentinel became NaN.
    assert clean["specObjID"].tolist() == [10]
    assert clean.loc[0, ["psfMag_u", "psfMagErr_u", "modelMag_u"]].isna().all()
    # A null clean flag goes to the eval-only messy set.
    assert messy["objID"].tolist() == [2]
