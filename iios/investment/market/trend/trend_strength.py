"""iios/investment/market/trend/trend_strength.py
Computes a normalized trend strength score from structure.
"""
from __future__ import annotations

from typing import ClassVar, Dict, List, TYPE_CHECKING

from iios.investment.market.trend.models import (
    TrendLegMetrics,
    ImpulseQuality,
)

if TYPE_CHECKING:
    from iios.investment.market.structure.models import TrendState


class TrendStrengthCalculator:
    """
    Computes a normalized trend strength score (0-100) from structure.
    No indicators — pure structure analysis.
    """

    _STRENGTH_SCORES: ClassVar[Dict[str, float]] = {
        "very_strong": 95.0,
        "strong":      80.0,
        "moderate":    60.0,
        "weak":        35.0,
        "very_weak":   15.0,
        "neutral":     50.0,
    }

    def calculate(
        self,
        trend_state: "TrendState",
        legs: List[TrendLegMetrics],
    ) -> float:
        """
        Returns strength score 0-100.
        """
        base = self._STRENGTH_SCORES.get(trend_state.strength.value, 50.0)

        confirmation_bonus = 5.0 if trend_state.confirmed else 0.0
        leg_bonus = min(15.0, trend_state.leg_count * 3.0)

        _quality_map = {
            ImpulseQuality.STRONG: 1.0,
            ImpulseQuality.MODERATE: 0.6,
            ImpulseQuality.WEAK: 0.3,
        }
        impulse_legs = [l for l in legs if l.is_impulse]
        if impulse_legs:
            avg_impulse_score = sum(
                _quality_map.get(l.impulse_quality, 0.6) for l in impulse_legs
            ) / len(impulse_legs)
        else:
            avg_impulse_score = 0.6
        impulse_contribution = avg_impulse_score * 20.0

        total = base + confirmation_bonus + leg_bonus + impulse_contribution
        return max(0.0, min(100.0, total))
