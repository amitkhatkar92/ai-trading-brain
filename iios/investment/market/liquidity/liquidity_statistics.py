"""iios/investment/market/liquidity/liquidity_statistics.py
Accumulates aggregate statistics over engine lifetime.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from iios.investment.market.liquidity.models import LiquidityEventType

if TYPE_CHECKING:
    from iios.investment.market.liquidity.models import VolumeLiquiditySnapshot

logger = logging.getLogger(__name__)


@dataclass
class VolumeLiquidityStats:
    total_bars: int
    avg_relative_volume: float
    avg_liquidity_score: float
    avg_execution_readiness: float
    volume_spike_count: int
    climax_count: int
    absorption_count: int
    dry_up_count: int
    avg_participation_score: float
    shock_count: int


class LiquidityStatistics:
    """Accumulates aggregate statistics over engine lifetime."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._total_bars: int = 0
        self._sum_rel_volume: float = 0.0
        self._sum_liquidity_score: float = 0.0
        self._sum_execution_readiness: float = 0.0
        self._sum_participation_score: float = 0.0
        self._volume_spike_count: int = 0
        self._climax_count: int = 0
        self._absorption_count: int = 0
        self._dry_up_count: int = 0
        self._shock_count: int = 0

    def record(self, snap: "VolumeLiquiditySnapshot") -> None:
        self._total_bars += 1
        self._sum_rel_volume += snap.volume_bar.relative_volume
        self._sum_liquidity_score += snap.liquidity_score
        self._sum_execution_readiness += snap.execution_readiness
        self._sum_participation_score += snap.participation.participation_score

        for event in snap.active_events:
            if event.event_type == LiquidityEventType.VOLUME_SPIKE:
                self._volume_spike_count += 1
            elif event.event_type in (
                LiquidityEventType.BUYING_CLIMAX,
                LiquidityEventType.SELLING_CLIMAX,
            ):
                self._climax_count += 1
            elif event.event_type == LiquidityEventType.ABSORPTION_DETECTED:
                self._absorption_count += 1
            elif event.event_type == LiquidityEventType.DRY_UP:
                self._dry_up_count += 1
            elif event.event_type == LiquidityEventType.SHOCK:
                self._shock_count += 1

    def stats(self) -> VolumeLiquidityStats:
        n = max(self._total_bars, 1)
        return VolumeLiquidityStats(
            total_bars=self._total_bars,
            avg_relative_volume=self._sum_rel_volume / n,
            avg_liquidity_score=self._sum_liquidity_score / n,
            avg_execution_readiness=self._sum_execution_readiness / n,
            volume_spike_count=self._volume_spike_count,
            climax_count=self._climax_count,
            absorption_count=self._absorption_count,
            dry_up_count=self._dry_up_count,
            avg_participation_score=self._sum_participation_score / n,
            shock_count=self._shock_count,
        )

    def total_bars(self) -> int:
        return self._total_bars
