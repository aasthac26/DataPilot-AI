"""
Novel Feature: Data Health Analyzer
After upload, automatically analyze the dataset for:
  - Missing values
  - Duplicate rows
  - Outliers (IQR method)
  - Column statistics
  - Overall Data Quality Score (0–100)

This is the resume differentiator — connects SQL + Data Science.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class ColumnHealth:
    name: str
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    is_constant: bool           # All values the same (useless column)
    outlier_count: int          # For numeric columns only
    min_val: Any = None
    max_val: Any = None
    mean_val: Any = None


@dataclass
class HealthReport:
    total_rows: int
    total_cols: int
    duplicate_rows: int
    duplicate_pct: float
    columns: List[ColumnHealth]
    score: int                  # 0–100
    grade: str                  # A / B / C / D / F
    issues: List[str]           # Human-readable issue descriptions
    suggestions: List[str]      # Actionable fix suggestions


def analyze_health(df: pd.DataFrame) -> HealthReport:
    """
    Run a full data health analysis on a DataFrame.
    Returns a HealthReport with score, issues, and suggestions.
    """
    issues = []
    suggestions = []
    col_reports = []

    total_rows = len(df)
    total_cols = len(df.columns)

    # ── 1. Duplicate rows ─────────────────────────────────────────────────────
    dup_count = int(df.duplicated().sum())
    dup_pct = round(dup_count / total_rows * 100, 2) if total_rows > 0 else 0.0
    if dup_count > 0:
        issues.append(f"{dup_count} duplicate rows detected ({dup_pct}% of data).")
        suggestions.append("Remove duplicate rows with df.drop_duplicates() before analysis.")

    # ── 2. Per-column analysis ────────────────────────────────────────────────
    total_missing = 0
    total_outliers = 0
    constant_cols = 0

    for col in df.columns:
        series = df[col]
        null_count = int(series.isnull().sum())
        null_pct = round(null_count / total_rows * 100, 2) if total_rows > 0 else 0.0
        unique_count = int(series.nunique())
        is_constant = unique_count <= 1

        total_missing += null_count
        if is_constant:
            constant_cols += 1

        # Numeric stats + outliers
        outlier_count = 0
        min_val = max_val = mean_val = None

        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            if len(clean) > 0:
                min_val = _safe_scalar(clean.min())
                max_val = _safe_scalar(clean.max())
                mean_val = round(float(clean.mean()), 4)
                outlier_count = _count_outliers(clean)
                total_outliers += outlier_count

        col_reports.append(ColumnHealth(
            name=col,
            dtype=str(series.dtype),
            null_count=null_count,
            null_pct=null_pct,
            unique_count=unique_count,
            is_constant=is_constant,
            outlier_count=outlier_count,
            min_val=min_val,
            max_val=max_val,
            mean_val=mean_val,
        ))

    # ── 3. Issue messages ─────────────────────────────────────────────────────
    overall_null_pct = round(total_missing / (total_rows * total_cols) * 100, 2) if total_rows * total_cols > 0 else 0.0
    if overall_null_pct > 0:
        issues.append(f"{overall_null_pct}% of all values are missing across the dataset.")
        if overall_null_pct > 10:
            suggestions.append("Consider imputing or removing columns with high missing-value rates.")

    high_missing_cols = [c for c in col_reports if c.null_pct > 20]
    for c in high_missing_cols:
        issues.append(f"Column '{c.name}' has {c.null_pct}% missing values.")

    if total_outliers > 0:
        issues.append(f"{total_outliers} outlier values detected across numeric columns (IQR method).")
        suggestions.append("Review outliers — they may be data entry errors or genuine extreme values.")

    if constant_cols > 0:
        const_names = [c.name for c in col_reports if c.is_constant]
        issues.append(f"Constant columns (only one unique value): {', '.join(const_names)}.")
        suggestions.append(f"Consider dropping constant columns — they add no analytical value.")

    # ── 4. Score calculation ──────────────────────────────────────────────────
    score = _calculate_score(
        dup_pct=dup_pct,
        null_pct=overall_null_pct,
        outlier_ratio=total_outliers / (total_rows * total_cols) * 100 if total_rows * total_cols > 0 else 0,
        constant_col_ratio=constant_cols / total_cols * 100 if total_cols > 0 else 0,
    )
    grade = _score_to_grade(score)

    if not issues:
        issues.append("No significant data quality issues detected.")
        suggestions.append("Your dataset looks clean — ready for analysis!")

    return HealthReport(
        total_rows=total_rows,
        total_cols=total_cols,
        duplicate_rows=dup_count,
        duplicate_pct=dup_pct,
        columns=col_reports,
        score=score,
        grade=grade,
        issues=issues,
        suggestions=suggestions,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count_outliers(series: pd.Series) -> int:
    """Count outliers using the IQR (Interquartile Range) method."""
    if len(series) < 4:
        return 0
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return 0
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return int(((series < lower) | (series > upper)).sum())


def _calculate_score(
    dup_pct: float,
    null_pct: float,
    outlier_ratio: float,
    constant_col_ratio: float,
) -> int:
    """
    Calculate a 0–100 data quality score.
    Start from 100 and deduct for each issue.
    """
    score = 100.0

    # Deduct for duplicates (max -20)
    score -= min(dup_pct * 2, 20)

    # Deduct for missing values (max -30)
    score -= min(null_pct * 1.5, 30)

    # Deduct for outliers (max -15)
    score -= min(outlier_ratio * 3, 15)

    # Deduct for constant columns (max -10)
    score -= min(constant_col_ratio * 0.5, 10)

    return max(0, round(score))


def _score_to_grade(score: int) -> str:
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


def _safe_scalar(val) -> Any:
    """Convert numpy scalars to Python native types for JSON safety."""
    if isinstance(val, (np.integer,)):
        return int(val)
    elif isinstance(val, (np.floating,)):
        return round(float(val), 4)
    return val
