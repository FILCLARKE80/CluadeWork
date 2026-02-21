"""
Analytics App — CSV Upload, Profile, Cast, Analyse & Visualise.

Run with:  streamlit run app.py
"""

import streamlit as st

from analytics_app.modules.data_ingestion import render_upload_step
from analytics_app.modules.data_profiler import render_profiling_step
from analytics_app.modules.type_caster import render_casting_step
from analytics_app.modules.analysis import render_analysis_step


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Analytics App",
    page_icon="\U0001f4ca",
    layout="wide",
    initial_sidebar_state="expanded",
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
    st.title("Analytics App")
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
