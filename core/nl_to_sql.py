"""
Module 3: Natural Language → SQL
Uses Groq LLM to convert a user's plain-English question
into a valid SQLite SELECT query based on the dataset schema.
"""

import re
from typing import Dict, Any, List, Optional
from utils.llm_client import chat
from core.ingestion import schema_to_prompt_str


# ── System prompt for SQL generation ──────────────────────────────────────────
_SQL_SYSTEM_PROMPT = """You are an expert SQL query generator for SQLite databases.

Your job:
- Read the database schema carefully, including the sample values shown for each column.
- Convert the user's natural language question into a single, valid SQLite SELECT query.
- ONLY output the raw SQL query. No explanation, no markdown, no code blocks, no backticks.
- Never use DROP, DELETE, UPDATE, INSERT, ALTER, or CREATE statements.
- Use only the table and column names exactly as given in the schema.
- If the question is ambiguous, write the most reasonable SELECT query.
- For text comparisons, use LOWER() for case-insensitive matching.
- Always use LIMIT 100 if the user does not specify a row limit.

CRITICAL — column type rules (check sample values before deciding):
- If a column's samples look like plain text e.g. "January", "North", "Q1" — use it DIRECTLY. Do NOT wrap in STRFTIME() or any date function.
- Only use STRFTIME() if samples are actual date strings like "2024-01-15" or "2024-01-15 10:30:00".
- Never assume a column is a date just because it's named "month", "date", "year" — always check the samples.
- If asked for a "month name", just SELECT the month column directly if samples already show month names.

CRITICAL — multi-table rules:
- Only JOIN tables when the question genuinely requires data from both tables.
- If the question is about one table only, query that table alone. Do NOT join unnecessarily.
- When joining, ALWAYS use the exact JOIN KEY provided in the prompt. Never invent or guess join columns.
- Always prefix column names with table name in JOIN queries to avoid ambiguity e.g. employees.name not just name.
- Never use any column other than the provided join key as the ON condition.

Output ONLY the SQL query, nothing else. End with a semicolon.
"""


def generate_sql(
    user_question: str,
    schema: Dict[str, Any],
    conversation_context: str = "",
    join_keys: Optional[List] = None,
) -> str:
    """
    Generate a SQLite SELECT query from a natural language question.

    Args:
        user_question:        The user's plain-English question.
        schema:               Schema dict from ingestion.detect_schema().
        conversation_context: Optional prior conversation summary for context.
        join_keys:            Optional list of (col_a, col_b, confidence) tuples.

    Returns:
        A SQL query string (not yet validated or executed).
    """
    schema = _trim_schema_for_llm(schema, user_question)
    schema_str = schema_to_prompt_str(schema)

    context_block = ""
    if conversation_context:
        context_block = f"\nPrevious conversation context:\n{conversation_context}\n"

    # Sample values block
    samples_block = "\nSample values per column:\n"
    for col in schema.get("columns", []):
        samples = ", ".join(str(s) for s in col.get("sample_values", []))
        samples_block += f"  {col['name']}: [{samples}]\n"

    # JOIN block — always inject when multi-table, LLM decides whether to use it
    join_block = ""
    if join_keys and schema.get("is_multi_table"):
        table_names = schema.get("table_names", [])
        t1 = table_names[0] if len(table_names) > 0 else "table1"
        t2 = table_names[1] if len(table_names) > 1 else "table2"
        best = join_keys[0]  # always use highest confidence key only
        join_block = (
            f"\nAVAILABLE TABLES: {t1} and {t2}\n"
            f"JOIN KEY (use this if your query spans both tables): "
            f"{t1}.{best[0]} = {t2}.{best[1]}\n"
            f"RULES:\n"
            f"  - If the question only needs one table, query that table alone. Do NOT join.\n"
            f"  - If the question needs data from both tables, always use the join key above.\n"
            f"  - Never use any other columns as the join condition.\n"
        )

    user_message = (
        f"Database schema:\n{schema_str}\n"
        f"{samples_block}"
        f"{join_block}"
        f"{context_block}"
        f"\nUser question: {user_question}"
    )

    raw = chat(
        system_prompt=_SQL_SYSTEM_PROMPT,
        user_message=user_message,
        temperature=0.05,
        max_tokens=512,
    )

    return _clean_sql(raw)


def _trim_schema_for_llm(schema: Dict[str, Any], question: str, max_cols: int = 30) -> Dict[str, Any]:
    """
    For wide tables, keep only columns whose names appear in the question
    or are likely relevant, up to max_cols.
    """
    cols = schema.get("columns", [])
    if len(cols) <= max_cols:
        return schema

    question_lower = question.lower()

    def relevance(col):
        name = col["name"].lower().replace("_", " ")
        return 2 if name in question_lower else (1 if any(w in question_lower for w in name.split()) else 0)

    scored = sorted(cols, key=relevance, reverse=True)
    return {**schema, "columns": scored[:max_cols]}


def _clean_sql(raw: str) -> str:
    """
    Strip any accidental markdown fences or leading/trailing whitespace
    that the LLM might add despite instructions.
    """
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
    raw = raw.replace("```", "")
    sql = raw.strip()
    if sql and not sql.endswith(";"):
        sql += ";"
    return sql