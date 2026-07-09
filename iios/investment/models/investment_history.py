"""iios/investment/models/investment_history.py
Thread-safe in-memory store for InvestmentResult objects.
"""
from __future__ import annotations

import threading

from iios.investment.investment_constants import MAX_HISTORY_SIZE
from iios.investment.investment_exceptions import InvestmentNotFoundError


class InvestmentHistory:
    """FIFO history store for InvestmentResults."""

    def __init__(self, max_size: int = MAX_HISTORY_SIZE) -> None:
        self._lock:    threading.RLock = threading.RLock()
        self._results: dict            = {}   # result_id → InvestmentResult
        self._order:   list[str]       = []   # insertion order for eviction
        self._max:     int             = max_size

    def store(self, result: object) -> None:
        with self._lock:
            rid = getattr(result, "result_id", None)
            if rid is None:
                return
            if rid in self._results:
                return  # idempotent
            if len(self._results) >= self._max:
                oldest = self._order.pop(0)
                del self._results[oldest]
            self._results[rid] = result
            self._order.append(rid)

    def get(self, result_id: str) -> object:
        with self._lock:
            r = self._results.get(result_id)
        if r is None:
            raise InvestmentNotFoundError(result_id)
        return r

    def by_request(self, request_id: str) -> list:
        with self._lock:
            return [
                r for r in self._results.values()
                if getattr(r, "request_id", None) == request_id
            ]

    def by_session(self, session_id: str) -> list:
        with self._lock:
            return [
                r for r in self._results.values()
                if getattr(r, "session_id", None) == session_id
            ]

    def recent(self, n: int = 10) -> list:
        with self._lock:
            ordered = [self._results[rid] for rid in reversed(self._order) if rid in self._results]
        return ordered[:n]

    def count(self) -> int:
        with self._lock:
            return len(self._results)
