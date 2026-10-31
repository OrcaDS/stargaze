import json

import pytest

from stargaze import export_demo

# Uses the shipped models and sample in models/ (tracked in git for the demo host).


@pytest.fixture(scope="module")
def data():
    return export_demo.build()


def test_every_case_the_page_offers_is_answered(data):
    per_object = 6 * sum(1 + 5 - bin(m).count("1") for m in range(32))  # noise x masks x typos
    assert len(data["answers"]) == len(export_demo.OBJECTS) * per_object
    for o in range(len(export_demo.OBJECTS)):
        for n in export_demo.NOISE:
            assert export_demo.key(o, n, 0b11111, -1) in data["answers"]
            assert export_demo.key(o, n, 0, 4) in data["answers"]


def test_seven_objects_of_each_type(data):
    types = [o["type"] for o in data["objects"]]
    assert {t: types.count(t) for t in set(types)} == {"Star": 7, "Galaxy": 7, "Quasar": 7}
    assert len({o["tag"] for o in data["objects"]}) == 21


def test_jname_matches_sdss_designations():
    assert export_demo.jname(187.2779158, 2.0523883) == "SDSS J122906.69+020308.5"  # 3C 273
    assert export_demo.jname(0.5, -0.01) == "SDSS J000200.00-000036.0"


@pytest.mark.parametrize("i", range(3))
def test_story_breaks_ordinary_model_but_not_stargaze(data, i):
    s = data["stories"][i]
    truth = data["objects"][s["obj"]]["type"]
    labels = data["labels"]
    clean = data["answers"][export_demo.key(s["obj"], 0, 0, -1)]
    broken = data["answers"][export_demo.key(s["obj"], s["noise"], s["mask"], s["typo"])]
    assert labels[clean[0]] == truth and labels[clean[3]] == truth  # both right when clean
    assert labels[broken[0]] != truth and broken[1] >= 0.9  # ordinary: confidently wrong
    assert labels[broken[3]] == truth  # Stargaze: still right


def test_scores_come_from_the_test_report(data):
    suites = json.loads(export_demo.REPORT.read_text())["suites"]
    s = suites["noise_8x"]
    assert data["scores"]["noise"]["8"] == [
        round(s["baseline_f1"] * 100),
        round(s["robust_f1"] * 100),
        round(s["trust"]["macro_f1_answered"] * 100),
        round(s["trust"]["coverage"] * 100),
    ]


def test_shipped_answers_file_is_up_to_date(data):
    shipped = json.loads(export_demo.OUT.read_text())
    assert shipped == json.loads(json.dumps(data)), "rerun: uv run python -m stargaze.export_demo"
