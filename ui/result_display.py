"""
ui/result_display.py
Renders a complete query result: table, chart, SQL explanation, and AI insights.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Optional


def render_result(
    df: pd.DataFrame,
    sql: str,
    explanation: str,
    insight: str,
    figure: Optional[go.Figure],
):
    """
    Display a complete query result block inside the chat.
    Layout:
      1. SQL used (collapsed)
      2. Chart (if available) | Table
      3. Explanation
      4. AI Insight
    """

    # ── 1. SQL Expander ───────────────────────────────────────────────────────
    with st.expander("🔍 View Generated SQL", expanded=False):
        st.code(sql, language="sql")

    # ── 2. Chart or Table ─────────────────────────────────────────────────────
    if figure is not None:
        st.plotly_chart(figure, use_container_width=True)
        # Show the underlying data in a collapsed expander
        with st.expander(f"📄 View Raw Data ({len(df):,} rows)", expanded=False):
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        # No chart — show plain table
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(df):,} rows returned")

    # ── 3. SQL Explanation ────────────────────────────────────────────────────
    st.markdown(
        f"<div style='"
        f"background:#EEF2FF; border-left:3px solid #6366F1; "
        f"padding:10px 14px; border-radius:6px; margin:8px 0; font-size:0.9rem;'>"
        f"📖 <b>What this query does:</b> {explanation}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── 4. AI Insight ─────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='"
        f"background:#F0FDF4; border-left:3px solid #10B981; "
        f"padding:10px 14px; border-radius:6px; margin:8px 0; font-size:0.9rem;'>"
        f"💡 <b>AI Insight:</b> {insight}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_error(message: str):
    """Display a user-friendly error message."""
    st.markdown(
        f"<div style='"
        f"background:#FEF2F2; border-left:3px solid #EF4444; "
        f"padding:10px 14px; border-radius:6px; margin:8px 0; font-size:0.9rem;'>"
        f"❌ <b>Error:</b> {message}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_thinking():
    """Show a spinner placeholder while the LLM is working."""
    return st.status("🤔 Analyzing your question...", expanded=True)
