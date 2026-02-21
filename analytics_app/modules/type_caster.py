"""Data type casting with user confirmation."""

import pandas as pd
import numpy as np
import streamlit as st


# Supported target types for casting
CAST_OPTIONS = [
    "text",
    "integer",
    "float",
    "datetime",
    "boolean",
    "category",
    "keep_original",
]


def render_casting_step(df: pd.DataFrame, profile: pd.DataFrame):
    """Render the type casting interface and return the cast DataFrame."""
    st.header("3. Confirm Data Types")
    st.markdown(
        "Review the detected types below and override any that should be different. "
        "The app will attempt to cast columns to your chosen types."
    )

    cast_config = {}
    columns_per_row = 3

    # Build groups of columns for a compact layout
    cols_list = profile["column"].tolist()
    for i in range(0, len(cols_list), columns_per_row):
        chunk = cols_list[i : i + columns_per_row]
        ui_cols = st.columns(len(chunk))
        for ui_col, col_name in zip(ui_cols, chunk):
            row = profile[profile["column"] == col_name].iloc[0]
            detected = row["detected_type"]
            default_idx = _map_detected_to_option(detected)
            with ui_col:
                chosen = st.selectbox(
                    f"`{col_name}`",
                    options=CAST_OPTIONS,
                    index=default_idx,
                    key=f"cast_{col_name}",
                    help=f"Detected: {detected} | Pandas dtype: {row['pandas_dtype']}",
                )
                cast_config[col_name] = chosen

    st.divider()

    if st.button("Apply Type Casting", type="primary"):
        cast_df, cast_report = _apply_casting(df.copy(), cast_config)
        st.session_state["cast_df"] = cast_df
        st.session_state["cast_report"] = cast_report
        st.session_state["cast_config"] = cast_config

    if st.session_state.get("cast_df") is not None and st.session_state.get("cast_report") is not None:
        report = st.session_state["cast_report"]
        cast_df = st.session_state["cast_df"]

        # Show casting results
        successes = [r for r in report if r["status"] == "success"]
        warnings = [r for r in report if r["status"] == "warning"]
        errors = [r for r in report if r["status"] == "error"]

        if successes:
            st.success(f"{len(successes)} column(s) cast successfully.")
        if warnings:
            for w in warnings:
                st.warning(f"**{w['column']}**: {w['message']}")
        if errors:
            for e in errors:
                st.error(f"**{e['column']}**: {e['message']}")

        with st.expander("Preview cast data", expanded=True):
            # Show dtypes alongside preview
            dtype_df = pd.DataFrame(
                {
                    "column": cast_df.columns,
                    "new_dtype": [str(cast_df[c].dtype) for c in cast_df.columns],
                }
            )
            st.dataframe(dtype_df, use_container_width=True, hide_index=True)
            st.dataframe(cast_df.head(50), use_container_width=True)

        return cast_df

    return None


def _map_detected_to_option(detected_type: str) -> int:
    """Map a detected type string to the index in CAST_OPTIONS."""
    mapping = {
        "numeric": 2,       # float
        "categorical": 0,   # text
        "datetime": 3,
        "boolean": 4,
        "empty": 6,         # keep_original
    }
    return mapping.get(detected_type, 6)


def _apply_casting(df: pd.DataFrame, cast_config: dict):
    """Apply the user-selected type casts and return (df, report)."""
    report = []

    for col, target in cast_config.items():
        if col not in df.columns:
            continue

        if target == "keep_original":
            report.append(
                {"column": col, "status": "success", "message": "Kept original type."}
            )
            continue

        try:
            if target == "text":
                df[col] = df[col].astype(str).replace("nan", pd.NA)
                report.append(
                    {"column": col, "status": "success", "message": "Cast to text."}
                )

            elif target == "integer":
                coerced = pd.to_numeric(df[col], errors="coerce")
                failed = coerced.isna().sum() - df[col].isna().sum()
                df[col] = coerced
                if failed > 0:
                    report.append(
                        {
                            "column": col,
                            "status": "warning",
                            "message": f"Cast to numeric; {failed} value(s) could not be converted and were set to NaN.",
                        }
                    )
                else:
                    # Use nullable integer if no NaNs
                    if coerced.isna().sum() == 0:
                        df[col] = coerced.astype(int)
                    report.append(
                        {
                            "column": col,
                            "status": "success",
                            "message": "Cast to integer.",
                        }
                    )

            elif target == "float":
                coerced = pd.to_numeric(df[col], errors="coerce")
                failed = coerced.isna().sum() - df[col].isna().sum()
                df[col] = coerced
                if failed > 0:
                    report.append(
                        {
                            "column": col,
                            "status": "warning",
                            "message": f"Cast to float; {failed} value(s) could not be converted.",
                        }
                    )
                else:
                    report.append(
                        {
                            "column": col,
                            "status": "success",
                            "message": "Cast to float.",
                        }
                    )

            elif target == "datetime":
                coerced = pd.to_datetime(df[col], errors="coerce")
                failed = coerced.isna().sum() - df[col].isna().sum()
                df[col] = coerced
                if failed > 0:
                    report.append(
                        {
                            "column": col,
                            "status": "warning",
                            "message": f"Cast to datetime; {failed} value(s) could not be parsed.",
                        }
                    )
                else:
                    report.append(
                        {
                            "column": col,
                            "status": "success",
                            "message": "Cast to datetime.",
                        }
                    )

            elif target == "boolean":
                bool_map = {
                    "true": True, "false": False,
                    "yes": True, "no": False,
                    "1": True, "0": False,
                    "y": True, "n": False,
                }
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .map(bool_map)
                )
                report.append(
                    {
                        "column": col,
                        "status": "success",
                        "message": "Cast to boolean.",
                    }
                )

            elif target == "category":
                df[col] = df[col].astype("category")
                report.append(
                    {
                        "column": col,
                        "status": "success",
                        "message": "Cast to category.",
                    }
                )

        except Exception as e:
            report.append(
                {
                    "column": col,
                    "status": "error",
                    "message": f"Casting failed: {e}",
                }
            )

    return df, report
