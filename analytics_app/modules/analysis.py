"""Multi-panel dashboard builder — metrics, dimensions, charts & layout."""

import pandas as pd
import numpy as np
import streamlit as st

from analytics_app.modules.visualizations import CHART_TYPES, render_chart
from analytics_app.modules.narrative import render_narrative


AGG_FUNCTIONS = ["sum", "mean", "median", "count", "min", "max", "std"]

# Layout options: label → number of columns
LAYOUT_OPTIONS = {
    "1 column": 1,
    "2 columns": 2,
    "3 columns": 3,
}

_DEFAULT_PANEL = {
    "metrics": [],
    "dimensions": [],
    "agg_func": "sum",
    "chart_type": "Bar Chart",
    "color_dim": None,
    "title": "",
}


def _ensure_dashboard_state():
    """Initialise dashboard session state if needed."""
    if "dashboard_panels" not in st.session_state:
        st.session_state["dashboard_panels"] = [_DEFAULT_PANEL.copy()]
    if "dashboard_layout" not in st.session_state:
        st.session_state["dashboard_layout"] = "1 column"


def render_analysis_step(df: pd.DataFrame, profile: pd.DataFrame):
    """Render the full dashboard builder: panels, layout and narrative."""
    _ensure_dashboard_state()

    st.header("4. Analyse & Visualise")
    st.markdown(
        "Build a dashboard by adding chart panels. Each panel has its own "
        "metrics, dimensions, aggregation, and chart type. Use the layout "
        "control to arrange panels side by side."
    )

    # Classify columns
    numeric_cols = [
        c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
    ]
    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]
    all_cols = list(df.columns)

    # ── Global controls ─────────────────────────────────────────────────────
    ctrl_a, ctrl_b, ctrl_c = st.columns([2, 2, 6])
    with ctrl_a:
        layout_choice = st.selectbox(
            "Dashboard layout",
            options=list(LAYOUT_OPTIONS.keys()),
            index=list(LAYOUT_OPTIONS.keys()).index(
                st.session_state["dashboard_layout"]
            ),
            key="layout_select",
        )
        st.session_state["dashboard_layout"] = layout_choice

    with ctrl_b:
        st.markdown("")  # spacer
        st.markdown("")
        if st.button("Add panel", use_container_width=True, type="primary"):
            st.session_state["dashboard_panels"].append(_DEFAULT_PANEL.copy())
            st.rerun()

    n_layout_cols = LAYOUT_OPTIONS[layout_choice]
    panels = st.session_state["dashboard_panels"]

    # ── Global filters (applied to all panels) ──────────────────────────────
    # Collect all dimensions used across panels for filtering
    all_selected_dims = []
    for p in panels:
        all_selected_dims.extend(p.get("dimensions", []))
    all_selected_dims = list(dict.fromkeys(all_selected_dims))  # dedupe, keep order

    filtered_df = _render_global_filters(df, non_numeric_cols)

    # ── Panel configuration ─────────────────────────────────────────────────
    with st.expander("Panel Configuration", expanded=True):
        for idx, panel in enumerate(panels):
            st.markdown(f"**Panel {idx + 1}**")
            p1, p2, p3 = st.columns([3, 3, 1])

            with p1:
                panel["metrics"] = st.multiselect(
                    "Metrics",
                    options=all_cols,
                    default=panel.get("metrics") or (numeric_cols[:2] if numeric_cols else []),
                    key=f"panel_metrics_{idx}",
                    help="Numeric columns to measure.",
                )
                panel["agg_func"] = st.selectbox(
                    "Aggregation",
                    options=AGG_FUNCTIONS,
                    index=AGG_FUNCTIONS.index(panel.get("agg_func", "sum")),
                    key=f"panel_agg_{idx}",
                )

            with p2:
                panel["dimensions"] = st.multiselect(
                    "Dimensions (group by)",
                    options=all_cols,
                    default=panel.get("dimensions") or (non_numeric_cols[:1] if non_numeric_cols else []),
                    key=f"panel_dims_{idx}",
                    help="Categorical columns to group or slice by.",
                )
                panel["chart_type"] = st.selectbox(
                    "Chart type",
                    options=CHART_TYPES,
                    index=CHART_TYPES.index(panel.get("chart_type", "Bar Chart")),
                    key=f"panel_chart_{idx}",
                )

            with p3:
                panel["color_dim"] = st.selectbox(
                    "Color by",
                    options=["None"] + non_numeric_cols,
                    index=0,
                    key=f"panel_color_{idx}",
                )
                if panel["color_dim"] == "None":
                    panel["color_dim"] = None

                if len(panels) > 1:
                    if st.button("Remove", key=f"remove_panel_{idx}", use_container_width=True):
                        st.session_state["dashboard_panels"].pop(idx)
                        st.rerun()

            panel["title"] = st.text_input(
                "Chart title (optional)",
                value=panel.get("title", ""),
                key=f"panel_title_{idx}",
            )

            if idx < len(panels) - 1:
                st.divider()

    # ── Render dashboard panels ─────────────────────────────────────────────
    st.divider()
    st.subheader("Dashboard")

    result_dfs = []
    # Chunk panels into rows of n_layout_cols
    for row_start in range(0, len(panels), n_layout_cols):
        row_panels = panels[row_start : row_start + n_layout_cols]
        cols = st.columns(len(row_panels))

        for col, panel in zip(cols, row_panels):
            with col:
                result_df = render_chart(
                    filtered_df,
                    panel["chart_type"],
                    panel["metrics"],
                    panel["dimensions"],
                    agg_func=panel["agg_func"],
                    color_dim=panel["color_dim"],
                    title=panel["title"],
                )
                if result_df is not None:
                    result_dfs.append(result_df)

    # ── Narrative (uses first panel's config) ───────────────────────────────
    if panels:
        first = panels[0]
        if first["metrics"]:
            st.divider()
            render_narrative(
                filtered_df,
                first["metrics"],
                first["dimensions"],
                first["agg_func"],
            )

    # ── Download ────────────────────────────────────────────────────────────
    if result_dfs:
        st.divider()
        combined = pd.concat(result_dfs, ignore_index=True)
        _render_download(combined)


def _render_global_filters(df: pd.DataFrame, non_numeric_cols: list) -> pd.DataFrame:
    """Render global filter widgets that apply to all panels."""
    with st.expander("Global Filters", expanded=False):
        if not non_numeric_cols:
            st.info("No categorical columns available for filtering.")
            return df

        filter_dims = st.multiselect(
            "Select columns to filter on",
            options=non_numeric_cols,
            default=[],
            key="global_filter_dims",
        )

        filtered = df.copy()
        for dim in filter_dims:
            if dim not in df.columns:
                continue

            unique_vals = df[dim].dropna().unique()
            if len(unique_vals) > 100:
                search = st.text_input(
                    f"Filter `{dim}` (comma-separated values)",
                    key=f"gfilter_{dim}",
                )
                if search.strip():
                    vals = [v.strip() for v in search.split(",")]
                    filtered = filtered[filtered[dim].astype(str).isin(vals)]
            elif len(unique_vals) > 0:
                selected = st.multiselect(
                    f"Filter `{dim}`",
                    options=sorted(unique_vals.astype(str)),
                    default=None,
                    key=f"gfilter_{dim}",
                )
                if selected:
                    filtered = filtered[filtered[dim].astype(str).isin(selected)]

        return filtered

    return df


def _render_download(result_df: pd.DataFrame):
    """Offer a CSV download of the aggregated result."""
    csv_data = result_df.to_csv(index=False)
    st.download_button(
        label="Download result as CSV",
        data=csv_data,
        file_name="analysis_output.csv",
        mime="text/csv",
    )
