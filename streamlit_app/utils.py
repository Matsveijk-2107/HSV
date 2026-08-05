"""Shared paths, constants, and cached loaders for the dashboard pages.

Every page reads directly from the already-validated result CSVs in
results/ (or the small prep tables in streamlit_app/data/, see
prepare_dashboard_data.py) -- no live recomputation happens in the app.
"""

from pathlib import Path

import pandas as pd
import plotly.io as pio
import streamlit as st

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"
APP_DATA_DIR = Path(__file__).resolve().parent / "data"
LOGO_PATH = Path(__file__).resolve().parents[1] / "Hamburger_SV_logo.svg"

DIMENSIONS = ["pressure", "compactness", "lpc", "pos", "anticipation", "synchronization"]
DIMENSION_LABELS = {
    "pressure": "Pressure",
    "compactness": "Compactness",
    "lpc": "Local Pitch Control",
    "pos": "Pass Option Suppression",
    "anticipation": "Anticipation (DAI)",
    "synchronization": "Synchronization (SI)",
}
DIMENSION_WEIGHTS = {
    "anticipation": 0.2305,
    "synchronization": 0.2109,
    "pressure": 0.1915,
    "pos": 0.1644,
    "lpc": 0.1217,
    "compactness": 0.0809,
}

# Single source of truth for every color in the app -- HSV's own brand
# blue (#1e5cb3, extracted directly from Hamburger_SV_logo.svg) paired
# with a categorical orange for "opponent"; blue/orange is one of the
# most CVD-robust hue pairs there is (it survives protanopia and
# deuteranopia, the two common forms, precisely because it doesn't rely
# on red-green discrimination). Status colors (validated/exploratory)
# are kept visually distinct from the HSV/Opponent pair on purpose, so a
# green "validated" badge never gets confused for a team color.
HSV_COLOR = "#1e5cb3"
OPPONENT_COLOR = "#eb6834"
VALIDATED_COLOR = "#2E7D32"
EXPLORATORY_COLOR = "#898781"
CRITICAL_COLOR = "#C62828"

# Fixed 8-hue categorical order, for charts with more than 2 series (e.g.
# player role) where HSV_COLOR/OPPONENT_COLOR don't apply -- validated
# order (adjacent-pair CVD-safe under protanopia/deuteranopia simulation),
# never cycled or reordered per-chart.
CATEGORICAL_SEQUENCE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
CHART_SURFACE = "#fcfcfb"

PLOTLY_TEMPLATE = "hsv_dashboard"


def _register_plotly_template():
    template = pio.templates["plotly_white"]
    template = pio.templates[PLOTLY_TEMPLATE] if PLOTLY_TEMPLATE in pio.templates else template.__class__(template)
    template.layout.font = dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK_PRIMARY, size=13)
    template.layout.paper_bgcolor = CHART_SURFACE
    template.layout.plot_bgcolor = CHART_SURFACE
    template.layout.colorway = [HSV_COLOR, OPPONENT_COLOR, VALIDATED_COLOR, "#4a3aa7", "#eda100", EXPLORATORY_COLOR]
    template.layout.xaxis = dict(gridcolor=GRIDLINE, zerolinecolor=GRIDLINE, linecolor="#c3c2b7", title_font=dict(color=INK_SECONDARY), tickfont=dict(color=INK_SECONDARY))
    template.layout.yaxis = dict(gridcolor=GRIDLINE, zerolinecolor=GRIDLINE, linecolor="#c3c2b7", title_font=dict(color=INK_SECONDARY), tickfont=dict(color=INK_SECONDARY))
    template.layout.margin = dict(l=10, r=10, t=40, b=10)
    template.layout.legend = dict(bgcolor="rgba(0,0,0,0)")
    pio.templates[PLOTLY_TEMPLATE] = template
    pio.templates.default = PLOTLY_TEMPLATE


_register_plotly_template()

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', system-ui, -apple-system, "Segoe UI", sans-serif;
}}

/* Sidebar: HSV navy with the crest, not Streamlit's default grey */
[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #0b1f3f 0%, #0a1830 100%);
}}
[data-testid="stSidebar"] * {{
    color: #eef2f9 !important;
}}
/* Logo gets its own boxed-off strip at the top, with a visible rule
   separating it from the page-nav list right below -- reads as a
   distinct header, not fused to the first nav item. */
[data-testid="stLogo"] {{
    padding: 14px 0 14px 0;
    margin-bottom: 6px;
    border-bottom: 1px solid rgba(255,255,255,0.15);
}}
[data-testid="stSidebarNav"] a {{
    border-radius: 8px;
    margin: 1px 8px;
}}
[data-testid="stSidebarNav"] a:hover {{
    background: rgba(255,255,255,0.08);
}}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
    background: rgba(30, 92, 179, 0.55);
    font-weight: 600;
}}

/* Page title block: a thin HSV-blue accent rule under every header */
h1 {{
    font-weight: 800 !important;
    letter-spacing: -0.01em;
    padding-bottom: 0.3rem;
    border-bottom: 3px solid {HSV_COLOR};
    display: inline-block;
}}
h2, h3 {{
    font-weight: 700 !important;
}}

/* Metric tiles: card-like, not bare numbers floating on the page. Value
   color set explicitly, not left to inherit -- .streamlit/config.toml
   pins the app to a light theme, but if that config is ever missing
   (e.g. a copy that dropped it) the tile background here still forces
   near-white, and an inherited dark-theme white value text would be
   invisible against it rather than just off-brand. */
[data-testid="stMetric"] {{
    background: {CHART_SURFACE};
    border: 1px solid {GRIDLINE};
    border-radius: 10px;
    padding: 14px 16px 10px 16px;
}}
[data-testid="stMetricLabel"] {{
    color: {INK_SECONDARY} !important;
}}
[data-testid="stMetricValue"] {{
    color: {INK_PRIMARY} !important;
}}

/* Tabs: distinct pill-shaped buttons with real spacing and padding, not
   plain text running together -- Streamlit's own defaults give each tab
   almost no horizontal padding and no background, so a row of longer
   labels reads as one continuous sentence instead of separate clickable
   controls. */
.stTabs [data-baseweb="tab-list"] {{
    gap: 6px;
    border-bottom: 2px solid {GRIDLINE};
}}
.stTabs [data-baseweb="tab"] {{
    height: 44px;
    padding: 0 20px;
    margin-bottom: -2px;
    border-radius: 8px 8px 0 0;
    background: {CHART_SURFACE};
    border: 1px solid {GRIDLINE};
    border-bottom: none;
    font-weight: 500;
    white-space: nowrap;
}}
.stTabs [data-baseweb="tab"] p {{
    font-size: 0.95rem;
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    background: #ffffff;
    border-color: {HSV_COLOR};
    box-shadow: inset 0 3px 0 {HSV_COLOR};
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] p {{
    color: {HSV_COLOR} !important;
    font-weight: 700;
}}
.stTabs [data-baseweb="tab-highlight"] {{
    background-color: transparent;
}}
.stTabs [data-baseweb="tab-border"] {{
    display: none;
}}

/* Expanders and alert boxes: rounded, consistent with the rest */
[data-testid="stExpander"], .stAlert {{
    border-radius: 10px !important;
}}

/* Dataframes: hairline border so tables read as one system, not a bare grid */
[data-testid="stDataFrame"] {{
    border: 1px solid {GRIDLINE};
    border-radius: 8px;
    overflow: hidden;
}}

footer {{visibility: hidden;}}
</style>
"""


def apply_theme():
    st.markdown(_CSS, unsafe_allow_html=True)
    if LOGO_PATH.exists():
        st.logo(str(LOGO_PATH), size="small")


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS_DIR / name)


@st.cache_data
def load_app_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(APP_DATA_DIR / name)


GLOSSARY_TERMS = [
    (
        "Percentile",
        "Where a value ranks against everything else in its comparison group, from 0 (lowest) to "
        "100 (highest). A defender at the 80th percentile for closing speed is faster than 80% of "
        "the defenders being compared.",
    ),
    (
        "Shift",
        "The change in percentile rank between two conditions, for example before vs. after a "
        "trigger, or HSV vs. the league average. A positive shift means the metric moved up in "
        "rank; a negative shift means it moved down.",
    ),
    (
        "p-value",
        "The probability of seeing a difference this large just by chance if there were really no "
        "effect at all. Below 0.05 is this app's cutoff for calling a difference statistically "
        "real rather than noise.",
    ),
    (
        "Validated vs. exploratory",
        "Validated findings passed a formal, baseline-controlled statistical test (p < 0.05), not "
        "just an eyeballed difference. Exploratory findings are descriptive patterns worth a "
        "closer look, not yet proven.",
    ),
    (
        "Confident vs. exploratory tier",
        "In player-level tables: confident-tier rows have enough matches or events behind them to "
        "trust the number. Exploratory-tier rows rest on too few observations to draw conclusions "
        "from directly.",
    ),
]


def page_header(title: str, caption: str = ""):
    apply_theme()
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title(title)
    with col2:
        with st.popover("How to read this", width="stretch"):
            for term, definition in GLOSSARY_TERMS:
                st.markdown(f"**{term}**  \n{definition}")
    if caption:
        st.caption(caption)


def confidence_badge(is_validated: bool) -> str:
    return "Statistically validated" if is_validated else "Exploratory / descriptive only"


def download_csv_button(df: pd.DataFrame, label: str, file_name: str, key: str | None = None):
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=file_name, mime="text/csv", key=key)
