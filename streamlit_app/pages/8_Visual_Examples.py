import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
from utils import DIMENSION_LABELS, LOGO_PATH, page_header

st.set_page_config(page_title="Visual Examples", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header(
    "Visual Examples: Face-Validity Checks",
    "Real pitch plots from real matches, not just numbers. Blue = defending team, red = attacking team, gray arrows = velocity.",
)

IMG_DIR = Path(__file__).resolve().parents[1].parent / "results" / "visual_validation"

tab1, tab2, tab3 = st.tabs(["Per-Dimension Extremes", "Synchronization Spot-Check (Muheim)", "One Match, End-to-End"])

with tab1:
    st.markdown(
        "For each dimension, the highest- and lowest-scoring frame in a real match (DFL-MAT-J041UB, HSV "
        "defending), plotted from actual tracking positions. Checks whether the metric's value corresponds "
        "to what a human would judge, not just formula-matching."
    )
    dim = st.selectbox("Dimension", list(DIMENSION_LABELS.keys()), format_func=lambda d: DIMENSION_LABELS[d])
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Highest**")
        p = IMG_DIR / f"DFL-MAT-J041UB_team0_{dim}_highest.png"
        if p.exists():
            st.image(str(p), width="stretch")
    with c2:
        st.markdown("**Lowest**")
        p = IMG_DIR / f"DFL-MAT-J041UB_team0_{dim}_lowest.png"
        if p.exists():
            st.image(str(p), width="stretch")
    if dim == "synchronization":
        st.warning(
            "Synchronization's highest-scoring frame (0.950) shows players essentially standing still, not "
            "actively moving together: a genuine, confirmed structural limitation. "
            "`max(n_fwd,n_bwd)/N` can never fall below 0.5, so the metric can't distinguish coordinated "
            "active movement from collective stillness."
        )
    if dim == "pressure":
        st.warning(
            "**Pressure=0 doesn't mean \"no defender is nearby\": it means no attacker clearly has the ball "
            "at their feet.** Checked directly against the lowest frame here (frame 10250): the nearest "
            "defender is only 2.96m from the ball, but the nearest *attacker* is 3.88m from it, past the "
            "2.0m threshold the formula uses to decide who's actually carrying it. This is a ball-in-transit "
            "moment (mid-pass or a loose ball), not a marking situation. Pressure measures time to close down "
            "a **ball carrier**, not proximity to wherever the ball physically is; with nobody in clear "
            "control, there's no carrier to press, so it correctly reads 0 even with defenders standing close "
            "to the ball's flight path."
        )

with tab2:
    st.markdown(
        "Muheim's highest-deviation Synchronization-flagged frames, checked directly rather than trusted, "
        "twice, since the si_v2 formula rebuild (see **Synchronization Attribution**) could have shifted "
        "which frames rank highest. It mostly didn't: frames 1-3 below are the original top-3 under both the "
        "old and new attribution logic. **Mixed, honest result on those**: 1 clear match, 2 inconclusive from "
        "static images. Rank 4 *did* change with the fix, and was checked fresh (frame 5 below): a clean, "
        "textbook example of the corrected mechanism specifically."
    )
    captions = [
        "Frame 1: ambiguous, hard to read at this scale",
        "Frame 2: CLEAR match, back line drifting one way, Muheim moving opposite, right at the byline near the ball",
        "Frame 3: inconclusive, Muheim's marker overlaps the ball",
        "Frame 4 (old mechanism): same passage of play as Frame 3, 11 frames later, same issue",
        "Frame 5 (new rank 4, corrected mechanism): CLEAR match, Muheim (circled) shows no velocity arrow while the rest of the back line visibly moves in a consistent direction; not one player running the wrong way, one player not moving while everyone else is",
    ]
    filenames = ["muheim_check_1.png", "muheim_check_2.png", "muheim_check_3.png", "muheim_check_4.png", "muheim_check_5_corrected.png"]
    cols = st.columns(2)
    for i, (filename, caption) in enumerate(zip(filenames, captions)):
        p = IMG_DIR / filename
        with cols[i % 2]:
            if p.exists():
                st.image(str(p), caption=caption, width="stretch")

with tab3:
    st.markdown(
        "One real breakdown event (HSV vs. Heidenheim, 2025-09-20), walked through end-to-end: raw tracking "
        "→ six dimension values → TPR recomputed and matched the checkpoint exactly → Synchronization flagged "
        "as weakest → resolved to a named defender (Muheim) whose position visually matches the story."
    )
    p = IMG_DIR / "demo_match_frame36863.png"
    if p.exists():
        st.image(str(p), width="stretch")
    st.caption("HSV's back line is bunched on the right near the ball; Muheim (circled) sits isolated well below and away from that cluster, visibly out of step with where the line shifted to.")
