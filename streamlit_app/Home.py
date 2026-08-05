import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st
from utils import DIMENSION_LABELS, DIMENSION_WEIGHTS, DIMENSIONS, LOGO_PATH, load_csv, page_header

st.set_page_config(page_title="HSV Pressing Analysis", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")

page_header(
    "HSV Team Pressing Response (TPR): Season Dashboard",
    "Hamburger SV, 2025-26 season, 34 matches. Every number here traces back to a validated result CSV; nothing on this page is computed live.",
)

st.info(
    "**Short on time? See Executive Summary.** It has the headline findings from every page in this "
    "dashboard on one screen, with links to the full analysis behind each one. This page goes deeper on "
    "the methodology itself: the composite formula, what each dimension measures, and why only "
    "Synchronization is validated."
)

st.markdown(
    "This dashboard is built on TPR (Team Pressing Response), a composite metric scoring how well a team "
    "presses at every moment it doesn't have the ball."
)

st.markdown("#### The composite formula: a weighted sum of six components, each scored 0–1 per frame")

PHASE_WEIGHT_LABELS = {
    "Deployed (thesis default)": None,
    "HSV season-pooled (recalibrated)": "pooled (reference)",
    "High Press": "high_press",
    "Mid Press": "mid_press",
    "Low Block": "low_press",
    "Transition (5s after recovery)": "transition",
}
weight_choice = st.selectbox(
    "Weights shown below",
    list(PHASE_WEIGHT_LABELS.keys()),
    help="The number labeled TPR everywhere else in this dashboard is always computed with the deployed "
    "(thesis-default) weights. That hasn't changed. These others show what the weights would be if "
    "recalibrated on HSV's own real data, and how much they shift by pressing phase; see Pressing Phases "
    "for the full analysis and why a fixed weighting isn't a fair comparison across styles.",
)

phase_key = PHASE_WEIGHT_LABELS[weight_choice]
if phase_key is None:
    weights_to_show = DIMENSION_WEIGHTS
else:
    phase_weights = load_csv("phase_specific_weights_v2.csv")
    row = phase_weights[phase_weights["phase"] == phase_key].set_index("metric")["weight"]
    weights_to_show = {dim: row[dim] for dim in DIMENSIONS}

# 3 columns x 2 rows, not 6 in one row -- six equal-width columns left the longer labels
# (Anticipation (DAI), Pass Option Suppression, Local Pitch Control) and even the plain
# percentage values clipped with an ellipsis at normal window widths.
ranked = sorted(weights_to_show.items(), key=lambda kv: -kv[1])
for row_start in (0, 3):
    cols = st.columns(3)
    for col, (dim, weight) in zip(cols, ranked[row_start:row_start + 3]):
        with col:
            deployed_weight = DIMENSION_WEIGHTS[dim]
            delta = None if phase_key is None else f"{(weight - deployed_weight) * 100:+.1f} pts vs. deployed"
            st.metric(DIMENSION_LABELS[dim], f"{weight:.1%}", delta)

if phase_key is not None:
    st.caption(
        "Recalibrated on HSV's own 2025-26 data, and corrected once already after a direct challenge: the "
        "first version targeted Ridge regression at PC1 alone (the thesis's own method), which turned out to "
        "structurally miss Compactness and Local Pitch Control entirely. Checked directly: in a low block, "
        "both load almost exactly zero onto PC1 but dominate PC2 almost exclusively (a real, substantial "
        "second axis, ~20% of variance); a PC1-only target is blind to it. Fixed by using the top-2 "
        "components together; Compactness in a low block went from 1.0% to 20.1%, LPC from 1.4% to 16.0%. "
        "**Tested, not just untried:** a phase-adjusted composite score built from these weights was still "
        "checked head-to-head against the deployed TPR at real breakdown moments. It does not detect "
        "breakdowns better in any phase (both versions read as *better*, not worse, right before a real "
        "breakdown, since they average together dimensions that improve mechanically near goal with the one, "
        "Synchronization, that doesn't; this holds true regardless of exactly how the six are weighted). "
        "That's exactly why every causal claim in this dashboard uses the six dimensions decomposed, never "
        "raw TPR. See **Pressing Phases** for the decomposed test these weights should not be confused with."
    )

with st.expander("What each dimension measures"):
    st.markdown(
        """
- **Pressure**: how quickly the fastest-closing defender could reach the ball *carrier* (time-to-intercept based). Requires a clear carrier, an attacker within ~2m of the ball, so it reads 0 during a pass in transit or a loose ball, even with defenders standing right next to the ball's flight path. See Visual Examples for a real frame showing exactly this.
- **Compactness**: how tight the defensive shape is right now vs. this team's own most-stretched moment in the match.
- **Local Pitch Control (LPC)**: how much of the space immediately around the ball the defense actually controls, cell by cell.
- **Pass Option Suppression (POS)**: what fraction of the ball carrier's realistic passing lanes are blocked.
- **Anticipation (DAI)**: how many defenders proactively got near the ball, and how tightly, before it arrived.
- **Synchronization (SI)**: whether the back line is shifting as one coordinated block or fragmented.
        """
    )

st.success(
    "**The headline finding:** of these six dimensions, only **Synchronization** is statistically confirmed "
    "to be worse at real breakdown moments than in ordinary defending (p = 5.4×10⁻¹²⁷, robust across random "
    "seeds, breakdown-window definitions, and a tempo confound check). Every other dimension actually measures "
    "*better*, not worse, right before a breakdown: a shot or dribble-past means the ball is near goal, which "
    "mechanically draws more defenders into the area regardless of whether the press is working. "
    "See **Pressing Phases** (Season Pooled tab) for the full story."
)
st.caption(
    "Synchronization's own formula was later rebuilt for this dashboard too. Its directional term carried no "
    "signal at all (tested two independent ways), so it was dropped rather than patched around. The improved "
    "version is even more significant (pooled p = 2.3×10⁻¹⁷⁸). See **Synchronization Attribution**."
)

st.markdown("### How to use this dashboard")

nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    with st.container(border=True):
        st.markdown("**Which player is responsible?**")
        st.markdown(
            "- **Synchronization Attribution**: the validated one, cross-checked against an independent method\n"
            "- **Player Weakness Finder** / **Best Defender**: furthest out of position vs. closest to the block at real danger moments, with a per-player dimension drill-down"
        )
    with st.container(border=True):
        st.markdown("**Scouting an opponent?**")
        st.markdown("- **Opponent Playmaker Impact**: which opposing players get more time on the ball than their position alone would predict, role-controlled")

with nav_col2:
    with st.container(border=True):
        st.markdown("**Why did it break down?**")
        st.markdown(
            "- **Pressing Phases**: the season-wide answer (Season Pooled tab) and the phase-specific breakdown\n"
            "- **Where It Goes Wrong**: the same test split for HSV specifically, plus a team strength/weakness profile"
        )
    with st.container(border=True):
        st.markdown("**Explore or sanity-check it yourself?**")
        st.markdown(
            "- **Match Explorer**: one match, one minute window, full frame-level detail\n"
            "- **Visual Examples**: real pitch plots for the extreme frames of each dimension"
        )

with nav_col3:
    with st.container(border=True):
        st.markdown("**Does it depend on the situation?**")
        st.markdown(
            "- **Pressing Phases**: high press, mid press, low block, and the 5s transition after a recovery, with cause and players broken out per phase\n"
            "- **Season Patterns**: home/away, fatigue, live game state, weather\n"
            "- **Restarts, Triggers & Recovery**: corners/throw-ins/goal-kicks, backpass-to-keeper pressing, and how fast HSV wins the ball back"
        )

st.warning(
    "**Use with care:** **Frame-Level Mistake Attribution** looks at every defending frame rather than just "
    "the ~1,255 real danger moments the rest of this dashboard is built on. Three of its six dimensions (LPC, "
    "Anticipation, POS) carry a likely positional-role bias even after correcting for playing time; check its "
    "own caveats before citing a name from it."
)

st.caption(
    "Every number on every page traces back to a saved result file. A finding is only reported as a *cause* "
    "once it's tested against a random baseline from the same context, not just observed to look different "
    "from a raw count. Where a result is descriptive rather than causally validated, the page says so directly."
)
