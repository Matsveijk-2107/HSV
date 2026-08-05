import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils import (
    CRITICAL_COLOR,
    DIMENSIONS,
    DIMENSION_LABELS,
    EXPLORATORY_COLOR,
    HSV_COLOR,
    LOGO_PATH,
    OPPONENT_COLOR,
    VALIDATED_COLOR,
    confidence_badge,
    page_header,
)

import frame_diagnostics as fd

# This page's data lives one level up from the rest of the dashboard
# (machine_learning/hsv_pipeline/results/, not .../hsv_player_attribution/results/)
# -- it's the one thing in this app that isn't a pre-validated finding CSV,
# it's a live per-minute reslice of the checkpoint data, built by
# machine_learning/hsv_pipeline/build_scrubber_data.py. Kept self-contained
# here rather than routed through utils.load_csv, which is hardcoded to
# this app's own results/ directory.
PROJECT_ROOT = Path(__file__).resolve().parents[4]
SCRUBBER_JSON = PROJECT_ROOT / "machine_learning/hsv_pipeline/results/scrubber_data.json"

REASON_LABELS = {
    "velocity_outlier_against_majority": "moving against team's direction (Synchronization)",
    "velocity_outlier_same_direction": "wrong pace vs. team's coherence (Synchronization)",
    "positional_gap": "furthest from the defensive block",
}

st.set_page_config(page_title="Match Explorer", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header(
    "Match Explorer",
    "Pick a match, drag a minute window, and see the frame-level shape underneath the season averages "
    "used on the other pages. Match-averaged TPR looks nearly identical game to game because averaging "
    "~6,000 frames compresses real frame-level variation roughly 11x -- this is that variation, exposed.",
)

with st.expander("How to read this page"):
    st.markdown(
        """
- **TPR chart**: HSV vs. opponent, frame-by-frame across the match. The shaded band is your selected window; red dots are flagged breakdown events (shot conceded or dribbled past).
- **The 6 dimensions**: each compared to HSV's own season norm *for that dimension specifically*, using a percentile rank, not a raw value. Raw values aren't comparable across dimensions: Pressure and Anticipation sit near 0 for most of ordinary play, while Synchronization can't mathematically fall below ~0.27, so a raw-value comparison would just pick whichever dimension has the lowest natural floor, not whichever is actually unusual. Percentile rank fixes that.
- **Validated vs. descriptive**: only **Synchronization** is statistically confirmed to predict real breakdowns league-wide (see Pressing Phases). Everything else on this page is descriptive: real patterns in this window, but not proof of cause.
        """
    )


@st.cache_data
def load_scrubber_data():
    with open(SCRUBBER_JSON, encoding="utf-8") as f:
        return json.load(f)


def _is_number(v):
    return isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v))


@st.cache_data
def season_hsv_baseline(_data):
    """Season-wide HSV average per dimension. Skips the rare NaN minute
    (2 occurrences across 34 matches x ~90 minutes, both in POS -- a brief
    tracking dropout) rather than summing it in directly: float NaN
    propagates through addition, so one missed guard here silently turns
    the ENTIRE season average for that dimension into NaN, not just the
    2 affected minutes -- confirmed this was happening for POS specifically
    before this fix."""
    sums = {c: [0.0, 0] for c in DIMENSIONS}
    for match_data in _data["match_data"].values():
        for row in match_data["timeline"]:
            for c in DIMENSIONS:
                k = f"hsv_{c}"
                if k in row and _is_number(row[k]):
                    sums[c][0] += row[k]
                    sums[c][1] += 1
    return {c: (sums[c][0] / sums[c][1] if sums[c][1] else float("nan")) for c in DIMENSIONS}


def window_avg(timeline, side, minute_from, minute_to, key):
    k = f"{side}_{key}"
    vals = [
        row[k]
        for row in timeline
        if minute_from <= row["minute"] <= minute_to and k in row and _is_number(row[k])
    ]
    return sum(vals) / len(vals) if vals else None


@st.cache_data
def dimension_baseline_lookup():
    """Sorted per-dimension value arrays from every is_defending==1 frame
    across all 34 matches (frame_diagnostics.build_baseline_percentile_lookup,
    the same lookup Pressing Phases and Where It Goes Wrong are built on)
    -- reused rather than reimplemented so a window's raw average converts
    to a percentile within its OWN distribution, comparable across
    dimensions, instead of a raw-value comparison across differently-scaled
    dimensions (the exact mistake already found and fixed on Pressing
    Phases's Season Pooled tab -- see that tab's debugging trail)."""
    return fd.build_baseline_percentile_lookup()


if not SCRUBBER_JSON.exists():
    st.error(
        f"Missing {SCRUBBER_JSON}. Run `python machine_learning/hsv_pipeline/build_scrubber_data.py` "
        "from the project root first."
    )
    st.stop()

data = load_scrubber_data()
hsv_baseline = season_hsv_baseline(data)
pct_baseline = dimension_baseline_lookup()

with st.container(border=True):
    sel_col, slider_col = st.columns([1, 2])
    with sel_col:
        match_labels = {f"MD{m['matchday']}: {m['opponent']} ({m['hsv_side']}) {m['score']}": m for m in data["matches"]}
        selected_label = st.selectbox("Match", list(match_labels.keys()))
        meta = match_labels[selected_label]
        match_id = meta["match_id"]
        match_data = data["match_data"][match_id]
        timeline = match_data["timeline"]
        max_minute = meta["max_minute"]
    with slider_col:
        minute_from, minute_to = st.slider("Minute window", min_value=0, max_value=max_minute, value=(0, max_minute), step=1)
        is_full_range = (minute_from == 0 and minute_to == max_minute)

# --- Chart ---
minutes = [r["minute"] for r in timeline]
hsv_tpr_series = [r.get("hsv_tpr") for r in timeline]
opp_tpr_series = [r.get("opp_tpr") for r in timeline]

fig = go.Figure()
fig.add_vrect(x0=minute_from, x1=minute_to, fillcolor=HSV_COLOR, opacity=0.12, line_width=0)
fig.add_trace(go.Scatter(x=minutes, y=opp_tpr_series, mode="lines", name="Opponent TPR", line=dict(color=OPPONENT_COLOR, width=2)))
fig.add_trace(go.Scatter(x=minutes, y=hsv_tpr_series, mode="lines", name="HSV TPR", line=dict(color=HSV_COLOR, width=2)))
event_minutes = [e["minute"] for e in match_data["events"]]
if event_minutes:
    fig.add_trace(go.Scatter(
        x=event_minutes, y=[0.0] * len(event_minutes), mode="markers", name="Breakdown event",
        marker=dict(color=CRITICAL_COLOR, size=6),
        hovertext=[f"{e['side'].upper()}: {e['player']}" for e in match_data["events"]],
    ))
fig.update_layout(
    height=320, margin=dict(l=40, r=10, t=10, b=30),
    yaxis=dict(range=[0, 1], title="TPR"), xaxis=dict(title="Minute"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.plotly_chart(fig, width="stretch")

# --- Stat tiles ---
hsv_window_tpr = window_avg(timeline, "hsv", minute_from, minute_to, "tpr")
opp_window_tpr = window_avg(timeline, "opp", minute_from, minute_to, "tpr")
hsv_full_tpr = window_avg(timeline, "hsv", 0, max_minute, "tpr")
opp_full_tpr = window_avg(timeline, "opp", 0, max_minute, "tpr")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("HSV TPR (window)", f"{hsv_window_tpr:.3f}" if hsv_window_tpr is not None else "n/a")
    st.caption("full match average" if is_full_range else f"{hsv_window_tpr - hsv_full_tpr:+.3f} vs. match avg")
with c2:
    st.metric("Opponent TPR (window)", f"{opp_window_tpr:.3f}" if opp_window_tpr is not None else "n/a")
    st.caption("full match average" if is_full_range else f"{opp_window_tpr - opp_full_tpr:+.3f} vs. match avg")
with c3:
    if hsv_window_tpr is not None and opp_window_tpr is not None:
        gap = hsv_window_tpr - opp_window_tpr
        st.metric("TPR gap (HSV − Opp)", f"{gap:+.3f}")
        if is_full_range or hsv_full_tpr is None or opp_full_tpr is None:
            st.caption("full match average")
        else:
            st.caption(f"{gap - (hsv_full_tpr - opp_full_tpr):+.3f} vs. match avg")
    else:
        st.metric("TPR gap (HSV − Opp)", "n/a")
with c4:
    st.metric("Minutes in window", minute_to - minute_from)

# --- 6-dimension breakdown ---
st.markdown("#### The 6 dimensions in this window")
st.caption(
    "HSV vs. its own season average (34 matches, same weights as the rest of this app); the opponent vs. "
    "its own average across this full match -- each opponent only plays HSV once or twice, so there's no "
    "meaningful season baseline for them."
)

opp_full_comp = {c: window_avg(timeline, "opp", 0, max_minute, c) for c in DIMENSIONS}

pct_rows = {}
for c in DIMENSIONS:
    hv = window_avg(timeline, "hsv", minute_from, minute_to, c)
    hf = hsv_baseline[c]
    if hv is not None and _is_number(hf):
        window_pct = fd.percentile_rank(pct_baseline[c], hv)
        season_pct = fd.percentile_rank(pct_baseline[c], hf)
        pct_rows[c] = {"window_pct": window_pct, "season_pct": season_pct, "shift": window_pct - season_pct}
    else:
        pct_rows[c] = {"window_pct": None, "season_pct": None, "shift": None}

# Most unusual dimension this window, by percentile shift vs. HSV's own
# season norm for THAT dimension -- comparable across dimensions, unlike a
# raw-value diff. Ties are reported rather than silently broken by list
# order (see frame_diagnostics._tie_aware_weakest for why that matters).
valid_shifts = {c: v["shift"] for c, v in pct_rows.items() if v["shift"] is not None}
worst_dim, n_tied = None, 0
if valid_shifts:
    min_shift = min(valid_shifts.values())
    tied = sorted(c for c, s in valid_shifts.items() if s == min_shift)
    worst_dim, n_tied = tied[0], len(tied)

chart_dims = [c for c in DIMENSIONS if pct_rows[c]["shift"] is not None]
if chart_dims:
    chart_df = pd.DataFrame({
        "dimension": chart_dims,
        "label": [DIMENSION_LABELS[c] for c in chart_dims],
        "shift": [pct_rows[c]["shift"] for c in chart_dims],
        "window_pct": [pct_rows[c]["window_pct"] for c in chart_dims],
        "season_pct": [pct_rows[c]["season_pct"] for c in chart_dims],
    }).sort_values("shift")

    colors = [VALIDATED_COLOR if d == "synchronization" else EXPLORATORY_COLOR for d in chart_df["dimension"]]
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        y=chart_df["label"], x=chart_df["shift"], orientation="h",
        marker_color=colors, marker_cornerradius=4,
        text=[f"{v:+.0%}" for v in chart_df["shift"]], textposition="outside", cliponaxis=False,
        customdata=chart_df[["window_pct", "season_pct"]],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Window percentile: %{customdata[0]:.0%}<br>"
            "HSV season norm: %{customdata[1]:.0%}<br>"
            "Shift: %{x:+.0%}<extra></extra>"
        ),
        showlegend=False,
    ))
    for proxy_color, proxy_name in [
        (VALIDATED_COLOR, "Validated cause of breakdowns (Synchronization only)"),
        (EXPLORATORY_COLOR, "Descriptive only, not a validated cause"),
    ]:
        fig2.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(size=10, symbol="square", color=proxy_color), name=proxy_name, showlegend=True))

    pad = max(0.03, (chart_df["shift"].max() - chart_df["shift"].min()) * 0.15)
    # Title moved out of the figure and into a markdown header above it, not a plotly `title` --
    # a plotly title plus a top-anchored legend in the same cramped top margin overlapped each
    # other at normal chart widths (the title wraps to 2 lines, the legend sits right through it).
    st.markdown("**Percentile shift this window vs. HSV's season norm, per dimension** (negative = unusually low)")
    fig2.update_layout(
        xaxis_title="Percentile-point shift (window minus season norm)",
        xaxis_tickformat="+.0%",
        xaxis_range=[chart_df["shift"].min() - pad, chart_df["shift"].max() + pad],
        xaxis_automargin=True, yaxis_automargin=True,
        height=320, margin=dict(l=10, r=10, t=40, b=10), bargap=0.45,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
    )
    fig2.add_vline(x=0, line_width=1, line_color="#c3c2b7")
    st.plotly_chart(fig2, width="stretch")

rows = []
for c in DIMENSIONS:
    hv = window_avg(timeline, "hsv", minute_from, minute_to, c)
    ov = window_avg(timeline, "opp", minute_from, minute_to, c)
    hf, of = hsv_baseline[c], opp_full_comp[c]
    h_diff = (hv - hf) if (hv is not None and _is_number(hf)) else None
    pr = pct_rows[c]
    rows.append({
        "Dimension": DIMENSION_LABELS[c],
        "HSV window": round(hv, 3) if hv is not None else None,
        "HSV season avg": round(hf, 3) if _is_number(hf) else None,
        "HSV Δ": round(h_diff, 3) if h_diff is not None else None,
        "HSV %ile (window)": f"{pr['window_pct']:.0%}" if pr["window_pct"] is not None else None,
        "HSV %ile (season norm)": f"{pr['season_pct']:.0%}" if pr["season_pct"] is not None else None,
        "Opp window": round(ov, 3) if ov is not None else None,
        "Opp full-match avg": round(of, 3) if of is not None else None,
    })
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

if worst_dim:
    tie_note = f" (tied with {n_tied - 1} other dimension{'s' if n_tied > 2 else ''})" if n_tied > 1 else ""
    wp = pct_rows[worst_dim]["window_pct"]
    sp = pct_rows[worst_dim]["season_pct"]
    shift = pct_rows[worst_dim]["shift"]
    detail = f"at the {wp:.0%} percentile this window vs. its normal {sp:.0%} for HSV this season ({shift:+.0%} pts)."
    if worst_dim == "synchronization":
        st.warning(
            f"**Most unusual dimension this window: {DIMENSION_LABELS[worst_dim]}**{tie_note}, {detail} "
            f"{confidence_badge(True)}: this is the one dimension proven to actually predict real breakdowns "
            "league-wide (see Pressing Phases)."
        )
    else:
        st.info(
            f"**Most unusual dimension this window: {DIMENSION_LABELS[worst_dim]}**{tie_note}, {detail} "
            f"{confidence_badge(False)}: only Synchronization is a validated cause of breakdowns league-wide; "
            "an unusual reading here is worth a look on film, not a causal claim on its own."
        )

# --- Events in window ---
st.markdown("#### Breakdown events in this window")
st.caption(
    "Same events as Player Weakness Finder / Synchronization Attribution, filtered to this window. Where "
    "available, the reason names the validated Synchronization cause instead of the general positional gap."
)
events_in_window = [e for e in match_data["events"] if minute_from <= e["minute"] <= minute_to]
if not events_in_window:
    st.info("No flagged breakdown events (shot conceded / dribbled past) in this window on either side.")
else:
    ev_df = pd.DataFrame(sorted(events_in_window, key=lambda e: e["minute"]))
    ev_df["side"] = ev_df["side"].map({"hsv": "HSV", "opp": "Opponent"})
    ev_df["reason"] = ev_df["reason"].map(lambda r: REASON_LABELS.get(r, r))
    ev_df = ev_df.rename(columns={"minute": "Minute", "side": "Side", "player": "Player", "reason": "Likely reason", "gap_m": "Gap (m)"})
    st.dataframe(ev_df[["Minute", "Side", "Player", "Likely reason", "Gap (m)"]], hide_index=True, width="stretch")

st.caption(
    "Assessment tool, not a diagnostic one: flags patterns in tracking data, doesn't identify causes or "
    "prescribe fixes. Cross-check against footage before treating any single flagged moment as a confirmed mistake."
)
