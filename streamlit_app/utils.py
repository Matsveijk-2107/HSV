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

/* Tabs: a cleaner underline instead of Streamlit's default heavy bar */
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
}}
.stTabs [data-baseweb="tab"] {{
    height: 40px;
    border-radius: 8px 8px 0 0;
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


def page_header(title: str, caption: str = ""):
    apply_theme()
    st.title(title)
    if caption:
        st.caption(caption)


def confidence_badge(is_validated: bool) -> str:
    return "Statistically validated" if is_validated else "Exploratory / descriptive only"
