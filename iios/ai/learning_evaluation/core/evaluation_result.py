"""
evaluation_result.py -- iios.ai.learning_evaluation.core
=========================================================
:class:`EvaluationOutcome` — high-level result classification.
:class:`EvaluationResult`  — immutable result for one evaluation request.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Optional, Tuple


class EvaluationOutcome(str, Enum):
    """High-level result of one evaluation task."""
    PASS    = "pass"
    FAIL    = "fail"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    ERROR   = "error"

    def is_success(self) -> bool:
        return self in (EvaluationOutcome.PASS, EvaluationOutcome.PARTIAL)


@dataclass(frozen=True)
class EvaluationResult:
    """
    Immutable result produced for one :class:`EvaluationRequest`.

    ``actual``      — AI system output under evaluation.
    ``scores``      — frozenset of ``(metric_name, score)`` float tuples.
    ``error_msg``   — populated only on ERROR outcome.
    """

    result_id:    str
    request_id:   str
    session_id:   str
    outcome:      EvaluationOutcome
    actual:       Any
    scores:       FrozenSet[Tuple[str, float]]
    confidence:   float
    latency_ms:   float
    error_msg:    Optional[str]
    evaluated_at: float
    notes:        str

    @classmethod
    def passed(
        cls,
        request_id:  str,
        session_id:  str,
        actual:      Any,
        scores:      FrozenSet[Tuple[str, float]] = frozenset(),
        confidence:  float = 1.0,
        latency_ms:  float = 0.0,
        notes:       str   = "",
    ) -> "EvaluationResult":
        return cls(
            result_id    = str(uuid.uuid4()),
            request_id   = request_id,
            session_id   = session_id,
            outcome      = EvaluationOutcome.PASS,
            actual       = actual,
            scores       = frozenset(scores),
            confidence   = max(0.0, min(1.0, confidence)),
            latency_ms   = latency_ms,
            error_msg    = None,
            evaluated_at = time.time(),
            notes        = notes,
        )

    @classmethod
    def failed(
        cls,
        request_id:  str,
        session_id:  str,
        actual:      Any        = None,
        error_msg:   str        = "",
        scores:      FrozenSet[Tuple[str, float]] = frozenset(),
        latency_ms:  float      = 0.0,
    ) -> "EvaluationResult":
        return cls(
            result_id    = str(uuid.uuid4()),
            request_id   = request_id,
            session_id   = session_id,
            outcome      = EvaluationOutcome.FAIL,
            actual       = actual,
            scores       = frozenset(scores),
            confidence   = 0.0,
            latency_ms   = latency_ms,
            error_msg    = error_msg or "Evaluation failed",
            evaluated_at = time.time(),
            notes        = "",
        )

    @classmethod
    def error(
        cls,
        request_id: str,
        session_id: str,
        error_msg:  str,
    ) -> "EvaluationResult":
        return cls(
            result_id    = str(uuid.uuid4()),
            request_id   = request_id,
            session_id   = session_id,
            outcome      = EvaluationOutcome.ERROR,
            actual       = None,
            scores       = frozenset(),
            confidence   = 0.0,
            latency_ms   = 0.0,
            error_msg    = error_msg,
            evaluated_at = time.time(),
            notes        = "",
        )

    def get_score(self, metric: str, default: float = 0.0) -> float:
        for k, v in self.scores:
            if k == metric:
                return v
        return default

    def is_success(self) -> bool:
        return self.outcome.is_success()
