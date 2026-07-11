"""iios/investment/market/trend/trend_deceleration.py
Detects deceleration signals beyond simple velocity comparison.
"""
from __future__ import annotations

from typing import List, Tuple

from iios.investment.market.trend.models import (
    TrendLegMetrics,
    ImpulseQuality,
)
from iios.investment.market.trend.trend_acceleration import TrendAccelerationAnalyzer


class TrendDecelerationDetector:
    """
    Detects deceleration signals beyond simple velocity comparison.
    Multiple signals increase deceleration confidence.
    """

    def __init__(self) -> None:
        self._accel = TrendAccelerationAnalyzer()

    def detect(
        self,
        legs: List[TrendLegMetrics],
        trend_phase: str,
        correction_depth: float,
    ) -> Tuple[bool, float]:
        """
        Returns (is_decelerating, deceleration_confidence 0-1).
        """
        confidence = 0.0

        # Signal 1: acceleration < 0 (velocity declining)
        accel_val, _, is_decel_accel = self._accel.analyze(legs)
        if accel_val < 0:
            confidence += 0.30

        # Signal 2: trend_phase in exhaustion/correction
        if trend_phase in ("exhaustion", "correction"):
            confidence += 0.25

        # Signal 3: latest impulse quality == WEAK
        impulse_legs = [l for l in legs if l.is_impulse]
        if impulse_legs and impulse_legs[-1].impulse_quality == ImpulseQuality.WEAK:
            confidence += 0.20

        # Signal 4: correction_depth > 0.618
        if correction_depth > 0.618:
            confidence += 0.20

        # Signal 5: three consecutive leg heights shrinking
        if len(legs) >= 3:
            last3 = legs[-3:]
            if (last3[0].displacement > last3[1].displacement > last3[2].displacement):
                confidence += 0.15

        return (confidence >= 0.40, min(1.0, confidence))
