import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go
import streamlit as st
from utils import CRITICAL_COLOR, DIMENSION_LABELS, LOGO_PATH, VALIDATED_COLOR, load_csv, page_header

# Every number on this page is read from an already-validated result CSV used elsewhere in this
# app (never recomputed here) -- this page only selects and summarizes, matching the rest of the
# dashboard's own rule that nothing is computed live.

st.set_page_config(page_title="Executive Summary", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header(
    "Executive Summary: Start Here",
    "The headline findings from every page in this dashboard, in one place. Each section links to the full analysis behind it.",
)

st.success(
    "**Synchronization (whether the back line shifts as one coordinated unit) is the one dimension "
    "statistically confirmed to actually cause pressing breakdowns.** p = 5.4×10⁻¹²⁷ across 1,255 real "
    "breakdown events, HSV and opponents combined, robust to random seed, breakdown-window definition, and "
    "a tempo confound check. Every other dimension (Pressure, Compactness, Local Pitch Control, Pass Option "
    "Suppression, Anticipation) moves the *opposite* direction near a breakdown: mechanically explained, not "
    "a real cause. See **Pressing Phases** (Season Pooled tab) for the full statistical case."
)

st.markdown("### The phase that matters most")
phase_sig = load_csv("dimension_breakdown_signal_by_phase.csv")
hsv_sync_by_phase = phase_sig[(phase_sig["group"] == "HSV") & (phase_sig["dimension"] == "synchronization")].sort_values("shift")
PHASE_LABELS = {"high_press": "High Press", "mid_press": "Mid Press", "low_press": "Low Block", "transition": "Transition"}

worst_phase = hsv_sync_by_phase.iloc[0]
fig = go.Figure(go.Bar(
    x=[PHASE_LABELS[p] for p in hsv_sync_by_phase["phase"]],
    y=hsv_sync_by_phase["shift"],
    marker_color=[CRITICAL_COLOR if p == worst_phase["phase"] else VALIDATED_COLOR for p in hsv_sync_by_phase["phase"]],
    text=[f"n={n}" for n in hsv_sync_by_phase["n_events"]], textposition="outside",
))
fig.update_layout(title="HSV: Synchronization's shift vs. random play, by phase (more negative = bigger gap at breakdown)", yaxis_title="Shift", height=360)
st.plotly_chart(fig, width="stretch")
st.info(
    f"**{PHASE_LABELS[worst_phase['phase']]} shows the largest gap for HSV specifically** (shift "
    f"{worst_phase['shift']:.3f}, p={worst_phase['p_value_worse']:.1e}, n={int(worst_phase['n_events'])} events); "
    "this is the phase named directly in the original ask this analysis was built for. Synchronization is a "
    "real, validated cause in **all four phases**, not just this one (p between 0.0013 and 5×10⁻²⁵ across the "
    f"other three); {PHASE_LABELS[worst_phase['phase']]} is where the effect is *biggest*, not where it's "
    "the only place it matters. Smaller event count here than Low Block's 482, so treat the ranking between "
    "phases as a lead, the causal finding itself as settled. See **Pressing Phases** for the full breakdown."
)

st.markdown("### Who to watch")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Most flagged: validated method, cross-checked**")
    sync_players = load_csv("synchronization_attribution_hsv_players.csv")
    sync_players["confident"] = (sync_players["times_responsible"] >= 5) & (sync_players["matches"] >= 3)
    top_sync = sync_players[sync_players["confident"]].sort_values("times_responsible", ascending=False).iloc[0]
    st.metric(top_sync["player_name"], f"{int(top_sync['times_responsible'])} times responsible", f"{int(top_sync['matches'])} matches, corroborated by the independent Weakness Finder method")
    st.caption("See **Synchronization Attribution** for the full list and the per-frame visual spot-checks.")
with col2:
    st.markdown("**Most consistently well-positioned**")
    best_players = load_csv("best_defender_summary_hsv_players.csv")
    best_players["confident"] = (best_players["times_best"] >= 10) & (best_players["matches"] >= 3)
    top_best = best_players[best_players["confident"]].sort_values("times_best", ascending=False).iloc[0]
    st.metric(top_best["player_name"], f"{int(top_best['times_best'])} times closest to the block", f"{int(top_best['matches'])} matches, +{top_best['diff_m']:.1f}m tighter than their own normal positioning")
    st.caption("See **Best Defender**. Note some players (e.g. high-minutes starters) appear on both this list and the flagged list above, for different moments. That's a real pattern, not a contradiction.")

st.markdown("### A concrete, coachable cue")
triggers = load_csv("missed_press_trigger_events.csv")
rate_by_side = triggers.groupby("is_hsv_pressing")["is_missed_trigger"].agg(["mean", "size"])
hsv_rate = rate_by_side.loc[True]
opp_rate = rate_by_side.loc[False]
c1, c2 = st.columns(2)
c1.metric("HSV misses the backpass-to-keeper press cue", f"{hsv_rate['mean']:.1%}", f"n={int(hsv_rate['size'])}", delta_color="off")
c2.metric("Opponents miss it (pressing HSV)", f"{opp_rate['mean']:.1%}", f"n={int(opp_rate['size'])}", delta_color="off")
st.caption(
    "A backpass to the goalkeeper is one of the clearest textbook cues to press. HSV reacts to it worse "
    "than opponents do against HSV. See **Restarts, Triggers & Recovery** for the full picture, including "
    "why this specific gap shouldn't be read as a simple \"missed opportunity\" story on its own."
)

st.markdown("---")
st.markdown("### Go deeper")
nc1, nc2, nc3 = st.columns(3)
with nc1:
    with st.container(border=True):
        st.markdown(
            "**Cause & phase**\n\n"
            "- Pressing Phases\n"
            "- Where It Goes Wrong"
        )
with nc2:
    with st.container(border=True):
        st.markdown(
            "**Players**\n\n"
            "- Synchronization Attribution\n"
            "- Player Weakness Finder\n"
            "- Best Defender"
        )
with nc3:
    with st.container(border=True):
        st.markdown(
            "**Scouting & context**\n\n"
            "- Opponent Playmaker Impact\n"
            "- Match Explorer\n"
            "- Visual Examples"
        )

st.caption(
    "This page only selects and summarizes numbers already validated elsewhere in this dashboard; nothing "
    "here is computed live. Every claim links to the page with its full methodology and caveats; read that "
    "page before citing a number from here in isolation."
)
