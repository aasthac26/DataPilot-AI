"""
Module 1: Dataset Ingestion
- Accepts CSV and Excel uploads
- Detects columns, data types, and generates schema
- Returns a clean DataFrame + schema dict
"""

import re
import unicodedata
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


def _sanitize_column(col: str) -> str:
    """
    Sanitize column name to a valid SQL identifier.
    - Normalize unicode (café → cafe, Hindi/Gujarati → stripped)
    - Strip non-ASCII characters
    - Replace spaces/special chars with underscores
    - Collapse multiple underscores
    - Ensure it doesn't start with a digit
    """
    col = unicodedata.normalize("NFKD", col)
    col = col.encode("ascii", "ignore").decode("ascii")
    col = col.strip().lower()
    col = re.sub(r"[^a-z0-9]+", "_", col)
    col = re.sub(r"_+", "_", col)
    col = col.strip("_")
    if not col or col[0].isdigit():
        col = "col_" + col
    return col


def _clean_excel_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle common Excel export issues:
    - Drop fully empty rows and columns
    - If first row looks like a second header, promote it
    - Reset index
    """
    # Drop columns and rows that are entirely NaN
    df = df.dropna(how="all", axis=1).dropna(how="all", axis=0)
    df = df.reset_index(drop=True)

    # If pandas read a blank/merged row as header, detect and fix
    unnamed_count = sum(1 for c in df.columns if str(c).startswith("Unnamed:"))
    if unnamed_count > len(df.columns) / 2 and not df.empty:
        df.columns = df.iloc[0].astype(str)
        df = df[1:].reset_index(drop=True)

    return df


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
        sheet_names = xl.sheet_names

        # Pick the first non-empty sheet with more than 1 column
        df = None
        for sheet in sheet_names:
            candidate = pd.read_excel(xl, sheet_name=sheet)
            candidate = _clean_excel_df(candidate)
            if not candidate.empty and len(candidate.columns) > 1:
                df = candidate
                break
        if df is None:
            df = _clean_excel_df(pd.read_excel(xl, sheet_name=sheet_names[0]))

    else:
        raise ValueError(f"Unsupported file type: .{ext}. Please upload a CSV or Excel file.")

    # ── Sanitize column names ─────────────────────────────────────────────────
    original_cols = list(df.columns)
    df.columns = [_sanitize_column(str(col)) for col in df.columns]

    # Ensure unique column names after sanitization
    seen = {}
    new_cols = []
    for col in df.columns:
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_cols.append(col)
    df.columns = new_cols

    # Store original→sanitized mapping for schema display
    df.attrs["original_columns"] = dict(zip(df.columns, original_cols))

    # Derive table name from filename
    table_name = _sanitize_column(filename.rsplit(".", 1)[0]) or "data"

    return df, table_name


def detect_schema(df: pd.DataFrame, table_name: str) -> Dict[str, Any]:
    """
    Analyze a DataFrame and return a schema dictionary with:
    - table name
    - row and column counts
    - column details (name, dtype, sample values, null count)
    """
    original_columns = df.attrs.get("original_columns", {})
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
                "original_name": original_columns.get(col, col),
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
    Convert schema to a compact string for LLM prompts.
    Includes original column names and sample values so the LLM
    understands what each column contains before writing SQL.
    """
    lines = [f"Table: {schema['table_name']}", f"Rows: {schema['row_count']}", "Columns:"]
    for c in schema["columns"]:
        samples = ", ".join(str(s) for s in c["sample_values"])
        original = c.get("original_name", "")
        name_hint = f" (original: '{original}')" if original and original != c["name"] else ""
        lines.append(f"  - {c['name']} ({c['dtype_sql']}){name_hint} — samples: [{samples}]")
    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────

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
    # Only match actual date separators — NOT month name abbreviations
    date_hints = ["-", "/", ":"]
    hits = 0
    for s in samples:
        s_lower = str(s).lower()
        if any(h in s_lower for h in date_hints):
            hits += 1
    return hits >= max(1, len(samples) // 2)