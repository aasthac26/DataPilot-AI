"""
Feature 2: Auto Chart Narrator
After rendering a chart, the LLM describes what it visually shows —
peaks, dips, dominant categories, trends, anomalies.

This makes DataPilot feel like an analyst presenting findings at a meeting,
not just a tool that draws graphs.

Different from AI Insights (Module 7) which focuses on business meaning.
The narrator focuses on VISUAL patterns: what you see in the chart.
"""

import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, Optional
from utils.llm_client import chat
from utils.chart_utils import detect_chart_type


_NARRATOR_SYSTEM_PROMPT = """You are a data analyst narrating a chart to a non-technical audience.

Describe what the chart visually shows in 2-3 sentences. Focus on:
- The most prominent visual feature (the tallest bar, the steepest line, the largest pie slice)
- Any obvious pattern, trend, or anomaly visible in the chart
- Specific values or labels that stand out

Rules:
- Use plain English — no jargon.
- Be specific: mention actual category names and numbers from the data.
- Keep it under 60 words.
- Do NOT give business recommendations — just describe what you see visually.
- Do NOT start with "The chart shows" — vary your opening.
"""


def narrate_chart(
    df: pd.DataFrame,
    chart_type: str,
    x_col: str,
    y_col: str,
    user_question: str,
) -> Optional[str]:
    """
    Generate a plain-English visual narration of a chart.

    Args:
        df:            The data the chart is built from.
        chart_type:    "bar", "line", "pie", "scatter"
        x_col:         The x-axis / label column name.
        y_col:         The y-axis / value column name.
        user_question: Original user question for context.

    Returns:
        A 2-3 sentence narration string, or None if chart is a table.
    """
    if chart_type == "table" or not x_col or not y_col:
        return None

    if df is None or df.empty:
        return None

    data_summary = _build_chart_summary(df, chart_type, x_col, y_col)

    user_message = (
        f"Chart type: {chart_type}\n"
        f"X-axis (categories/labels): {x_col}\n"
        f"Y-axis (values): {y_col}\n"
        f"User's question: \"{user_question}\"\n\n"
        f"Chart data:\n{data_summary}"
    )

    try:
        narration = chat(
            system_prompt=_NARRATOR_SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.3,
            max_tokens=120,
        )
        return narration.strip()
    except Exception:
        return None


def narrate_chart_from_df(
    df: pd.DataFrame,
    user_question: str,
) -> Optional[str]:
    """
    Convenience wrapper: auto-detect chart type from DataFrame
    then generate narration.
    """
    if df is None or df.empty:
        return None

    chart_type, x_col, y_col = detect_chart_type(df)

    if chart_type == "table":
        return None

    return narrate_chart(df, chart_type, x_col, y_col, user_question)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_chart_summary(
    df: pd.DataFrame,
    chart_type: str,
    x_col: str,
    y_col: str,
    max_rows: int = 15,
) -> str:
    """
    Build a compact data summary for the LLM, tailored to the chart type.
    """
    lines = []

    if chart_type in ("bar", "pie") and x_col in df.columns and y_col in df.columns:
        # Sort by value descending so LLM sees the most important items first
        try:
            sorted_df = df[[x_col, y_col]].sort_values(y_col, ascending=False)
            lines.append(f"Top values ({x_col} → {y_col}):")
            lines.append(sorted_df.head(max_rows).to_string(index=False))

            # Add total for context
            total = df[y_col].sum()
            if total > 0:
                lines.append(f"Total: {total:,.2f}")
                # Add % share for top item
                top_val = sorted_df.iloc[0][y_col]
                lines.append(f"Top item share: {top_val/total*100:.1f}%")
        except Exception:
            lines.append(df.head(max_rows).to_string(index=False))

    elif chart_type == "line" and x_col in df.columns and y_col in df.columns:
        try:
            lines.append(f"Trend data ({x_col} → {y_col}):")
            lines.append(df[[x_col, y_col]].head(max_rows).to_string(index=False))

            col_data = df[y_col].dropna()
            if len(col_data) > 1:
                lines.append(f"Min: {col_data.min():,.2f}, Max: {col_data.max():,.2f}")
                # Direction of trend
                first_half = col_data.iloc[:len(col_data)//2].mean()
                second_half = col_data.iloc[len(col_data)//2:].mean()
                direction = "upward" if second_half > first_half else "downward"
                lines.append(f"Overall trend: {direction}")
        except Exception:
            lines.append(df.head(max_rows).to_string(index=False))

    elif chart_type == "scatter" and x_col in df.columns and y_col in df.columns:
        try:
            lines.append(f"Scatter data ({x_col} vs {y_col}):")
            lines.append(df[[x_col, y_col]].head(max_rows).to_string(index=False))
            # Correlation hint
            try:
                corr = df[[x_col, y_col]].corr().iloc[0, 1]
                direction = "positive" if corr > 0.1 else ("negative" if corr < -0.1 else "no clear")
                lines.append(f"Correlation: {direction} (r={corr:.2f})")
            except Exception:
                pass
        except Exception:
            lines.append(df.head(max_rows).to_string(index=False))

    else:
        lines.append(df.head(max_rows).to_string(index=False))

    return "\n".join(lines)
