"""iios/investment/market/trend/trend_acceleration.py
Computes acceleration (change in velocity) from consecutive impulse legs.
"""
from __future__ import annotations

from typing import List, Tuple

from iios.investment.market.trend.models import TrendLegMetrics


class TrendAccelerationAnalyzer:
    """
    Computes acceleration (change in velocity) from consecutive impulse legs.
    Acceleration > 0 = trend gaining speed.
    Acceleration < 0 = trend losing speed (deceleration).
    """

    def analyze(
        self,
        legs: List[TrendLegMetrics],
    ) -> Tuple[float, bool, bool]:
        """
        Returns (acceleration_value, is_accelerating, is_decelerating).
        """
        impulse_legs = [l for l in legs if l.is_impulse]
        if len(impulse_legs) < 2:
            return (0.0, False, False)

        latest = impulse_legs[-1]
        prev = impulse_legs[-2]

        acceleration = latest.velocity - prev.velocity

        if prev.velocity > 0:
            is_accelerating = acceleration > 0.05 * prev.velocity
            is_decelerating = acceleration < -0.10 * prev.velocity
        else:
            is_accelerating = acceleration > 0.0
            is_decelerating = acceleration < 0.0

        return (acceleration, is_accelerating, is_decelerating)
