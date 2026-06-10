"""
Module 7: AI Insights Engine
Turns raw query results into natural-language business insights.
Makes DataPilot feel like a real analyst, not just a query runner.
"""

import pandas as pd
from typing import Dict, Any
from utils.llm_client import chat
from core.ingestion import schema_to_prompt_str


_INSIGHTS_SYSTEM_PROMPT = """You are a senior business analyst giving insights to a non-technical executive.

When given a SQL query result, provide:
1. The single most important finding (bold it using **text**).
2. 2-3 additional business insights or patterns you notice.
3. One actionable recommendation based on the data.

Rules:
- Be specific — use actual numbers and percentages from the data.
- Keep total response under 150 words.
- Write in clear, confident business language.
- Do NOT describe what the query does — focus only on what the DATA means.
- Do NOT use bullet points. Write as flowing prose.
"""


def generate_insights(
    df: pd.DataFrame,
    user_question: str,
    schema: Dict[str, Any],
) -> str:
    """
    Generate business insights from a query result DataFrame.

    Args:
        df:            The query result as a DataFrame.
        user_question: The original user question (for context).
        schema:        Schema dict from ingestion.detect_schema().

    Returns:
        A string with AI-generated business insights.
    """
    if df is None or df.empty:
        return "No data returned — unable to generate insights."

    # Summarize the data for the LLM (avoid sending huge tables)
    data_summary = _summarize_dataframe(df)
    schema_str = schema_to_prompt_str(schema)

    user_message = (
        f"The user asked: \"{user_question}\"\n\n"
        f"Schema context:\n{schema_str}\n\n"
        f"Query result summary:\n{data_summary}"
    )

    insight = chat(
        system_prompt=_INSIGHTS_SYSTEM_PROMPT,
        user_message=user_message,
        temperature=0.4,
        max_tokens=250,
    )

    return insight


def _summarize_dataframe(df: pd.DataFrame, max_rows: int = 20) -> str:
    """
    Convert a DataFrame to a compact text representation for the LLM.
    Caps at max_rows to keep prompt size reasonable.
    """
    total_rows = len(df)
    sample = df.head(max_rows)

    lines = [f"Total rows returned: {total_rows}"]

    # Add numeric column stats
    num_cols = df.select_dtypes(include="number").columns.tolist()
    for col in num_cols[:4]:   # Cap at 4 numeric columns
        col_data = df[col].dropna()
        if len(col_data) > 0:
            lines.append(
                f"{col}: min={col_data.min():.2f}, max={col_data.max():.2f}, "
                f"mean={col_data.mean():.2f}, sum={col_data.sum():.2f}"
            )

    lines.append("\nData (first rows):")
    lines.append(sample.to_string(index=False, max_colwidth=30))

    return "\n".join(lines)
