"""Narrative generation module — produces textual insights from data."""

import pandas as pd
import numpy as np
import streamlit as st


def generate_narrative(
    df: pd.DataFrame,
    metrics: list,
    dimensions: list,
    agg_func: str = "sum",
) -> str:
    """Generate a plain-English narrative summarising the selected data slice."""
    sections = []

    # Overview
    sections.append(_overview_narrative(df, metrics, dimensions))

    # Per-metric insights
    for metric in metrics:
        if metric in df.columns and pd.api.types.is_numeric_dtype(df[metric]):
            sections.append(_metric_narrative(df, metric, dimensions, agg_func))

    # Correlation insight (if multiple metrics)
    if len(metrics) >= 2:
        corr_narrative = _correlation_narrative(df, metrics)
        if corr_narrative:
            sections.append(corr_narrative)

    # Dimension distribution insight
    for dim in dimensions:
        if dim in df.columns:
            sections.append(_dimension_narrative(df, dim, metrics, agg_func))

    return "\n\n".join(s for s in sections if s)


def render_narrative(
    df: pd.DataFrame,
    metrics: list,
    dimensions: list,
    agg_func: str,
):
    """Render the narrative section in the Streamlit UI."""
    st.subheader("Data Narrative")
    narrative = generate_narrative(df, metrics, dimensions, agg_func)
    st.markdown(narrative)


def _overview_narrative(df, metrics, dimensions):
    parts = [f"The dataset contains **{len(df):,}** records."]

    if metrics:
        parts.append(
            f"The analysis focuses on **{len(metrics)}** metric(s): "
            f"{', '.join(f'`{m}`' for m in metrics)}."
        )
    if dimensions:
        parts.append(
            f"Data is segmented by **{len(dimensions)}** dimension(s): "
            f"{', '.join(f'`{d}`' for d in dimensions)}."
        )
    return " ".join(parts)


def _metric_narrative(df, metric, dimensions, agg_func):
    series = df[metric].dropna()
    if series.empty:
        return f"**{metric}**: No non-null values available for analysis."

    total = series.sum()
    mean = series.mean()
    median = series.median()
    std = series.std()
    min_val = series.min()
    max_val = series.max()

    parts = [f"**{metric}**:"]
    parts.append(
        f"Total = {_fmt(total)}, Mean = {_fmt(mean)}, "
        f"Median = {_fmt(median)}, Std Dev = {_fmt(std)}."
    )
    parts.append(f"Range: {_fmt(min_val)} to {_fmt(max_val)}.")

    # Skewness insight
    skew = series.skew()
    if abs(skew) > 1:
        direction = "right (positively)" if skew > 0 else "left (negatively)"
        parts.append(
            f"The distribution is notably skewed to the {direction} "
            f"(skewness = {skew:.2f}), indicating the presence of "
            f"{'high' if skew > 0 else 'low'} outliers."
        )

    # Top/bottom by first dimension
    if dimensions and dimensions[0] in df.columns:
        dim = dimensions[0]
        grouped = df.groupby(dim)[metric].agg(agg_func).sort_values(ascending=False)
        if len(grouped) >= 2:
            top_name = str(grouped.index[0])
            top_val = grouped.iloc[0]
            bottom_name = str(grouped.index[-1])
            bottom_val = grouped.iloc[-1]
            parts.append(
                f"Across `{dim}`, the highest {agg_func} is "
                f"**{top_name}** ({_fmt(top_val)}) and the lowest is "
                f"**{bottom_name}** ({_fmt(bottom_val)})."
            )

            # Concentration
            if total > 0:
                top_pct = top_val / total * 100
                if top_pct > 50:
                    parts.append(
                        f"**{top_name}** alone accounts for {top_pct:.1f}% "
                        f"of the total, indicating high concentration."
                    )

    return " ".join(parts)


def _correlation_narrative(df, metrics):
    """Describe pairwise correlations between metrics."""
    numeric_metrics = [m for m in metrics if m in df.columns and pd.api.types.is_numeric_dtype(df[m])]
    if len(numeric_metrics) < 2:
        return None

    corr_matrix = df[numeric_metrics].corr()

    strong = []
    for i, m1 in enumerate(numeric_metrics):
        for m2 in numeric_metrics[i + 1 :]:
            r = corr_matrix.loc[m1, m2]
            if abs(r) > 0.7:
                direction = "positive" if r > 0 else "negative"
                strong.append(f"`{m1}` and `{m2}` (r = {r:.2f}, {direction})")

    if strong:
        return (
            "**Correlations**: Strong linear relationships detected between: "
            + "; ".join(strong)
            + "."
        )
    return "**Correlations**: No strong linear relationships (|r| > 0.7) found between the selected metrics."


def _dimension_narrative(df, dim, metrics, agg_func):
    """Describe the distribution of a dimension."""
    series = df[dim].dropna()
    n_unique = series.nunique()

    parts = [f"**{dim}**:"]
    parts.append(f"{n_unique:,} unique value(s).")

    if n_unique <= 20:
        value_counts = series.value_counts()
        top = value_counts.head(5)
        breakdown = ", ".join(f"{v} ({c:,})" for v, c in top.items())
        parts.append(f"Top values: {breakdown}.")

        # Evenness check
        if n_unique > 1:
            proportions = value_counts / value_counts.sum()
            entropy = -(proportions * np.log2(proportions)).sum()
            max_entropy = np.log2(n_unique)
            evenness = entropy / max_entropy if max_entropy > 0 else 0
            if evenness > 0.9:
                parts.append("Values are **evenly distributed**.")
            elif evenness < 0.5:
                parts.append(
                    "Values are **highly concentrated** in a few categories."
                )
    else:
        parts.append(
            f"High cardinality dimension with {n_unique:,} unique values — "
            "consider grouping or filtering for clearer analysis."
        )

    return " ".join(parts)


def _fmt(value):
    """Format a numeric value for display."""
    if pd.isna(value):
        return "N/A"
    if abs(value) >= 1_000_000:
        return f"{value:,.0f}"
    if abs(value) >= 1:
        return f"{value:,.2f}"
    return f"{value:.4f}"
