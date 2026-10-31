"""Silver layer: sentinels to NaN, one row per object, clean / messy split.

Run: uv run python -m stargaze.silver   (after stargaze.bronze)
"""

import pandas as pd

from stargaze.bronze import OUT as BRONZE

OUT = BRONZE.parent / "silver"
SENTINEL = -9999


def to_silver(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (clean, messy): clean = 1 is the main dataset, clean = 0 the messy test set."""
    df = df.copy()
    phot = [c for c in df if c.startswith(("psfMag", "modelMag"))]
    df[phot] = df[phot].mask(df[phot] <= SENTINEL)
    # Keep one spectrum per photometric object so no object can land in two splits.
    df = df.sort_values("specObjID").drop_duplicates("objID").reset_index(drop=True)
    df["clean"] = df["clean"] == 1  # a null flag goes to messy (eval-only), never to training
    return df[df["clean"]].reset_index(drop=True), df[~df["clean"]].reset_index(drop=True)


def main() -> None:
    clean, messy = to_silver(pd.read_parquet(BRONZE / "sdss_dr17.parquet"))
    OUT.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(OUT / "sdss_dr17_clean.parquet", index=False)
    messy.to_parquet(OUT / "sdss_dr17_messy.parquet", index=False)
    print(f"silver: {len(clean):,} clean, {len(messy):,} messy -> {OUT}")


if __name__ == "__main__":
    main()
