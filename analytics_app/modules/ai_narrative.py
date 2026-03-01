"""AI-powered narrative generation using the Claude API."""

import os

import anthropic
import pandas as pd
import numpy as np
import streamlit as st


MODEL_OPTIONS = [
    "claude-sonnet-4-20250514",
    "claude-haiku-4-5-20251001",
    "claude-opus-4-20250514",
]


def _get_client() -> anthropic.Anthropic | None:
    """Return an Anthropic client using the configured API key, or None."""
    api_key = st.session_state.get("anthropic_api_key") or os.environ.get(
        "ANTHROPIC_API_KEY"
    )
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def render_ai_config_sidebar():
    """Render AI configuration controls in the sidebar."""
    with st.sidebar:
        st.markdown("---")
        st.subheader("AI Insights")

        env_key = os.environ.get("ANTHROPIC_API_KEY", "")
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            value=st.session_state.get("anthropic_api_key", env_key),
            key="sidebar_api_key",
            help="Required for AI-generated narratives. Set here or via ANTHROPIC_API_KEY env var.",
        )
        st.session_state["anthropic_api_key"] = api_key

        # Ensure the widget key holds a valid value before the selectbox renders;
        # Streamlit validates the key internally and raises ValueError otherwise.
        if st.session_state.get("sidebar_model") not in MODEL_OPTIONS:
            st.session_state["sidebar_model"] = MODEL_OPTIONS[0]

        model = st.selectbox(
            "Model",
            options=MODEL_OPTIONS,
            key="sidebar_model",
        )
        st.session_state["ai_model"] = model

        if api_key:
            st.caption("API key configured.")
        else:
            st.caption("Enter an API key to enable AI insights.")


def _build_data_context(
    df: pd.DataFrame,
    panels: list,
    agg_results: list[pd.DataFrame],
) -> str:
    """Build a concise data context string to send to the model."""
    lines = []

    # Dataset overview
    n_rows, n_cols = df.shape
    lines.append(f"Dataset: {n_rows:,} rows, {n_cols} columns.")
    lines.append(f"Columns: {', '.join(df.columns)}")
    lines.append("")

    # Numeric summary
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        desc = df[numeric_cols].describe().round(2)
        lines.append("Numeric summary:")
        lines.append(desc.to_string())
        lines.append("")

    # Per-panel aggregated data
    for i, (panel, agg_df) in enumerate(zip(panels, agg_results)):
        lines.append(f"--- Panel {i + 1}: {panel.get('chart_type', 'Chart')} ---")
        lines.append(f"Metrics: {panel.get('metrics', [])}")
        lines.append(f"Dimensions (group by): {panel.get('dimensions', [])}")
        lines.append(f"Aggregation: {panel.get('agg_func', 'sum')}")

        if agg_df is not None and not agg_df.empty:
            # Truncate large tables to keep prompt concise
            display_df = agg_df.head(50)
            lines.append(f"Aggregated data ({len(agg_df)} rows, showing top 50):")
            lines.append(display_df.to_string(index=False))
        else:
            lines.append("(No aggregated data available for this panel.)")
        lines.append("")

    # Correlation matrix for numeric columns in the dataset
    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr().round(3)
        lines.append("Correlation matrix:")
        lines.append(corr.to_string())

    return "\n".join(lines)


def generate_ai_narrative(
    df: pd.DataFrame,
    panels: list,
    agg_results: list[pd.DataFrame],
) -> str | None:
    """Call the Claude API and return an AI-generated narrative."""
    client = _get_client()
    if client is None:
        return None

    model = st.session_state.get("ai_model", MODEL_OPTIONS[0])
    data_context = _build_data_context(df, panels, agg_results)

    system_prompt = (
        "You are a senior data analyst. The user has uploaded a CSV dataset "
        "and built a dashboard with one or more chart panels. Your job is to "
        "provide a clear, insightful narrative covering:\n"
        "1. Key trends — what direction are the metrics moving and why?\n"
        "2. Drivers — which dimensions or categories are driving the numbers?\n"
        "3. Correlations — which metrics move together and what might that mean?\n"
        "4. Anomalies — any outliers, sudden changes, or unexpected patterns.\n"
        "5. Actionable takeaways — brief recommendations based on the data.\n\n"
        "Keep your response concise (under 400 words). Use markdown formatting. "
        "Reference specific numbers and categories from the data."
    )

    user_message = (
        "Here is the data context for the dashboard:\n\n"
        f"{data_context}\n\n"
        "Please provide a narrative analysis of this data."
    )

    try:
        with client.messages.stream(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            final = stream.get_final_message()

        return final.content[0].text

    except anthropic.AuthenticationError:
        return "**Error:** Invalid API key. Please check your Anthropic API key in the sidebar."
    except anthropic.RateLimitError:
        return "**Error:** Rate limited. Please wait a moment and try again."
    except anthropic.BadRequestError as e:
        return f"**Error:** Bad request ({e.status_code}): {e.message}"
    except anthropic.APIStatusError as e:
        return f"**Error:** API error ({e.status_code}): {e.message}"
    except anthropic.APIConnectionError:
        return "**Error:** Could not connect to the Anthropic API. Check your network."


def _build_panel_context(panel: dict, agg_df: pd.DataFrame) -> str:
    """Build a concise data context string for a single panel."""
    lines = []
    chart_type = panel.get("chart_type", "Chart")
    metrics = panel.get("metrics", [])
    dimensions = panel.get("dimensions", [])
    agg_func = panel.get("agg_func", "sum")
    title = panel.get("title", "")

    lines.append(f"Chart type: {chart_type}")
    if title:
        lines.append(f"Title: {title}")
    lines.append(f"Metrics: {', '.join(metrics) if metrics else 'None'}")
    lines.append(f"Dimensions (group by): {', '.join(dimensions) if dimensions else 'None'}")
    lines.append(f"Aggregation: {agg_func}")
    lines.append("")

    if agg_df is not None and not agg_df.empty:
        display_df = agg_df.head(50)
        lines.append(f"Aggregated data ({len(agg_df)} rows, showing up to 50):")
        lines.append(display_df.to_string(index=False))
    else:
        lines.append("(No aggregated data available.)")

    return "\n".join(lines)


def generate_panel_insight(panel: dict, agg_df: pd.DataFrame) -> str | None:
    """Call the Claude API and return a short AI insight for a single panel."""
    client = _get_client()
    if client is None:
        return None

    model = st.session_state.get("ai_model", MODEL_OPTIONS[0])
    panel_context = _build_panel_context(panel, agg_df)

    system_prompt = (
        "You are a senior data analyst. The user has a chart panel from their "
        "dashboard. Provide a brief, insightful analysis of the data shown. "
        "Highlight the most important pattern, trend, or outlier. Reference "
        "specific numbers and categories. Be concise — maximum 200 words. "
        "Use plain text, no markdown headers."
    )

    user_message = (
        "Here is the panel data:\n\n"
        f"{panel_context}\n\n"
        "Provide a brief analysis (max 200 words)."
    )

    try:
        with client.messages.stream(
            model=model,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            final = stream.get_final_message()

        return final.content[0].text

    except anthropic.AuthenticationError:
        return "**Error:** Invalid API key."
    except anthropic.RateLimitError:
        return "**Error:** Rate limited. Please wait and try again."
    except anthropic.APIStatusError as e:
        return f"**Error:** API error ({e.status_code}): {e.message}"
    except anthropic.APIConnectionError:
        return "**Error:** Could not connect to the Anthropic API."


def render_panel_insight(panel_idx: int, panel: dict, agg_df: pd.DataFrame):
    """Render a per-panel AI insight below the chart."""
    has_key = bool(
        st.session_state.get("anthropic_api_key")
        or os.environ.get("ANTHROPIC_API_KEY")
    )
    if not has_key:
        return

    cache_key = f"panel_insight_{panel_idx}"

    if st.button("AI Analysis", key=f"gen_panel_insight_{panel_idx}",
                 use_container_width=True):
        with st.spinner("Analysing..."):
            insight = generate_panel_insight(panel, agg_df)
            if insight:
                st.session_state[cache_key] = insight

    cached = st.session_state.get(cache_key)
    if cached:
        st.caption(cached)


def render_ai_narrative(
    df: pd.DataFrame,
    panels: list,
    agg_results: list[pd.DataFrame],
):
    """Render the AI narrative section in the dashboard."""
    st.subheader("AI-Powered Insights")

    has_key = bool(
        st.session_state.get("anthropic_api_key")
        or os.environ.get("ANTHROPIC_API_KEY")
    )

    if not has_key:
        st.info(
            "Enter your Anthropic API key in the sidebar to enable "
            "AI-generated data narratives."
        )
        return

    if st.button("Generate AI Narrative", type="primary", key="gen_ai_narrative"):
        with st.spinner("Analysing your data with Claude..."):
            narrative = generate_ai_narrative(df, panels, agg_results)
            if narrative:
                st.session_state["ai_narrative"] = narrative

    # Display cached narrative
    cached = st.session_state.get("ai_narrative")
    if cached:
        st.markdown(cached)
