"""
acceptance_policy.py -- iios.ai.learning_evaluation.policy
============================================================
Abstract and default acceptance policy for evaluation results.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.evaluation_result import EvaluationResult


class AcceptancePolicy(ABC):
    """Abstract policy deciding whether an EvaluationResult is acceptable."""

    @abstractmethod
    def is_acceptable(self, result: EvaluationResult) -> bool:
        """Return True if the result meets acceptance criteria."""

    @abstractmethod
    def min_pass_rate(self) -> float:
        """Minimum fraction of passing results required in a session."""


class DefaultAcceptancePolicy(AcceptancePolicy):
    """Default acceptance: result must pass (outcome == PASS or PARTIAL)."""

    def is_acceptable(self, result: EvaluationResult) -> bool:
        return result.is_success()

    def min_pass_rate(self) -> float:
        return 0.5
