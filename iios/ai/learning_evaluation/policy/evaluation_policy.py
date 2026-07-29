"""
evaluation_policy.py -- iios.ai.learning_evaluation.policy
============================================================
Abstract and default evaluation policy.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.evaluation_request import EvaluationRequest
from ..exceptions.learning_evaluation_exceptions import AILearningEvaluationPolicyViolationError


class EvaluationPolicy(ABC):
    """Abstract policy governing evaluation request acceptance."""

    @abstractmethod
    def validate_request(self, session_id: str, request: EvaluationRequest) -> None:
        """Raise :class:`AILearningEvaluationPolicyViolationError` if request is invalid."""

    @abstractmethod
    def min_confidence(self) -> float:
        """Minimum required confidence threshold (0.0–1.0)."""


class DefaultEvaluationPolicy(EvaluationPolicy):
    """Default permissive evaluation policy."""

    def validate_request(self, session_id: str, request: EvaluationRequest) -> None:
        if request.session_id != session_id:
            raise AILearningEvaluationPolicyViolationError(
                f"Request session_id {request.session_id!r} does not match {session_id!r}"
            )

    def min_confidence(self) -> float:
        return 0.0
