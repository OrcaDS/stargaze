"""Prediction API (spec: Demo and API): validate -> add_colors -> model.

Run: uv run uvicorn stargaze.api:app   (after stargaze.trust; docs at /docs)
uv run python -m stargaze.api writes the demo's sample objects (models/samples.parquet).
"""

from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from stargaze import trust
from stargaze.gold import BANDS, ERRS, FEATURES, MAGS, MODEL_MAGS, add_colors
from stargaze.silver import OUT as SILVER
from stargaze.split import OUT as SPLITS
from stargaze.split import SEED
from stargaze.train import OUT as MODELS
from stargaze.validate import validate

VERSION = version("stargaze")
# Clean test objects for the demo's "load real object" button; showing a label is not scoring.
SAMPLES = MODELS / "samples.parquet"
N_SAMPLES = 1000


class Photometry(BaseModel):
    """PSF magnitudes u..z and, optionally, model magnitudes; null means missing.

    The features include PSF - model per band, so leaving the model mags out costs a lot
    (robust on val: coverage 0.94 -> 0.52).
    """

    u: float | None = None
    g: float | None = None
    r: float | None = None
    i: float | None = None
    z: float | None = None
    u_model: float | None = None
    g_model: float | None = None
    r_model: float | None = None
    i_model: float | None = None
    z_model: float | None = None
    model: Literal["robust", "baseline"] = "robust"


def to_row(p: Photometry) -> pd.DataFrame:
    values = [getattr(p, b) for b in BANDS] + [getattr(p, f"{b}_model") for b in BANDS]
    return pd.DataFrame([values], columns=MAGS + MODEL_MAGS, dtype=float)


def predict(models: dict, p: Photometry) -> dict:
    df, corrupted = validate(to_row(p))
    df = add_colors(df)
    flags = [f"missing_band:{b}" for b, m in zip(BANDS, MAGS, strict=True) if df[m].isna().all()]
    if corrupted.iloc[0]:
        flags.append("corrupted_input")
    if p.model == "robust":
        t = models["robust"]
        proba = t["cal"].predict_proba(df[FEATURES])[0]
        classes = t["cal"].classes_
        label = trust.predict(t, df)["label"].iloc[0]
    else:  # the baseline has no trust layer: it always answers
        proba = models["baseline"].predict_proba(df[FEATURES])[0]
        classes = models["baseline"].classes_
        label = classes[proba.argmax()]
    abstained = label in trust.ABSTAIN
    if abstained:
        flags.append(label)
    return {
        "label": "uncertain" if abstained else str(label),
        "probabilities": {str(c): float(v) for c, v in zip(classes, proba, strict=True)},
        "flags": flags,
        "abstained": bool(abstained),
        "model_version": f"{p.model}-{VERSION}",
    }


def load_models() -> dict:
    return {
        "robust": joblib.load(MODELS / "robust_trust.joblib"),
        "baseline": joblib.load(MODELS / "baseline.joblib"),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.models = load_models()
    app.state.samples = pd.read_parquet(SAMPLES) if SAMPLES.exists() else None
    yield


app = FastAPI(title="Stargaze", version=VERSION, lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_version": VERSION}


@app.post("/predict")
def post_predict(p: Photometry, request: Request) -> dict:
    return predict(request.app.state.models, p)


@app.get("/sample")
def sample(request: Request) -> dict:
    samples = request.app.state.samples
    if samples is None:
        raise HTTPException(404, "no sample objects on this server")
    row = samples.iloc[np.random.default_rng().integers(len(samples))]
    out = {b: row[m] for b, m in zip(BANDS, MAGS, strict=True)}
    out |= {f"{b}_model": row[m] for b, m in zip(BANDS, MODEL_MAGS, strict=True)}
    # NaN is not valid JSON: missing values go out as null, as /predict expects them.
    return {k: None if pd.isna(v) else float(v) for k, v in out.items()} | {"class": row["class"]}


def main() -> None:
    # Errors are kept so the demo's noise slider scales with each object's real errors.
    test = pd.read_parquet(SPLITS / "test.parquet").dropna(subset=MAGS + MODEL_MAGS)
    test = test.sample(N_SAMPLES, random_state=SEED + 5)[MAGS + MODEL_MAGS + ERRS + ["class"]]
    # ra/dec only fetch the demo's sky picture, never features. Gold drops them; the ten mags
    # are unique per silver row, so they find each object's position.
    silver = pd.read_parquet(
        SILVER / "sdss_dr17_clean.parquet", columns=MAGS + MODEL_MAGS + ["ra", "dec"]
    )
    test = test.merge(silver, on=MAGS + MODEL_MAGS, how="left", validate="one_to_one")
    assert test[["ra", "dec"]].notna().all().all()
    test.to_parquet(SAMPLES, index=False)
    print(f"{len(test)} sample objects -> {SAMPLES}")


if __name__ == "__main__":
    main()
