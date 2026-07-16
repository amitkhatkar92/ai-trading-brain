"""iios/execution/positions/engine/position_history.py
==================================================
EngineHistory — thread-safe, bounded, append-only record of all
Position Engine operation results.

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

import threading
from typing import Iterator, List

from .constants import DEFAULT_MAX_HISTORY, OperationType
from .position_result import PositionResult


class EngineHistory:
    """
    Thread-safe, bounded, append-only history of ``PositionResult`` records.

    When capacity is reached, the oldest entry is evicted.
    Eviction count is tracked for audit purposes.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._max       = max(1, max_size)
        self._results:  List[PositionResult] = []
        self._evicted   = 0
        self._lock      = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, result: PositionResult) -> None:
        """Append a result; evict the oldest if at capacity."""
        with self._lock:
            if len(self._results) >= self._max:
                self._results.pop(0)
                self._evicted += 1
            self._results.append(result)

    # ── Read ──────────────────────────────────────────────────────────────────

    def all(self) -> List[PositionResult]:
        """All recorded results, oldest first."""
        with self._lock:
            return list(self._results)

    def latest(self, n: int = 10) -> List[PositionResult]:
        """The most recent *n* results, newest first."""
        with self._lock:
            return list(reversed(self._results[-n:]))

    def by_operation(self, op_type: OperationType) -> List[PositionResult]:
        """All results whose ``operation_type`` matches *op_type*."""
        with self._lock:
            return [r for r in self._results if r.operation_type == op_type]

    def by_position(self, position_id: str) -> List[PositionResult]:
        """All results related to *position_id*."""
        with self._lock:
            return [r for r in self._results if r.position_id == position_id]

    def failed(self) -> List[PositionResult]:
        """All results that indicate a failed operation."""
        with self._lock:
            return [r for r in self._results if r.failed]

    def successful(self) -> List[PositionResult]:
        """All results that indicate a successful operation."""
        with self._lock:
            return [r for r in self._results if r.succeeded]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        """Total results appended (including evicted)."""
        with self._lock:
            return len(self._results) + self._evicted

    @property
    def evicted(self) -> int:
        with self._lock:
            return self._evicted

    def __len__(self) -> int:
        with self._lock:
            return len(self._results)

    def __iter__(self) -> Iterator[PositionResult]:
        with self._lock:
            return iter(list(self._results))
