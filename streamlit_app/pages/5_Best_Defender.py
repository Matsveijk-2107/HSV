import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.express as px
import streamlit as st
from utils import LOGO_PATH, download_csv_button, load_csv, page_header

st.set_page_config(page_title="Best Defender", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header(
    "\"Best Defender\": the Positive Counterpart",
    "Same method as the Weakness Finder, flipped: at the same real danger moments, who stays closest to the defensive block instead of furthest?",
)

st.markdown(
    """
`diff_m` = each player's own *normal* positioning gap minus their danger-moment gap. A large positive `diff_m`
means genuinely tighter specifically when it matters, not just naturally central as part of a normal role
(e.g. a centre-back). Times-best gets you *how often*; `diff_m` gets you *whether it was actually earned*.
"""
)

THRESHOLDS = {"HSV squad": (10, 3), "Opponents": (5, 2)}
group = st.radio("Squad", ["HSV squad", "Opponents"], horizontal=True)
file = "best_defender_summary_hsv_players.csv" if group == "HSV squad" else "best_defender_summary_opponents.csv"
min_flagged, min_matches = THRESHOLDS[group]

df = load_csv(file)
df["confident"] = (df["times_best"] >= min_flagged) & (df["matches"] >= min_matches)
confident = df[df["confident"]].sort_values("diff_m", ascending=False)
exploratory = df[~df["confident"]]

st.caption(f"Confident tier: ≥{min_flagged} times best across ≥{min_matches} matches. {len(confident)} confident, {len(exploratory)} exploratory.")

if not confident.empty:
    # confident is sorted by diff_m descending (line 23), so iloc[0] there is the biggest-gap
    # player -- a DIFFERENT ranking from "most consistent" (highest times_best). Previously both
    # this tile and its label showed the diff_m leader (e.g. Muheim, 20 times) while the actual
    # most-consistent confident player (Remberg, 227 times across 32 matches) never appeared --
    # same bug already found and fixed on the Weakness Finder.
    biggest_gap = confident.iloc[0]
    most_consistent = confident.sort_values("times_best", ascending=False).iloc[0]
    c1, c2, c3 = st.columns(3)
    # Player name as the metric's label, not its value: st.metric's value line doesn't wrap and
    # hard-truncates with an ellipsis on longer names ("Miro Max Maria Muheim" clipped to "Miro
    # Max Mar..."); the label line wraps cleanly instead, and stays safe regardless of name length.
    # The category framing ("most consistent", "largest diff_m") moved to its own caption above
    # the tile: with 3 narrow columns instead of 2, even the delta line truncated once it also
    # had to carry that framing ("32 matches; most consistent (conf...").
    with c1:
        st.caption("Most consistent (confident tier)")
        st.metric(most_consistent["player_name"], f"{int(most_consistent['times_best'])} times", f"{int(most_consistent['matches'])} matches", delta_color="off")
    c2.metric("Its diff_m", f"{most_consistent['diff_m']:+.1f} m", "vs. their own normal positioning", delta_color="off")
    with c3:
        st.caption("Largest diff_m (confident tier)")
        st.metric(biggest_gap["player_name"], f"{biggest_gap['diff_m']:+.1f} m", f"over {int(biggest_gap['times_best'])} times", delta_color="off")

st.markdown("#### Confident-tier players: volume vs. genuine effect")
st.caption("Top-right: frequently the tightest AND meaningfully tighter than their own normal positioning, not just naturally central.")
fig = px.scatter(
    confident, x="times_best", y="diff_m", size="matches", color="diff_m",
    color_continuous_scale="Greens", hover_name="player_name",
    labels={"times_best": "Times best-positioned", "diff_m": "Diff (m): baseline gap minus breakdown gap"},
    hover_data={"matches": True, "avg_breakdown_gap_m": ":.1f", "avg_baseline_gap_m": ":.1f"},
)
fig.add_hline(y=0, line_dash="dash", line_color="gray")
fig.update_layout(height=480, coloraxis_colorbar_title="diff_m")
st.plotly_chart(fig, width="stretch")

if group == "HSV squad":
    st.info(
        "**Königsdörffer genuinely tops both lists: #2 of 15 on Weakness Finder (+11.2m) and #2 of 14 here "
        "(+14.3m), zero overlapping frames between his \"best\" and \"worst\" appearances.** A real, symmetric "
        "boom-or-bust pattern, not a contradiction. Muheim is a different story, worth being precise about: "
        "he tops *this* list (#1, +16.4m) but is only #10 of 15 on Weakness Finder (+3.0m, barely above the "
        "confidence bar); his \"worst\" moments are mild, not extreme. Both being high-minutes starters "
        "explains why they show up on *both* lists at all (far more chances to land at either tail than a "
        "squad player gets), but frequency isn't diff_m, which is normalized against each player's own "
        "baseline, not raw counts. That's exactly why Königsdörffer's case is the genuinely notable one."
    )
if group == "Opponents":
    st.success(
        "**Independent confirmation, unprompted:** this list includes Joshua Kimmich, Maximilian Arnold, "
        "Rani Khedira, Nicolas Seiwald: recognizable, elite defensive midfielders, found without any "
        "positional label being fed into the method."
    )

tab1, tab2 = st.tabs(["Confident", "Exploratory (below confidence bar)"])
with tab1:
    confident_table = confident[["player_name", "times_best", "matches", "avg_breakdown_gap_m", "avg_baseline_gap_m", "diff_m"]].round(2)
    st.dataframe(confident_table, width="stretch", hide_index=True)
    download_csv_button(confident_table, "Download confident-tier table (CSV)", f"best_defender_{group.replace(' ', '_').lower()}.csv")
with tab2:
    st.caption("Real data, smaller sample: treat as suggestive, not confirmed.")
    st.dataframe(
        exploratory.sort_values("diff_m", ascending=False)[["player_name", "times_best", "matches", "avg_breakdown_gap_m", "avg_baseline_gap_m", "diff_m"]].round(2),
        width="stretch", hide_index=True,
    )

st.caption(
    "Assessment tool, not a diagnostic one: `diff_m` is a positional-gap pattern, controlled against each "
    "player's own normal positioning, not a statistically validated cause the way Synchronization is (see "
    "Pressing Phases). A player topping this list is a real, coachable pattern to reinforce, not proof they "
    "single-handedly prevented anything."
)
