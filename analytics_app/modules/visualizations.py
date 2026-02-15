"""Visualization engine supporting bar, line, pie, sankey, scatter, and table."""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


CHART_TYPES = [
    "Bar Chart",
    "Line Chart",
    "Pie Chart",
    "Scatter Plot",
    "Sankey Diagram",
    "Data Table",
    "Heatmap",
    "Histogram",
    "Box Plot",
    "Treemap",
]


def render_chart(
    df: pd.DataFrame,
    chart_type: str,
    metrics: list,
    dimensions: list,
    agg_func: str = "sum",
    color_dim: str = None,
    title: str = "",
):
    """Render the selected chart type with the given configuration."""
    if chart_type == "Bar Chart":
        return _bar_chart(df, metrics, dimensions, agg_func, color_dim, title)
    elif chart_type == "Line Chart":
        return _line_chart(df, metrics, dimensions, agg_func, color_dim, title)
    elif chart_type == "Pie Chart":
        return _pie_chart(df, metrics, dimensions, agg_func, title)
    elif chart_type == "Scatter Plot":
        return _scatter_plot(df, metrics, dimensions, color_dim, title)
    elif chart_type == "Sankey Diagram":
        return _sankey_diagram(df, metrics, dimensions, agg_func, title)
    elif chart_type == "Data Table":
        return _data_table(df, metrics, dimensions, agg_func)
    elif chart_type == "Heatmap":
        return _heatmap(df, metrics, dimensions, agg_func, title)
    elif chart_type == "Histogram":
        return _histogram(df, metrics, color_dim, title)
    elif chart_type == "Box Plot":
        return _box_plot(df, metrics, dimensions, title)
    elif chart_type == "Treemap":
        return _treemap(df, metrics, dimensions, agg_func, title)
    else:
        st.warning(f"Chart type '{chart_type}' is not supported.")
        return None


def _aggregate(df, metrics, dimensions, agg_func):
    """Helper to group by dimensions and aggregate metrics."""
    if not dimensions:
        agg_df = pd.DataFrame({m: [df[m].agg(agg_func)] for m in metrics})
        agg_df["_group"] = "All"
        return agg_df

    agg_dict = {m: agg_func for m in metrics}
    agg_df = df.groupby(dimensions, dropna=False).agg(agg_dict).reset_index()
    return agg_df


def _bar_chart(df, metrics, dimensions, agg_func, color_dim, title):
    if not metrics:
        st.info("Select at least one metric for a bar chart.")
        return None

    agg_df = _aggregate(df, metrics, dimensions, agg_func)

    if dimensions:
        x_col = dimensions[0]
    else:
        x_col = "_group"

    if len(metrics) == 1:
        fig = px.bar(
            agg_df,
            x=x_col,
            y=metrics[0],
            color=color_dim if color_dim and color_dim in agg_df.columns else None,
            title=title or f"{metrics[0]} by {x_col}",
            barmode="group",
        )
    else:
        # Multiple metrics — melt into long form
        id_vars = dimensions if dimensions else ["_group"]
        melted = agg_df.melt(id_vars=id_vars, value_vars=metrics, var_name="Metric", value_name="Value")
        fig = px.bar(
            melted,
            x=id_vars[0],
            y="Value",
            color="Metric",
            title=title or f"Metrics by {id_vars[0]}",
            barmode="group",
        )

    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    return agg_df


def _line_chart(df, metrics, dimensions, agg_func, color_dim, title):
    if not metrics:
        st.info("Select at least one metric for a line chart.")
        return None

    agg_df = _aggregate(df, metrics, dimensions, agg_func)

    if dimensions:
        x_col = dimensions[0]
    else:
        st.info("A line chart works best with at least one dimension (e.g., time).")
        x_col = agg_df.index.name or "_index"
        agg_df[x_col] = agg_df.index

    if len(metrics) == 1:
        fig = px.line(
            agg_df,
            x=x_col,
            y=metrics[0],
            color=color_dim if color_dim and color_dim in agg_df.columns else None,
            title=title or f"{metrics[0]} over {x_col}",
            markers=True,
        )
    else:
        id_vars = dimensions if dimensions else [x_col]
        melted = agg_df.melt(id_vars=id_vars, value_vars=metrics, var_name="Metric", value_name="Value")
        fig = px.line(
            melted,
            x=id_vars[0],
            y="Value",
            color="Metric",
            title=title or f"Metrics over {id_vars[0]}",
            markers=True,
        )

    st.plotly_chart(fig, use_container_width=True)
    return agg_df


def _pie_chart(df, metrics, dimensions, agg_func, title):
    if not metrics or not dimensions:
        st.info("Select one metric and one dimension for a pie chart.")
        return None

    agg_df = _aggregate(df, [metrics[0]], [dimensions[0]], agg_func)

    fig = px.pie(
        agg_df,
        names=dimensions[0],
        values=metrics[0],
        title=title or f"{metrics[0]} by {dimensions[0]}",
        hole=0.3,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)
    return agg_df


def _scatter_plot(df, metrics, dimensions, color_dim, title):
    if len(metrics) < 2:
        st.info("Select at least two metrics for a scatter plot (X and Y axes).")
        return None

    fig = px.scatter(
        df,
        x=metrics[0],
        y=metrics[1],
        color=color_dim if color_dim and color_dim in df.columns else None,
        title=title or f"{metrics[1]} vs {metrics[0]}",
        opacity=0.7,
    )
    st.plotly_chart(fig, use_container_width=True)
    return df[[m for m in metrics[:2]] + ([color_dim] if color_dim else [])]


def _sankey_diagram(df, metrics, dimensions, agg_func, title):
    if len(dimensions) < 2:
        st.info("Select at least two dimensions to create a Sankey diagram (source → target).")
        return None

    metric = metrics[0] if metrics else None
    source_col = dimensions[0]
    target_col = dimensions[1]

    if metric:
        flow_df = df.groupby([source_col, target_col])[metric].agg(agg_func).reset_index()
        flow_df.columns = ["source", "target", "value"]
    else:
        flow_df = df.groupby([source_col, target_col]).size().reset_index(name="value")

    # Build node lists
    all_nodes = list(pd.concat([flow_df["source"], flow_df["target"]]).unique())
    node_map = {name: i for i, name in enumerate(all_nodes)}

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=all_nodes,
                ),
                link=dict(
                    source=[node_map[s] for s in flow_df["source"]],
                    target=[node_map[t] for t in flow_df["target"]],
                    value=flow_df["value"].tolist(),
                ),
            )
        ]
    )
    fig.update_layout(
        title_text=title or f"Flow: {source_col} → {target_col}",
        font_size=12,
    )
    st.plotly_chart(fig, use_container_width=True)
    return flow_df


def _data_table(df, metrics, dimensions, agg_func):
    selected_cols = dimensions + metrics
    if not selected_cols:
        st.info("Select at least one column to display.")
        return None

    agg_df = _aggregate(df, metrics, dimensions, agg_func) if metrics and dimensions else df[selected_cols]
    st.dataframe(agg_df, use_container_width=True, hide_index=True)
    return agg_df


def _heatmap(df, metrics, dimensions, agg_func, title):
    if len(dimensions) < 2 or not metrics:
        st.info("Select two dimensions and one metric for a heatmap.")
        return None

    pivot_df = df.pivot_table(
        values=metrics[0],
        index=dimensions[0],
        columns=dimensions[1],
        aggfunc=agg_func,
        fill_value=0,
    )

    fig = px.imshow(
        pivot_df,
        title=title or f"{metrics[0]} by {dimensions[0]} × {dimensions[1]}",
        aspect="auto",
        color_continuous_scale="Viridis",
    )
    st.plotly_chart(fig, use_container_width=True)
    return pivot_df


def _histogram(df, metrics, color_dim, title):
    if not metrics:
        st.info("Select at least one metric for a histogram.")
        return None

    fig = px.histogram(
        df,
        x=metrics[0],
        color=color_dim if color_dim and color_dim in df.columns else None,
        title=title or f"Distribution of {metrics[0]}",
        nbins=30,
        marginal="box",
    )
    st.plotly_chart(fig, use_container_width=True)
    return None


def _box_plot(df, metrics, dimensions, title):
    if not metrics:
        st.info("Select at least one metric for a box plot.")
        return None

    x_col = dimensions[0] if dimensions else None
    fig = px.box(
        df,
        x=x_col,
        y=metrics[0],
        title=title or f"Distribution of {metrics[0]}" + (f" by {x_col}" if x_col else ""),
        points="outliers",
    )
    st.plotly_chart(fig, use_container_width=True)
    return None


def _treemap(df, metrics, dimensions, agg_func, title):
    if not dimensions or not metrics:
        st.info("Select at least one dimension and one metric for a treemap.")
        return None

    agg_df = _aggregate(df, [metrics[0]], dimensions, agg_func)
    # Add a root parent for the treemap
    path_cols = dimensions

    fig = px.treemap(
        agg_df,
        path=path_cols,
        values=metrics[0],
        title=title or f"{metrics[0]} by {', '.join(dimensions)}",
    )
    st.plotly_chart(fig, use_container_width=True)
    return agg_df
