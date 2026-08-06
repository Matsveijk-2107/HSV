import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import spearmanr
from utils import CRITICAL_COLOR, HSV_COLOR, LOGO_PATH, OPPONENT_COLOR, VALIDATED_COLOR, load_app_csv, load_csv, page_header

st.set_page_config(page_title="Restarts, Triggers & Recovery", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header(
    "Restarts, Triggers & Recovery",
    "Four different specific moments, one question each time: does pressing intensity actually respond the "
    "way it should: at corners, throw-ins, goal kicks, the textbook backpass-to-keeper cue, and winning the "
    "ball back after a turnover?",
)

baseline_tpr = load_app_csv("overall_baseline_tpr.csv")["overall_baseline_tpr"].iloc[0]

# Labels kept short on purpose: the original longer labels pushed this 4-tab bar's right edge
# past common laptop viewport widths (1280-1440px), confirmed with a real headless-browser
# measurement. Full framing for each tab is in its own markdown text just below.
tab1, tab2, tab3, tab4 = st.tabs([
    "Restart Pressing",
    "Missed-Press-Trigger",
    "Does TPR Predict Recovery?",
    "HSV vs. Opponent Recovery Speed",
])

with tab1:
    st.markdown(
        """
        Does the defending team's TPR in the 5s right after a stoppage differ from their normal defending
        TPR? Uses StatsBomb's own `play_pattern` field to find every corner/throw-in/goal-kick, compared
        against each team's own match-defending baseline (Mann-Whitney, not a raw pooled average).
        **Pooling all three types first would have hidden all three real effects** underneath a practically
        meaningless average.
        """
    )
    windows = load_csv("restart_pressing_windows.csv")
    summary = windows.groupby("restart_type")["TPR"].agg(["mean", "count"]).reset_index()
    summary["restart_type"] = summary["restart_type"].map({"corner": "Corner", "throw_in": "Throw-in", "goal_kick": "Goal Kick"})

    # Colors keyed by label, not position -- groupby sorts alphabetically (corner, goal_kick,
    # throw_in), which previously put Goal Kick second and Throw-in third, so the old positional
    # [VALIDATED, VALIDATED, CRITICAL] list painted Goal Kick as "validated" (green) and Throw-in
    # as "critical" (red) -- backwards from the caption below, which says Goal Kick is the outlier.
    bar_colors = {"Corner": VALIDATED_COLOR, "Throw-in": VALIDATED_COLOR, "Goal Kick": CRITICAL_COLOR}
    fig = go.Figure()
    fig.add_trace(go.Bar(x=summary["restart_type"], y=summary["mean"], marker_color=summary["restart_type"].map(bar_colors), text=summary["count"].map(lambda n: f"n={n}"), textposition="outside"))
    fig.add_hline(y=baseline_tpr, line_dash="dash", annotation_text=f"Overall baseline ({baseline_tpr:.3f})", line_color="gray")
    fig.update_layout(title="Mean pressing TPR in the 5s after each restart type", yaxis_title="Mean TPR", height=450)
    st.plotly_chart(fig, width="stretch")

    c1, c2, c3 = st.columns(3)
    c1.metric("Corner", f"{summary[summary.restart_type=='Corner']['mean'].iloc[0]:.3f}", f"+{summary[summary.restart_type=='Corner']['mean'].iloc[0]-baseline_tpr:.3f} vs baseline, p=3.7e-54")
    c2.metric("Throw-in", f"{summary[summary.restart_type=='Throw-in']['mean'].iloc[0]:.3f}", f"+{summary[summary.restart_type=='Throw-in']['mean'].iloc[0]-baseline_tpr:.3f} vs baseline, p=9.8e-35")
    c3.metric("Goal Kick", f"{summary[summary.restart_type=='Goal Kick']['mean'].iloc[0]:.3f}", f"{summary[summary.restart_type=='Goal Kick']['mean'].iloc[0]-baseline_tpr:.3f} vs baseline, p=4.2e-89")
    st.caption("Corners and throw-ins are proximity-driven defensive scrambles (intensity rises). A goal kick starts from the keeper deep in their own half; the opposing team hasn't had time to engage yet (intensity falls, the largest effect of the three).")

with tab2:
    st.markdown(
        """
        A backpass to the goalkeeper is one of the clearest textbook cues to press. Does pressing intensity
        actually rise after one? Goalkeeper identified from StatsBomb's own Starting XI lineup data.
        """
    )
    triggers = load_csv("missed_press_trigger_events.csv")
    window_mean = triggers["window_mean_tpr"].mean()
    missed_rate = triggers["is_missed_trigger"].mean()

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(go.Indicator(
            mode="number+delta", value=window_mean,
            delta={"reference": baseline_tpr, "valueformat": ".3f"},
            title={"text": "Mean TPR after a backpass to keeper<br><span style='font-size:0.7em'>vs. overall baseline</span>"},
            number={"valueformat": ".3f"},
        ))
        fig.update_layout(height=250)
        st.plotly_chart(fig, width="stretch")
    with c2:
        st.metric("Individual missed-trigger rate", f"{missed_rate:.1%}", "789 backpass-to-keeper moments, p=8.2e-166")

    st.warning(
        "**Read carefully, not as a simple \"missed opportunity\" story.** The effect size (-0.051 TPR) is "
        "almost identical to the goal-kick effect above (-0.044); both are moments where the ball sits deep "
        "in the passing team's own third, so the pressing team is mechanically not close to it regardless of "
        "intent. This data can't distinguish a deliberate low block from a genuine missed opportunity."
    )

    # `is_hsv_pressing` used to be missing from the saved CSV (missed_press_triggers.py computed
    # it only after already writing the file, so this whole section silently never rendered --
    # fixed at the source; see that script's docstring note). Reads it directly now rather than
    # guarding for its absence, since a missing column here should error loudly, not vanish quietly.
    hsv_role_note = triggers.groupby("is_hsv_pressing")["is_missed_trigger"].agg(["mean", "size"]).reset_index()
    hsv_row = hsv_role_note[hsv_role_note.is_hsv_pressing == True]
    opp_row = hsv_role_note[hsv_role_note.is_hsv_pressing == False]
    st.markdown("**The genuinely useful, comparative part, same situation, two different rates:**")
    c1, c2 = st.columns(2)
    if not hsv_row.empty:
        c1.metric("HSV misses the cue", f"{hsv_row['mean'].iloc[0]:.1%}", f"n={int(hsv_row['size'].iloc[0])}")
    if not opp_row.empty:
        c2.metric("Opponents miss the cue (vs. HSV)", f"{opp_row['mean'].iloc[0]:.1%}", f"n={int(opp_row['size'].iloc[0])}")

with tab3:
    st.markdown(
        "A different kind of turnover moment from the two tabs above: not a stoppage or a specific cue, but "
        "any genuine open-play loss of possession (StatsBomb's `possession`/`possession_team` fields, same "
        "team-name matching fix as elsewhere in this project applied here too, see the caption on the next tab)."
    )
    recovery_df = load_csv("counter_press_recoveries.csv")
    valid = recovery_df.dropna(subset=["post_loss_tpr"])
    rho, p = spearmanr(valid["post_loss_tpr"], valid["recovery_seconds"])
    st.metric("Spearman correlation: post-loss TPR vs. recovery time", f"ρ = {rho:.3f}", f"p = {p:.1e} (n={len(valid)})", delta_color="off")
    # Plotted directly, not a random subsample -- n=2288 is small enough that there's no real
    # performance reason to downsample, and this way the chart shows exactly the same population
    # the correlation stat above is computed on, not an approximation of it.
    fig = px.scatter(
        valid, x="post_loss_tpr", y="recovery_seconds",
        trendline="ols", opacity=0.4,
        labels={"post_loss_tpr": "TPR in the 3s right after losing the ball", "recovery_seconds": "Actual recovery time (s)"},
    )
    fig.update_layout(height=450)
    st.plotly_chart(fig, width="stretch")
    st.success(
        "**The genuinely useful result here is a validation of TPR itself.** Small in magnitude but real and "
        "correctly signed: higher immediate pressing intensity predicts a faster recovery. A different kind "
        "of check than anything else in this project, not \"does the formula match its spec,\" but \"does "
        "TPR predict a real, independent match outcome.\""
    )

with tab4:
    st.markdown(
        """
        Built from StatsBomb's `possession`/`possession_team` fields, a genuine open-play turnover, not a
        dead-ball restart (covered in the first tab). Same team-name matching bug (DFL "FC St. Pauli" vs.
        StatsBomb "St. Pauli") caught here as elsewhere in this project: an early pass showed HSV losing the
        ball 3.2x more than opponents did against them, an implausible ratio traced to the bug and fixed.
        """
    )
    hsv_rec = recovery_df[recovery_df["is_hsv"]]["recovery_seconds"]
    opp_rec = recovery_df[~recovery_df["is_hsv"]]["recovery_seconds"]
    c1, c2 = st.columns(2)
    c1.metric("HSV loses the ball", f"median {hsv_rec.median():.1f}s", f"n={len(hsv_rec)}, within 6s: {(hsv_rec<=6).mean():.1%}", delta_color="off")
    c2.metric("Opponent loses the ball (vs. HSV)", f"median {opp_rec.median():.1f}s", f"n={len(opp_rec)}, within 6s: {(opp_rec<=6).mean():.1%}", delta_color="off")

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=hsv_rec, name="HSV loses ball", opacity=0.6, nbinsx=40, marker_color=HSV_COLOR))
    fig.add_trace(go.Histogram(x=opp_rec, name="Opponent loses ball", opacity=0.6, nbinsx=40, marker_color=OPPONENT_COLOR))
    fig.update_layout(barmode="overlay", xaxis_title="Recovery time (seconds, capped at 60s)", height=400)
    st.plotly_chart(fig, width="stretch")

    st.info(
        "**Honest null result, checked properly rather than eyeballed:** the raw medians look different, "
        "but neither a pooled Mann-Whitney (p=0.35) nor a per-match paired test (30 matches, p=0.16) shows "
        "this as statistically real. HSV's counter-pressing speed isn't meaningfully different from what "
        "opponents show recovering the ball against them."
    )
