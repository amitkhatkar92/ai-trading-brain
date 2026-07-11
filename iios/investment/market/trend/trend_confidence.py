"""iios/investment/market/trend/trend_confidence.py
Calculates trend confidence and probability estimates.
"""
from __future__ import annotations

from iios.investment.market.trend.models import (
    TrendStage,
    TrendQualityMetrics,
    TrendMomentumState,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from iios.investment.market.structure.models import TrendState


class TrendConfidenceCalculator:
    """
    Calculates trend confidence and probability estimates.
    Result is float in [0.05, 0.97].
    """

    def calculate(
        self,
        trend_state: "TrendState",
        stage: TrendStage,
        quality: TrendQualityMetrics,
        momentum: TrendMomentumState,
        regime_aligned: bool,
        structure_quality: float,
    ) -> float:
        """
        Weighted composite confidence score.
        """
        # Factor 1: Structure quality (weight 0.30)
        f1 = (structure_quality / 100.0) * 0.30

        # Factor 2: Confirmation + legs (weight 0.25)
        leg_count = trend_state.leg_count
        confirmed = trend_state.confirmed
        if confirmed and leg_count >= 3:
            legs_score = 0.9
        elif confirmed and leg_count == 2:
            legs_score = 0.7
        elif confirmed and leg_count == 1:
            legs_score = 0.5
        else:
            legs_score = 0.3
        f2 = legs_score * 0.25

        # Factor 3: Regime alignment (weight 0.20)
        f3 = (0.9 if regime_aligned else 0.5) * 0.20

        # Factor 4: Stage appropriateness (weight 0.15)
        _stage_scores = {
            TrendStage.ESTABLISHED: 0.9,
            TrendStage.DEVELOPING: 0.9,
            TrendStage.MATURE: 0.7,
            TrendStage.EMERGING: 0.6,
            TrendStage.EXHAUSTING: 0.4,
            TrendStage.FAILING: 0.4,
            TrendStage.REVERSING: 0.2,
            TrendStage.COMPLETED: 0.2,
        }
        f4 = _stage_scores.get(stage, 0.5) * 0.15

        # Factor 5: Momentum (weight 0.10)
        if momentum.is_accelerating:
            momentum_score = 0.9
        elif momentum.is_decelerating:
            momentum_score = 0.4
        else:
            momentum_score = 0.65
        f5 = momentum_score * 0.10

        raw = f1 + f2 + f3 + f4 + f5
        return max(0.05, min(0.97, raw))

    def continuation_probability(
        self,
        stage: TrendStage,
        quality: TrendQualityMetrics,
        momentum: TrendMomentumState,
        regime_aligned: bool,
    ) -> float:
        _base = {
            TrendStage.EMERGING:    0.50,
            TrendStage.DEVELOPING:  0.60,
            TrendStage.ESTABLISHED: 0.72,
            TrendStage.MATURE:      0.55,
            TrendStage.EXHAUSTING:  0.35,
            TrendStage.FAILING:     0.20,
            TrendStage.REVERSING:   0.10,
            TrendStage.COMPLETED:   0.05,
        }
        base = _base.get(stage, 0.40)

        adj = 0.0
        if regime_aligned and stage in (TrendStage.ESTABLISHED, TrendStage.MATURE):
            adj += 0.08
        if momentum.is_accelerating:
            adj += 0.05
        if momentum.is_decelerating:
            adj -= 0.10
        adj += (quality.overall / 100.0 - 0.5) * 0.10

        return max(0.05, min(0.92, base + adj))

    def failure_probability(
        self,
        stage: TrendStage,
        momentum: TrendMomentumState,
    ) -> float:
        _base = {
            TrendStage.EMERGING:    0.40,
            TrendStage.DEVELOPING:  0.30,
            TrendStage.ESTABLISHED: 0.15,
            TrendStage.MATURE:      0.30,
            TrendStage.EXHAUSTING:  0.55,
            TrendStage.FAILING:     0.75,
            TrendStage.REVERSING:   0.85,
            TrendStage.COMPLETED:   0.95,
        }
        base = _base.get(stage, 0.50)

        if momentum.is_decelerating and stage in (TrendStage.ESTABLISHED, TrendStage.MATURE):
            base += 0.10
        if momentum.is_accelerating and stage in (TrendStage.ESTABLISHED, TrendStage.MATURE):
            base -= 0.08

        return max(0.02, min(0.98, base))

    def reversal_probability(
        self,
        trend_phase: str,
        stage: TrendStage,
        correction_depth: float,
    ) -> float:
        _phase_base = {
            "reversal":      0.80,
            "exhaustion":    0.45,
            "correction":    0.20,
            "impulse":       0.08,
            "continuation":  0.08,
            "acceleration":  0.08,
        }
        base = _phase_base.get(trend_phase, 0.15)

        if stage == TrendStage.REVERSING:
            base += 0.10
        if correction_depth > 0.618:
            base += 0.05

        return max(0.02, min(0.95, base))

    def expected_remaining_legs(
        self,
        stage: TrendStage,
        leg_count: int,
        quality: TrendQualityMetrics,
    ) -> float:
        _base = {
            TrendStage.EMERGING:    6.0,
            TrendStage.DEVELOPING:  4.0,
            TrendStage.ESTABLISHED: 3.0,
            TrendStage.MATURE:      2.0,
            TrendStage.EXHAUSTING:  1.0,
            TrendStage.FAILING:     0.5,
            TrendStage.REVERSING:   0.2,
            TrendStage.COMPLETED:   0.0,
        }
        base = _base.get(stage, 1.0)
        factor = 0.7 + (quality.overall / 100.0) * 0.6
        return max(0.0, base * factor)
