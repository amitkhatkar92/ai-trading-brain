"""iios/investment/market/trend/trend_strategy_mapper.py
Facade answering strategy readiness questions for a given trend state.
"""
from __future__ import annotations

from typing import Optional, Tuple

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.trend.models import (
    TrendStage,
    TrendQualityMetrics,
    TrendMomentumState,
    StrategyReadiness,
)
from iios.investment.market.trend.trend_permissions import (
    STAGE_PERMISSIONS,
    TrendStrategyType,
    best_approach as _best_approach_fn,
)
from iios.investment.market.trend.trend_constraints import TrendConstraintEngine


class TrendStrategyMapper:
    """
    Facade answering strategy readiness questions for a given trend state.
    Combines STAGE_PERMISSIONS with TrendConstraintEngine.
    """

    def __init__(
        self,
        constraints: Optional[TrendConstraintEngine] = None,
    ) -> None:
        self._constraints = constraints or TrendConstraintEngine()

    def readiness(
        self,
        stage: TrendStage,
        direction: TrendDirection,
        quality: TrendQualityMetrics,
        momentum: TrendMomentumState,
        confidence: float,
    ) -> StrategyReadiness:
        """
        Build StrategyReadiness using STAGE_PERMISSIONS as base suitability,
        then adjust for direction and momentum.
        """
        base = dict(STAGE_PERMISSIONS.get(stage, {}))

        # Ensure all strategy types present
        for st in TrendStrategyType.ALL:
            base.setdefault(st, 0.0)

        # Direction adjustment: SIDEWAYS reduces momentum/breakout
        if direction == TrendDirection.SIDEWAYS:
            base[TrendStrategyType.MOMENTUM] = max(0.0, base[TrendStrategyType.MOMENTUM] - 0.20)
            base[TrendStrategyType.BREAKOUT] = max(0.0, base[TrendStrategyType.BREAKOUT] - 0.20)

        # Momentum adjustments
        if momentum.is_decelerating:
            base[TrendStrategyType.MOMENTUM] = max(0.0, base[TrendStrategyType.MOMENTUM] - 0.15)
            base[TrendStrategyType.BREAKOUT] = max(0.0, base[TrendStrategyType.BREAKOUT] - 0.15)
            base[TrendStrategyType.MEAN_REVERSION] = min(1.0, base[TrendStrategyType.MEAN_REVERSION] + 0.15)

        if momentum.is_accelerating:
            base[TrendStrategyType.MOMENTUM] = min(1.0, base[TrendStrategyType.MOMENTUM] + 0.10)
            base[TrendStrategyType.BREAKOUT] = min(1.0, base[TrendStrategyType.BREAKOUT] + 0.10)
            base[TrendStrategyType.MEAN_REVERSION] = max(0.0, base[TrendStrategyType.MEAN_REVERSION] - 0.10)

        # Determine best approach
        best = max(base, key=lambda k: base[k])

        # Build notes
        momentum_state = "accelerating" if momentum.is_accelerating else (
            "decelerating" if momentum.is_decelerating else "neutral"
        )
        notes = (
            f"Stage={stage.value}, direction={direction.value}, momentum={momentum_state}"
        )

        return StrategyReadiness(
            momentum_suitability=base[TrendStrategyType.MOMENTUM],
            breakout_suitability=base[TrendStrategyType.BREAKOUT],
            retest_suitability=base[TrendStrategyType.RETEST],
            mean_reversion_suitability=base[TrendStrategyType.MEAN_REVERSION],
            swing_trading_suitability=base[TrendStrategyType.SWING],
            position_trading_suitability=base[TrendStrategyType.POSITION],
            best_approach=best,
            notes=notes,
        )

    def is_suitable(self, strategy_type: str, stage: TrendStage) -> bool:
        """Returns True if suitability >= 0.50."""
        perms = STAGE_PERMISSIONS.get(stage, {})
        return perms.get(strategy_type, 0.0) >= 0.50

    def check_trade(
        self,
        strategy_type: str,
        stage: TrendStage,
        direction: str,
        confidence: float,
        quality_overall: float,
        trend_confirmed: bool,
    ) -> Tuple[bool, str]:
        """Full gate: permission + constraint check."""
        # First check permission suitability
        perms = STAGE_PERMISSIONS.get(stage, {})
        suitability = perms.get(strategy_type, 0.0)
        if suitability < 0.10:
            return (False, f"{strategy_type} not permitted in {stage.value} stage")

        # Then check constraints
        return self._constraints.check(
            strategy_type=strategy_type,
            stage=stage,
            direction=direction,
            confidence=confidence,
            quality_overall=quality_overall,
            trend_confirmed=trend_confirmed,
        )
