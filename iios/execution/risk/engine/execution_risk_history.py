"""iios/execution/risk/engine/execution_risk_history.py
==================================================
EngineRiskHistory — thread-safe, bounded, append-only record of all
Execution Risk Engine operation results.

C6 Execution Intelligence — Phase 4, Module 2
"""
from __future__ import annotations

import threading
from typing import List

from .constants import DEFAULT_MAX_HISTORY, OperationType
from .execution_risk_result import EvaluationResult


class EngineRiskHistory:
    """
    Thread-safe, bounded, append-only history of ``EvaluationResult`` records.

    When capacity is reached, the oldest entry is evicted.
    Eviction count is tracked for audit purposes.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._max      = max(1, max_size)
        self._results: List[EvaluationResult] = []
        self._evicted  = 0
        self._lock     = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, result: EvaluationResult) -> None:
        """Append a result; evict the oldest if at capacity."""
        with self._lock:
            if len(self._results) >= self._max:
                self._results.pop(0)
                self._evicted += 1
            self._results.append(result)

    # ── Read ──────────────────────────────────────────────────────────────────

    def all(self) -> List[EvaluationResult]:
        """All recorded results, oldest first."""
        with self._lock:
            return list(self._results)

    def latest(self, n: int = 10) -> List[EvaluationResult]:
        """The most recent *n* results, newest first."""
        with self._lock:
            return list(reversed(self._results[-n:]))

    def by_operation(self, op_type: OperationType) -> List[EvaluationResult]:
        """All results whose ``operation_type`` matches *op_type*."""
        with self._lock:
            return [r for r in self._results if r.operation_type == op_type]

    def by_evaluation(self, evaluation_id: str) -> List[EvaluationResult]:
        """All results related to *evaluation_id*."""
        with self._lock:
            return [r for r in self._results if r.evaluation_id == evaluation_id]

    def failed(self) -> List[EvaluationResult]:
        """All results that indicate a failed operation."""
        with self._lock:
            return [r for r in self._results if r.failed]

    def successful(self) -> List[EvaluationResult]:
        """All results that indicate a successful operation."""
        with self._lock:
            return [r for r in self._results if r.succeeded]

    def blocked(self) -> List[EvaluationResult]:
        """All results where the outcome was BLOCKED."""
        with self._lock:
            return [r for r in self._results if r.is_blocked]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        """Total results appended (including evicted)."""
        with self._lock:
            return len(self._results) + self._evicted

    @property
    def evicted(self) -> int:
        """Number of results evicted due to capacity."""
        with self._lock:
            return self._evicted

    def __len__(self) -> int:
        with self._lock:
            return len(self._results)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._results) == 0
