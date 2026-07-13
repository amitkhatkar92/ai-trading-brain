"""iios/investment/strategy/core/strategy_history.py
Thread-safe per-strategy ring buffer of StrategySnapshot objects.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any

from iios.investment.strategy.strategy_constants import DEFAULT_SNAPSHOT_HISTORY
from iios.investment.strategy.core.strategy_snapshot import StrategySnapshot


class StrategyHistory:
    """
    Per-strategy ordered snapshot ring buffer.
    Each strategy maintains a bounded history of snapshots (default 200).
    """

    def __init__(self, max_per_strategy: int = DEFAULT_SNAPSHOT_HISTORY) -> None:
        self._lock              = threading.RLock()
        self._max_per_strategy  = max_per_strategy
        self._store:            dict[str, deque[StrategySnapshot]] = {}

    def add(self, strategy_id: str, snapshot: StrategySnapshot) -> None:
        with self._lock:
            buf = self._store.setdefault(
                strategy_id, deque(maxlen=self._max_per_strategy)
            )
            buf.append(snapshot)

    def get_latest(self, strategy_id: str) -> StrategySnapshot | None:
        with self._lock:
            buf = self._store.get(strategy_id)
            return buf[-1] if buf else None

    def get_recent(self, strategy_id: str, n: int = 10) -> list[StrategySnapshot]:
        with self._lock:
            buf = self._store.get(strategy_id)
            if not buf:
                return []
            items = list(buf)
            return items[-n:] if len(items) >= n else items

    def count(self, strategy_id: str) -> int:
        with self._lock:
            return len(self._store.get(strategy_id, []))

    def all_strategies(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())

    def total_snapshots(self) -> int:
        with self._lock:
            return sum(len(b) for b in self._store.values())

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "strategies":        len(self._store),
                "total_snapshots":   self.total_snapshots(),
                "max_per_strategy":  self._max_per_strategy,
            }
