"""iios/investment/market/liquidity/participation_engine.py
Stateful participation analysis engine.
"""
from __future__ import annotations

import logging
from typing import List, Optional, TYPE_CHECKING

from iios.investment.market.liquidity.models import VolumeBar, ParticipationSnapshot
from iios.investment.market.liquidity.participation_score import ParticipationScoreCalculator
from iios.investment.market.liquidity.participation_tracker import ParticipationTracker

if TYPE_CHECKING:
    from iios.investment.market.structure.models import Bar

logger = logging.getLogger(__name__)


class ParticipationEngine:
    """Stateful participation analysis engine."""

    def __init__(
        self,
        window: int = 20,
        scorer: Optional[ParticipationScoreCalculator] = None,
        tracker: Optional[ParticipationTracker] = None,
    ) -> None:
        self._window = window
        self._scorer = scorer or ParticipationScoreCalculator()
        self._tracker = tracker or ParticipationTracker(window=window)
        self._current: Optional[ParticipationSnapshot] = None

    def update(self, vbar: VolumeBar, relative_volume: float) -> ParticipationSnapshot:
        snap = self._tracker.update(vbar, relative_volume)
        self._current = snap
        return snap

    def initialize(
        self, bars: List["Bar"], vbars: List[VolumeBar]
    ) -> ParticipationSnapshot:
        """Bulk-initialize from historical bars."""
        last: Optional[ParticipationSnapshot] = None
        for vbar in vbars:
            last = self.update(vbar, vbar.relative_volume)
        if last is None:
            raise ValueError("initialize() requires at least one bar")
        return last

    def current(self) -> Optional[ParticipationSnapshot]:
        return self._current
