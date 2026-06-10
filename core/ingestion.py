"""
Module 1: Dataset Ingestion
- Accepts CSV and Excel uploads
- Detects columns, data types, and generates schema
- Returns a clean DataFrame + schema dict
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
import io


# Map pandas dtypes to friendly SQL-like type names
DTYPE_MAP = {
    "int64": "INTEGER",
    "int32": "INTEGER",
    "float64": "FLOAT",
    "float32": "FLOAT",
    "object": "TEXT",
    "bool": "BOOLEAN",
    "datetime64[ns]": "DATETIME",
    "category": "TEXT",
}


def load_file(uploaded_file) -> Tuple[pd.DataFrame, str]:
    """
    Load a CSV or Excel file from Streamlit's UploadedFile object.
    Returns (DataFrame, table_name).
    """
    filename = uploaded_file.name
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "csv":
        try:
         df = pd.read_csv(uploaded_file, encoding="utf-8")
        except UnicodeDecodeError:
         uploaded_file.seek(0)
         df = pd.read_csv(uploaded_file, encoding="latin-1")
    elif ext in ("xlsx", "xls"):
        xl = pd.ExcelFile(uploaded_file)
        sheet = xl.sheet_names[0]   # or let user pick
        df = pd.read_excel(xl, sheet_name=sheet)
    else:
        raise ValueError(f"Unsupported file type: .{ext}. Please upload a CSV or Excel file.")

    # Sanitize column names: lowercase, replace spaces with underscores
    df.columns = [
        col.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")
        for col in df.columns
    ]

    # Derive table name from filename (strip extension, sanitize)
    table_name = (
        filename.rsplit(".", 1)[0]
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )

    return df, table_name


def detect_schema(df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
    """
    Analyze a DataFrame and return a schema dictionary with:
    - table name
    - row and column counts
    - column details (name, dtype, sample values, null count)
    """
    columns = []
    for col in df.columns:
        dtype_raw = str(df[col].dtype)
        sql_type = DTYPE_MAP.get(dtype_raw, "TEXT")

        # Try to detect datetime columns stored as strings
        if sql_type == "TEXT":
            sample = df[col].dropna().head(5).tolist()
            if _looks_like_datetime(sample):
                sql_type = "DATETIME"
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                except Exception:
                    pass

        columns.append(
            {
                "name": col,
                "dtype_pandas": dtype_raw,
                "dtype_sql": sql_type,
                "null_count": int(df[col].isnull().sum()),
                "null_pct": round(df[col].isnull().mean() * 100, 2),
                "unique_count": int(df[col].nunique()),
                "sample_values": _safe_samples(df[col]),
            }
        )

    schema = {
        "table_name": table_name,
        "row_count": len(df),
        "col_count": len(df.columns),
        "columns": columns,
    }
    return schema


def schema_to_prompt_str(schema: Dict[str, Any]) -> str:
    """
    Convert the schema dict into a compact string for LLM prompts.
    Example:
        Table: customers
        Columns: customer_id (INTEGER), name (TEXT), revenue (FLOAT), city (TEXT)
        Rows: 1200
    """
    col_parts = ", ".join(
        f"{c['name']} ({c['dtype_sql']})" for c in schema["columns"]
    )
    return (
        f"Table: {schema['table_name']}\n"
        f"Columns: {col_parts}\n"
        f"Rows: {schema['row_count']}"
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_samples(series: pd.Series, n: int = 3) -> list:
    """Return up to n non-null sample values from a Series, JSON-safe."""
    samples = series.dropna().head(n).tolist()
    result = []
    for s in samples:
        if isinstance(s, (np.integer,)):
            result.append(int(s))
        elif isinstance(s, (np.floating,)):
            result.append(float(s))
        else:
            result.append(str(s))
    return result


def _looks_like_datetime(samples: list) -> bool:
    """Heuristic: does this list of strings look like dates/datetimes?"""
    if not samples:
        return False
    date_hints = ["-", "/", ":", "jan", "feb", "mar", "apr", "may", "jun",
                  "jul", "aug", "sep", "oct", "nov", "dec"]
    hits = 0
    for s in samples:
        s_lower = str(s).lower()
        if any(h in s_lower for h in date_hints):
            hits += 1
    return hits >= max(1, len(samples) // 2)
