"""iios/investment/strategy/integration/aggregation_history.py
Append-only history of all IntelligenceUpdates and state snapshots.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from iios.investment.strategy.integration.integration_constants import IntelligenceSource
from iios.investment.strategy.integration.aggregation_state import IntelligenceUpdate


class AggregationHistory:
    """
    Thread-safe, rolling history of IntelligenceUpdates across all strategies.
    Default ring size: 50 000 updates.
    """

    def __init__(self, max_size: int = 50_000) -> None:
        self._lock:    threading.RLock = threading.RLock()
        self._store:   List[IntelligenceUpdate] = []
        self._max      = max_size
        self._total:   int = 0   # cumulative count even after eviction

    def record(self, update: IntelligenceUpdate) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                self._store.pop(0)
            self._store.append(update)
            self._total += 1

    def record_all(self, updates: List[IntelligenceUpdate]) -> None:
        for u in updates:
            self.record(u)

    def for_strategy(self, strategy_id: str) -> List[IntelligenceUpdate]:
        with self._lock:
            return [u for u in self._store if u.strategy_id == strategy_id]

    def for_source(self, source: IntelligenceSource) -> List[IntelligenceUpdate]:
        with self._lock:
            return [u for u in self._store if u.source == source]

    def recent(self, n: int = 100) -> List[IntelligenceUpdate]:
        with self._lock:
            return list(self._store[-n:])

    def since(self, ts: datetime) -> List[IntelligenceUpdate]:
        with self._lock:
            return [u for u in self._store if u.timestamp >= ts]

    def total_recorded(self) -> int:
        with self._lock:
            return self._total

    def current_size(self) -> int:
        with self._lock:
            return len(self._store)
