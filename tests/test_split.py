import pandas as pd

from stargaze.split import split


def make(n=1000):
    classes = ["GALAXY"] * 600 + ["STAR"] * 200 + ["QSO"] * 200
    return pd.DataFrame({"psfMag_r": range(n), "class": classes[:n]})


def test_split_sizes_disjoint_stratified_and_deterministic():
    df = make()
    parts = split(df)
    assert [len(p) for p in parts.values()] == [700, 150, 150]
    idx = [set(p.index) for p in parts.values()]
    assert not (idx[0] & idx[1] or idx[0] & idx[2] or idx[1] & idx[2])
    for p in parts.values():
        assert p["class"].value_counts(normalize=True).round(2).to_dict() == {
            "GALAXY": 0.6,
            "STAR": 0.2,
            "QSO": 0.2,
        }
    assert parts["test"].index.equals(split(df)["test"].index)
