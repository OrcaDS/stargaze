"""Cross-survey test (spec suite 5): DESI DR1 objects, scored with the shipped SDSS models.

Run: uv run python -m stargaze.desi   (pulls bronze once, ~30 s; reports -> reports/desi/)
Evaluation only: DESI never enters training, and nothing is tuned on it.
DESI has g, r, z only and one total flux per band (no PSF vs model split), so the SDSS val
split is scored with the same information removed, to separate "less information" from
"another telescope".
"""

import io
import json
import urllib.parse
import urllib.request
import warnings
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.exceptions import UndefinedMetricWarning

from stargaze.bronze import OUT as BRONZE
from stargaze.bronze import ROOT
from stargaze.evaluate import REPORTS, run
from stargaze.gold import FEATURES, MAGS, MODEL_MAGS, add_colors
from stargaze.split import OUT as SPLITS
from stargaze.train import OUT as MODELS
from stargaze.train import evaluate
from stargaze.validate import validate

RELEASE = "DESI DR1"
URL = "https://datalab.noirlab.edu/tap/sync"
QUERY = (ROOT / "sql" / "bronze_desi_dr1.sql").read_text()
SHARED = "grz"


def sql(query: str) -> str:
    """The query without its comment lines: what is sent, and what decides the rows."""
    return "\n".join(ln for ln in query.splitlines() if not ln.startswith("--"))


def fetch(adql: str) -> pd.DataFrame:
    body = urllib.parse.urlencode(
        {"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql}
    ).encode()
    with urllib.request.urlopen(URL, body, timeout=600) as r:
        text = r.read().decode()
    if not text.startswith("targetid"):  # errors come back as a VOTable
        raise RuntimeError(f"Data Lab error: {text[:300]}")
    return pd.read_csv(io.StringIO(text), dtype={"targetid": "int64", "spectype": "string"})


def pull() -> pd.DataFrame:
    path, meta_path = BRONZE / "desi_dr1.parquet", BRONZE / "desi_dr1.meta.json"
    if path.exists():
        if sql(json.loads(meta_path.read_text())["query"]) != sql(QUERY):
            raise SystemExit(f"{path} was pulled with another query: delete it and rerun.")
        return pd.read_parquet(path)
    BRONZE.mkdir(parents=True, exist_ok=True)
    df = fetch(sql(QUERY))
    assert df["targetid"].is_unique, "a DESI object came back twice"
    df.to_parquet(path, index=False)
    meta = {
        "release": RELEASE,
        "source": URL,
        "query": QUERY,
        "run_date": datetime.now(UTC).isoformat(timespec="seconds"),
        "rows": len(df),
        "class_counts": df["spectype"].value_counts().to_dict(),
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"bronze: {len(df):,} DESI rows -> {path}")
    return df


def to_features(desi: pd.DataFrame) -> pd.DataFrame:
    """DESI fluxes -> the SDSS feature table: g, r, z as PSF mags; u, i and model mags missing.

    shortcut: Legacy Surveys g, r, z are put straight on the SDSS scale (AB mags, no colour
    terms) and their total flux stands in for the PSF mag, which is right for point sources
    (stars, quasars) and too bright for galaxies; that mismatch is part of what this measures.
    """
    df = pd.DataFrame(np.nan, index=desi.index, columns=MAGS + MODEL_MAGS)
    for b in SHARED:
        flux = desi[f"flux_{b}"].where(desi[f"flux_{b}"] > 0)  # no detection -> missing
        df[f"psfMag_{b}"] = 22.5 - 2.5 * np.log10(flux)  # nanomaggies -> AB magnitude
    df = add_colors(validate(df)[0])
    df["class"] = desi["spectype"].to_numpy()
    return df


def sdss_like_desi(val: pd.DataFrame) -> pd.DataFrame:
    """SDSS val with only what DESI gives: g, r, z PSF mags, no u, i or model mags."""
    df = val.copy()
    df[[m for m in MAGS if m[-1] not in SHARED] + MODEL_MAGS] = np.nan
    return add_colors(df)


def score(models: dict, trust: dict, df: pd.DataFrame) -> dict:
    out = run(models, trust, df) | {"rows": len(df)}
    out["class_counts"] = df["class"].value_counts().to_dict()
    out["detail"] = {m: evaluate(models[m], df, FEATURES) for m in ("baseline", "robust")}
    return out


def main() -> None:
    # A model that never predicts a class gets precision 0 for it: the honest score here.
    warnings.filterwarnings("ignore", category=UndefinedMetricWarning)
    models = {m: joblib.load(MODELS / f"{m}.joblib") for m in ("baseline", "robust")}
    trust = joblib.load(MODELS / "robust_trust.joblib")
    r = {
        "release": RELEASE,
        "bands": SHARED,
        "desi": score(models, trust, to_features(pull())),
        # Not held out: tau, the outlier cutoff and blocked patterns were tuned on these rows,
        # so its trust-layer numbers are slightly optimistic next to DESI's.
        "sdss_val_same_info_note": "SDSS val, tau/cutoff/blocked patterns tuned on these rows",
        "sdss_val_same_info": score(
            models, trust, sdss_like_desi(pd.read_parquet(SPLITS / "val.parquet"))
        ),
    }
    out = REPORTS / "desi"
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(r, indent=2))
    for k in ("sdss_val_same_info", "desi"):
        v, t = r[k], r[k]["trust"]
        answered = f"{t['macro_f1_answered']:.3f}" if t["coverage"] else "n/a"
        print(
            f"{k:18} baseline {v['baseline_f1']:.3f}  robust {v['robust_f1']:.3f}  "
            f"answered {answered} @ {t['coverage']:.0%}"
        )


if __name__ == "__main__":
    main()
