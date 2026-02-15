"""CSV upload and data ingestion module."""

import pandas as pd
import streamlit as st
import io


def render_upload_step():
    """Render the CSV upload interface and return loaded DataFrame."""
    st.header("1. Upload Your Data")
    st.markdown(
        "Upload any CSV file to begin analysis. The app will automatically "
        "detect columns, data types, and prepare your data for profiling."
    )

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Upload a flat CSV file containing your metrics and dimensions.",
    )

    if uploaded_file is not None:
        try:
            # Detect encoding and separator
            sep, encoding = _detect_csv_params(uploaded_file)
            uploaded_file.seek(0)

            df = pd.read_csv(
                uploaded_file,
                sep=sep,
                encoding=encoding,
                on_bad_lines="warn",
            )

            if df.empty:
                st.error("The uploaded file is empty.")
                return None

            st.success(
                f"Loaded **{len(df):,}** rows and **{len(df.columns)}** columns."
            )

            with st.expander("Preview raw data", expanded=True):
                st.dataframe(df.head(50), use_container_width=True)

            return df

        except Exception as e:
            st.error(f"Failed to read the CSV file: {e}")
            return None

    return None


def _detect_csv_params(uploaded_file):
    """Try to detect the separator and encoding of the uploaded CSV."""
    sample = uploaded_file.read(8192)

    # Try UTF-8 first, fall back to latin-1
    for encoding in ["utf-8", "latin-1"]:
        try:
            text = sample.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        encoding = "utf-8"
        text = sample.decode(encoding, errors="replace")

    # Detect separator by counting occurrences in first few lines
    lines = text.split("\n")[:5]
    candidates = {",": 0, ";": 0, "\t": 0, "|": 0}
    for line in lines:
        for sep in candidates:
            candidates[sep] += line.count(sep)

    best_sep = max(candidates, key=candidates.get)
    if candidates[best_sep] == 0:
        best_sep = ","

    return best_sep, encoding
