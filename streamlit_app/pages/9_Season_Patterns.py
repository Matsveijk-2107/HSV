import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils import CRITICAL_COLOR, EXPLORATORY_COLOR, HSV_COLOR, LOGO_PATH, VALIDATED_COLOR, load_app_csv, load_csv, page_header

st.set_page_config(page_title="Season Patterns", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header("Season-Level Patterns", "Team-level, season-wide pressing trends: home/away, fatigue, game state, weather.")

RESULT_COLORS = {"Win": VALIDATED_COLOR, "Draw": EXPLORATORY_COLOR, "Loss": CRITICAL_COLOR}

# Real findings first, null results (confound-elimination housekeeping, not presentation
# material) last -- Home/Away and Weather are both "checked and ruled out," not actionable.
tab2, tab3, tab1, tab4 = st.tabs(["Fatigue & Game State", "Compactness", "Home vs. Away", "Weather"])

with tab1:
    st.markdown("HSV's own average TPR while defending, by venue. **Null result**: venue doesn't meaningfully affect pressing intensity.")
    # Sorted here explicitly, not left to the CSV's own groupby row order (alphabetical --
    # "A" before "H" -- which previously put Away first and silently painted it HSV_COLOR while
    # Home got OPPONENT_COLOR: positionally-assigned colors on a chart with only one real team in
    # it, HSV split by venue -- there's no opponent series here at all).
    home_away = load_app_csv("home_away_summary.csv")
    home_away["label"] = home_away["hsv_side"].map({"H": "Home", "A": "Away"})
    home_away = home_away.set_index("label").loc[["Home", "Away"]].reset_index()
    fig = go.Figure(go.Bar(x=home_away["label"], y=home_away["mean"], error_y=dict(type="data", array=home_away["std"] / (home_away["count"] ** 0.5) * 1.96), marker_color=HSV_COLOR))
    fig.update_layout(yaxis_title="Mean defending TPR", height=400)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(home_away[["label", "mean", "std", "count"]].round(4), width="stretch", hide_index=True)

with tab2:
    st.markdown(
        "**The naive aggregate (all matches pooled) shows TPR *rising* late, the opposite of fatigue. "
        "Splitting by result reveals this was masking a scoreline-dependent story.**"
    )
    naive = load_app_csv("naive_fatigue.csv")
    fig = px.line(naive, x="time_block", y="TPR", markers=True, title="Naive aggregate (misleading on its own)")
    fig.update_layout(height=350)
    st.plotly_chart(fig, width="stretch")

    by_result = load_app_csv("fatigue_by_result.csv")
    fig2 = go.Figure()
    for result in ["Win", "Draw", "Loss"]:
        fig2.add_trace(go.Scatter(x=by_result["time_block"], y=by_result[result], mode="lines+markers", name=result, line=dict(color=RESULT_COLORS[result])))
    fig2.update_layout(title="TPR by 15-minute block, split by HSV's actual result", yaxis_title="Mean defending TPR", height=450)
    st.plotly_chart(fig2, width="stretch")
    st.markdown(
        "- **Losses**: clear late intensification, chasing the game.\n"
        "- **Wins**: dip mid-game (game management), spike late (closing out / opponent committing forward).\n"
        "- **Draws**: mildest pattern of the three."
    )

    st.markdown("---")
    st.markdown("**Game state, the live score differential, not just final result: sharper than the win/loss/draw split above:**")
    gs_summary = load_app_csv("game_state_summary.csv")
    # category_orders forces the narrative order (behind -> level -> leading) instead of the
    # CSV's alphabetical row order (behind, leading, level) -- left alphabetical, the bars read
    # high-low-medium, not the monotonic decline the caption below claims is visible.
    fig3 = px.bar(
        gs_summary, x="game_state", y="mean", color="game_state",
        category_orders={"game_state": ["behind", "level", "leading"]},
        color_discrete_map={"behind": CRITICAL_COLOR, "level": EXPLORATORY_COLOR, "leading": VALIDATED_COLOR},
    )
    fig3.update_layout(height=350, showlegend=False, yaxis_title="Mean defending TPR")
    st.plotly_chart(fig3, width="stretch")
    st.caption("Monotonic: HSV presses hardest chasing a goal, most conservatively protecting a lead. Validated by reconstructing all 34 matches' scorelines from detected goals; 34/34 match.")

with tab3:
    st.markdown("Compactness tells a genuinely different story from TPR, not just a repeat of it.")
    comp = load_app_csv("compactness_by_result.csv")
    fig = go.Figure()
    for result in ["Win", "Draw", "Loss"]:
        fig.add_trace(go.Scatter(x=comp["time_block"], y=comp[result], mode="lines+markers", name=result, line=dict(color=RESULT_COLORS[result])))
    fig.update_layout(title="Compactness by 15-minute block, split by result", yaxis_title="Mean compactness", height=450)
    st.plotly_chart(fig, width="stretch")
    st.caption("Wins are consistently the most compact across nearly every time block, not just late; unlike TPR, no sharp result-dependent late-game swing.")

with tab4:
    st.markdown("Checked and ruled out: a genuine null result, not a gap.")
    weather = load_csv("weather_tpr.csv")
    fig = px.scatter(weather, x="temperature", y="hsv_tpr", trendline="ols", labels={"temperature": "Temperature (°C)", "hsv_tpr": "HSV avg defending TPR"})
    fig.update_layout(height=400)
    st.plotly_chart(fig, width="stretch")
    c1, c2 = st.columns(2)
    c1.metric("Temperature correlation", "r = 0.134", "p = 0.448 (not significant)", delta_color="off")
    c2.metric("Humidity correlation", "r = -0.243", "p = 0.165 (not significant)", delta_color="off")
