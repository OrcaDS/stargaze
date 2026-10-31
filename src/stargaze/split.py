"""Split the clean gold table 70 / 15 / 15, stratified by class, fixed seed.

Run: uv run python -m stargaze.split   (after stargaze.gold)
The test split is touched once, at the end.
"""

import pandas as pd
from sklearn.model_selection import train_test_split

from stargaze.gold import OUT as GOLD

OUT = GOLD / "splits"
SEED = 42


def split(df: pd.DataFrame, seed: int = SEED) -> dict[str, pd.DataFrame]:
    train, rest = train_test_split(df, test_size=0.30, stratify=df["class"], random_state=seed)
    val, test = train_test_split(rest, test_size=0.50, stratify=rest["class"], random_state=seed)
    return {"train": train, "val": val, "test": test}


def main() -> None:
    # By name, never a glob: the messy file sits next to it and is eval-only.
    parts = split(pd.read_parquet(GOLD / "sdss_dr17_clean.parquet"))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, df in parts.items():
        df.reset_index(drop=True).to_parquet(OUT / f"{name}.parquet", index=False)
        share = df["class"].value_counts(normalize=True).round(3).to_dict()
        print(f"{name}: {len(df):,} rows {share}")


if __name__ == "__main__":
    main()
