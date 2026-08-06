import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from utils import CATEGORICAL_SEQUENCE, DIMENSION_LABELS, DIMENSIONS, EXPLORATORY_COLOR, HSV_COLOR, LOGO_PATH, OPPONENT_COLOR, VALIDATED_COLOR, load_csv, page_header

# Same gray the plotly template already uses for axis lines (utils._register_plotly_template) --
# keeps the zero-baseline visually consistent with the rest of the chart's chrome. Used by the
# Season Pooled tab's chart.
BASELINE_COLOR = "#c3c2b7"

st.set_page_config(page_title="Pressing Phases", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header(
    "Pressing Phases: High Press / Mid Press / Low Block / Transition",
    "Is HSV vulnerable in a specific phase, to specific players, in specific dimensions, not just on average across the whole match?",
)

PHASE_LABELS = {"high_press": "High Press", "mid_press": "Mid Press", "low_press": "Low Block", "transition": "Transition (5s after recovery)"}
PHASES = list(PHASE_LABELS.keys())

st.markdown(
    """
Four states, not one average: **high press** (ball in the attacking third relative to this team's own goal),
**mid press** (middle third), **low block** (defensive third), and **transition** (the 5 seconds right after
this team wins the ball back in open play, the classic counter-pressing window). Phase is direction-aware
per team per half (teams swap ends at kick-off), derived from each team's own goalkeeper position, not assumed.
"""
)

st.warning(
    "**Why a single fixed weighting isn't fair across phases:** checked directly, Compactness, Pass Option "
    "Suppression, and Anticipation all move substantially between phases in completely ordinary defending, "
    "not just at breakdowns. A low block scores ~50% higher on Compactness and POS than a high press, and "
    "*higher* on Anticipation too, not because the defending is better, but mechanically: a team sitting deep "
    "is packed near its own goal by definition, so bodies are naturally close together and the ball is "
    "naturally nearer a crowd of defenders once it's in the box. A fixed weighting would silently reward a low "
    "block (or punish a high press) for its style, not its execution."
)

st.error(
    "**Tab 1 and tab 2 answer different questions, and tab 2 alone can be misread as an importance ranking.** "
    "Tab 1 tests which dimension actually predicts a real breakdown: the answer is unambiguous in every phase "
    "(p between 0.0013 and 5×10⁻²⁵). Tab 2 measures how much each dimension varies frame to frame, a different "
    "question entirely. Synchronization scores *lowest* on tab 2 in almost every phase, not because it doesn't "
    "matter, but because it's the dimension that varies the *least*: most of the time a back line already "
    "moves together, so there's little frame-to-frame swing for that chart to assign weight to. Rare and "
    "important aren't in tension: a back line rarely loses its shape, and every time it's been checked against "
    "real conceded chances, that's exactly when it hurts."
)

# Labels kept short on purpose: at common laptop widths (1280-1440px) the original longer
# labels pushed the 4th tab's right edge past the viewport entirely, off-screen with only a
# small scroll arrow hinting more tabs existed -- confirmed with a real headless-browser
# measurement, not assumed. The full framing for each tab lives in the markdown/warning boxes
# right below it, so shortening the label loses no information, just the redundant restating of it.
tab1, tab2, tab3, tab4 = st.tabs([
    "What Causes It, by Phase",
    "Variance by Dimension (Not Cause)",
    "Who's the Problem",
    "Season Pooled (Methodology)",
])

with tab1:
    st.markdown(
        "Same rigorous test as the **Season Pooled** tab and **Where It Goes Wrong** (each dimension's percentile "
        "at real breakdown moments vs. a random sample of *that same phase's own* ordinary defending, one-sided "
        "Mann-Whitney), run **separately within each phase**, so a phase that naturally runs hot or cold on a "
        "dimension can't be mistaken for a real effect."
    )
    signal = load_csv("dimension_breakdown_signal_by_phase.csv")
    signal["dim_label"] = signal["dimension"].map(DIMENSION_LABELS)

    group = st.radio("Group", ["Pooled", "HSV", "Opponents"], horizontal=True, key="phase_signal_group")
    g = signal[signal["group"] == group]

    fig = go.Figure()
    for phase, color in zip(PHASES, CATEGORICAL_SEQUENCE):
        gp = g[g["phase"] == phase].sort_values("shift")
        fig.add_trace(go.Bar(name=PHASE_LABELS[phase], y=gp["dim_label"], x=gp["shift"], orientation="h", marker_color=color))
    fig.update_layout(
        barmode="group", title="Shift in mean percentile at breakdown vs. same-phase random baseline (negative = worse = real cause)",
        xaxis_title="Mean percentile shift", height=460,
    )
    fig.add_vline(x=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, width="stretch")

    sync_by_phase = g[g["dimension"] == "synchronization"][["phase", "shift", "p_value_worse", "n_events"]]
    all_sync_significant = (g[g["dimension"] == "synchronization"]["significant_and_worse"]).all()
    if all_sync_significant:
        st.success(
            "**Synchronization is the validated cause in every single phase**: high press, mid press, low "
            "block, and transition alike. Not a phase-dependent story: the same specific issue (losing "
            "coordinated pace as a back line) undermines pressing the same way regardless of where on the pitch "
            "it happens."
        )
    st.dataframe(
        g[["phase", "dim_label", "n_events", "mean_pct_random", "mean_pct_breakdown", "shift", "significant_and_worse"]]
        .rename(columns={"phase": "Phase", "dim_label": "Dimension", "n_events": "Events", "mean_pct_random": "Mean %ile (same-phase random)", "mean_pct_breakdown": "Mean %ile (breakdown)", "shift": "Shift", "significant_and_worse": "Validated cause?"})
        .round(4),
        width="stretch", hide_index=True,
    )

with tab2:
    st.error(
        "**This tab measures a different question from tab 1.** It shows how much each dimension explains "
        "*overall tactical variance* in this phase, not which dimension causes breakdowns (that's tab 1). "
        "Weight means how much this dimension moves day to day; cause means whether a bad value on this "
        "dimension is actually why a breakdown happened."
    )

    with st.expander("Methodology correction: the first version of these weights missed Compactness and LPC"):
        st.markdown(
            """
            First version targeted Ridge regression at PC1 alone: the six metrics' single dominant shared
            axis of variation, and the thesis's own weight-optimization method, just refit on HSV's real data
            instead of the original Feyenoord/Eredivisie dataset it was published on. Challenged directly:
            *"in a low block, surely Compactness and Local Pitch Control count for a lot more than this."*
            Checked rather than argued: in a low block, Compactness and LPC load almost exactly **zero**
            onto PC1 (-0.02, -0.03) but dominate PC2 almost exclusively (0.72, -0.64), a real, substantial
            second axis (20.1% of variance, vs. PC1's 31.4%) that a PC1-only target is structurally blind to.
            Not specific to low block either: the same split shows up in high press too.

            Fixed by using the **top-2 components together**, each weighted by how much variance it actually
            explains, instead of only the first. Compactness in a low block went from **1.0% to 20.1%**; LPC
            from **1.4% to 16.0%**. (A first attempt at fixing this, using all six components, turned out
            to be a degenerate identity that trivially gives every dimension exactly 16.7% regardless of the
            data, caught by actually running it rather than trusting the formula.)
            """
        )

    weights = load_csv("phase_specific_weights_v2.csv")
    weights["dim_label"] = weights["metric"].map(DIMENSION_LABELS)
    weights["phase_label"] = weights["phase"].map(lambda p: PHASE_LABELS.get(p, p))
    weights["weight_pct"] = weights["weight"] * 100

    fig2 = px.bar(
        weights, x="phase_label", y="weight_pct", color="dim_label", barmode="group",
        color_discrete_sequence=CATEGORICAL_SEQUENCE,
        category_orders={"phase_label": ["pooled (reference)"] + [PHASE_LABELS[p] for p in PHASES]},
        labels={"weight_pct": "Weight (%)", "phase_label": "", "dim_label": "Dimension"},
    )
    fig2.update_layout(height=460, legend_title="Dimension")
    st.plotly_chart(fig2, width="stretch")

    st.caption(
        "\"pooled (reference)\" is all phases combined, HSV's real 2025-26 data. Included to show this "
        "reimplementation lands in the same ballpark ordering as the thesis's own published weights before "
        "trusting the phase splits, not because the exact percentages should match a different team's dataset."
    )
    pivot = weights.pivot(index="dim_label", columns="phase_label", values="weight_pct")
    col_order = ["pooled (reference)"] + [PHASE_LABELS[p] for p in PHASES]
    st.dataframe(pivot[col_order].round(1).sort_values("pooled (reference)", ascending=False), width="stretch")

    st.success(
        "**Synchronization is the lowest-weighted dimension here in every phase except transition (where "
        "it's a close second), and that's not a contradiction with tab 1, it's the whole point.** This "
        "weight measures how much a dimension *moves* frame to frame; Synchronization moves the least of all "
        "six, in every phase. But it's still the one dimension whose movement is the real, validated cause of "
        "breakdowns. It doesn't fluctuate much, but when it dips, that's when it hurts. Low weight (variance "
        "explained) and being the actual cause aren't in tension; they're answering two different questions, "
        "and Synchronization is the clearest possible illustration of the gap between them."
    )

    st.info(
        "**Tested, not left as a hypothesis: re-checked again after the Compactness/LPC correction above.** "
        "A phase-adjusted composite TPR built from these corrected weights (each frame scored with its own "
        "phase's weight set) was checked head-to-head against the deployed, fixed-weight TPR at real "
        "breakdown moments, in every phase. It still does **not** detect breakdowns better, and is still "
        "marginally worse in every single phase (low block: deployed shift +0.157 vs. phase-adjusted +0.172; "
        "transition: +0.098 vs. +0.116, both positive, meaning both versions read as *better*, not worse, "
        "right before a real breakdown). If anything the gap widened slightly vs. the pre-correction weights, "
        "because Compactness (one of the five dimensions that improves mechanically near goal) now correctly "
        "carries more weight. Structural, not a bug: any weighting of these six dimensions that gives enough "
        "combined weight to the five that improve mechanically near goal will net out \"better\" regardless "
        "of the exact split. This is exactly why every causal claim in this dashboard uses the six dimensions "
        "decomposed (tab 1), never a composite score."
    )

with tab3:
    st.markdown(
        "For each flagged player, which dimension was tied-weakest at their flagged moments **in this specific "
        "phase**, fractional credit when multiple dimensions tied. Descriptive breakdown of real events; only "
        "Synchronization is a validated cause (tab 1)."
    )
    involvement = load_csv("player_dimension_involvement_by_phase.csv")

    c1, c2 = st.columns(2)
    with c1:
        squad = st.radio("Squad", ["HSV squad", "Opponents"], horizontal=True, key="phase_player_squad")
    with c2:
        phase_choice = st.selectbox("Phase", PHASES, format_func=lambda p: PHASE_LABELS[p], key="phase_player_phase")

    group_df = involvement[(involvement["is_hsv"] == (squad == "HSV squad")) & (involvement["phase"] == phase_choice)].sort_values("total_flagged", ascending=False)

    if group_df.empty:
        st.info("No flagged events for this squad/phase combination.")
    else:
        top_n = st.slider("Show top N players", 3, min(20, len(group_df)), min(10, len(group_df)), key="phase_top_n")
        plot_df = group_df.head(top_n)
        fig3 = px.bar(
            plot_df, x=DIMENSIONS, y="player_name", orientation="h",
            labels={"value": "Fractional flagged credit", "player_name": "", "variable": "Dimension"},
            color_discrete_sequence=CATEGORICAL_SEQUENCE,
        )
        for trace in fig3.data:
            trace.name = DIMENSION_LABELS.get(trace.name, trace.name)
        fig3.update_layout(barmode="stack", height=max(360, 32 * top_n), legend_title="Dimension", yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig3, width="stretch")
        st.dataframe(
            group_df.head(top_n)[["player_name", *DIMENSIONS, "total_flagged"]].rename(columns=DIMENSION_LABELS).round(1),
            width="stretch", hide_index=True,
        )

    if phase_choice == "transition":
        st.info(
            "**Transition specifically:** the 5 seconds right after HSV (or an opponent) wins the ball back in "
            "open play, the moment a team is least organized, having just been attacking. Fewer total events "
            "than the other three phases (open-play recoveries are rarer than settled defending), so treat "
            "single-player transition names as a lead to check on video, not a season-long verdict the way the "
            "low-block numbers already can be."
        )

with tab4:
    st.markdown(
        "*Formerly its own page (\"Dimension Validation\"), folded in here because three other pages already "
        "treated it as a dependency rather than a destination (\"same rigorous test as...\"), and the "
        "phase-stratified version above is the more useful one for actual analysis. This tab is what backs "
        "every causal claim in this app: the season-wide test, ignoring phase, plus the methodology and "
        "robustness checks behind it.*"
    )

    pooled_signal = load_csv("dimension_breakdown_signal.csv")
    pooled_signal["dim_label"] = pooled_signal["dimension"].map(DIMENSION_LABELS)
    pooled_signal = pooled_signal.sort_values("shift")

    st.markdown(
        """
Tested with a one-sided Mann-Whitney U test: is each dimension's percentile value at 1,255 real breakdown
moments (a shot conceded, a player dribbled past, **both HSV's and their opponents', pooled across all 34
matches and all phases**, since a mistake is a mistake regardless of which side made it or when) significantly
lower (worse) than at a 20,000-frame random sample of ordinary defending? **Only one dimension passes.**
"""
    )

    def _format_p_short(p: float) -> str:
        # The one-sided test only checks "is this worse at breakdown." For a dimension that's
        # overwhelmingly BETTER instead, that p-value doesn't just fail to be significant -- it
        # saturates at exactly 1.0 in float64, because the true value is 1 minus something
        # astronomically small (e.g. Anticipation's opposite-direction p is 1.05e-213).
        return "p ≈ 1" if p >= 0.999 else f"p={p:.1e}"

    def _pooled_hover_note(row) -> str:
        if row.significant_and_worse:
            return "Validated: worse at breakdown, not explained by chance"
        if row.p_value_worse_at_breakdown >= 0.999:
            return "Moves the opposite direction: measures better, not worse, near a breakdown"
        return "Not statistically significant"

    pooled_signal["p_label"] = pooled_signal["p_value_worse_at_breakdown"].apply(_format_p_short)
    pooled_signal["hover_note"] = [_pooled_hover_note(r) for r in pooled_signal.itertuples()]
    pooled_colors = [VALIDATED_COLOR if row.significant_and_worse else EXPLORATORY_COLOR for row in pooled_signal.itertuples()]

    pooled_fig = go.Figure()
    pooled_fig.add_trace(
        go.Bar(
            y=pooled_signal["dim_label"],
            x=pooled_signal["shift"],
            orientation="h",
            marker_color=pooled_colors,
            marker_cornerradius=4,
            text=pooled_signal["p_label"],
            textposition="outside",
            cliponaxis=False,
            customdata=pooled_signal[["mean_percentile_random", "mean_percentile_breakdown", "hover_note"]],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Mean percentile, random play: %{customdata[0]:.3f}<br>"
                "Mean percentile, breakdown: %{customdata[1]:.3f}<br>"
                "Shift: %{x:+.3f}<br>"
                "%{customdata[2]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    # Legend proxies: color here is a status (validated / not), not a data series, so it gets its
    # own explicit legend rather than relying on the reader to infer green-vs-gray from the text.
    for proxy_color, proxy_name in [(VALIDATED_COLOR, "Validated cause (p<0.01, worse at breakdown)"), (EXPLORATORY_COLOR, "Not a validated cause")]:
        pooled_fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, symbol="square", color=proxy_color), name=proxy_name, showlegend=True))

    pooled_pad = max(0.02, (pooled_signal["shift"].max() - pooled_signal["shift"].min()) * 0.12)
    pooled_fig.update_layout(
        title="Shift in mean percentile at breakdown vs. random play (negative = worse, i.e. a real cause)",
        xaxis_title="Mean percentile shift (breakdown minus random)",
        xaxis_range=[pooled_signal["shift"].min() - pooled_pad, pooled_signal["shift"].max() + pooled_pad],
        xaxis_automargin=True,
        yaxis_automargin=True,
        height=420,
        margin=dict(l=10, r=10, t=60, b=10),
        bargap=0.45,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
    )
    pooled_fig.add_vline(x=0, line_width=1, line_color=BASELINE_COLOR)
    st.plotly_chart(pooled_fig, width="stretch")

    st.caption(
        "Why four bars show \"p ≈ 1\" instead of a small number: the test is one-sided, checking only \"is this "
        "dimension worse at breakdown.\" For a dimension that's actually overwhelmingly *better* instead, that "
        "p-value doesn't just fail to be significant, it mathematically saturates at 1.0, because the true value "
        "is 1 minus something astronomically small (checked directly: Anticipation's opposite-direction p-value "
        "is 1.05×10⁻²¹³). Not a bug: 64-bit floats can't represent a number that close to 1 as anything else."
    )

    pooled_signal_display = pooled_signal.copy()
    pooled_signal_display["p_value_display"] = pooled_signal_display["p_value_worse_at_breakdown"].apply(lambda p: "≈ 1" if p >= 0.999 else f"{p:.2e}")
    st.dataframe(
        pooled_signal_display[["dim_label", "mean_percentile_random", "mean_percentile_breakdown", "shift", "p_value_display", "significant_and_worse"]]
        .rename(columns={"dim_label": "Dimension", "mean_percentile_random": "Mean %ile (random)", "mean_percentile_breakdown": "Mean %ile (breakdown)", "shift": "Shift", "p_value_display": "p-value", "significant_and_worse": "Validated cause?"})
        .round(4),
        width="stretch",
        hide_index=True,
    )

    st.success(
        "**Synchronization is the one validated cause.** p = 5.4×10⁻¹²⁷, not a borderline result. "
        "Every other dimension moves the *wrong* direction (gets better, not worse, near a breakdown), "
        "which makes tactical sense: a breakdown means the ball is near goal, which mechanically draws more "
        "defenders into the area regardless of whether the press is actually working."
    )

    st.info(
        "**The story continued on the Synchronization Attribution page:** the formula itself was rebuilt for "
        "this dashboard after further testing showed its directional term carries no signal at all, and the "
        "improved version (`si_v2`) is even more significant: pooled p=2.3×10⁻¹⁷⁸, vs. 5.4×10⁻¹²⁷ here. The "
        "numbers on this page are the original six-dimension comparison and are still accurate; see that page "
        "for the refinement."
    )

    st.subheader("Robustness checks")
    robustness = load_csv("dimension_validation_robustness.csv")

    def _fmt_p(p: float) -> str:
        return f"{p:.1e}"

    seed_rows = robustness[robustness["check"] == "random_seed"]
    window_rows = robustness[robustness["check"] == "breakdown_window"]
    tempo_rows = robustness[robustness["check"] == "tempo_confound"]
    tempo_raw = tempo_rows[tempo_rows["variant"] == "raw"].iloc[0]
    tempo_resid = tempo_rows[tempo_rows["variant"] == "residualized_on_ball_speed"].iloc[0]

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.metric(
            "Random-seed check",
            f"{len(seed_rows)} seeds tested",
            f"shift {seed_rows['shift'].min():+.3f} to {seed_rows['shift'].max():+.3f}",
            delta_color="off",
        )
    with rc2:
        st.metric(
            "Breakdown-window check",
            "1.0s / 1.5s / 2.0s lookback",
            f"p < {window_rows['p_value'].max():.0e} at all three",
            delta_color="off",
        )
    with rc3:
        st.metric(
            "Tempo confound",
            "residualized on ball speed",
            f"shift {tempo_raw['shift']:+.3f} → {tempo_resid['shift']:+.3f}, still p={_fmt_p(tempo_resid['p_value'])}",
            delta_color="off",
        )

    with st.expander("Robustness checks, in full, and why 2 of the 3 numbers above changed"):
        st.markdown(
            "These 3 checks used to be hardcoded text with no script or CSV behind them anywhere in the repo, "
            "a direct violation of this app's own rule that every number traces to a saved result file. Reproducing "
            "them directly (`verify_dimension_validation_robustness.py`) found the random-seed check basically held "
            "up, but the other two didn't: the breakdown-window check's old claim (\"p < 1e-98 at all three\") was "
            "actually false at the loosest window: 2.0s lookback gives p≈4×10⁻⁹⁸, not below 1×10⁻⁹⁸, and the old "
            "tempo-confound numbers (shift -0.094 → -0.077) didn't match anything reproducible from current data, "
            "not even the same order of magnitude as the real raw shift (-0.202). Likely leftover from an earlier, "
            "since-abandoned test setup. Replaced with numbers computed fresh from current data, every run."
        )
        st.dataframe(
            robustness.rename(columns={"check": "Check", "variant": "Variant", "shift": "Shift", "p_value": "p-value", "n_breakdown": "n breakdown events"}).round(4),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Tempo confound method: fit Synchronization ~ ball_speed on the 20,000-frame ordinary-play sample "
            "(r=-0.148, faster ball movement mildly predicts lower Synchronization, plausibly more defensive "
            "scrambling), then re-run the same percentile-shift test on the regression residuals instead of raw "
            "values. The shift shrinks (-0.202 → -0.174, about 14%) but stays enormous: ball speed is a real but "
            "small part of the story, not a confound that explains the finding away."
        )

    st.markdown("---")
    st.subheader("Why this took 4 attempts: the debugging trail")

    with st.expander("Attempt 1 (wrong): compare raw values across dimensions"):
        st.markdown(
            """
            Pressure "weakest" in 71% of breakdown events, Anticipation 18%. Looked strong, but a random sample
            of *ordinary* frames showed almost the same split (69.5% / 24.2%). Pressure and Anticipation float
            near zero in **any** defending frame (58.7% and 63.5% of all ordinary defending frames are exactly
            0.0), so a raw-value `argmin` just picks whichever dimension has the lowest natural floor, breakdown
            or not.
            """
        )
    with st.expander("Attempt 2: percentile rank instead of raw value"):
        st.markdown(
            """
            Looked like a fix (Pressure 40%, Synchronization 32%), but percentile rank still assigns "most
            extreme possible" (0.0) to *every* frame tied at that same common floor, so it didn't solve the
            base-rate problem, just moved it one layer down.
            """
        )
    with st.expander("Attempt 3: fixed a tie-breaking bug, still argmin-based"):
        st.markdown(
            """
            Pressure and Anticipation genuinely tie at the exact floor often; `sorted(...)[0]` silently resolved
            every tie in Pressure's favor by list order. Fixed with fractional tie-credit: Pressure 33%,
            Synchronization 32% (effectively tied). Better, but still fundamentally the wrong question.
            """
        )
    with st.expander("Attempt 4 (the real fix): stop comparing dimensions to each other"):
        st.markdown(
            """
            `argmin` across 6 dimensions measures **relative competition in that one frame**, not whether a
            dimension is actually elevated at breakdowns. Confirmed directly: a random sample of ordinary frames
            shows Pressure "winning" the argmin 35% of the time regardless of context; its 33% breakdown share
            was just its resting base rate. LPC's apparent "2.6x lift" didn't survive either: its own percentile
            barely moves between breakdown and random play (0.485 vs. 0.490); it only won more often because its
            *competitors* got relatively better, not because LPC itself got worse.

            The fix: test each dimension against **its own random-play baseline**, independently, one at a time.
            That's the chart above.
            """
        )

st.markdown("---")
st.caption(
    "Sample sizes are smaller here than the season-pooled pages by construction: splitting ~1,255 real "
    "breakdown events four ways leaves some phase/squad/dimension cells with only a few dozen events. Real "
    "data, but treat single-phase findings as a lead to verify, the same discipline already applied everywhere "
    "else in this project."
)
