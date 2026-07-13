"""iios/investment/strategy/evaluation/evaluation_grade.py
EvaluationGrade — letter grade derived from an overall numeric score.
"""
from __future__ import annotations

from enum import Enum
from typing import Tuple


class EvaluationGrade(str, Enum):
    A_PLUS  = "A+"   # >= 90
    A       = "A"    # >= 80
    B_PLUS  = "B+"   # >= 70
    B       = "B"    # >= 60
    C       = "C"    # >= 50
    D       = "D"    # >= 40
    F       = "F"    # < 40
    UNKNOWN = "?"


# (min_score, grade)
_THRESHOLDS: Tuple[Tuple[float, EvaluationGrade], ...] = (
    (90.0, EvaluationGrade.A_PLUS),
    (80.0, EvaluationGrade.A),
    (70.0, EvaluationGrade.B_PLUS),
    (60.0, EvaluationGrade.B),
    (50.0, EvaluationGrade.C),
    (40.0, EvaluationGrade.D),
    ( 0.0, EvaluationGrade.F),
)


def grade_from_score(score: float) -> EvaluationGrade:
    """Map a numeric score (0–100) to an EvaluationGrade."""
    for threshold, grade in _THRESHOLDS:
        if score >= threshold:
            return grade
    return EvaluationGrade.F


def score_range_for_grade(grade: EvaluationGrade) -> Tuple[float, float]:
    """Return (low, high) score range for a given grade."""
    ranges = {
        EvaluationGrade.A_PLUS: (90.0, 100.0),
        EvaluationGrade.A:      (80.0,  90.0),
        EvaluationGrade.B_PLUS: (70.0,  80.0),
        EvaluationGrade.B:      (60.0,  70.0),
        EvaluationGrade.C:      (50.0,  60.0),
        EvaluationGrade.D:      (40.0,  50.0),
        EvaluationGrade.F:      ( 0.0,  40.0),
    }
    return ranges.get(grade, (0.0, 100.0))


def grade_label(grade: EvaluationGrade) -> str:
    labels = {
        EvaluationGrade.A_PLUS:  "Exceptional",
        EvaluationGrade.A:       "Excellent",
        EvaluationGrade.B_PLUS:  "Good",
        EvaluationGrade.B:       "Satisfactory",
        EvaluationGrade.C:       "Marginal",
        EvaluationGrade.D:       "Poor",
        EvaluationGrade.F:       "Failing",
        EvaluationGrade.UNKNOWN: "Unknown",
    }
    return labels.get(grade, "Unknown")
