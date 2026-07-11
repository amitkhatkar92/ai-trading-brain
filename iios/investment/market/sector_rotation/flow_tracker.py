"""iios/investment/market/sector_rotation/flow_tracker.py
Maintains a rolling flow history for a single sector.
"""
from __future__ import annotations

from collections import deque
from typing import List, Optional

from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    FlowType,
    SecurityData,
)
from iios.investment.market.sector_rotation.flow_profile import build_flow_profile


class FlowTracker:
    """Stateful flow tracker for one sector.  Exposes rolling flow history."""

    def __init__(self, sector: str, window: int = 60) -> None:
        self._sector  = sector
        self._window  = window
        self._history: deque[CapitalFlowProfile] = deque(maxlen=window)
        self._current: Optional[CapitalFlowProfile] = None

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def sector(self) -> str:
        return self._sector

    @property
    def current(self) -> Optional[CapitalFlowProfile]:
        return self._current

    def update(
        self, securities: List[SecurityData], bar_index: int
    ) -> CapitalFlowProfile:
        profile = build_flow_profile(self._sector, securities, bar_index)
        self._history.append(profile)
        self._current = profile
        return profile

    def rolling_net_signal(self, n: int = 5) -> float:
        """Average net_flow_signal over last n bars."""
        recent = list(self._history)[-n:]
        if not recent:
            return 0.0
        return sum(p.net_flow_signal for p in recent) / len(recent)

    def dominant_flow_type(self, n: int = 5) -> FlowType:
        """Most common FlowType over last n bars."""
        recent = list(self._history)[-n:]
        if not recent:
            return FlowType.NEUTRAL
        counts: dict = {}
        for p in recent:
            counts[p.flow_type] = counts.get(p.flow_type, 0) + 1
        return max(counts, key=counts.__getitem__)

    def history_length(self) -> int:
        return len(self._history)
