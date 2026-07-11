"""iios/investment/market/trend/trend_state.py
Thread-safe mutable state container for per-symbol trend intelligence.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.trend.models import (
    TrendStage,
    TrendIntelligenceSnapshot,
)

# Import structure's TrendState under an alias to avoid name collision
from iios.investment.market.structure.models import TrendState as StructureTrendState


class TrendIntelligenceState:
    """Thread-safe per-symbol trend intelligence state."""

    def __init__(self, symbol: str, timeframe: str = "1d") -> None:
        self._symbol = symbol
        self._timeframe = timeframe
        self._lock = threading.RLock()
        self._current: Optional[TrendIntelligenceSnapshot] = None
        self._stage_entry_bar: int = 0

    def update(self, snap: TrendIntelligenceSnapshot) -> bool:
        """Thread-safe update. Returns True if stage changed."""
        with self._lock:
            stage_changed = (
                self._current is None or self._current.stage != snap.stage
            )
            if stage_changed:
                self._stage_entry_bar = snap.bar_index
            self._current = snap
            return stage_changed

    def current(self) -> Optional[TrendIntelligenceSnapshot]:
        with self._lock:
            return self._current

    def current_stage(self) -> TrendStage:
        with self._lock:
            if self._current is None:
                return TrendStage.EMERGING
            return self._current.stage

    def current_direction(self) -> TrendDirection:
        with self._lock:
            if self._current is None:
                return TrendDirection.UNDEFINED
            return self._current.direction

    def bars_in_stage(self) -> int:
        with self._lock:
            if self._current is None:
                return 0
            return max(0, self._current.bar_index - self._stage_entry_bar)

    def reset(self) -> None:
        with self._lock:
            self._current = None
            self._stage_entry_bar = 0

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "symbol": self._symbol,
                "timeframe": self._timeframe,
                "stage": self.current_stage().value,
                "direction": self.current_direction().value,
                "bars_in_stage": self.bars_in_stage(),
                "snapshot": self._current.to_dict() if self._current else None,
            }
