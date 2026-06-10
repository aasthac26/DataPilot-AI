"""
tests/test_validator.py
Unit tests for the SQL safety validator.
Run with: python -m pytest tests/test_validator.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.validator import validate_query, assert_safe


class TestValidQueryPasses:
    def test_simple_select(self):
        result = validate_query("SELECT * FROM customers;")
        assert result.is_safe

    def test_select_with_where(self):
        result = validate_query("SELECT name, revenue FROM customers WHERE city = 'Mumbai';")
        assert result.is_safe

    def test_select_with_group_by(self):
        result = validate_query("SELECT city, SUM(revenue) FROM customers GROUP BY city;")
        assert result.is_safe

    def test_select_with_order_and_limit(self):
        result = validate_query("SELECT * FROM customers ORDER BY revenue DESC LIMIT 10;")
        assert result.is_safe

    def test_select_with_aggregate(self):
        result = validate_query("SELECT COUNT(*), AVG(revenue) FROM customers;")
        assert result.is_safe


class TestDangerousQueryBlocked:
    def test_drop_table(self):
        result = validate_query("DROP TABLE customers;")
        assert not result.is_safe
        assert any("DROP" in i.upper() or "Only SELECT" in i for i in result.issues)

    def test_delete(self):
        result = validate_query("DELETE FROM customers WHERE city = 'Mumbai';")
        assert not result.is_safe

    def test_update(self):
        result = validate_query("UPDATE customers SET revenue = 0;")
        assert not result.is_safe

    def test_insert(self):
        result = validate_query("INSERT INTO customers VALUES (1, 'Test', 'Delhi', 100);")
        assert not result.is_safe

    def test_alter_table(self):
        result = validate_query("ALTER TABLE customers ADD COLUMN age INTEGER;")
        assert not result.is_safe

    def test_create_table(self):
        result = validate_query("CREATE TABLE hack (id INTEGER);")
        assert not result.is_safe

    def test_non_select_start(self):
        result = validate_query("PRAGMA journal_mode = WAL;")
        assert not result.is_safe

    def test_sql_comment_injection(self):
        result = validate_query("SELECT * FROM customers; -- DROP TABLE customers")
        assert not result.is_safe

    def test_assert_safe_raises_on_danger(self):
        try:
            assert_safe("DROP TABLE customers;")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_assert_safe_passes_on_select(self):
        sql = assert_safe("SELECT * FROM customers LIMIT 5;")
        assert sql.startswith("SELECT")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
