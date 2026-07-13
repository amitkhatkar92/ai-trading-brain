"""iios/investment/strategy/evaluation/performance_history.py
Thread-safe ring buffer of PerformanceMetrics snapshots per strategy.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from iios.investment.strategy.evaluation.performance_metrics import PerformanceMetrics


@dataclass
class PerformanceSnapshot:
    strategy_id: str
    metrics: PerformanceMetrics
    recorded_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class PerformanceHistory:
    """Rolling window of PerformanceMetrics per strategy."""

    def __init__(self, max_per_strategy: int = 50) -> None:
        self._max = max_per_strategy
        self._store: Dict[str, Deque[PerformanceSnapshot]] = {}
        self._lock = threading.RLock()

    def record(self, strategy_id: str, metrics: PerformanceMetrics) -> None:
        with self._lock:
            if strategy_id not in self._store:
                self._store[strategy_id] = deque(maxlen=self._max)
            self._store[strategy_id].append(
                PerformanceSnapshot(strategy_id=strategy_id, metrics=metrics)
            )

    def latest(self, strategy_id: str) -> Optional[PerformanceMetrics]:
        with self._lock:
            buf = self._store.get(strategy_id)
            return buf[-1].metrics if buf else None

    def history(
        self, strategy_id: str, n: int = 10
    ) -> List[PerformanceSnapshot]:
        with self._lock:
            buf = self._store.get(strategy_id, deque())
            snaps = list(buf)
            return snaps[-n:] if len(snaps) > n else snaps

    def known_strategy_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def purge(self, strategy_id: str) -> None:
        with self._lock:
            self._store.pop(strategy_id, None)
