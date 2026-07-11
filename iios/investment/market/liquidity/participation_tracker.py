"""iios/investment/market/liquidity/participation_tracker.py
Rolling participation tracker over a window of VolumeBar objects.
"""
from __future__ import annotations

import logging
from collections import deque
from typing import List, Optional

from iios.investment.market.liquidity.models import (
    VolumeBar, ParticipationSnapshot, ParticipationBias,
)
from iios.investment.market.liquidity.participation_score import ParticipationScoreCalculator

logger = logging.getLogger(__name__)


class ParticipationTracker:
    """
    Rolling participation tracker over a window of VolumeBar objects.
    Maintains history for trend analysis.
    """

    def __init__(self, window: int = 20) -> None:
        self._window = window
        self._scorer = ParticipationScoreCalculator()
        self._snapshots: deque[ParticipationSnapshot] = deque(maxlen=window)

    def update(self, vbar: VolumeBar, relative_volume: float) -> ParticipationSnapshot:
        (
            buying_participation,
            selling_participation,
            institutional_est,
            retail_est,
            bias,
            score,
        ) = self._scorer.calculate(vbar, relative_volume)

        confidence = min(1.0, relative_volume / 1.5) * 0.7 + 0.3

        snap = ParticipationSnapshot(
            buying_participation=buying_participation,
            selling_participation=selling_participation,
            institutional_participation=institutional_est,
            retail_participation=retail_est,
            participation_balance=buying_participation - selling_participation,
            participation_bias=bias,
            participation_confidence=confidence,
            participation_score=score,
        )
        self._snapshots.append(snap)
        return snap

    def avg_buying_participation(self, n: int = 10) -> float:
        snaps = list(self._snapshots)[-n:]
        if not snaps:
            return 0.5
        return sum(s.buying_participation for s in snaps) / len(snaps)

    def avg_selling_participation(self, n: int = 10) -> float:
        snaps = list(self._snapshots)[-n:]
        if not snaps:
            return 0.5
        return sum(s.selling_participation for s in snaps) / len(snaps)

    def bias_streak(self) -> int:
        """Consecutive bars with same bias direction (+ for buy, - for sell)."""
        snaps = list(self._snapshots)
        if not snaps:
            return 0
        last = snaps[-1]
        is_buy = last.participation_balance > 0
        streak = 0
        for s in reversed(snaps):
            if is_buy and s.participation_balance > 0:
                streak += 1
            elif not is_buy and s.participation_balance < 0:
                streak -= 1
            else:
                break
        return streak

    def count(self) -> int:
        return len(self._snapshots)
