"""Stargaze demo (spec: Demo and API): break the input, compare baseline and robust.

Written for visitors with no data or astronomy background: plain words on the page, technical
detail in the README. Run: uv run streamlit run streamlit_app.py   (needs models/, see README)
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import streamlit as st

from stargaze.api import SAMPLES, Photometry, load_models, predict, to_row
from stargaze.augment import perturb
from stargaze.explain import COLOUR, NAME, describe
from stargaze.gold import BANDS, FEATURES, MAGS, MODEL_MAGS, add_colors
from stargaze.validate import validate

REPORT = Path(__file__).parent / "reports" / "test" / "metrics.json"
# The browser fetches the picture straight from SDSS; it is never a model input.
CUTOUT = "https://skyserver.sdss.org/dr17/SkyServerWS/ImgCutout/getjpeg?ra={}&dec={}&scale=0.3&width={}&height={}"
BAR = dict(u="#7b3fbf", g="#2ca02c", r="#d62728", i="#8c3b1a", z="#5a2410")
MODEL_NAME = {"baseline": "Ordinary model", "robust": "Stargaze"}
# Guided examples: rows of models/samples.parquet where both models are right on the clean object
# and the ordinary model is confidently wrong once broken (hand-picked; the charts show the
# average). Rebuilding the sample file changes the rows: re-pick them (tests/test_app.py checks).
SCENARIOS = {
    "Lose two colours": {
        "i": 42,
        "deleted": "gr",
        "story": "A quasar loses its green and red measurements. The ordinary model calls it a "
        "star and is very sure; Stargaze still says quasar.",
    },
    "Make it very noisy": {
        "i": 4,
        "noise": 8.0,
        "story": "A galaxy measured 8 times less precisely than normal. The ordinary model calls "
        "it a star; Stargaze still says galaxy.",
    },
    "Add a typo": {
        "i": 22,
        "typo": 3,
        "story": "A quasar's near-infrared value gets a misplaced decimal point (10 times too "
        "big). Stargaze's checks catch and remove it. The ordinary model then calls it a galaxy; "
        "Stargaze still says quasar.",
    },
}


@st.cache_resource
def resources():
    models = load_models()
    explainers = {  # SHAP on the raw boosted trees; temperature calibration keeps the ranking
        "baseline": shap.TreeExplainer(models["baseline"]),
        "robust": shap.TreeExplainer(models["robust"]["cal"].estimator.estimator),
    }
    samples = pd.read_parquet(SAMPLES)
    typical = add_colors(samples)[FEATURES].median()
    return models, explainers, samples, typical, json.loads(REPORT.read_text())["suites"]


models, explainers, samples, typical, suites = resources()
state = st.session_state


def picture(obj, px: int = 160) -> str:
    return CUTOUT.format(obj["ra"], obj["dec"], px, px)


def load_object(i: int | None = None) -> None:
    rng = np.random.default_rng()
    state.obj = samples.iloc[rng.integers(len(samples)) if i is None else i]
    state.noise_seed = int(rng.integers(2**31))  # same noise draw while the slider moves
    state.typo = state.story = None
    for b, m in zip(BANDS, MAGS, strict=True):
        state[f"mag_{b}"] = float(np.clip(state.obj[m], 10.0, 30.0))


def run_scenario(name: str) -> None:
    sc = SCENARIOS[name]
    load_object(sc["i"])
    state.noise_seed = sc["i"]  # the noise draw the example was picked with
    state.noise = sc.get("noise", 0.0)
    for b in BANDS:
        state[f"del_{b}"] = b in sc.get("deleted", "")
    if "typo" in sc:
        state.typo = (sc["typo"], state[f"mag_{BANDS[sc['typo']]}"] * 10)
    state.story = sc["story"]


def inject_typo() -> None:
    i = int(np.random.default_rng().integers(5))
    state.typo = (i, state[f"mag_{BANDS[i]}"] * 10)  # a misplaced decimal point: 19.2 -> 192


def clues(name: str, row: pd.Series, cls: str, n: int = 3) -> list[str]:
    """The n features that pushed hardest for or against cls (SHAP), in plain words."""
    classes = list(models["robust"]["cal"].classes_ if name == "robust" else models[name].classes_)
    v = explainers[name](row[FEATURES].to_frame().T.astype(float)).values[0, :, classes.index(cls)]
    # Features that read the same (e.g. a missing band behind a mag and two colours) are merged.
    pushes = pd.Series(v).groupby([describe(f, row, typical) for f in FEATURES]).sum()
    top = pushes[pushes.abs().sort_values(ascending=False).index[:n]]
    return [
        f"{text}: {'points to' if p > 0 else 'argues against'} {NAME[cls].lower()}"
        for text, p in top.items()
    ]


def fingerprint(clean: pd.Series, now: pd.Series):
    """The five brightnesses as bars, relative to the brightest clean band (= 100)."""
    ref = clean[MAGS].min()
    fig, ax = plt.subplots(figsize=(5, 2.6))
    x = np.arange(5)
    ax.bar(x, 100 * 10 ** (-0.4 * (clean[MAGS] - ref)), color="none", edgecolor="grey", ls="--")
    for k, (b, m) in enumerate(zip(BANDS, MAGS, strict=True)):
        if pd.isna(now[m]):
            ax.text(k, 5, "missing", ha="center", color="grey", rotation=90, va="bottom")
        else:
            ax.bar(k, 100 * 10 ** (-0.4 * (now[m] - ref)), color=BAR[b], alpha=0.85)
    ax.set_xticks(x, [COLOUR[b] for b in BANDS], fontsize=8)
    ax.set_ylabel("Brightness")
    ax.set_yticks([])
    ax.set_title("Light fingerprint (dashed = original measurement)", fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return fig


def show(fig) -> None:
    st.pyplot(fig)
    plt.close(fig)


if "obj" not in state:
    load_object()
# Gallery: the two brightest sample objects of each class (bright = clearest picture).
gallery = samples.sort_values("psfMag_r").groupby("class").head(2).sort_values("class")

with st.sidebar:
    st.header("Words used here")
    st.markdown(
        "- **Galaxy**: billions of stars far away; looks like a fuzzy patch.\n"
        "- **Star**: a single star in our own galaxy; a sharp point of light.\n"
        "- **Quasar**: the core of a distant galaxy, lit up by a giant black hole. It looks "
        "like a star, which is what makes it tricky.\n"
        "- **Colours**: the telescope measures brightness through five filters, from "
        "ultraviolet to infrared (most of them invisible to our eyes).\n"
        "- **Ordinary model**: learned only from clean, complete measurements.\n"
        "- **Stargaze**: also learned from damaged copies, checks its input, and says "
        "*not sure* rather than guess."
    )
    n8, b2 = suites["noise_8x"], suites["random_2_bands"]
    st.subheader("Tested on 37,775 objects it never saw")
    st.markdown(
        "Score out of 100 (higher is better):\n"
        f"- Very noisy: ordinary {n8['baseline_f1'] * 100:.0f} · "
        f"Stargaze {n8['robust_f1'] * 100:.0f}\n"
        f"- Two colours missing: ordinary {b2['baseline_f1'] * 100:.0f} · "
        f"Stargaze {b2['robust_f1'] * 100:.0f}"
    )

WEB_DEMO = "https://stargaze.automate-tasks.workers.dev/"

st.title("Stargaze")
st.write(
    "Telescopes measure how bright an object is through five colour filters. From those five "
    "numbers alone, can a computer tell a **star** from a **galaxy** from a **quasar**? "
    "Real measurements are often noisy, incomplete or wrong. Break them and see which model "
    "copes: an ordinary one, or Stargaze, which is built to admit when it isn't sure."
)
st.caption(f"Prefer a guided tour? [Try the new version]({WEB_DEMO}).")

st.subheader("Try a quick demo")
for col, name in zip(st.columns(len(SCENARIOS)), SCENARIOS, strict=True):
    col.button(name, on_click=run_scenario, args=(name,), use_container_width=True)
if state.story:
    st.info(state.story)

st.subheader("Or do it yourself: 1. pick an object")
for col, (i, obj) in zip(st.columns(len(gallery)), gallery.iterrows(), strict=True):
    col.image(picture(obj, 120))
    col.button(
        NAME[obj["class"]], key=f"pick_{i}", on_click=load_object, args=(samples.index.get_loc(i),)
    )
st.button("Surprise me (random object)", on_click=load_object)

st.subheader("2. Break the measurements")
left, right = st.columns([2, 3])
with left:
    st.image(picture(state.obj), caption="Picture for you only: the models never see it")
    st.markdown(f"Actually: **{NAME[state.obj['class']]}**")
with right:
    noise = st.slider("Add noise (× the normal measurement error)", 0.0, 8.0, step=0.5, key="noise")
    st.caption("Remove colours:")
    deleted = [
        b
        for b, c in zip(BANDS, st.columns(5), strict=True)
        if c.checkbox(COLOUR[b], key=f"del_{b}")
    ]
    c1, c2 = st.columns(2)
    c1.button("Add a typo", on_click=inject_typo)
    c2.button("Remove typo", on_click=lambda: state.update(typo=None))
    with st.expander("Fine-tune the five brightness values (smaller number = brighter)"):
        for b in BANDS:
            st.slider(COLOUR[b], 10.0, 30.0, step=0.01, key=f"mag_{b}")

df = pd.DataFrame([state.obj])
df[MAGS] = [[state[f"mag_{b}"] for b in BANDS]]
df = perturb(df, np.random.default_rng(state.noise_seed), noise, mask_p=0.0)
for b in deleted:  # a removed colour hides both its PSF and model mag, as in training
    df[[f"psfMag_{b}", f"modelMag_{b}"]] = np.nan
if state.typo:
    df[MAGS[state.typo[0]]] = state.typo[1]
row = df.iloc[0]
values = {b: row[m] for b, m in zip(BANDS, MAGS, strict=True)}
values |= {f"{b}_model": row[m] for b, m in zip(BANDS, MODEL_MAGS, strict=True)}
values = {k: None if pd.isna(v) else float(v) for k, v in values.items()}
checked, corrupted = validate(to_row(Photometry(**values)))
checked = add_colors(checked).iloc[0]  # what the models see

show(fingerprint(state.obj, checked))
problems = [
    f"{COLOUR[b].capitalize()} is missing" for b in BANDS if pd.isna(checked[f"psfMag_{b}"])
]
if corrupted.iloc[0]:
    problems.append("an impossible value was caught and removed")
if problems:
    st.warning("What's wrong with this input: " + "; ".join(problems) + ".")

st.subheader("3. Who copes?")
for col, name in zip(st.columns(2), ("baseline", "robust"), strict=True):
    r = predict(models, Photometry(**values, model=name))
    lean = max(r["probabilities"], key=r["probabilities"].get)
    conf = r["probabilities"][lean]
    with col:
        st.markdown(f"#### {MODEL_NAME[name]}")
        st.metric("Answer", NAME[r["label"]])
        if r["abstained"]:
            why = (
                "this doesn't look like anything it learned from"
                if "unusual_input" in r["flags"]
                else "the clues left aren't enough to decide"
            )
            st.caption(f"Won't guess: {why}. It leaned toward {NAME[lean].lower()} ({conf:.0%}).")
        else:
            st.caption(
                f"{'Very sure' if conf >= 0.9 else 'Fairly sure' if conf >= 0.6 else 'Leaning'} "
                f"({conf:.0%})"
            )
        for c, p in sorted(r["probabilities"].items(), key=lambda kv: -kv[1]):
            st.progress(p, text=f"{NAME[c]} {p:.0%}")
        st.markdown("**Why?** The strongest clues:")
        st.markdown("\n".join(f"- {c}" for c in clues(name, checked, lean)))

st.subheader("How this compares on 37,775 test objects")
n_missing = sum(pd.isna(checked[m]) for m in MAGS)
curves = [
    ("Noise (× normal error)", [0, 1, 2, 3, 5, 8], "noise_{}x", noise),
    ("Colours missing (of 5)", [0, 1, 2, 3, 4], "random_{}_bands", n_missing),
]
for col, (xlabel, xs, key, here) in zip(st.columns(2), curves, strict=True):
    fig, ax = plt.subplots(figsize=(4, 3))
    for name in ("baseline", "robust"):
        ys = [suites[key.format(x)][f"{name}_f1"] * 100 for x in xs]
        ax.plot(xs, ys, "o-", label=MODEL_NAME[name])
    ax.axvline(here, color="grey", ls="--", label="you are here")
    ax.set(xlabel=xlabel, ylabel="Score out of 100", ylim=(0, 100))
    ax.legend(fontsize=8)
    with col:
        show(fig)
st.caption(
    "Score: how often each model is right, averaged so each kind of object counts equally "
    "(macro F1). Details and code in the project README."
)
