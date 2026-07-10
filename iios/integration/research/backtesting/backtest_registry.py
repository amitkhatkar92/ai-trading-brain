"""backtest_registry.py — Thread-safe registry of Backtest entities."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.backtesting.backtest_constants import (
    BacktestStatus,
    DEFAULT_MAX_BACKTESTS,
)
from iios.integration.research.backtesting.backtest_exceptions import (
    BacktestAlreadyExistsError,
    BacktestCapacityError,
    BacktestNotFoundError,
)
from iios.integration.research.backtesting.core.backtest import Backtest


class BacktestRegistry:
    """
    Central in-memory store for all Backtest entities.

    Thread-safe via a single RLock.  Intended as a singleton managed by
    the BacktestingEngine.
    """

    def __init__(self, max_backtests: int = DEFAULT_MAX_BACKTESTS) -> None:
        self._store:    dict[str, Backtest] = {}
        self._max       = max_backtests
        self._lock      = threading.RLock()
        self._total_registered = 0

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def register(self, backtest: Backtest) -> None:
        with self._lock:
            if backtest.backtest_id in self._store:
                raise BacktestAlreadyExistsError(
                    f"Backtest {backtest.backtest_id!r} already exists"
                )
            if len(self._store) >= self._max:
                raise BacktestCapacityError(
                    f"Registry capacity ({self._max}) reached"
                )
            self._store[backtest.backtest_id] = backtest
            self._total_registered += 1

    def get(self, backtest_id: str) -> Backtest:
        with self._lock:
            if backtest_id not in self._store:
                raise BacktestNotFoundError(f"Backtest {backtest_id!r} not found")
            return self._store[backtest_id]

    def update(self, backtest: Backtest) -> None:
        with self._lock:
            if backtest.backtest_id not in self._store:
                raise BacktestNotFoundError(f"Backtest {backtest.backtest_id!r} not found")
            self._store[backtest.backtest_id] = backtest

    def remove(self, backtest_id: str) -> None:
        with self._lock:
            if backtest_id not in self._store:
                raise BacktestNotFoundError(f"Backtest {backtest_id!r} not found")
            del self._store[backtest_id]

    def has(self, backtest_id: str) -> bool:
        with self._lock:
            return backtest_id in self._store

    # ── Queries ───────────────────────────────────────────────────────────────

    def all_backtests(self) -> list[Backtest]:
        with self._lock:
            return list(self._store.values())

    def find_by_status(self, status: BacktestStatus) -> list[Backtest]:
        with self._lock:
            return [b for b in self._store.values() if b.status == status]

    def find_by_strategy(self, strategy_id: str) -> list[Backtest]:
        with self._lock:
            return [b for b in self._store.values() if b.strategy_id == strategy_id]

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status = {}
            for b in self._store.values():
                by_status[b.status.value] = by_status.get(b.status.value, 0) + 1
            return {
                "total":            len(self._store),
                "total_registered": self._total_registered,
                "capacity":         self._max,
                "by_status":        by_status,
            }
