"""iios/execution/risk/integration/execution_risk_history.py
==================================================
IntegrationHistory — bounded, thread-safe history of
ExecutionRiskResponse objects.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional

from .constants import DEFAULT_MAX_HISTORY


class IntegrationHistory:
    """
    Bounded deque-backed store of ExecutionRiskResponse objects.

    Thread-safe via an internal RLock.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._max  = max(1, max_size)
        self._lock = threading.RLock()
        self._data: deque = deque(maxlen=self._max)

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, response) -> None:
        with self._lock:
            self._data.append(response)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    # ── Read ──────────────────────────────────────────────────────────────────

    def all(self) -> List:
        with self._lock:
            return list(self._data)

    def latest(self, n: int = 10) -> List:
        """Return the *n* most recent responses (newest last)."""
        with self._lock:
            items = list(self._data)
            return items[-n:] if n < len(items) else items

    def by_execution_id(self, execution_id: str) -> List:
        with self._lock:
            return [r for r in self._data if r.execution_id == execution_id]

    def by_order_id(self, order_id: str) -> List:
        with self._lock:
            return [r for r in self._data if r.order_id == order_id]

    def by_portfolio_id(self, portfolio_id: str) -> List:
        with self._lock:
            return [r for r in self._data if r.portfolio_id == portfolio_id]

    def by_strategy_id(self, strategy_id: str) -> List:
        with self._lock:
            return [r for r in self._data if r.strategy_id == strategy_id]

    def blocked_only(self) -> List:
        """Return responses where the evaluation was blocked."""
        with self._lock:
            return [r for r in self._data if r.is_blocked]

    def approved_only(self) -> List:
        """Return responses where the evaluation was approved."""
        with self._lock:
            return [r for r in self._data if r.approved]

    def emergencies(self) -> List:
        """Return responses that triggered an emergency stop."""
        with self._lock:
            return [r for r in self._data if r.is_emergency]

    # ── Metrics ───────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._data)

    @property
    def max_size(self) -> int:
        return self._max
