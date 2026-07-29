"""
evaluation_session.py -- iios.ai.learning_evaluation.evaluation
================================================================
:class:`EvaluationSession` — mutable coordinator for one evaluation session.

A7 Learning & Evaluation Platform — Phase 3, Module 7
"""
from __future__ import annotations

import threading
import time
from typing import List, Optional

from ..core.evaluation_metadata import EvaluationMetadata, EvaluationStatus
from ..core.evaluation_result   import EvaluationResult
from ..exceptions.learning_evaluation_exceptions import (
    AIEvaluationSessionAlreadyExistsError,
    AIEvaluationSessionClosedError,
)


class EvaluationSession:
    """
    Thread-safe mutable coordinator for one evaluation session.

    State transitions:
        CREATED → RUNNING → COMPLETED
                           → FAILED
                           → CANCELLED
    """

    def __init__(self, metadata: EvaluationMetadata) -> None:
        self._lock    = threading.Lock()
        self._meta    = metadata
        self._status  = EvaluationStatus.CREATED
        self._results: List[EvaluationResult] = []
        self._failure_reason: Optional[str]   = None
        self._started_at: Optional[float]     = None
        self._ended_at: Optional[float]       = None

    # ── identity ──────────────────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._meta.session_id

    @property
    def metadata(self) -> EvaluationMetadata:
        return self._meta

    @property
    def status(self) -> EvaluationStatus:
        with self._lock:
            return self._status

    @property
    def results(self) -> List[EvaluationResult]:
        with self._lock:
            return list(self._results)

    @property
    def result_count(self) -> int:
        with self._lock:
            return len(self._results)

    @property
    def failure_reason(self) -> Optional[str]:
        with self._lock:
            return self._failure_reason

    # ── state transitions ─────────────────────────────────────────────────────

    def start(self) -> None:
        with self._lock:
            if self._status != EvaluationStatus.CREATED:
                raise AIEvaluationSessionAlreadyExistsError(
                    f"Session {self.session_id!r} already started"
                )
            self._status     = EvaluationStatus.RUNNING
            self._started_at = time.time()

    def add_result(self, result: EvaluationResult) -> None:
        with self._lock:
            if self._status.is_terminal():
                raise AIEvaluationSessionClosedError(
                    f"Session {self.session_id!r} is {self._status.value}"
                )
            self._results.append(result)

    def complete(self) -> None:
        with self._lock:
            if self._status.is_terminal():
                return
            self._status   = EvaluationStatus.COMPLETED
            self._ended_at = time.time()

    def fail(self, reason: str = "") -> None:
        with self._lock:
            if self._status.is_terminal():
                return
            self._status         = EvaluationStatus.FAILED
            self._failure_reason = reason
            self._ended_at       = time.time()

    def cancel(self) -> None:
        with self._lock:
            if self._status.is_terminal():
                return
            self._status   = EvaluationStatus.CANCELLED
            self._ended_at = time.time()

    # ── analytics ─────────────────────────────────────────────────────────────

    def pass_rate(self) -> float:
        with self._lock:
            if not self._results:
                return 0.0
            return sum(1 for r in self._results if r.is_success()) / len(self._results)

    def duration_s(self) -> Optional[float]:
        with self._lock:
            if self._started_at is None:
                return None
            end = self._ended_at or time.time()
            return end - self._started_at
