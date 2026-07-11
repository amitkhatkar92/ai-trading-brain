"""iios/investment/market/trend/trend_history.py
Thread-safe ring buffer of TrendIntelligenceSnapshot objects.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional

from iios.investment.market.trend.models import (
    TrendStage,
    TrendIntelligenceSnapshot,
    TrendTransitionRecord,
)


class TrendHistory:
    """Thread-safe ring buffer of TrendIntelligenceSnapshot objects."""

    def __init__(self, max_size: int = 500) -> None:
        self._max_size = max_size
        self._lock = threading.RLock()
        self._snapshots: deque[TrendIntelligenceSnapshot] = deque(maxlen=max_size)
        self._transitions: List[TrendTransitionRecord] = []

    def record(self, snap: TrendIntelligenceSnapshot) -> None:
        with self._lock:
            self._snapshots.append(snap)

    def recent(self, n: int = 20) -> List[TrendIntelligenceSnapshot]:
        """Last n snapshots, most recent last."""
        with self._lock:
            snaps = list(self._snapshots)
        return snaps[-n:]

    def get_by_stage(self, stage: TrendStage) -> List[TrendIntelligenceSnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.stage == stage]

    def get_transitions(self) -> List[TrendTransitionRecord]:
        with self._lock:
            return list(self._transitions)

    def record_transition(self, t: TrendTransitionRecord) -> None:
        with self._lock:
            self._transitions.append(t)

    def count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    def last(self) -> Optional[TrendIntelligenceSnapshot]:
        with self._lock:
            if not self._snapshots:
                return None
            return self._snapshots[-1]
