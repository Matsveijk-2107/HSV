import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.express as px
import streamlit as st
from utils import HSV_COLOR, LOGO_PATH, load_csv, page_header

st.set_page_config(page_title="Synchronization Attribution", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header(
    "Synchronization Attribution: the One Validated Cause",
    "Per-player attribution built on the one dimension confirmed to actually drive breakdowns.",
)

st.markdown(
    """
Reimplements Synchronization's own two terms per defender instead of the collapsed team score.
**100% of 400 events attributed.** Unlike Pressure attribution, there's no "ball mid-flight" failure mode
here, since this only needs defender velocities, not the ball or an attacker.
"""
)

THRESHOLDS = {"HSV squad": (5, 3), "Opponents": (3, 2)}
group = st.radio("Squad", ["HSV squad", "Opponents"], horizontal=True)
file = "synchronization_attribution_hsv_players.csv" if group == "HSV squad" else "synchronization_attribution_opponents.csv"
min_flagged, min_matches = THRESHOLDS[group]

df = load_csv(file)
df["confident"] = (df["times_responsible"] >= min_flagged) & (df["matches"] >= min_matches)
confident = df[df["confident"]].sort_values("times_responsible", ascending=False)

st.caption(f"Confident tier: ≥{min_flagged} times responsible across ≥{min_matches} matches. {len(confident)} of {len(df)} players.")

fig = px.bar(
    confident.sort_values("times_responsible"),
    x="times_responsible", y="player_name", orientation="h",
    color_discrete_sequence=[HSV_COLOR],
    labels={"times_responsible": "Times responsible", "player_name": ""},
    hover_data=["matches", "avg_deviation_cm_s"],
)
fig.update_layout(height=max(400, 28 * len(confident)))
st.plotly_chart(fig, width="stretch")

if group == "HSV squad":
    st.success(
        "**Cross-metric agreement holds up completely:** all 11 confident names here are corroborated by the "
        "independent Player Weakness Finder method (6 at its confident tier, 5 more at its exploratory tier), "
        "two methods that share no computation, agreeing on every single name. Goalkeepers are excluded from "
        "the underlying formula entirely (`compute_si_v2.py`), not just flagged, since a keeper's job was "
        "never to shift with the back line; confirmed zero goalkeeper rows in this data."
    )

st.dataframe(
    confident[["player_name", "times_responsible", "matches", "avg_deviation_cm_s"]].round(1),
    width="stretch", hide_index=True,
)

with st.expander("The metric itself was rebuilt after a direct challenge: methodology and robustness"):
    st.markdown(
        """
        Challenged directly, twice: *"just count who's moving with the block; if one player isn't going the
        same way, that's the problem."* That's the metric's directional term. Tested every version of this
        idea against real breakdown data: the thesis formula's own crude version (sign of one axis, with and
        without the goalkeeper) and a proper full 2D compass-angle version built specifically to test the
        refined proposal (`synchronization_decompose_test.py`, `synchronization_compass_test.py`):

        **Directional term (is a majority moving the same rough direction), HSV:**

        | Method | Shift | p-value |
        |---|---|---|
        | Sign-based, GK included | -0.005 | 0.345 |
        | Sign-based, GK excluded (si_v2's own convention) | -0.002 | 0.416 |
        | Full 2D compass angle | +0.008 | 0.970 |

        **Speed-coherence term (are defenders moving at *similar speed*, not just direction), HSV:**

        | Method | Shift | p-value |
        |---|---|---|
        | With GK | -0.173 | 2.0×10⁻⁶⁴ |
        | No GK (si_v2's own convention) | -0.180 | 2.1×10⁻⁶⁶ |

        **Direction-agreement carries no real signal at all, however you measure it: every variant above, at**
        **every population split checked (HSV/Opponents/Pooled), lands between p=0.34 and p=1.00.** The entire
        validated effect is about *pace*: one player moving much faster or slower than the rest of the unit,
        even while broadly aligned in direction.

        Since the directional term is proven dead weight, it was dropped from the formula entirely rather
        than patched around; kept in at 50% weight, it only dilutes the half that's real. Two more
        hypotheses were tested before finalizing this (`synchronization_formula_search.py`): full 2D speed
        instead of just the y-axis, and smoothing velocity over a trailing 1-second window instead of one
        instantaneous frame. **Both made things worse, not better**: the plain single-frame, y-axis-only
        version wins outright. Best explanation: y is specifically the pitch's *width* axis, and lateral
        "shifting as a block" is the real coaching concept; a genuine lapse is often a sharp instant that
        smoothing dilutes.

        The result, `compute_si_v2.py` (goalkeeper excluded, single-frame, y-axis coherence only), tested
        with the exact same baseline-controlled method used everywhere else in this project:

        | | Original SI | Improved si_v2 |
        |---|---|---|
        | Pooled | shift -0.202, p=5.4×10⁻¹²⁷ | shift **-0.239**, p=**2.3×10⁻¹⁷⁸** |
        | HSV | shift -0.194, p=1.5×10⁻⁵⁹ | shift **-0.229**, p=**1.8×10⁻⁸³** |
        | Opponents | shift -0.209, p=5.4×10⁻⁷³ | shift **-0.248**, p=**2.3×10⁻⁹⁷** |

        Bigger effect, far more significant, every cut, with the goalkeeper now excluded from the pool
        entirely (not just flagged), since a keeper's job was never to shift with the back line. This is the
        HSV-dashboard's version specifically; the thesis's own submitted formula and results are untouched
        (`compute_si_thesis.py`). "Responsible" below is whichever outfield defender deviates most from the
        team's average velocity: the mechanism actually driving the validated effect.
        """
    )

st.markdown("---")
st.subheader("Visual spot-check")
st.markdown(
    """
Muheim's highest-deviation flagged frames were checked against real tracking positions (see **Visual
Examples** page), twice, since the mechanism change could have shifted which frames rank highest. It
mostly didn't: his top 3 frames are identical under both the old and new attribution logic (he was already
the biggest deviator there regardless of which mechanism was used to pick him). Of those, 1 was a clear,
unambiguous match (back line drifting one way, Muheim moving the other, right at the byline near the ball);
the other 2 were inconclusive from a static image; his marker sits on top of the ball, making the velocity
arrow unreadable at plot scale. Rank 4 changed with the fix, and was checked fresh: a clean, textbook example
of the *corrected* mechanism specifically. Muheim stands still while the rest of the back line shows real,
visible velocity in a consistent direction, matching the frame's own label
(`velocity_outlier_same_direction`) exactly. Not one player running the wrong way; one player not moving
while everyone else is. Full video review of the rest still not attempted.
"""
)

st.markdown("---")
with st.expander("Superseded: Pressure attribution (kept for reference, not a validated cause)"):
    st.caption(
        "Pressure looked like a leading cause under three earlier, flawed comparison methods (see Pressing "
        "Phases' Season Pooled tab for the debugging trail), but is NOT actually elevated at real breakdown "
        "moments once tested properly. Kept as exploratory data only; this is who has the least individual "
        "pressure right before HSV concedes a chance, not a validated explanation of why."
    )
    pressure_group = st.radio("Squad ", ["HSV squad", "Opponents"], horizontal=True, key="pressure_group")
    pfile = "pressure_attribution_hsv_players.csv" if pressure_group == "HSV squad" else "pressure_attribution_opponents.csv"
    pdf = load_csv(pfile).sort_values("times_responsible", ascending=False)
    st.dataframe(pdf.head(15)[["player_name", "times_responsible", "matches", "avg_individual_pressure", "avg_dist_to_carrier_m"]].round(3), width="stretch", hide_index=True)
