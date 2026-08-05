import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils import DIMENSIONS, DIMENSION_LABELS, EXPLORATORY_COLOR, LOGO_PATH, VALIDATED_COLOR, download_csv_button, load_app_csv, load_csv, page_header

st.set_page_config(page_title="Player Weakness Finder", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header(
    "Player Weakness Finder",
    "At every real defensive-danger moment (a shot conceded, a player dribbled past), who's furthest out of position relative to the rest of the defensive block?",
)

st.markdown(
    """
`diff_m` = each player's danger-moment gap minus their own *normal* positioning. A large positive `diff_m`
means genuinely worse-positioned specifically when it matters, not just naturally spread further from the
pack as part of a normal role (e.g. a fullback). Position gets you *which* player and *when*. Select a
player below to see *which of the 6 dimensions* was actually behind their flagged moments.
"""
)

THRESHOLDS = {"HSV squad": (10, 3), "Opponents": (5, 2)}
group = st.radio("Squad", ["HSV squad", "Opponents"], horizontal=True)
file = "weakness_summary_hsv_players.csv" if group == "HSV squad" else "weakness_summary_opponents.csv"
min_flagged, min_matches = THRESHOLDS[group]

df = load_csv(file)
df["confident"] = (df["times_flagged"] >= min_flagged) & (df["matches"] >= min_matches)
confident = df[df["confident"]].sort_values("diff_m", ascending=False)
exploratory = df[~df["confident"]]

st.caption(f"Confident tier: ≥{min_flagged} flagged instances across ≥{min_matches} matches. {len(confident)} confident, {len(exploratory)} exploratory.")

if not confident.empty:
    # confident is already sorted by diff_m descending (line 33), so iloc[0] there is the
    # biggest-gap player -- a DIFFERENT ranking from "most flagged" (highest times_flagged).
    # Previously both tiles showed the diff_m leader under a "most flagged" label (wrong: the
    # actual most-flagged confident player, e.g. Konigsdorffer at 102 flags/27 matches, never
    # appeared), and the 3rd tile re-sorted the same already-sorted frame, duplicating tile 1.
    biggest_gap = confident.iloc[0]
    most_flagged = confident.sort_values("times_flagged", ascending=False).iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Most flagged (confident tier)", most_flagged["player_name"], f"{int(most_flagged['times_flagged'])} times, {int(most_flagged['matches'])} matches")
    c2.metric("Its diff_m", f"{most_flagged['diff_m']:+.1f} m", "vs. their own normal positioning", delta_color="off")
    c3.metric("Largest diff_m (confident tier)", biggest_gap["player_name"], f"{biggest_gap['diff_m']:+.1f} m over {int(biggest_gap['times_flagged'])} flags", delta_color="off")

st.markdown("#### Confident-tier players: volume vs. genuine effect")
st.caption("Read this as a gradient, not a hard cutoff: top-right (high flags, high diff_m) are the strongest findings. Bottom-right (high flags, low diff_m) means frequently flagged but not actually worse than their own normal positioning, just their normal role.")
fig = px.scatter(
    confident, x="times_flagged", y="diff_m", size="matches", color="diff_m",
    color_continuous_scale="RdYlGn_r", hover_name="player_name",
    labels={"times_flagged": "Times flagged", "diff_m": "Diff (m): breakdown gap minus baseline gap"},
    hover_data={"matches": True, "avg_breakdown_gap_m": ":.1f", "avg_baseline_gap_m": ":.1f"},
)
fig.add_hline(y=0, line_dash="dash", line_color="gray")
fig.update_layout(height=480, coloraxis_colorbar_title="diff_m")
st.plotly_chart(fig, width="stretch")

st.markdown("---")
st.markdown("#### Drill down: which dimension was behind a specific player's flagged moments?")
involvement = load_app_csv("player_dimension_involvement.csv")
group_involvement = involvement[involvement["is_hsv"] == (group == "HSV squad")]
player_names = confident["player_name"].tolist() + exploratory.sort_values("times_flagged", ascending=False)["player_name"].tolist()
if player_names:
    selected = st.selectbox("Player", player_names)
    row = group_involvement[group_involvement["player_name"] == selected]
    if not row.empty:
        row = row.iloc[0]
        vals = [row[d] for d in DIMENSIONS]
        labels = [DIMENSION_LABELS[d] for d in DIMENSIONS]
        colors = [VALIDATED_COLOR if d == "synchronization" else EXPLORATORY_COLOR for d in DIMENSIONS]
        fig2 = go.Figure(go.Bar(x=labels, y=vals, marker_color=colors))
        fig2.update_layout(title=f"{selected}: fractional credit per dimension at their flagged moments", yaxis_title="Fractional credit (ties split evenly)", height=380)
        st.plotly_chart(fig2, width="stretch")
        st.caption("Green = Synchronization, the one statistically validated cause (see Where It Goes Wrong). Grey bars are real counts, not validated explanations; a dimension can score low at a flagged moment without being the reason it happened.")
    else:
        st.info("No dimension-diagnosis data for this player (may not appear in the breakdown-event set directly).")

tab1, tab2 = st.tabs(["Confident", "Exploratory (below confidence bar)"])
with tab1:
    confident_table = confident[["player_name", "times_flagged", "matches", "avg_breakdown_gap_m", "avg_baseline_gap_m", "diff_m"]].round(2)
    st.dataframe(confident_table, width="stretch", hide_index=True)
    download_csv_button(confident_table, "Download confident-tier table (CSV)", f"weakness_finder_{group.replace(' ', '_').lower()}.csv")
with tab2:
    st.caption("Real data, smaller sample: treat as suggestive, not confirmed.")
    st.dataframe(
        exploratory.sort_values("diff_m", ascending=False)[["player_name", "times_flagged", "matches", "avg_breakdown_gap_m", "avg_baseline_gap_m", "diff_m"]].round(2),
        width="stretch", hide_index=True,
    )

st.caption(
    "Assessment tool, not a diagnostic one: `diff_m` is a positional-gap pattern, controlled against each "
    "player's own normal positioning, not a statistically validated cause the way Synchronization is (see "
    "Pressing Phases). A large diff_m is worth a look on film, not a confirmed mistake on its own."
)
