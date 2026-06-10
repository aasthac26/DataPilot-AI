"""
Module 5: Query Explanation
Given a SQL query and the schema, ask the LLM to explain
what the query does in plain English for a non-technical user.
"""

from typing import Dict, Any
from utils.llm_client import chat
from core.ingestion import schema_to_prompt_str


_EXPLAIN_SYSTEM_PROMPT = """You are a friendly data analyst explaining SQL queries to non-technical users.

When given a SQL query and a database schema:
- Explain what the query does in 2-3 plain English sentences.
- Mention which table and columns are involved.
- Describe any filters, sorting, grouping, or limits applied.
- Do NOT use SQL jargon like "predicate", "projection", or "join condition".
- Be clear, concise, and friendly.
- Do NOT repeat the SQL code in your explanation.
"""


def explain_sql(sql: str, schema: Dict[str, Any]) -> str:
    """
    Generate a plain-English explanation of a SQL query.

    Args:
        sql:    The SQL query string.
        schema: Schema dict from ingestion.detect_schema().

    Returns:
        A human-friendly explanation string.
    """
    schema_str = schema_to_prompt_str(schema)

    user_message = (
        f"Database schema:\n{schema_str}\n\n"
        f"SQL query:\n{sql}\n\n"
        f"Explain what this query does in plain English."
    )

    explanation = chat(
        system_prompt=_EXPLAIN_SYSTEM_PROMPT,
        user_message=user_message,
        temperature=0.3,
        max_tokens=200,
    )

    return explanation
