"""
Module 6: Visualization Engine
Automatically generates interactive Plotly charts from query result DataFrames.
Chart type is detected automatically using chart_utils heuristics.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional

from utils.chart_utils import detect_chart_type, ChartType


# ── Color palette for DataPilot AI ────────────────────────────────────────────
PALETTE = [
    "#6366F1",  # indigo
    "#06B6D4",  # cyan
    "#10B981",  # emerald
    "#F59E0B",  # amber
    "#EF4444",  # red
    "#8B5CF6",  # violet
    "#EC4899",  # pink
    "#14B8A6",  # teal
]


def render_chart(
    df: pd.DataFrame,
    title: str = "",
    force_type: Optional[ChartType] = None,
) -> Optional[go.Figure]:
    """
    Generate a Plotly figure from a DataFrame.

    Args:
        df:         Query result DataFrame.
        title:      Chart title (usually the user's question).
        force_type: Override auto-detection with a specific chart type.

    Returns:
        A Plotly Figure, or None if the data can't be visualized.
    """
    if df is None or df.empty:
        return None

    chart_type, x_col, y_col = detect_chart_type(df)

    if force_type:
        chart_type = force_type

    if chart_type == "table":
        return None   # Caller will render a plain dataframe table instead

    try:
        fig = _build_figure(df, chart_type, x_col, y_col, title)
        fig = _apply_theme(fig)
        return fig
    except Exception:
        return None   # Graceful fallback to table


def _build_figure(
    df: pd.DataFrame,
    chart_type: ChartType,
    x_col: str,
    y_col: str,
    title: str,
) -> go.Figure:
    """Dispatch to the right Plotly chart builder."""

    if chart_type == "bar":
        fig = px.bar(
            df,
            x=x_col,
            y=y_col,
            title=title,
            color_discrete_sequence=PALETTE,
            text_auto=True,
        )
        fig.update_traces(textposition="outside")

    elif chart_type == "line":
        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            title=title,
            color_discrete_sequence=PALETTE,
            markers=True,
        )

    elif chart_type == "pie":
        fig = px.pie(
            df,
            names=x_col,
            values=y_col,
            title=title,
            color_discrete_sequence=PALETTE,
            hole=0.35,          # Donut style
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")

    elif chart_type == "scatter":
        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            title=title,
            color_discrete_sequence=PALETTE,
            trendline="ols",    # Add trend line automatically
        )

    else:
        raise ValueError(f"Unknown chart type: {chart_type}")

    return fig


def _apply_theme(fig: go.Figure) -> go.Figure:
    """Apply a clean, professional dark-adjacent theme to all charts."""
    fig.update_layout(
        font_family="Inter, system-ui, sans-serif",
        font_color="#1E293B",
        title_font_size=15,
        title_font_color="#0F172A",
        plot_bgcolor="#F8FAFC",
        paper_bgcolor="#FFFFFF",
        margin=dict(t=50, l=10, r=10, b=10),
        legend=dict(
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#E2E8F0",
            borderwidth=1,
        ),
        xaxis=dict(
            gridcolor="#E2E8F0",
            linecolor="#CBD5E1",
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            gridcolor="#E2E8F0",
            linecolor="#CBD5E1",
            tickfont=dict(size=11),
        ),
    )
    return fig
