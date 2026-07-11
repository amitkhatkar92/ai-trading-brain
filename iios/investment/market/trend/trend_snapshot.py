"""iios/investment/market/trend/trend_snapshot.py
Stateless factory that assembles a TrendIntelligenceSnapshot from components.
"""
from __future__ import annotations

import time
from typing import Optional, TYPE_CHECKING

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.regime.models import RegimeType
from iios.investment.market.trend.models import (
    TrendStage,
    TrendQualityMetrics,
    TrendMomentumState,
    TrendScore,
    StrategyReadiness,
    TrendEventRecord,
    TrendTransitionRecord,
    TrendIntelligenceSnapshot,
)

if TYPE_CHECKING:
    from iios.investment.market.structure.models import MarketStructureSnapshot
    from iios.investment.market.regime.models import RegimeSnapshot


class TrendSnapshotBuilder:
    """
    Assembles a TrendIntelligenceSnapshot from all computed components.
    Stateless factory — all components injected.
    """

    def build(
        self,
        symbol: str,
        timeframe: str,
        structure: "MarketStructureSnapshot",
        regime: Optional["RegimeSnapshot"],
        stage: TrendStage,
        stage_confidence: float,
        quality: TrendQualityMetrics,
        momentum: TrendMomentumState,
        confidence: float,
        continuation_probability: float,
        failure_probability: float,
        reversal_probability: float,
        expected_remaining_legs: float,
        strategy_readiness: StrategyReadiness,
        score: TrendScore,
        last_event: Optional[TrendEventRecord] = None,
    ) -> TrendIntelligenceSnapshot:
        """Builds a complete snapshot. regime may be None (defaults to UNKNOWN)."""
        regime_type = regime.primary if regime is not None else RegimeType.UNKNOWN
        regime_aligned = _is_regime_aligned(
            structure.trend.direction, regime_type
        )

        return TrendIntelligenceSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            bar_index=structure.bar_index,
            timestamp=structure.timestamp,
            direction=structure.trend.direction,
            confirmed=structure.trend.confirmed,
            leg_count=structure.trend.leg_count,
            structure_phase=structure.structure_phase.value,
            trend_phase=structure.trend.phase.value,
            stage=stage,
            stage_confidence=stage_confidence,
            quality=quality,
            momentum=momentum,
            confidence=confidence,
            continuation_probability=continuation_probability,
            failure_probability=failure_probability,
            reversal_probability=reversal_probability,
            expected_remaining_legs=expected_remaining_legs,
            strategy_readiness=strategy_readiness,
            regime=regime_type,
            regime_aligned=regime_aligned,
            last_event=last_event,
            score=score,
        )


def _is_regime_aligned(direction: TrendDirection, regime: RegimeType) -> bool:
    if direction == TrendDirection.UP:
        return regime in (RegimeType.BULL, RegimeType.TRENDING)
    if direction == TrendDirection.DOWN:
        return regime == RegimeType.BEAR
    if direction == TrendDirection.SIDEWAYS:
        return regime in (RegimeType.SIDEWAYS, RegimeType.RANGING)
    return False
