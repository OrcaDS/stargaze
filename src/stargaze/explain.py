"""Plain-word explanations of single features, shared by the Streamlit demo and the web export."""

import pandas as pd

from stargaze.gold import MAGS

COLOUR = dict(u="ultraviolet", g="green", r="red", i="near-infrared", z="infrared")
NAME = {"GALAXY": "Galaxy", "STAR": "Star", "QSO": "Quasar", "uncertain": "Not sure"}


def describe(feature: str, row: pd.Series, typical: pd.Series) -> str:
    """One feature of one object in plain words, compared with the typical sample object."""
    v = row[feature]
    bands = feature.split("_")[-1] if "_" in feature else feature.split("-")
    if pd.isna(v):
        gone = [COLOUR[b] for b in bands if pd.isna(row[f"psfMag_{b}"])] or ["shape"]
        return f"The missing {' and '.join(gone)} measurement{'s' if len(gone) > 1 else ''}"
    if feature in MAGS:
        side = "brighter" if v < typical[feature] else "fainter"  # smaller magnitude = brighter
        return f"It looks {side} than most objects in {COLOUR[bands]} light"
    if feature.startswith("psf-model"):
        if v < 0.3:  # point sources (stars, quasars) sit near 0, galaxies near 1
            return f"In {COLOUR[bands]} light it is a sharp point, like stars and quasars"
        return f"In {COLOUR[bands]} light it is spread out, like galaxies"
    a, b = (COLOUR[x] for x in bands)
    side = "more" if v < typical[feature] else "less"  # a smaller a-b colour = more a light
    return f"It gives off {side} {a} light, relative to {b}, than most objects"
