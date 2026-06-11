"""
ui/result_display.py
Renders a complete query result:
  1. SQL (collapsed)
  2. Chart (if available) + Chart Narration  ← Feature 2
  3. Table
  4. SQL Explanation
  5. AI Insight
  6. Follow-up Question Suggestions          ← Feature 1
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Optional, List


def render_result(
    df: pd.DataFrame,
    sql: str,
    explanation: str,
    insight: str,
    figure: Optional[go.Figure],
    narration: Optional[str] = None,        # Feature 2: chart narration
    followup_questions: Optional[List[str]] = None,  # Feature 1: follow-up suggestions
):
    """
    Display a complete query result block inside the chat.
    """

    # ── 1. SQL Expander ───────────────────────────────────────────────────────
    with st.expander("🔍 View Generated SQL", expanded=False):
        st.code(sql, language="sql")

    # ── 2. Chart + Narration ──────────────────────────────────────────────────
    if figure is not None:
        st.plotly_chart(figure, use_container_width=True)

        # Feature 2: Chart narration directly below chart
        if narration:
            st.markdown(
                f"<div style='"
                f"background:rgba(148,163,184,0.15); border-left:3px solid #94A3B8; "
                f"padding:8px 14px; border-radius:6px; margin:4px 0 8px 0; "
                f"font-size:0.88rem; color:inherit; font-style:italic;'>"
                f"📊 {narration}"
                f"</div>",
                unsafe_allow_html=True,
            )

        with st.expander(f"📄 View Raw Data ({len(df):,} rows)", expanded=False):
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(df):,} rows returned")

    # ── 3. SQL Explanation ────────────────────────────────────────────────────
    st.markdown(
        f"<div style='"
        f"background:rgba(99,102,241,0.15); border-left:3px solid #6366F1; "
        f"padding:10px 14px; border-radius:6px; margin:8px 0; font-size:0.9rem; color:inherit;'>"
        f"📖 <b>What this query does:</b> {explanation}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── 4. AI Insight ─────────────────────────────────────────────────────────
    st.markdown(
        f"<div style='"
        f"background:rgba(16,185,129,0.15); border-left:3px solid #10B981; "
        f"padding:10px 14px; border-radius:6px; margin:8px 0; font-size:0.9rem; color:inherit;'>"
        f"💡 <b>AI Insight:</b> {insight}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── 5. Follow-up Questions ────────────────────────────────────────────────
    # Feature 1: Smart follow-up question suggester
    if followup_questions:
        st.markdown(
            "<div style='margin-top:12px; margin-bottom:4px; "
            "font-size:0.82rem; color:#64748B; font-weight:600;'>"
            "🔮 You might also want to ask:</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(len(followup_questions))
        for i, (col, q) in enumerate(zip(cols, followup_questions)):
            with col:
                if st.button(
                    q,
                    key=f"followup_{hash(q)}_{i}",
                    use_container_width=True,
                    help="Click to ask this question",
                ):
                    st.session_state["prefill_question"] = q
                    st.rerun()


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
