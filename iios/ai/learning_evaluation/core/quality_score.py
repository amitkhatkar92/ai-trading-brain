"""
quality_score.py -- iios.ai.learning_evaluation.core
=====================================================
:class:`QualityDimension` — quality axis classification.
:class:`QualityGrade`     — letter grade for a quality score.
:class:`QualityScore`     — immutable multi-dimension quality assessment.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Optional, Tuple


class QualityDimension(str, Enum):
    """Quality evaluation axis."""
    ACCURACY          = "accuracy"
    CONSISTENCY       = "consistency"
    COMPLETENESS      = "completeness"
    RELEVANCE         = "relevance"
    HALLUCINATION_FREE = "hallucination_free"
    TIMELINESS        = "timeliness"
    SAFETY            = "safety"


class QualityGrade(str, Enum):
    """Letter grade derived from aggregate quality score."""
    A = "A"   # ≥ 0.90
    B = "B"   # ≥ 0.75
    C = "C"   # ≥ 0.60
    D = "D"   # ≥ 0.45
    F = "F"   # < 0.45

    @classmethod
    def from_score(cls, score: float) -> "QualityGrade":
        if score >= 0.90:
            return cls.A
        if score >= 0.75:
            return cls.B
        if score >= 0.60:
            return cls.C
        if score >= 0.45:
            return cls.D
        return cls.F


@dataclass(frozen=True)
class QualityScore:
    """
    Immutable multi-dimension quality score for one AI output.

    ``dimension_scores`` — frozenset of ``(QualityDimension.value, score)`` tuples.
    ``aggregate``        — weighted mean of all dimension scores.
    ``grade``            — derived :class:`QualityGrade`.
    ``violations``       — rule names that were violated (if any).
    """

    score_id:         str
    target_id:        str
    aggregate:        float
    grade:            QualityGrade
    dimension_scores: FrozenSet[Tuple[str, float]]
    violations:       FrozenSet[str]
    assessed_at:      float
    notes:            str

    @classmethod
    def build(
        cls,
        target_id:        str,
        dimension_scores: FrozenSet[Tuple[str, float]],
        violations:       FrozenSet[str] = frozenset(),
        notes:            str            = "",
    ) -> "QualityScore":
        scores = [v for _, v in dimension_scores]
        agg    = (sum(scores) / len(scores)) if scores else 0.0
        agg    = round(max(0.0, min(1.0, agg)), 6)
        # Penalise if there are hallucination_free violations
        if violations:
            agg = max(0.0, agg - 0.05 * len(violations))
        return cls(
            score_id         = str(uuid.uuid4()),
            target_id        = target_id,
            aggregate        = agg,
            grade            = QualityGrade.from_score(agg),
            dimension_scores = frozenset(dimension_scores),
            violations       = frozenset(violations),
            assessed_at      = time.time(),
            notes            = notes,
        )

    def get_dimension(self, dim: QualityDimension, default: float = 0.0) -> float:
        for k, v in self.dimension_scores:
            if k == dim.value:
                return v
        return default

    def passed(self, min_grade: QualityGrade = QualityGrade.C) -> bool:
        order = [QualityGrade.F, QualityGrade.D, QualityGrade.C, QualityGrade.B, QualityGrade.A]
        return order.index(self.grade) >= order.index(min_grade)
