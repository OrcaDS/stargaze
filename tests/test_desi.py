import numpy as np
import pandas as pd

from stargaze.desi import to_features


def test_to_features_converts_fluxes_and_leaves_unshared_bands_missing():
    desi = pd.DataFrame(
        {
            "flux_g": [1.0, -0.5],  # 1 nanomaggy = mag 22.5; a negative flux is no detection
            "flux_r": [10.0, 10.0],
            "flux_z": [100.0, 100.0],
            "spectype": ["STAR", "QSO"],
        }
    )
    df = to_features(desi)
    assert np.allclose(df.loc[0, ["psfMag_g", "psfMag_r", "psfMag_z"]], [22.5, 20.0, 17.5])
    assert np.isnan(df.loc[1, "psfMag_g"]) and np.isnan(df.loc[1, "g-r"])
    assert df[["psfMag_u", "psfMag_i", "psf-model_r"]].isna().all().all()
    assert df["class"].tolist() == ["STAR", "QSO"]
