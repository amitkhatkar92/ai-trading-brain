"""iios/decision_governance/history/governance_history.py

Thread-safe store for GovernanceResult objects.
"""
from __future__ import annotations

import threading

from iios.decision_governance.governance_exceptions import GovernanceNotFoundError


class GovernanceHistory:
    """Stores GovernanceResult objects with O(1) retrieval by result_id."""

    def __init__(self, max_size: int = 10_000) -> None:
        self._lock:    threading.RLock = threading.RLock()
        self._results: dict            = {}   # result_id → GovernanceResult (avoid circular import)
        self._max:     int             = max_size

    def store(self, result: object) -> None:
        with self._lock:
            rid = getattr(result, "result_id", None)
            if rid is None:
                return
            if len(self._results) >= self._max and rid not in self._results:
                # evict oldest (FIFO)
                oldest = next(iter(self._results))
                del self._results[oldest]
            self._results[rid] = result

    def get(self, result_id: str) -> object:
        with self._lock:
            r = self._results.get(result_id)
        if r is None:
            raise GovernanceNotFoundError(result_id)
        return r

    def all(self) -> list:
        with self._lock:
            return list(self._results.values())

    def recent(self, n: int = 10) -> list:
        with self._lock:
            items = list(self._results.values())
        items.sort(key=lambda r: getattr(r, "created_at", 0), reverse=True)
        return items[:n]

    def count(self) -> int:
        with self._lock:
            return len(self._results)
