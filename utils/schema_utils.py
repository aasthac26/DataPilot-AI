"""
utils/schema_utils.py
Helpers for formatting schema information for display in the UI.
"""

from typing import Dict, Any


def schema_to_display_table(schema: Dict[str, Any]) -> list:
    """
    Convert schema dict into a list of dicts suitable for st.dataframe().
    Columns: Column Name | SQL Type | Nulls | Unique Values | Sample
    """
    rows = []
    for col in schema["columns"]:
        rows.append({
            "Column": col["name"],
            "Type": col["dtype_sql"],
            "Nulls": f"{col['null_count']} ({col['null_pct']}%)",
            "Unique": col["unique_count"],
            "Sample Values": ", ".join(str(s) for s in col["sample_values"]),
        })
    return rows


def format_schema_badge(schema: Dict[str, Any]) -> str:
    """
    One-line summary string: e.g. "customers • 1,200 rows • 5 columns"
    """
    return (
        f"**{schema['table_name']}** • "
        f"{schema['row_count']:,} rows • "
        f"{schema['col_count']} columns"
    )
