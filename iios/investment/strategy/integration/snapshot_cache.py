"""iios/investment/strategy/integration/snapshot_cache.py
Thread-safe StrategySnapshot cache with version-based invalidation.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from iios.investment.strategy.integration.strategy_snapshot import StrategySnapshot


class SnapshotCache:
    """Thread-safe Dict[strategy_id → latest StrategySnapshot]."""

    def __init__(self) -> None:
        self._lock:  threading.RLock             = threading.RLock()
        self._cache: Dict[str, StrategySnapshot] = {}

    def set(self, snapshot: StrategySnapshot) -> None:
        with self._lock:
            self._cache[snapshot.strategy_id] = snapshot

    def get(self, strategy_id: str) -> Optional[StrategySnapshot]:
        with self._lock:
            return self._cache.get(strategy_id)

    def invalidate(self, strategy_id: str) -> None:
        with self._lock:
            self._cache.pop(strategy_id, None)

    def all(self) -> List[StrategySnapshot]:
        with self._lock:
            return list(self._cache.values())

    def known_strategies(self) -> List[str]:
        with self._lock:
            return list(self._cache.keys())

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
