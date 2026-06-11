"""
Feature 1: Smart Follow-up Question Suggester
After every query result, proactively generates 3 smart follow-up questions
the user might want to ask next — based on the schema, the question asked,
and the actual result data.

This is what turns DataPilot from a query tool into a true copilot.
The system doesn't wait for the user to think of the next question —
it thinks ahead for them.
"""

import pandas as pd
from typing import Dict, Any, List
from utils.llm_client import chat
from core.ingestion import schema_to_prompt_str


_FOLLOWUP_SYSTEM_PROMPT = """You are a data analyst helping a non-technical user explore their dataset.

Based on the user's question, the query result, and the dataset schema, generate exactly 3 smart follow-up questions the user might want to ask next.

Rules:
- Each question must be specific, short (under 12 words), and directly answerable from the same dataset.
- Make each question explore a DIFFERENT angle: one about filtering/drilling down, one about comparison, one about trend or ranking.
- Write questions as the user would naturally ask them — plain English, no SQL jargon.
- Do NOT repeat the original question.
- Do NOT number the questions.
- Output ONLY the 3 questions, one per line, nothing else. No intro, no explanation.

Example output format:
Which city has the highest average revenue?
Show customers who joined in 2023 only.
Compare revenue between Premium and Basic segments.
"""


def generate_followup_questions(
    user_question: str,
    result_df: pd.DataFrame,
    schema: Dict[str, Any],
) -> List[str]:
    """
    Generate 3 smart follow-up questions based on what the user just asked
    and what the data returned.

    Args:
        user_question: The question the user just asked.
        result_df:     The query result DataFrame.
        schema:        Full schema dict from ingestion.detect_schema().

    Returns:
        List of 3 question strings. Falls back to generic questions on error.
    """
    if result_df is None or result_df.empty:
        return _generic_fallback(schema)

    schema_str = schema_to_prompt_str(schema)
    result_preview = _result_preview(result_df)

    user_message = (
        f"Dataset schema:\n{schema_str}\n\n"
        f"User just asked: \"{user_question}\"\n\n"
        f"Query result preview:\n{result_preview}\n\n"
        f"Generate 3 smart follow-up questions."
    )

    try:
        raw = chat(
            system_prompt=_FOLLOWUP_SYSTEM_PROMPT,
            user_message=user_message,
            temperature=0.6,    # Slightly higher = more varied suggestions
            max_tokens=150,
        )
        questions = _parse_questions(raw)
        if len(questions) >= 2:
            return questions[:3]
        return _generic_fallback(schema)

    except Exception:
        return _generic_fallback(schema)


def _parse_questions(raw: str) -> List[str]:
    """
    Parse LLM output into a clean list of question strings.
    Handles numbered lists, bullet points, or plain lines.
    """
    import re
    lines = raw.strip().splitlines()
    questions = []
    for line in lines:
        # Strip numbering like "1.", "1)", "-", "•"
        clean = re.sub(r"^[\d]+[.)]\s*|^[-•*]\s*", "", line).strip()
        if clean and len(clean) > 5 and "?" in clean or len(clean) > 10:
            questions.append(clean)
    return questions


def _result_preview(df: pd.DataFrame, max_rows: int = 5) -> str:
    """Compact string preview of result for LLM context."""
    return df.head(max_rows).to_string(index=False, max_colwidth=20)


def _generic_fallback(schema: Dict[str, Any]) -> List[str]:
    """
    Return sensible generic follow-up questions when LLM call fails
    or returns bad output. Uses actual column names from the schema.
    """
    cols = schema.get("columns", [])
    num_cols = [c["name"] for c in cols if c["dtype_sql"] in ("INTEGER", "FLOAT")]
    cat_cols = [c["name"] for c in cols if c["dtype_sql"] == "TEXT"]
    table = schema.get("table_name", "the data")

    questions = []

    if num_cols:
        questions.append(f"What is the average {num_cols[0]}?")
    if cat_cols:
        questions.append(f"Show total count grouped by {cat_cols[0]}.")
    if num_cols and cat_cols:
        questions.append(f"Which {cat_cols[0]} has the highest {num_cols[0]}?")

    # Absolute fallback
    while len(questions) < 3:
        fallbacks = [
            f"Show the top 10 rows from {table}.",
            "How many rows are in the dataset?",
            "Show rows with missing values.",
        ]
        for f in fallbacks:
            if f not in questions:
                questions.append(f)
                break

    return questions[:3]
