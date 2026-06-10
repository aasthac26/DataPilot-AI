"""
tests/test_nl_to_sql.py
Tests for the NL-to-SQL module.
Uses monkeypatching to mock the LLM so no API key is needed to run tests.
Run with: python -m pytest tests/test_nl_to_sql.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.nl_to_sql import _clean_sql, generate_sql
from core.ingestion import detect_schema
import pandas as pd


class TestCleanSQL:
    def test_strips_markdown_fences(self):
        raw = "```sql\nSELECT * FROM customers;\n```"
        result = _clean_sql(raw)
        assert result == "SELECT * FROM customers;"
        assert "```" not in result

    def test_adds_semicolon_if_missing(self):
        result = _clean_sql("SELECT * FROM customers")
        assert result.endswith(";")

    def test_does_not_double_semicolon(self):
        result = _clean_sql("SELECT * FROM customers;")
        assert result.count(";") == 1

    def test_strips_whitespace(self):
        result = _clean_sql("   SELECT 1;   ")
        assert result == "SELECT 1;"

    def test_strips_plain_fences(self):
        raw = "```\nSELECT id FROM t;\n```"
        result = _clean_sql(raw)
        assert "```" not in result
        assert "SELECT" in result


class TestGenerateSQL:
    """
    These tests mock the LLM client to avoid needing a real API key.
    """

    def _make_schema(self):
        df = pd.DataFrame({
            "customer_id": [1, 2, 3],
            "name": ["Alice", "Bob", "Carol"],
            "revenue": [1000.0, 2000.0, 1500.0],
            "city": ["Mumbai", "Delhi", "Bangalore"],
        })
        return detect_schema(df, "customers")

    def test_generate_sql_with_mock(self, monkeypatch):
        # Mock the LLM to return a canned SQL
        import utils.llm_client as llm
        def fake_chat(system_prompt, user_message, **kwargs):
            return "SELECT * FROM customers ORDER BY revenue DESC LIMIT 10;"
        monkeypatch.setattr(llm, "chat", fake_chat)

        schema = self._make_schema()
        sql = generate_sql("Show top 10 customers by revenue", schema)
        assert "SELECT" in sql.upper()
        assert "customers" in sql.lower()

    def test_generate_sql_cleans_output(self, monkeypatch):
        import utils.llm_client as llm
        def fake_chat(system_prompt, user_message, **kwargs):
            # Simulate LLM returning markdown-wrapped SQL
            return "```sql\nSELECT city, SUM(revenue) FROM customers GROUP BY city;\n```"
        monkeypatch.setattr(llm, "chat", fake_chat)

        schema = self._make_schema()
        sql = generate_sql("Total revenue by city", schema)
        assert "```" not in sql
        assert sql.endswith(";")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
