"""iios/investment/market/structure/structure_history.py
Rolling history of MarketStructureSnapshot objects with query APIs.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import Deque, List, Optional

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.structure.models import (
    MarketStructureSnapshot,
    TrendTransition,
)

logger = logging.getLogger(__name__)


class StructureHistory:
    """Bounded rolling history of structure snapshots."""

    def __init__(self, max_snapshots: int = 500) -> None:
        self._max = max_snapshots
        self._snapshots: Deque[MarketStructureSnapshot] = deque(maxlen=max_snapshots)

    def record(self, snapshot: MarketStructureSnapshot) -> None:
        self._snapshots.append(snapshot)

    def get_latest(self) -> Optional[MarketStructureSnapshot]:
        if not self._snapshots:
            return None
        return self._snapshots[-1]

    def get_at(self, bar_index: int) -> Optional[MarketStructureSnapshot]:
        for snap in reversed(self._snapshots):
            if snap.bar_index == bar_index:
                return snap
        return None

    def get_range(
        self, from_idx: int, to_idx: int
    ) -> List[MarketStructureSnapshot]:
        return [
            s for s in self._snapshots if from_idx <= s.bar_index <= to_idx
        ]

    def trend_was(self, direction: TrendDirection, bars_ago: int) -> bool:
        """True if the trend `bars_ago` snapshots back matched direction."""
        if len(self._snapshots) <= bars_ago:
            return False
        snap = list(self._snapshots)[-(bars_ago + 1)]
        return snap.trend.direction == direction

    def count(self) -> int:
        return len(self._snapshots)

    def transitions_since(self, bar_index: int) -> List[TrendTransition]:
        """Return all trend transitions recorded after bar_index."""
        result: List[TrendTransition] = []
        for snap in self._snapshots:
            if snap.bar_index >= bar_index and snap.last_transition is not None:
                result.append(snap.last_transition)
        # Deduplicate by trigger_index
        seen: set = set()
        deduped: List[TrendTransition] = []
        for t in result:
            if t.trigger_index not in seen:
                seen.add(t.trigger_index)
                deduped.append(t)
        return deduped
