"""
ui/health_report.py
Renders the Data Health Analyzer report as a rich Streamlit dashboard.
This is the resume-differentiating feature.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from core.health_analyzer import HealthReport


def render_health_report(report: HealthReport):
    """Render the full data health report as an expandable Streamlit section."""

    st.subheader("🩺 Data Health Report")

    # ── Score gauge + top metrics ─────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        color = _grade_color(report.grade)
        st.markdown(
            f"<div style='text-align:center'>"
            f"<div style='font-size:2.5rem; font-weight:800; color:{color}'>"
            f"{report.score}<span style='font-size:1rem'>/100</span></div>"
            f"<div style='font-size:0.85rem; color:#64748B'>Quality Score</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.metric("Duplicate Rows", f"{report.duplicate_rows:,}", delta=f"{report.duplicate_pct}%",
                  delta_color="inverse")
    with col3:
        total_nulls = sum(c.null_count for c in report.columns)
        st.metric("Missing Values", f"{total_nulls:,}")
    with col4:
        total_outliers = sum(c.outlier_count for c in report.columns)
        st.metric("Outliers Detected", f"{total_outliers:,}")

    st.divider()

    # ── Issues and Suggestions ────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**⚠️ Issues Found**")
        for issue in report.issues:
            icon = "✅" if "No significant" in issue else "⚠️"
            st.markdown(f"{icon} {issue}")

    with col_right:
        st.markdown("**💡 Suggestions**")
        for tip in report.suggestions:
            st.markdown(f"→ {tip}")

    st.divider()

    # ── Per-column health table ───────────────────────────────────────────────
    with st.expander("📊 Column-Level Health Details", expanded=False):
        rows = []
        for c in report.columns:
            health_icon = "🟢" if c.null_pct < 5 and c.outlier_count == 0 else (
                "🟡" if c.null_pct < 20 else "🔴"
            )
            rows.append({
                "": health_icon,
                "Column": c.name,
                "Type": c.dtype,
                "Missing": f"{c.null_count} ({c.null_pct}%)",
                "Unique": c.unique_count,
                "Outliers": c.outlier_count if c.outlier_count > 0 else "—",
                "Min / Max": f"{c.min_val} / {c.max_val}" if c.min_val is not None else "—",
                "Mean": c.mean_val if c.mean_val is not None else "—",
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    # ── Missing value bar chart ───────────────────────────────────────────────
    missing_cols = [c for c in report.columns if c.null_count > 0]
    if missing_cols:
        with st.expander("📉 Missing Values by Column", expanded=False):
            names = [c.name for c in missing_cols]
            pcts = [c.null_pct for c in missing_cols]
            fig = go.Figure(go.Bar(
                x=names,
                y=pcts,
                marker_color=["#EF4444" if p > 20 else "#F59E0B" if p > 5 else "#6366F1" for p in pcts],
                text=[f"{p}%" for p in pcts],
                textposition="outside",
            ))
            fig.update_layout(
                title="Missing Value % per Column",
                yaxis_title="% Missing",
                xaxis_title="Column",
                plot_bgcolor="#F8FAFC",
                paper_bgcolor="#FFFFFF",
                margin=dict(t=40, l=10, r=10, b=10),
                font_family="Inter, system-ui, sans-serif",
            )
            st.plotly_chart(fig, use_container_width=True)


def _grade_color(grade: str) -> str:
    return {
        "A": "#10B981",
        "B": "#6366F1",
        "C": "#F59E0B",
        "D": "#EF4444",
        "F": "#DC2626",
    }.get(grade, "#64748B")
