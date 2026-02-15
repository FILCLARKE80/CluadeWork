"""Data profiling and quality analysis engine."""

import pandas as pd
import numpy as np
import streamlit as st


def render_profiling_step(df: pd.DataFrame):
    """Render the data profiling and quality report."""
    st.header("2. Data Profile & Quality Report")
    st.markdown(
        "Automatic profiling of your dataset. Review column statistics, "
        "data quality issues, and suggested data types below."
    )

    profile = _build_profile(df)
    quality_issues = _detect_quality_issues(df, profile)

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", f"{len(df):,}")
    col2.metric("Columns", f"{len(df.columns)}")
    col3.metric("Missing Cells", f"{df.isna().sum().sum():,}")
    dup_count = df.duplicated().sum()
    col4.metric("Duplicate Rows", f"{dup_count:,}")

    # Column profile table
    st.subheader("Column Profile")
    profile_display = profile[
        [
            "column",
            "detected_type",
            "non_null_count",
            "null_count",
            "null_pct",
            "unique_count",
            "sample_values",
        ]
    ].copy()
    profile_display["null_pct"] = profile_display["null_pct"].apply(
        lambda x: f"{x:.1f}%"
    )
    st.dataframe(profile_display, use_container_width=True, hide_index=True)

    # Numeric column statistics
    numeric_cols = profile[profile["detected_type"] == "numeric"]["column"].tolist()
    if numeric_cols:
        st.subheader("Numeric Column Statistics")
        numeric_stats = df[numeric_cols].describe().T
        numeric_stats.index.name = "column"
        st.dataframe(numeric_stats, use_container_width=True)

    # Quality issues
    if quality_issues:
        st.subheader("Data Quality Issues")
        for issue in quality_issues:
            severity_color = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢",
            }.get(issue["severity"], "⚪")
            st.markdown(
                f"{severity_color} **{issue['severity'].upper()}** — "
                f"**{issue['column']}**: {issue['description']}"
            )
    else:
        st.success("No significant data quality issues detected.")

    # Suggested metrics and dimensions
    st.subheader("Suggested Column Roles")
    suggested_metrics, suggested_dimensions = _suggest_roles(df, profile)

    mcol, dcol = st.columns(2)
    with mcol:
        st.markdown("**Suggested Metrics** (numeric, aggregatable)")
        for m in suggested_metrics:
            st.markdown(f"- `{m}`")
        if not suggested_metrics:
            st.info("No numeric columns detected as potential metrics.")

    with dcol:
        st.markdown("**Suggested Dimensions** (categorical, groupable)")
        for d in suggested_dimensions:
            st.markdown(f"- `{d}`")
        if not suggested_dimensions:
            st.info("No categorical columns detected as potential dimensions.")

    return profile, quality_issues


def _build_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Build a profile DataFrame with one row per column."""
    rows = []
    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        detected_type = _detect_column_type(series)

        samples = non_null.head(5).astype(str).tolist()
        sample_str = ", ".join(samples)
        if len(sample_str) > 80:
            sample_str = sample_str[:80] + "..."

        rows.append(
            {
                "column": col,
                "pandas_dtype": str(series.dtype),
                "detected_type": detected_type,
                "non_null_count": int(non_null.shape[0]),
                "null_count": int(series.isna().sum()),
                "null_pct": series.isna().mean() * 100,
                "unique_count": int(series.nunique()),
                "sample_values": sample_str,
            }
        )
    return pd.DataFrame(rows)


def _detect_column_type(series: pd.Series) -> str:
    """Heuristic detection of the semantic type of a column."""
    non_null = series.dropna()
    if non_null.empty:
        return "empty"

    # Already numeric
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    # Try to coerce to numeric
    coerced = pd.to_numeric(non_null, errors="coerce")
    if coerced.notna().mean() > 0.8:
        return "numeric"

    # Try datetime
    try:
        parsed = pd.to_datetime(non_null, errors="coerce")
        if parsed.notna().mean() > 0.8:
            return "datetime"
    except Exception:
        pass

    # Boolean-like
    unique_lower = set(non_null.astype(str).str.strip().str.lower().unique())
    if unique_lower.issubset({"true", "false", "yes", "no", "1", "0", "y", "n"}):
        return "boolean"

    return "categorical"


def _detect_quality_issues(df: pd.DataFrame, profile: pd.DataFrame) -> list:
    """Detect common data quality issues."""
    issues = []

    for _, row in profile.iterrows():
        col = row["column"]
        series = df[col]

        # High nulls
        if row["null_pct"] > 50:
            issues.append(
                {
                    "column": col,
                    "severity": "high",
                    "description": f"{row['null_pct']:.1f}% missing values.",
                }
            )
        elif row["null_pct"] > 10:
            issues.append(
                {
                    "column": col,
                    "severity": "medium",
                    "description": f"{row['null_pct']:.1f}% missing values.",
                }
            )

        # Single-value columns (zero variance)
        if row["unique_count"] == 1 and row["non_null_count"] > 0:
            issues.append(
                {
                    "column": col,
                    "severity": "low",
                    "description": "Column has only one unique value — may not be useful for analysis.",
                }
            )

        # Potential mixed types in string columns
        if row["detected_type"] == "categorical" and row["pandas_dtype"] == "object":
            non_null = series.dropna()
            coerced_numeric = pd.to_numeric(non_null, errors="coerce")
            numeric_frac = coerced_numeric.notna().mean()
            if 0.1 < numeric_frac < 0.8:
                issues.append(
                    {
                        "column": col,
                        "severity": "medium",
                        "description": (
                            f"Mixed types detected — {numeric_frac:.0%} of values "
                            "appear numeric while the rest are text."
                        ),
                    }
                )

        # Leading/trailing whitespace in strings
        if series.dtype == object:
            non_null = series.dropna().astype(str)
            whitespace_count = (non_null != non_null.str.strip()).sum()
            if whitespace_count > 0:
                issues.append(
                    {
                        "column": col,
                        "severity": "low",
                        "description": (
                            f"{whitespace_count:,} values have leading/trailing "
                            "whitespace."
                        ),
                    }
                )

        # Numeric outliers (IQR method)
        if row["detected_type"] == "numeric" and pd.api.types.is_numeric_dtype(series):
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                outlier_count = (
                    (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)
                ).sum()
                if outlier_count > 0:
                    pct = outlier_count / len(series) * 100
                    issues.append(
                        {
                            "column": col,
                            "severity": "low" if pct < 5 else "medium",
                            "description": (
                                f"{outlier_count:,} potential outliers "
                                f"({pct:.1f}% of values) detected via IQR method."
                            ),
                        }
                    )

    # Duplicate rows
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        pct = dup_count / len(df) * 100
        issues.append(
            {
                "column": "(all)",
                "severity": "medium" if pct > 5 else "low",
                "description": f"{dup_count:,} duplicate rows ({pct:.1f}%).",
            }
        )

    return issues


def _suggest_roles(df: pd.DataFrame, profile: pd.DataFrame):
    """Suggest which columns are metrics vs dimensions."""
    metrics = []
    dimensions = []

    for _, row in profile.iterrows():
        col = row["column"]
        if row["detected_type"] == "numeric":
            # High cardinality numeric → likely a metric
            if row["unique_count"] > 10 or row["unique_count"] / max(row["non_null_count"], 1) > 0.1:
                metrics.append(col)
            else:
                # Low cardinality numeric could be a dimension (e.g., rating 1-5)
                dimensions.append(col)
        elif row["detected_type"] in ("categorical", "boolean"):
            dimensions.append(col)
        elif row["detected_type"] == "datetime":
            dimensions.append(col)

    return metrics, dimensions
