"""
utils/chart_utils.py
Heuristics to decide what chart type best fits a query result DataFrame.
"""

import pandas as pd
from typing import Tuple


ChartType = str   # "bar" | "line" | "pie" | "scatter" | "table"


def detect_chart_type(df: pd.DataFrame) -> Tuple[ChartType, str, str]:
    """
    Analyze a DataFrame and return the best chart type plus
    which columns to use as x-axis and y-axis.

    Returns:
        (chart_type, x_col, y_col)
        chart_type: one of "bar", "line", "pie", "scatter", "table"
        x_col:      column name for the x-axis (or label axis)
        y_col:      column name for the y-axis (or value axis)
    """
    if df is None or df.empty or len(df.columns) < 2:
        return "table", "", ""

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(exclude="number").columns.tolist()
    date_cols = [c for c in df.columns if _is_datetime_col(df[c])]

    # ── Rule 1: Time series → line chart ─────────────────────────────────────
    if date_cols and num_cols:
        return "line", date_cols[0], num_cols[0]

    # ── Rule 2: One category + one number ────────────────────────────────────
    if len(cat_cols) >= 1 and len(num_cols) >= 1:
        x = cat_cols[0]
        y = num_cols[0]
        n_categories = df[x].nunique()

        # Pie: few distinct categories, the numbers sum to something meaningful
        if n_categories <= 8 and len(df) <= 8:
            return "pie", x, y

        # Bar: reasonable number of categories
        if n_categories <= 30:
            return "bar", x, y

    # ── Rule 3: Two numeric columns → scatter ────────────────────────────────
    if len(num_cols) >= 2:
        return "scatter", num_cols[0], num_cols[1]

    # ── Fallback: plain table ─────────────────────────────────────────────────
    return "table", "", ""


def _is_datetime_col(series: pd.Series) -> bool:
    """Return True if the series looks like a date/time column."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if series.dtype == object:
        sample = series.dropna().head(5).astype(str).tolist()
        hints = ["-", "/", "jan", "feb", "mar", "apr", "may", "jun",
                 "jul", "aug", "sep", "oct", "nov", "dec"]
        hits = sum(1 for s in sample if any(h in s.lower() for h in hints))
        return hits >= max(1, len(sample) // 2)
    return False
