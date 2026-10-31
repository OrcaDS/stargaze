import pytest

from stargaze.bronze import HI, LO, chunk_bounds, parse_csv


def test_chunks_cover_range_without_gaps():
    bounds = chunk_bounds()
    assert bounds[0][0] == LO and bounds[-1][1] == HI
    assert all(a[1] == b[0] for a, b in zip(bounds, bounds[1:], strict=False))


def test_parse_keeps_ids_beyond_int64():
    text = (
        "#Table1\nspecObjID,class,objID,zWarning\n14126941158849665024,QSO,1237654605865484363,0\n"
    )
    df = parse_csv(text)
    assert df["specObjID"].iloc[0] == 14126941158849665024


def test_parse_rejects_error_page():
    with pytest.raises(RuntimeError, match="SkyServer error"):
        parse_csv("<html>Query timeout</html>")
