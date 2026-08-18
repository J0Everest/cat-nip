"""
CAT-NIP Design System
Everest brand palette, typography, and shared CSS for the modernized UI.
"""
import streamlit as st

# ── Brand palette (Brand Guide Oct 2024, p.16) ────────────────────────────────
EVEREST_BLUE  = "#235CF4"
MID_BLUE      = "#0A3699"
DARK_BLUE     = "#061C49"
MID_GRAY      = "#A4ABC8"
LIGHT_GRAY    = "#F5F5F5"
BORDER_GRAY   = "#E2E8F0"
WHITE         = "#FFFFFF"

# ── Data-viz secondary palette ─────────────────────────────────────────────────
VIZ_PURPLE       = "#6929C4"
VIZ_PURPLE_LIGHT = "#A56EFF"
VIZ_TEAL         = "#075D5D"
VIZ_TEAL_LIGHT   = "#119D9A"

# ── Semantic colours ───────────────────────────────────────────────────────────
COLOR_SUCCESS = "#198038"
COLOR_WARNING = "#F1C21B"
COLOR_DANGER  = "#DA1E28"

SCENARIO_LOW  = COLOR_SUCCESS
SCENARIO_MED  = "#E67E22"
SCENARIO_HIGH = COLOR_DANGER

# ── Plotly colour sequences ────────────────────────────────────────────────────
PERIL_COLOR_MAP = {
    "Wind":     EVEREST_BLUE,
    "EQ":       VIZ_PURPLE,
    "Flood":    VIZ_TEAL,
    "Wildfire":  MID_BLUE,
    "MPCI":     VIZ_PURPLE_LIGHT,
    "CROP":     VIZ_TEAL_LIGHT,
    "FI":       "#8B5CF6",
}

SCENARIO_COLOR_MAP = {
    "Low":  SCENARIO_LOW,
    "Med":  SCENARIO_MED,
    "High": SCENARIO_HIGH,
}


def inject_global_css():
    """Inject once from app.py to set the visual baseline."""
    st.markdown(
        f"""
<style>
/* ── Typography ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif !important;
}}

/* ── Streamlit chrome cleanup ───────────────────────────── */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
.stDeployButton {{display: none;}}

/* ── Sidebar refinements ────────────────────────────────── */
[data-testid="stSidebar"] {{
    background: {DARK_BLUE};
}}
[data-testid="stSidebar"] * {{
    color: {WHITE} !important;
}}
[data-testid="stSidebar"] .stCaption {{
    color: {MID_GRAY} !important;
}}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label {{
    color: {MID_GRAY} !important;
    font-size: 0.78rem !important;
}}
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] [data-baseweb="select"] {{
    background: rgba(255,255,255,0.08) !important;
    border-color: rgba(255,255,255,0.15) !important;
    color: {WHITE} !important;
}}

/* ── Metric cards ───────────────────────────────────────── */
[data-testid="stMetric"] {{
    background: {WHITE};
    border: 1px solid {BORDER_GRAY};
    border-radius: 12px;
    padding: 18px 20px 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
[data-testid="stMetric"] [data-testid="stMetricLabel"] {{
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: {MID_GRAY} !important;
}}
[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-weight: 700 !important;
    color: {DARK_BLUE} !important;
    font-size: 1.6rem !important;
}}

/* ── Primary buttons ────────────────────────────────────── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {{
    background: {EVEREST_BLUE} !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.55rem 1.5rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em;
    transition: background 0.15s;
}}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {{
    background: {MID_BLUE} !important;
}}

/* ── Cards (custom class) ───────────────────────────────── */
.catnip-card {{
    background: {WHITE};
    border: 1px solid {BORDER_GRAY};
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
.catnip-card-accent {{
    border-left: 4px solid {EVEREST_BLUE};
}}

/* ── Parsed-filter pills ────────────────────────────────── */
.catnip-pill {{
    display: inline-block;
    background: #EBF0FE;
    color: {MID_BLUE};
    border-radius: 16px;
    padding: 4px 14px;
    font-size: 0.82rem;
    font-weight: 500;
    margin: 3px 4px 3px 0;
}}
.catnip-pill-muted {{
    background: {LIGHT_GRAY};
    color: {MID_GRAY};
}}

/* ── Confidence badges ──────────────────────────────────── */
.catnip-badge {{
    display: inline-block;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}}
.catnip-badge-high {{
    background: #D4EDDA; color: {COLOR_SUCCESS};
}}
.catnip-badge-med {{
    background: #FFF3CD; color: #856404;
}}
.catnip-badge-low {{
    background: #F8D7DA; color: {COLOR_DANGER};
}}

/* ── Scenario cards ─────────────────────────────────────── */
.scenario-card {{
    background: {WHITE};
    border: 2px solid {BORDER_GRAY};
    border-radius: 12px;
    padding: 18px;
    text-align: center;
    transition: border-color 0.15s, box-shadow 0.15s;
}}
.scenario-card:hover {{
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}}
.scenario-card-low  {{ border-top: 4px solid {SCENARIO_LOW}; }}
.scenario-card-med  {{ border-top: 4px solid {SCENARIO_MED}; }}
.scenario-card-high {{ border-top: 4px solid {SCENARIO_HIGH}; }}
.scenario-label {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700;
    margin-bottom: 6px;
}}
.scenario-value {{
    font-size: 1.4rem;
    font-weight: 700;
    color: {DARK_BLUE};
    margin-bottom: 2px;
}}
.scenario-detail {{
    font-size: 0.78rem;
    color: {MID_GRAY};
}}

/* ── Section headers ────────────────────────────────────── */
.catnip-section-title {{
    font-size: 1.05rem;
    font-weight: 700;
    color: {DARK_BLUE};
    border-bottom: 2px solid {EVEREST_BLUE};
    padding-bottom: 6px;
    margin: 24px 0 12px;
}}

/* ── Prompt hero area ───────────────────────────────────── */
.prompt-hero {{
    background: linear-gradient(135deg, {DARK_BLUE} 0%, {MID_BLUE} 100%);
    border-radius: 16px;
    padding: 32px 36px 24px;
    margin-bottom: 24px;
    color: {WHITE};
}}
.prompt-hero h2 {{
    color: {WHITE} !important;
    border: none !important;
    font-weight: 700;
    margin: 0 0 4px;
    font-size: 1.35rem;
}}
.prompt-hero p {{
    color: {MID_GRAY};
    font-size: 0.88rem;
    margin: 0;
}}

/* ── Data tables ────────────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border-radius: 8px;
    overflow: hidden;
}}

/* ── Step indicator ─────────────────────────────────────── */
.step-bar {{
    display: flex;
    gap: 0;
    margin-bottom: 20px;
}}
.step-item {{
    flex: 1;
    text-align: center;
    padding: 10px 8px;
    font-size: 0.78rem;
    font-weight: 600;
    border-bottom: 3px solid {BORDER_GRAY};
    color: {MID_GRAY};
    transition: all 0.2s;
}}
.step-item.active {{
    border-bottom-color: {EVEREST_BLUE};
    color: {EVEREST_BLUE};
}}
.step-item.done {{
    border-bottom-color: {COLOR_SUCCESS};
    color: {COLOR_SUCCESS};
}}
</style>
""",
        unsafe_allow_html=True,
    )
