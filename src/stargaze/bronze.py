"""Bronze layer: pull the raw SDSS DR17 sample from SkyServer into Parquet, untouched.

Run: uv run python -m stargaze.bronze
If SkyServer answers 403 (rate limit) or times out, run it again: finished chunks are skipped.
"""

import io
import json
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

RELEASE = "DR17"
URL = f"https://skyserver.sdss.org/{RELEASE.lower()}/SkyServerWS/SearchTools/SqlSearch"
ROOT = Path(__file__).resolve().parents[2]
QUERY = (ROOT / "sql" / "bronze_sdss_dr17.sql").read_text()
OUT = ROOT / "data" / "bronze"
# Full specObjID range of the labeled set (checked 2026-10-26); hi is exclusive.
LO, HI = 299489677444933632, 14126941158849665025
N_CHUNKS = 20
# specObjID exceeds int64 at the top of its range.
DTYPES = {"specObjID": "uint64", "objID": "int64", "class": "string", "zWarning": "int64"}


def parse_csv(text: str) -> pd.DataFrame:
    """Parse a SkyServer CSV response; anything else is a server error."""
    if not text.startswith("#Table1"):
        raise RuntimeError(f"SkyServer error: {text[:300]}")
    return pd.read_csv(io.StringIO(text), skiprows=1, dtype=DTYPES)


def fetch(sql: str) -> pd.DataFrame:
    url = URL + "?" + urllib.parse.urlencode({"cmd": sql, "format": "csv"})
    with urllib.request.urlopen(url, timeout=600) as r:
        return parse_csv(r.read().decode())


def chunk_bounds(lo: int = LO, hi: int = HI, n: int = N_CHUNKS) -> list[tuple[int, int]]:
    edges = [lo + (hi - lo) * i // n for i in range(n)] + [hi]
    return list(zip(edges, edges[1:], strict=False))


def main() -> None:
    chunks_dir = OUT / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    for i, (lo, hi) in enumerate(chunk_bounds()):
        path = chunks_dir / f"{i:02d}.parquet"
        if path.exists():  # resume after a timeout without re-pulling finished chunks
            continue
        df = fetch(QUERY.format(lo=lo, hi=hi))
        df.to_parquet(path, index=False)
        print(f"chunk {i:02d}: {len(df):,} rows")

    df = pd.concat(
        [pd.read_parquet(p) for p in sorted(chunks_dir.glob("*.parquet"))], ignore_index=True
    )
    assert df["specObjID"].is_unique, "chunks overlap"
    df.to_parquet(OUT / "sdss_dr17.parquet", index=False)
    meta = {
        "release": RELEASE,
        "source": URL,
        "query": QUERY,
        "run_date": datetime.now(UTC).isoformat(timespec="seconds"),
        "rows": len(df),
        "class_counts": df["class"].value_counts().to_dict(),
    }
    (OUT / "sdss_dr17.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"bronze: {len(df):,} rows -> {OUT / 'sdss_dr17.parquet'}")


if __name__ == "__main__":
    main()
