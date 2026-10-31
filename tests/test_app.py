import pytest
from streamlit.testing.v1 import AppTest

# Uses the shipped models and sample in models/ (tracked in git for the demo host).
APP = "../streamlit_app.py"


def _truth(at: AppTest) -> str:
    return next(m.value for m in at.markdown if m.value.startswith("Actually")).split("**")[1]


def test_demo_runs_and_stargaze_is_not_sure_on_ultraviolet_alone():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    for b in "griz":
        at.checkbox(key=f"del_{b}").check()
    at.run()
    assert not at.exception
    assert at.metric[1].value == "Not sure"  # u alone is a blocked band pattern


@pytest.mark.parametrize("name", ["Lose two colours", "Make it very noisy", "Add a typo"])
def test_scenario_breaks_ordinary_model_but_not_stargaze(name):
    at = AppTest.from_file(APP, default_timeout=60).run()
    next(b for b in at.button if b.label == name).click().run()
    assert not at.exception
    ordinary, stargaze = (m.value for m in at.metric)
    assert ordinary != _truth(at) and stargaze == _truth(at)
