"""iios/investment/market/trend/trend_velocity.py
Computes trend velocity (displacement per bar) from leg metrics.
"""
from __future__ import annotations

from typing import List

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.trend.models import TrendLegMetrics


class TrendVelocityCalculator:
    """
    Computes trend velocity (displacement per bar) from leg metrics.
    Signed: positive = bullish velocity, negative = bearish velocity.
    """

    def calculate_current(
        self,
        legs: List[TrendLegMetrics],
        direction: TrendDirection,
    ) -> float:
        """
        Returns signed velocity of the latest impulse leg.
        + for UP direction, - for DOWN.
        0.0 if no legs available.
        """
        impulse_legs = [l for l in legs if l.is_impulse]
        if not impulse_legs:
            if not legs:
                return 0.0
            # Fall back to latest leg
            latest = legs[-1]
        else:
            latest = impulse_legs[-1]

        sign = -1.0 if direction == TrendDirection.DOWN else 1.0
        return sign * latest.velocity

    def calculate_avg(
        self,
        legs: List[TrendLegMetrics],
        n: int = 3,
    ) -> float:
        """Average velocity of last n impulse legs (unsigned)."""
        impulse_legs = [l for l in legs if l.is_impulse]
        recent = impulse_legs[-n:]
        if not recent:
            return 0.0
        return sum(l.velocity for l in recent) / len(recent)

    def calculate_signed_avg(
        self,
        legs: List[TrendLegMetrics],
        direction: TrendDirection,
        n: int = 3,
    ) -> float:
        """Signed average velocity."""
        avg = self.calculate_avg(legs, n)
        sign = -1.0 if direction == TrendDirection.DOWN else 1.0
        return sign * avg
