import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.express as px
import streamlit as st
from utils import CATEGORICAL_SEQUENCE, LOGO_PATH, download_csv_button, load_csv, page_header

st.set_page_config(page_title="Opponent Playmaker Impact", page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None, layout="wide")
page_header(
    "Opponent Playmaker Impact",
    "Which specific opposing players, when personally on the ball, correlate with HSV's press measurably loosening?",
)

with st.expander("6 attempts before this was trustworthy: what changed each time", expanded=False):
    st.markdown(
        """
        1. **First pass (TPR, match baseline):** correlation between a player's average pitch position and
           their "impact" score was **0.855**: the "suppresses the press" list was literally every
           goalkeeper, the "increases it" list literally every forward. Pure pitch geometry.
        2. **3-zone position control:** correlation only dropped to 0.717.
        3. **Switched to real nearest-HSV-defender distance** (a tracking-XML rebuild, not TPR) with 10m
           x-bins: -0.723. A 2D x/y grid: -0.650. Barely better; nearest-defender distance is, if anything,
           *more* tied to pitch zone than TPR was.
        4. **The actual fix: control for ROLE, not position.** A striker's zone and a center-back's zone
           aren't just spatially different, they're categorically different jobs. Grouping into 8 broad
           roles from StatsBomb's own Starting XI data brought the correlation to **-0.107**, effectively
           resolved.
        """
    )
    st.caption("Residual: within-role position correlation isn't fully zero for every role (Full Back -0.53, Center Back -0.37); smaller than the original confound by a wide margin, but real.")

df = load_csv("opponent_playmaker_impact_role_controlled_summary.csv")
min_touches = st.slider("Minimum touches", 5, 50, 15)
confident = df[df["touches"] >= min_touches]

roles = ["All"] + sorted(confident["role"].dropna().unique().tolist())
role_filter = st.selectbox("Filter by role", roles)
if role_filter != "All":
    confident = confident[confident["role"] == role_filter]

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Most pressed relative to same-role peers**")
    most_pressed = confident.sort_values("role_adjusted_dist").head(12)
    fig = px.bar(most_pressed.sort_values("role_adjusted_dist", ascending=False), x="role_adjusted_dist", y="player_name", orientation="h", color="role", color_discrete_sequence=CATEGORICAL_SEQUENCE, labels={"role_adjusted_dist": "m vs. role baseline", "player_name": ""})
    fig.update_layout(height=420)
    st.plotly_chart(fig, width="stretch")
with col2:
    st.markdown("**Most space relative to same-role peers**")
    most_space = confident.sort_values("role_adjusted_dist", ascending=False).head(12)
    fig = px.bar(most_space.sort_values("role_adjusted_dist"), x="role_adjusted_dist", y="player_name", orientation="h", color="role", color_discrete_sequence=CATEGORICAL_SEQUENCE, labels={"role_adjusted_dist": "m vs. role baseline", "player_name": ""})
    fig.update_layout(height=420)
    st.plotly_chart(fig, width="stretch")

st.caption("Even within goalkeepers specifically there's real spread: some get pressed far more than others, plausibly reflecting which keepers HSV respects enough to press higher against.")

# Was re-deriving from the unfiltered `df` here, ignoring the role_filter applied to `confident`
# above -- the two charts respected the "Filter by role" dropdown but this table silently didn't,
# so picking e.g. "Center Back" filtered the charts but left every role in the table below them.
playmaker_table = confident.sort_values("role_adjusted_dist")[["player_name", "role", "touches", "matches", "avg_x_m", "role_adjusted_dist"]].round(2)
st.dataframe(playmaker_table, width="stretch", hide_index=True)
download_csv_button(playmaker_table, "Download table (CSV)", "opponent_playmaker_impact.csv")
