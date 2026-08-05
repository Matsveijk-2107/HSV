import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils import DIMENSIONS, DIMENSION_LABELS, HSV_COLOR, LOGO_PATH, OPPONENT_COLOR, page_header

# This page's data lives in the same results/ directory as the rest of the
# app (dimension_mistake_attribution.py / aggregate_dimension_mistakes.py),
# so it can use load_csv... except those helpers aren't imported by name
# here to keep this page's own confidence-tier constants explicit and
# visible in one place, matching Player Weakness Finder's pattern.
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"

ROLE_CONFOUNDED = {"lpc", "anticipation", "pos"}

st.set_page_config(page_title="Frame-Level Mistake Attribution", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header(
    "Frame-Level Mistake Attribution",
    "A different question from every other page here: not \"who was out of position at a real danger "
    "moment\" (the ~1,255 discrete events used elsewhere), but \"on every single defending frame, why "
    "isn't each of the 6 dimensions higher, and who's the specific reason,\" continuous, not "
    "event-triggered, and not gated on TPR being low.",
)

st.error(
    "**Local Pitch Control, Anticipation, and Pass Option Suppression still show a likely "
    "positional-role bias even after correcting for playing time.** A lone advanced forward is "
    "structurally more likely to be the geometric outlier in these three checks, regardless of real "
    "defending quality. Compactness, Synchronization, and Pressure read as more trustworthy, meaning "
    "less prone to *this specific role-bias in who gets picked*, **not** that they're validated causes "
    "of breakdowns. Only Synchronization has passed that test (see Pressing Phases); Compactness and "
    "Pressure have not. None of the six has been checked against footage yet."
)

with st.expander("Method: how each dimension's mistake is attributed (click to expand)"):
    st.markdown(
        """
- **Pressure**: among defenders within 15m of the ball carrier (the metric's own radius), the
  *second*-fastest closer, not the fastest; someone clearly in position to help press, not the one
  leading it. Only attributed when 2+ defenders are in range.
- **Compactness**: whichever defender's removal would shrink the team's convex hull the most
  (leave-one-out hull-area test), not just "furthest from the average."
- **Local Pitch Control**: the single worst-controlled cell in the 15m grid around the ball, attributed
  to that cell's own best (fastest) defender.
- **Pass Option Suppression**: of the carrier's open passing lanes (not blocked within 2.5m by any
  defender), the most exposed one, attributed to its nearest defender.
- **Anticipation**: **exploratory, not a reuse of a validated formula** like the other five. DAI is a
  team count (defenders within 5m), not an individual quantity; this uses a new, unvalidated heuristic:
  the closest defender still outside 5m.
- **Synchronization**: identical logic to the validated Synchronization Attribution page, whoever moves
  against the team's majority direction.

Goalkeepers are excluded from every check (a keeper sitting apart from the outfield block by design
would otherwise dominate Compactness/Synchronization purely from role, not failure; caught on a first
pass before this page shipped).
        """
    )

team_df = pd.read_csv(RESULTS_DIR / "team_dimension_mistakes_per_match.csv", index_col=0)
player_df = pd.read_csv(RESULTS_DIR / "player_dimension_mistakes.csv")

st.markdown("### Team-level: mistakes per match, by dimension")
st.caption(
    "Raw counts per match, not yet controlled for how much defending each side actually did that "
    "match. HSV showing more than opponents in every dimension is consistent with facing more "
    "attacking phases per game, not necessarily worse execution. Cross-reference against the "
    "properly-tested HSV-vs-opponents comparison in Where It Goes Wrong before reading this as a gap."
)
fig = go.Figure()
for side, color in [("Opponents", OPPONENT_COLOR), ("HSV", HSV_COLOR)]:
    fig.add_trace(go.Bar(name=side, x=[DIMENSION_LABELS[d] for d in DIMENSIONS], y=team_df.loc[side, DIMENSIONS], marker_color=color))
fig.update_layout(barmode="group", height=380, yaxis_title="Mistakes per match")
st.plotly_chart(fig, width="stretch")

st.markdown("### Player-level: who, and in which dimension")
st.caption(
    "Rate per 1000 defending frames present, not a raw count. A starter who plays every minute would "
    "otherwise outrank a substitute purely from more time on the pitch. Confidence gating still runs on "
    "the raw count/match-count (HSV: ≥10 flags across ≥3 matches; opponents: ≥5 across ≥2) before a rate is "
    "shown, so it isn't computed from a handful of frames."
)

squad = st.radio("Squad", ["HSV squad", "Opponents"], horizontal=True)
side_key = "hsv" if squad == "HSV squad" else "opponent"
dim = st.selectbox("Dimension", DIMENSIONS, format_func=lambda d: DIMENSION_LABELS[d])

if dim in ROLE_CONFOUNDED:
    st.warning(f"{DIMENSION_LABELS[dim]} is one of the three likely role-confounded dimensions; see the warning above before treating this ranking as a real weakness list.")

side_df = player_df[(player_df["side"] == side_key) & (player_df["dimension"] == dim)]
confident = side_df[side_df["confident"]].sort_values("mistakes_per_1000_frames", ascending=False)
exploratory = side_df[~side_df["confident"]].sort_values("mistakes_per_1000_frames", ascending=False)

if confident.empty:
    st.info("No player clears the confidence bar for this dimension/squad.")
else:
    fig2 = px.bar(
        confident.head(15), x="mistakes_per_1000_frames", y="player_name", orientation="h",
        labels={"mistakes_per_1000_frames": "Mistakes per 1000 defending frames", "player_name": ""},
        hover_data={"times_flagged": True, "matches": True},
        color="mistakes_per_1000_frames", color_continuous_scale="RdYlGn_r",
    )
    fig2.update_layout(height=max(360, 28 * min(15, len(confident))), yaxis={"categoryorder": "total ascending"}, coloraxis_colorbar_title="/1000 frames")
    st.plotly_chart(fig2, width="stretch")

tab1, tab2 = st.tabs(["Confident", "Exploratory (below confidence bar)"])
with tab1:
    st.dataframe(
        confident[["player_name", "mistakes_per_1000_frames", "times_flagged", "matches"]].rename(
            columns={"player_name": "Player", "mistakes_per_1000_frames": "Rate /1000 frames", "times_flagged": "Times flagged", "matches": "Matches"}
        ),
        hide_index=True, width="stretch",
    )
with tab2:
    st.caption("Real data, smaller sample: treat as suggestive, not confirmed.")
    st.dataframe(
        exploratory[["player_name", "mistakes_per_1000_frames", "times_flagged", "matches"]].rename(
            columns={"player_name": "Player", "mistakes_per_1000_frames": "Rate /1000 frames", "times_flagged": "Times flagged", "matches": "Matches"}
        ),
        hide_index=True, width="stretch",
    )
