"""Metrics and dimensions selection and analysis module."""

import pandas as pd
import numpy as np
import streamlit as st

from analytics_app.modules.visualizations import CHART_TYPES, render_chart
from analytics_app.modules.narrative import render_narrative


AGG_FUNCTIONS = ["sum", "mean", "median", "count", "min", "max", "std"]


def render_analysis_step(df: pd.DataFrame, profile: pd.DataFrame):
    """Render the main analysis interface: metric/dimension selection + visualization."""
    st.header("4. Analyse & Visualise")
    st.markdown(
        "Select your metrics (numeric columns to measure) and dimensions "
        "(categorical columns to group by), choose a chart type, and explore your data."
    )

    # Classify columns
    numeric_cols = [
        c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
    ]
    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]
    all_cols = list(df.columns)

    # --- Sidebar-style controls in an expander ---
    with st.expander("Analysis Configuration", expanded=True):
        config_col1, config_col2 = st.columns(2)

        with config_col1:
            selected_metrics = st.multiselect(
                "Metrics (values to measure)",
                options=all_cols,
                default=numeric_cols[:3] if numeric_cols else [],
                help="Choose the numeric columns you want to aggregate and visualise.",
            )

        with config_col2:
            selected_dimensions = st.multiselect(
                "Dimensions (categories to group by)",
                options=all_cols,
                default=non_numeric_cols[:2] if non_numeric_cols else [],
                help="Choose the columns to slice and group your data by.",
            )

        ctrl1, ctrl2, ctrl3 = st.columns(3)

        with ctrl1:
            agg_func = st.selectbox(
                "Aggregation function",
                options=AGG_FUNCTIONS,
                index=0,
            )

        with ctrl2:
            chart_type = st.selectbox(
                "Chart type",
                options=CHART_TYPES,
                index=0,
            )

        with ctrl3:
            color_dim = st.selectbox(
                "Color by (optional)",
                options=["None"] + non_numeric_cols,
                index=0,
            )
            if color_dim == "None":
                color_dim = None

        chart_title = st.text_input("Chart title (optional)", value="")

    # --- Filters ---
    filtered_df = _render_filters(df, selected_dimensions)

    if not selected_metrics and chart_type != "Data Table":
        st.info("Select at least one metric to generate a visualisation.")
        return

    # --- Render chart ---
    st.divider()

    result_df = render_chart(
        filtered_df,
        chart_type,
        selected_metrics,
        selected_dimensions,
        agg_func=agg_func,
        color_dim=color_dim,
        title=chart_title,
    )

    # --- Narrative ---
    st.divider()
    render_narrative(filtered_df, selected_metrics, selected_dimensions, agg_func)

    # --- Download ---
    if result_df is not None and not result_df.empty:
        st.divider()
        _render_download(result_df)


def _render_filters(df: pd.DataFrame, dimensions: list) -> pd.DataFrame:
    """Render dynamic filter widgets for each selected dimension."""
    if not dimensions:
        return df

    with st.expander("Filters", expanded=False):
        filtered = df.copy()
        for dim in dimensions:
            if dim not in df.columns:
                continue

            unique_vals = df[dim].dropna().unique()
            if len(unique_vals) > 100:
                # Text input for high-cardinality dims
                search = st.text_input(
                    f"Filter `{dim}` (comma-separated values)", key=f"filter_{dim}"
                )
                if search.strip():
                    vals = [v.strip() for v in search.split(",")]
                    filtered = filtered[filtered[dim].astype(str).isin(vals)]
            elif len(unique_vals) > 0:
                selected = st.multiselect(
                    f"Filter `{dim}`",
                    options=sorted(unique_vals.astype(str)),
                    default=None,
                    key=f"filter_{dim}",
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
