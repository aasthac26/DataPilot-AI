"""
Module 4: Query Validator
Before any SQL is executed, check it for dangerous statements.
Blocks: DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE, EXEC, PRAGMA writes.
Only SELECT queries are allowed through.
"""

import re
from dataclasses import dataclass
from typing import List


# Dangerous SQL keywords / patterns that must never be executed
_BLOCKED_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bTRUNCATE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bPRAGMA\s+\w+\s*=",     # PRAGMA writes (reads are fine)
    r";\s*\w",                  # Multiple statements (SQL injection guard)
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _BLOCKED_PATTERNS]


@dataclass
class ValidationResult:
    is_safe: bool
    issues: List[str]
    cleaned_sql: str


def validate_query(sql: str) -> ValidationResult:
    """
    Check whether a SQL string is safe to execute.

    Returns a ValidationResult with:
      - is_safe:    True if the query can proceed
      - issues:     List of reason strings if blocked
      - cleaned_sql: The lightly-cleaned SQL (stripped whitespace)
    """
    issues = []
    cleaned = sql.strip()

    # Must start with SELECT (allow optional leading whitespace/newlines)
    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        issues.append(
            "Only SELECT queries are allowed. "
            "Data-modifying statements (INSERT, UPDATE, DELETE, etc.) are blocked."
        )

    # Check for dangerous keywords
    for pattern in _COMPILED:
        if pattern.search(cleaned):
            keyword = pattern.pattern.strip(r"\b").split(r"\b")[0].replace("\\b", "")
            issues.append(f"Blocked keyword detected: {keyword.upper()}")

    # Check for suspicious comment-based injection tricks
    if "--" in cleaned or "/*" in cleaned:
        issues.append("SQL comments detected — potential injection attempt blocked.")

    return ValidationResult(
        is_safe=len(issues) == 0,
        issues=list(dict.fromkeys(issues)),  # deduplicate while preserving order
        cleaned_sql=cleaned,
    )


def assert_safe(sql: str) -> str:
    """
    Convenience wrapper: validate and return cleaned SQL, or raise ValueError.
    Use this in the execution pipeline.
    """
    result = validate_query(sql)
    if not result.is_safe:
        raise ValueError(
            "Query blocked for safety reasons:\n" + "\n".join(f"• {i}" for i in result.issues)
        )
    return result.cleaned_sql
