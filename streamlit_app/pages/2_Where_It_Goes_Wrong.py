import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils import CATEGORICAL_SEQUENCE, CRITICAL_COLOR, DIMENSIONS, DIMENSION_LABELS, EXPLORATORY_COLOR, HSV_COLOR, LOGO_PATH, OPPONENT_COLOR, VALIDATED_COLOR, load_app_csv, load_csv, page_header

st.set_page_config(page_title="Where It Goes Wrong", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header(
    "Where Does It Go Wrong? HSV's Dimension Profile",
    "Is it Pressure? Anticipation? Local Pitch Control? Compactness? Answered properly, split specifically for HSV.",
)

st.error(
    "**\"Which dimension scores lowest at a given moment\" is not the same question as \"which dimension "
    "causes breakdowns.\"** A dimension can score low constantly, breakdown or not, just because that's its "
    "normal resting range (Pressure and Anticipation are exactly 0.0 in 59% and 64% of *all* ordinary "
    "defending frames). The full statistical case for this distinction is on Pressing Phases' Season Pooled "
    "tab. Everything below that's just a raw or low-score count is labeled **descriptive**, not a cause; only "
    "Synchronization has passed the actual causal test."
)

tab1, tab2, tab3 = st.tabs(["Validated: Which Dimension Actually Causes It (HSV vs. Opponents)", "Team Profile: Strong vs. Weak Dimensions", "Per-Player: Which Dimension, By Player"])

with tab1:
    st.markdown(
        "Same rigorous test as **Pressing Phases**' Season Pooled tab (each dimension's percentile at real "
        "breakdown moments vs. a random sample of ordinary defending, one-sided Mann-Whitney), run "
        "**separately** for HSV's own defending and for opponents defending against HSV, each against its own "
        "matched baseline."
    )
    signal = load_csv("dimension_breakdown_signal_by_team.csv")
    signal["dim_label"] = signal["dimension"].map(DIMENSION_LABELS)

    fig = go.Figure()
    for group, color in [("HSV", HSV_COLOR), ("Opponents", OPPONENT_COLOR)]:
        g = signal[signal["group"] == group].sort_values("shift")
        fig.add_trace(go.Bar(name=group, y=g["dim_label"], x=g["shift"], orientation="h", marker_color=color))
    fig.update_layout(
        barmode="group", title="Shift in mean percentile at breakdown vs. own random baseline (negative = worse = real cause)",
        xaxis_title="Mean percentile shift", height=420,
    )
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, width="stretch")

    hsv_sync = signal[(signal["group"] == "HSV") & (signal["dimension"] == "synchronization")].iloc[0]
    st.success(
        f"**For HSV specifically: still Synchronization, and only Synchronization** (p={hsv_sync['p_value_worse_at_breakdown']:.1e}, "
        f"shift={hsv_sync['shift']:.3f}). Opponents show the identical pattern against HSV (p=5.4e-73); "
        "this isn't a uniquely-HSV problem, it's the general pattern. Every other dimension for HSV specifically "
        "moves the wrong direction (gets better, not worse) near a breakdown, same as the pooled result."
    )
    st.dataframe(
        signal[["group", "dim_label", "n_events", "mean_percentile_random", "mean_percentile_breakdown", "shift", "significant_and_worse"]]
        .rename(columns={"group": "Group", "dim_label": "Dimension", "n_events": "Events", "mean_percentile_random": "Mean %ile (random)", "mean_percentile_breakdown": "Mean %ile (breakdown)", "shift": "Shift", "significant_and_worse": "Validated cause?"})
        .round(4),
        width="stretch", hide_index=True,
    )

with tab2:
    st.markdown(
        "Where HSV's defending is generally strong vs. weak across all six dimensions: mean percentile in "
        "**ordinary play** (not breakdown moments). A percentile near 0.5 is \"typical\"; well above 0.5 is a "
        "relative strength; well below is a relative weakness, independent of the breakdown-causality question above."
    )
    hsv_general = signal[signal["group"] == "HSV"].sort_values("mean_percentile_random")
    # EXPLORATORY_COLOR (this app's own established "neutral/middling" status color) for the
    # middle tier, not OPPONENT_COLOR -- there's no opponent series on this chart at all (it's
    # HSV's own profile), OPPONENT_COLOR just happened to already be imported for the tab above.
    fig2 = go.Figure(go.Bar(
        x=hsv_general["mean_percentile_random"], y=hsv_general["dim_label"], orientation="h",
        marker_color=[CRITICAL_COLOR if v < 0.4 else EXPLORATORY_COLOR if v < 0.5 else VALIDATED_COLOR for v in hsv_general["mean_percentile_random"]],
    ))
    fig2.add_vline(x=0.5, line_dash="dash", line_color="gray", annotation_text="league-typical (0.5)")
    fig2.update_layout(title="HSV's own dimension profile in ordinary defending", xaxis_title="Mean percentile (0=weakest, 1=strongest)", height=380)
    st.plotly_chart(fig2, width="stretch")
    st.caption(
        "Pressure and Anticipation sitting low here is expected and not meaningful on its own (see the warning "
        "above). This chart is about relative standing across HSV's own six dimensions, not a claim about cause."
    )

with tab3:
    st.markdown(
        "For each flagged player (same events as the Player Weakness Finder), which dimension was tied-weakest "
        "at their flagged moments, fractional credit when multiple dimensions tied. **Descriptive breakdown "
        "of real events, not a per-dimension causal claim** (only Synchronization is validated as a cause overall)."
    )
    involvement = load_app_csv("player_dimension_involvement.csv")
    squad = st.radio("Squad", ["HSV squad", "Opponents"], horizontal=True, key="wig_squad")
    group_df = involvement[involvement["is_hsv"] == (squad == "HSV squad")].sort_values("total_flagged", ascending=False)

    top_n = st.slider("Show top N players", 5, min(25, len(group_df)), min(12, len(group_df)))
    plot_df = group_df.head(top_n)

    # CATEGORICAL_SEQUENCE, not plotly's generic Set2 default -- this app's own established
    # categorical palette, used for this exact chart type (per-player dimension credit) on
    # Pressing Phases' equivalent tab; Set2 here was a leftover inconsistency between the two.
    fig3 = px.bar(
        plot_df, x=DIMENSIONS, y="player_name", orientation="h",
        labels={"value": "Fractional flagged credit", "player_name": "", "variable": "Dimension"},
        color_discrete_sequence=CATEGORICAL_SEQUENCE,
    )
    for trace in fig3.data:
        trace.name = DIMENSION_LABELS.get(trace.name, trace.name)
    fig3.update_layout(barmode="stack", height=max(400, 32 * top_n), legend_title="Dimension", yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig3, width="stretch")

    st.dataframe(
        group_df.head(top_n)[["player_name", *DIMENSIONS, "total_flagged"]].rename(columns=DIMENSION_LABELS).round(1),
        width="stretch", hide_index=True,
    )
