"""
tests/test_health_analyzer.py
Unit tests for the Data Health Analyzer.
Run with: python -m pytest tests/test_health_analyzer.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
from core.health_analyzer import analyze_health, _count_outliers, _calculate_score


class TestHealthScoring:
    def test_clean_df_scores_high(self):
        df = pd.DataFrame({
            "id": range(100),
            "value": np.random.normal(50, 5, 100),
            "category": ["A", "B"] * 50,
        })
        report = analyze_health(df)
        assert report.score >= 90
        assert report.grade == "A"

    def test_duplicates_lower_score(self):
        df = pd.DataFrame({"a": [1, 2, 3, 1, 2, 3], "b": ["x", "y", "z", "x", "y", "z"]})
        report = analyze_health(df)
        assert report.duplicate_rows == 3
        assert report.score < 100

    def test_missing_values_detected(self):
        df = pd.DataFrame({
            "name": ["Alice", "Bob", None, None, None],
            "score": [90, None, 85, None, 78],
        })
        report = analyze_health(df)
        null_counts = [c.null_count for c in report.columns if c.name == "name"]
        assert null_counts[0] == 3

    def test_outliers_detected(self):
        normal_values = list(np.random.normal(50, 2, 100))
        outlier_values = [1000, -1000]  # Clear outliers
        series = pd.Series(normal_values + outlier_values)
        count = _count_outliers(series)
        assert count >= 2

    def test_empty_df(self):
        df = pd.DataFrame({"a": [], "b": []})
        report = analyze_health(df)
        assert report.total_rows == 0

    def test_grade_boundaries(self):
        assert _calculate_score(0, 0, 0, 0) == 100
        assert _calculate_score(5, 5, 3, 5) < 100
        assert _calculate_score(10, 20, 5, 10) < 80

    def test_constant_column_flagged(self):
        df = pd.DataFrame({
            "id": range(50),
            "constant": ["same_value"] * 50,
            "value": np.random.rand(50),
        })
        report = analyze_health(df)
        const_col = next(c for c in report.columns if c.name == "constant")
        assert const_col.is_constant
        assert any("constant" in issue.lower() or "Constant" in issue for issue in report.issues)


class TestHealthReport:
    def test_report_has_all_fields(self):
        df = pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]})
        report = analyze_health(df)
        assert report.total_rows == 3
        assert report.total_cols == 2
        assert isinstance(report.score, int)
        assert report.grade in ("A", "B", "C", "D", "F")
        assert isinstance(report.issues, list)
        assert isinstance(report.suggestions, list)

    def test_column_count_correct(self):
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3], "d": [4]})
        report = analyze_health(df)
        assert len(report.columns) == 4


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
