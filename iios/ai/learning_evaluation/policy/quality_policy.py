"""
quality_policy.py -- iios.ai.learning_evaluation.policy
=========================================================
Abstract and default quality policy.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.quality_score import QualityGrade, QualityScore
from ..exceptions.learning_evaluation_exceptions import AILearningEvaluationPolicyViolationError


class QualityPolicy(ABC):
    """Abstract policy governing acceptable quality scores."""

    @abstractmethod
    def validate_score(self, score: QualityScore) -> None:
        """Raise :class:`AILearningEvaluationPolicyViolationError` if score is below threshold."""

    @abstractmethod
    def min_quality_grade(self) -> QualityGrade:
        """Minimum acceptable quality grade."""


class DefaultQualityPolicy(QualityPolicy):
    """Default quality policy — accepts grade D and above."""

    def validate_score(self, score: QualityScore) -> None:
        min_grade = self.min_quality_grade()
        order = [QualityGrade.F, QualityGrade.D, QualityGrade.C, QualityGrade.B, QualityGrade.A]
        if order.index(score.grade) < order.index(min_grade):
            raise AILearningEvaluationPolicyViolationError(
                f"Quality grade {score.grade.value!r} is below minimum {min_grade.value!r}"
            )

    def min_quality_grade(self) -> QualityGrade:
        return QualityGrade.D
