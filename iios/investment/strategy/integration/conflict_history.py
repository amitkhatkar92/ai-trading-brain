"""iios/investment/strategy/integration/conflict_history.py
Thread-safe, append-only history of all conflicts.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.strategy.integration.integration_constants import (
    ConflictSeverity,
    ConflictType,
)
from iios.investment.strategy.integration.conflict_classifier import Conflict


class ConflictHistory:
    """Thread-safe rolling store of all Conflict records."""

    def __init__(self, max_size: int = 20_000) -> None:
        self._lock:  threading.RLock = threading.RLock()
        self._store: List[Conflict]  = []
        self._max    = max_size

    def record(self, conflict: Conflict) -> None:
        with self._lock:
            if len(self._store) >= self._max:
                self._store.pop(0)
            self._store.append(conflict)

    def record_all(self, conflicts: List[Conflict]) -> None:
        for c in conflicts:
            self.record(c)

    def for_strategy(self, strategy_id: str) -> List[Conflict]:
        with self._lock:
            return [c for c in self._store if c.strategy_id == strategy_id]

    def active(self, strategy_id: Optional[str] = None) -> List[Conflict]:
        with self._lock:
            results = [c for c in self._store if not c.is_resolved]
            if strategy_id:
                results = [c for c in results if c.strategy_id == strategy_id]
            return results

    def resolved(self, strategy_id: Optional[str] = None) -> List[Conflict]:
        with self._lock:
            results = [c for c in self._store if c.is_resolved]
            if strategy_id:
                results = [c for c in results if c.strategy_id == strategy_id]
            return results

    def by_severity(self, severity: ConflictSeverity) -> List[Conflict]:
        with self._lock:
            return [c for c in self._store if c.severity == severity]

    def by_type(self, conflict_type: ConflictType) -> List[Conflict]:
        with self._lock:
            return [c for c in self._store if c.conflict_type == conflict_type]

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def active_count(self, strategy_id: Optional[str] = None) -> int:
        return len(self.active(strategy_id))
