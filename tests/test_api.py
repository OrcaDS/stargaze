import numpy as np
from fastapi.testclient import TestClient

from stargaze.api import app


class _Sure:
    """Stands in for the calibrated model, the baseline and the outlier detector."""

    classes_ = np.array(["GALAXY", "QSO", "STAR"])

    def predict_proba(self, X):
        return np.tile([0.1, 0.8, 0.1], (len(X), 1))

    def score_samples(self, X):
        return np.zeros(len(X))


def _client(blocked=()) -> TestClient:
    robust = {"cal": _Sure(), "iso": _Sure(), "tau": 0.5, "cutoff": -0.5, "blocked": list(blocked)}
    app.state.models = {"robust": robust, "baseline": _Sure()}
    app.state.samples = None
    return TestClient(app)  # no `with`: skips the lifespan that loads the real models


def test_predict_flags_missing_and_corrupted_bands():
    body = {"u": 19.2, "g": 17.8, "r": None, "i": 16.9, "z": 99.0}
    out = _client().post("/predict", json=body).json()
    assert out["label"] == "QSO" and not out["abstained"]
    assert out["flags"] == ["missing_band:r", "missing_band:z", "corrupted_input"]
    assert out["probabilities"]["QSO"] == 0.8
    assert out["model_version"].startswith("robust-")


def test_robust_abstains_where_baseline_answers():
    body = {"u": 19.2}  # u alone: pattern 0b00001
    client = _client(blocked=[0b00001])
    robust = client.post("/predict", json=body).json()
    assert robust["label"] == "uncertain" and robust["abstained"]
    assert robust["flags"][-1] == "uncertain"
    baseline = client.post("/predict", json=body | {"model": "baseline"}).json()
    assert baseline["label"] == "QSO" and not baseline["abstained"]


def test_rejects_unknown_model_and_missing_samples():
    client = _client()
    assert client.post("/predict", json={"model": "nn"}).status_code == 422
    assert client.get("/sample").status_code == 404
    assert client.get("/health").json()["status"] == "ok"
