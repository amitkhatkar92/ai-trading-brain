"""
learning_policy.py -- iios.ai.learning_evaluation.policy
==========================================================
Abstract and default learning policy.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.learning_record import LearningRecord
from ..exceptions.learning_evaluation_exceptions import AILearningEvaluationPolicyViolationError


class LearningPolicy(ABC):
    """Abstract policy governing learning record acceptance."""

    @abstractmethod
    def validate_record(self, record: LearningRecord) -> None:
        """Raise :class:`AILearningEvaluationPolicyViolationError` if record is invalid."""

    @abstractmethod
    def max_records_per_source(self) -> int:
        """Maximum learning records stored per source_id."""


class DefaultLearningPolicy(LearningPolicy):
    """Default learning policy — 10 000 records per source."""

    def validate_record(self, record: LearningRecord) -> None:
        # No additional validation by default
        pass

    def max_records_per_source(self) -> int:
        return 10_000
