"""
Feature 3: Multi-table JOIN Support
Lets users upload 2 or more CSV/Excel files and ask questions
that span across them — DataPilot automatically generates JOIN queries.

This is the hardest and most impressive feature. Almost no portfolio
NL-to-SQL project supports this. It requires:
  - Managing multiple schemas simultaneously
  - Teaching the LLM about table relationships
  - Auto-detecting likely join keys between tables
  - Generating correct multi-table SQL
"""

import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from utils.llm_client import chat


# ── Join Key Detection ────────────────────────────────────────────────────────

def detect_join_keys(
    schema_a: Dict[str, Any],
    schema_b: Dict[str, Any],
) -> List[Tuple[str, str, float]]:
    """
    Auto-detect likely join keys between two tables.
    Returns a list of (col_a, col_b, confidence_score) tuples,
    sorted by confidence descending.

    Detection strategy:
    1. Exact name match (col name identical in both tables)
    2. Fuzzy name match (e.g. 'customer_id' vs 'cust_id')
    3. Same dtype + similar value overlap
    """
    cols_a = {c["name"]: c for c in schema_a["columns"]}
    cols_b = {c["name"]: c for c in schema_b["columns"]}
    candidates = []

    for name_a, col_a in cols_a.items():
        for name_b, col_b in cols_b.items():
            score = 0.0

            # Exact name match
            if name_a == name_b:
                score += 0.8

            # One contains the other (e.g. 'id' in 'customer_id')
            elif name_a in name_b or name_b in name_a:
                score += 0.5

            # Both end in '_id' or both are 'id'
            elif name_a.endswith("_id") and name_b.endswith("_id"):
                score += 0.3

            # Strip common prefixes and compare
            elif _strip_prefix(name_a) == _strip_prefix(name_b):
                score += 0.4

            if score == 0:
                continue

            # Boost if same SQL type
            if col_a["dtype_sql"] == col_b["dtype_sql"]:
                score += 0.1

            # Boost if both look like IDs (INTEGER or low-cardinality TEXT)
            if col_a["dtype_sql"] == "INTEGER" and col_b["dtype_sql"] == "INTEGER":
                score += 0.1

            candidates.append((name_a, name_b, round(score, 2)))

    # Sort by confidence descending, deduplicate
    candidates.sort(key=lambda x: x[2], reverse=True)
    return candidates


def _strip_prefix(name: str) -> str:
    """Remove common table-prefix patterns like 'customer_id' → 'id'."""
    parts = name.split("_")
    if len(parts) > 1 and parts[-1] in ("id", "key", "code", "num", "no"):
        return parts[-1]
    return name


# ── Multi-schema prompt builder ───────────────────────────────────────────────

def build_multi_table_schema_str(schemas: List[Dict[str, Any]]) -> str:
    """
    Build a combined schema string for all uploaded tables.
    Includes join key hints so the LLM knows how to connect them.
    """
    lines = [f"Database has {len(schemas)} table(s):\n"]

    for schema in schemas:
        col_parts = []
        for c in schema["columns"]:
            samples = ", ".join(str(s) for s in c.get("sample_values", []))
            col_parts.append(f"    {c['name']} ({c['dtype_sql']}) — samples: [{samples}]")
        lines.append(f"Table: {schema['table_name']}")
        lines.append(f"Rows: {schema['row_count']}")
        lines.append("Columns:")
        lines.extend(col_parts)
        lines.append("")

    # Add join hints if multiple tables
    if len(schemas) == 2:
        join_keys = detect_join_keys(schemas[0], schemas[1])
        if join_keys:
            lines.append("Likely join keys (auto-detected):")
            for col_a, col_b, score in join_keys[:3]:
                lines.append(
                    f"  {schemas[0]['table_name']}.{col_a} ↔ "
                    f"{schemas[1]['table_name']}.{col_b} "
                    f"(confidence: {score:.0%})"
                )

    return "\n".join(lines)


# ── Multi-table SQL generation ────────────────────────────────────────────────

_MULTI_TABLE_SQL_PROMPT = """You are an expert SQL query generator for SQLite databases with multiple tables.

Your job:
- Read ALL table schemas carefully, including column names, types, and sample values.
- Use the auto-detected join keys to connect tables when the question spans multiple tables.
- Generate a single valid SQLite SELECT query.
- ONLY output the raw SQL. No explanation, no markdown, no backticks.
- Never use DROP, DELETE, UPDATE, INSERT, ALTER, or CREATE.
- Use table aliases (e.g. t1, t2) for clarity in JOINs.
- Use LEFT JOIN unless an INNER JOIN is clearly more appropriate.
- Always qualify column names with table name or alias when joining.
- Always use LIMIT 100 unless the user specifies otherwise.

Output ONLY the SQL query. End with a semicolon.
"""


def generate_multi_table_sql(
    user_question: str,
    schemas: List[Dict[str, Any]],
    conversation_context: str = "",
) -> str:
    """
    Generate a SQL query that may span multiple tables using JOINs.

    Args:
        user_question:        The user's plain-English question.
        schemas:              List of schema dicts, one per uploaded table.
        conversation_context: Prior conversation context string.

    Returns:
        A SQL query string (not yet validated or executed).
    """
    import re

    schema_str = build_multi_table_schema_str(schemas)

    context_block = ""
    if conversation_context:
        context_block = f"\nPrevious conversation context:\n{conversation_context}\n"

    user_message = (
        f"Database schemas:\n{schema_str}\n"
        f"{context_block}"
        f"\nUser question: {user_question}"
    )

    raw = chat(
        system_prompt=_MULTI_TABLE_SQL_PROMPT,
        user_message=user_message,
        temperature=0.05,
        max_tokens=600,
    )

    # Clean markdown fences
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
    raw = raw.replace("```", "").strip()
    if raw and not raw.endswith(";"):
        raw += ";"

    return raw


# ── Session state helpers ─────────────────────────────────────────────────────

def is_multi_table_mode(session_state) -> bool:
    """Return True if more than one table is loaded in the session."""
    return len(session_state.get("schemas", {})) > 1


def get_active_schemas(session_state) -> List[Dict[str, Any]]:
    """Return list of all active schema dicts from session state."""
    schemas_dict = session_state.get("schemas", {})
    return list(schemas_dict.values())


def get_combined_schema_for_display(schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a synthetic 'combined schema' for display purposes
    when multiple tables are loaded.
    """
    total_rows = sum(s["row_count"] for s in schemas)
    total_cols = sum(s["col_count"] for s in schemas)
    table_names = [s["table_name"] for s in schemas]

    return {
        "table_name": " + ".join(table_names),
        "row_count": total_rows,
        "col_count": total_cols,
        "columns": [col for s in schemas for col in s["columns"]],
        "is_multi_table": True,
        "table_names": table_names,
    }
