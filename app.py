"""
Analytics App — CSV Upload, Profile, Cast, Analyse & Visualise.

Run with:  streamlit run app.py
"""

import streamlit as st

from analytics_app.modules.data_ingestion import render_upload_step
from analytics_app.modules.data_profiler import render_profiling_step
from analytics_app.modules.type_caster import render_casting_step
from analytics_app.modules.analysis import render_analysis_step
from analytics_app.modules.ai_narrative import render_ai_config_sidebar


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Analytics App",
    page_icon="\U0001f4ca",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── MIFL-inspired custom styling ────────────────────────────────────────────
# Brand palette derived from Mediolanum International Funds (mifl.ie):
#   Persian Blue  #1033CF  (primary)
#   Midnight Moss #010504  (text)
#   White         #FFFFFF  (background)
# Fonts: Montserrat (headings) + Inter (body) — geometric sans-serifs
#        that mirror the custom Mediolanum typeface characteristics.
st.markdown(
    """
    <style>
    /* ── Google Fonts ─────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Montserrat:wght@400;500;600;700;800&display=swap');

    /* ── Root variables ──────────────────────────────────────── */
    :root {
        --mifl-blue:       #1033CF;
        --mifl-blue-light: #E8EDFA;
        --mifl-blue-mid:   #6B8ADB;
        --mifl-dark:       #010504;
        --mifl-grey:       #4A4F5C;
        --mifl-grey-light: #F0F2F8;
        --mifl-white:      #FFFFFF;
        --mifl-accent:     #0D2A8A;
        --mifl-success:    #0F7B3F;
        --mifl-warning:    #C67D0A;
        --mifl-radius:     6px;
        --mifl-shadow:     0 1px 3px rgba(16, 51, 207, 0.08),
                           0 4px 12px rgba(16, 51, 207, 0.06);
    }

    /* ── Global typography ───────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--mifl-dark);
    }

    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Montserrat', 'Inter', sans-serif !important;
        font-weight: 700 !important;
        color: var(--mifl-dark) !important;
        letter-spacing: -0.02em;
    }

    h1, .stMarkdown h1 { font-size: 2rem !important; }
    h2, .stMarkdown h2 { font-size: 1.5rem !important; }
    h3, .stMarkdown h3 { font-size: 1.2rem !important; }

    /* ── Sidebar ─────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0A1E6E 0%, var(--mifl-blue) 100%) !important;
    }
    section[data-testid="stSidebar"] * {
        color: var(--mifl-white) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown hr {
        border-color: rgba(255, 255, 255, 0.15) !important;
    }
    /* Sidebar title */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] .stMarkdown h1 {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 800 !important;
        color: var(--mifl-white) !important;
        letter-spacing: -0.01em;
    }

    /* Sidebar buttons (step navigation) */
    section[data-testid="stSidebar"] button[kind="secondary"],
    section[data-testid="stSidebar"] .stButton > button {
        background: rgba(255, 255, 255, 0.10) !important;
        color: var(--mifl-white) !important;
        border: 1px solid rgba(255, 255, 255, 0.20) !important;
        border-radius: var(--mifl-radius) !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        padding: 0.55rem 1rem !important;
        transition: all 0.2s ease !important;
        backdrop-filter: blur(4px);
    }
    section[data-testid="stSidebar"] button[kind="secondary"]:hover,
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255, 255, 255, 0.22) !important;
        border-color: rgba(255, 255, 255, 0.40) !important;
        transform: translateY(-1px);
    }
    section[data-testid="stSidebar"] button[disabled] {
        opacity: 0.35 !important;
    }

    /* Sidebar captions & small text */
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] small {
        color: rgba(255, 255, 255, 0.70) !important;
    }

    /* ── Primary buttons (main area) ─────────────────────────── */
    .stButton > button[kind="primary"],
    button[data-testid="stBaseButton-primary"] {
        background: var(--mifl-blue) !important;
        color: var(--mifl-white) !important;
        border: none !important;
        border-radius: var(--mifl-radius) !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.6rem 1.5rem !important;
        letter-spacing: 0.01em;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 6px rgba(16, 51, 207, 0.25) !important;
    }
    .stButton > button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {
        background: var(--mifl-accent) !important;
        box-shadow: 0 4px 14px rgba(16, 51, 207, 0.35) !important;
        transform: translateY(-1px);
    }

    /* Secondary buttons (main area) */
    .stMainBlockContainer .stButton > button:not([kind="primary"]) {
        background: var(--mifl-white) !important;
        color: var(--mifl-blue) !important;
        border: 1.5px solid var(--mifl-blue) !important;
        border-radius: var(--mifl-radius) !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    .stMainBlockContainer .stButton > button:not([kind="primary"]):hover {
        background: var(--mifl-blue-light) !important;
    }

    /* ── Cards / expanders ───────────────────────────────────── */
    .stExpander {
        border: 1px solid #E1E5F0 !important;
        border-radius: var(--mifl-radius) !important;
        box-shadow: var(--mifl-shadow) !important;
        overflow: hidden;
    }
    .stExpander summary {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }

    /* ── Metrics ─────────────────────────────────────────────── */
    [data-testid="stMetric"] {
        background: var(--mifl-white);
        border: 1px solid #E1E5F0;
        border-radius: var(--mifl-radius);
        padding: 1rem;
        box-shadow: var(--mifl-shadow);
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: var(--mifl-grey) !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        color: var(--mifl-blue) !important;
    }

    /* ── Selectboxes / multiselects ──────────────────────────── */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        border-radius: var(--mifl-radius) !important;
        border-color: #D0D5E4 !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stSelectbox > div > div:focus-within,
    .stMultiSelect > div > div:focus-within {
        border-color: var(--mifl-blue) !important;
        box-shadow: 0 0 0 2px rgba(16, 51, 207, 0.15) !important;
    }

    /* ── File uploader ───────────────────────────────────────── */
    [data-testid="stFileUploader"] {
        border: 2px dashed var(--mifl-blue-mid) !important;
        border-radius: var(--mifl-radius) !important;
        background: var(--mifl-blue-light) !important;
        padding: 1.5rem !important;
    }

    /* ── Dataframes ──────────────────────────────────────────── */
    [data-testid="stDataFrame"] {
        border: 1px solid #E1E5F0 !important;
        border-radius: var(--mifl-radius) !important;
        overflow: hidden;
    }

    /* ── Tabs ────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
        border-bottom: 2px solid #E1E5F0;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        border-radius: var(--mifl-radius) var(--mifl-radius) 0 0 !important;
        padding: 0.5rem 1.25rem !important;
    }
    .stTabs [aria-selected="true"] {
        border-bottom: 3px solid var(--mifl-blue) !important;
        color: var(--mifl-blue) !important;
    }

    /* ── Alerts ──────────────────────────────────────────────── */
    .stAlert {
        border-radius: var(--mifl-radius) !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* ── Download button ─────────────────────────────────────── */
    .stDownloadButton > button {
        background: var(--mifl-white) !important;
        color: var(--mifl-blue) !important;
        border: 1.5px solid var(--mifl-blue) !important;
        border-radius: var(--mifl-radius) !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
    }
    .stDownloadButton > button:hover {
        background: var(--mifl-blue-light) !important;
    }

    /* ── Main area subtle refinements ────────────────────────── */
    .stMainBlockContainer {
        padding-top: 2rem;
    }
    .stMarkdown p {
        line-height: 1.65;
        color: var(--mifl-grey);
    }
    .stMarkdown a {
        color: var(--mifl-blue) !important;
        text-decoration: none !important;
        font-weight: 500;
    }
    .stMarkdown a:hover {
        text-decoration: underline !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state defaults ───────────────────────────────────────────────────
_DEFAULTS = {
    "raw_df": None,
    "profile": None,
    "quality_issues": None,
    "cast_df": None,
    "cast_report": None,
    "current_step": 1,
    "dashboard_panels": None,
    "dashboard_layout": None,
    "anthropic_api_key": None,
    "ai_model": None,
    "ai_narrative": None,
    "pres_sections": [],
}
for key, val in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── Sidebar navigation ──────────────────────────────────────────────────────
STEPS = {
    1: "Upload CSV",
    2: "Data Profile & Quality",
    3: "Confirm Data Types",
    4: "Analyse & Visualise",
}

with st.sidebar:
    st.title("MIFL Analytics")
    st.markdown("---")

    for step_num, step_label in STEPS.items():
        # Determine if step is reachable
        enabled = step_num <= st.session_state["current_step"]
        if enabled:
            if st.button(
                f"Step {step_num}: {step_label}",
                key=f"nav_{step_num}",
                use_container_width=True,
            ):
                st.session_state["current_step"] = step_num
                st.rerun()
        else:
            st.button(
                f"Step {step_num}: {step_label}",
                key=f"nav_{step_num}",
                disabled=True,
                use_container_width=True,
            )

    st.markdown("---")
    if st.session_state["raw_df"] is not None:
        df = st.session_state["raw_df"]
        st.caption(f"Loaded: {len(df):,} rows x {len(df.columns)} cols")

    # Reset button
    if st.button("Start Over", use_container_width=True):
        for key in _DEFAULTS:
            st.session_state[key] = _DEFAULTS[key]
        st.rerun()

render_ai_config_sidebar()


# ── Main content area ────────────────────────────────────────────────────────
current = st.session_state["current_step"]

if current == 1:
    df = render_upload_step()
    if df is not None:
        st.session_state["raw_df"] = df
        if st.button("Proceed to Data Profiling", type="primary"):
            st.session_state["current_step"] = 2
            st.rerun()

elif current == 2:
    df = st.session_state["raw_df"]
    if df is None:
        st.warning("No data loaded. Go back to Step 1.")
    else:
        profile, quality_issues = render_profiling_step(df)
        st.session_state["profile"] = profile
        st.session_state["quality_issues"] = quality_issues
        if st.button("Proceed to Type Casting", type="primary"):
            st.session_state["current_step"] = 3
            st.rerun()

elif current == 3:
    df = st.session_state["raw_df"]
    profile = st.session_state["profile"]
    if df is None or profile is None:
        st.warning("Complete Step 2 first.")
    else:
        cast_df = render_casting_step(df, profile)
        if cast_df is not None:
            if st.button("Proceed to Analysis", type="primary"):
                st.session_state["current_step"] = 4
                st.rerun()

elif current == 4:
    # Use cast data if available, otherwise raw
    df = st.session_state.get("cast_df", st.session_state["raw_df"])
    profile = st.session_state["profile"]
    if df is None:
        st.warning("No data available. Start from Step 1.")
    else:
        render_analysis_step(df, profile)
