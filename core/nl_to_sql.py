"""
Module 3: Natural Language → SQL
Uses Groq LLM to convert a user's plain-English question
into a valid SQLite SELECT query based on the dataset schema.
"""

import re
from typing import Dict, Any
from utils.llm_client import chat
from core.ingestion import schema_to_prompt_str


# ── System prompt for SQL generation ──────────────────────────────────────────
_SQL_SYSTEM_PROMPT = """You are an expert SQL query generator for SQLite databases.

Your job:
- Read the database schema provided.
- Convert the user's natural language question into a single, valid SQLite SELECT query.
- ONLY output the raw SQL query. No explanation, no markdown, no code blocks, no backticks.
- Never use DROP, DELETE, UPDATE, INSERT, ALTER, or CREATE statements.
- Use only the table and column names exactly as given in the schema.
- If the question is ambiguous, write the most reasonable SELECT query.
- For text comparisons, use LOWER() for case-insensitive matching.
- Always use LIMIT 100 if the user does not specify a row limit, to avoid huge results.

Rules:
- Output ONLY the SQL query, nothing else.
- End the query with a semicolon.
"""


def generate_sql(
    user_question: str,
    schema: Dict[str, Any],
    conversation_context: str = "",
) -> str:
    """
    Generate a SQLite SELECT query from a natural language question.

    Args:
        user_question:        The user's plain-English question.
        schema:               Schema dict from ingestion.detect_schema().
        conversation_context: Optional prior conversation summary for context.

    Returns:
        A SQL query string (not yet validated or executed).
    """
    schema_str = schema_to_prompt_str(schema)

    context_block = ""
    if conversation_context:
        context_block = f"\nPrevious conversation context:\n{conversation_context}\n"

    user_message = (
        f"Database schema:\n{schema_str}\n"
        f"{context_block}"
        f"\nUser question: {user_question}"
    )

    raw = chat(
        system_prompt=_SQL_SYSTEM_PROMPT,
        user_message=user_message,
        temperature=0.05,   # Very low temperature for precise SQL
        max_tokens=512,
    )

    sql = _clean_sql(raw)
    return sql


def _clean_sql(raw: str) -> str:
    """
    Strip any accidental markdown fences or leading/trailing whitespace
    that the LLM might add despite instructions.
    """
    # Remove ```sql ... ``` or ``` ... ``` blocks
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE)
    raw = raw.replace("```", "")
    sql = raw.strip()

    # Ensure it ends with a semicolon
    if sql and not sql.endswith(";"):
        sql += ";"

    return sql
