"""iios/investment/market/trend/trend_momentum.py
Orchestrates velocity + acceleration + deceleration into TrendMomentumState.
"""
from __future__ import annotations

from typing import List, Optional

from iios.investment.market.market_constants import TrendDirection
from iios.investment.market.trend.models import (
    TrendLegMetrics,
    TrendMomentumState,
    ImpulseQuality,
    CorrectionQuality,
)
from iios.investment.market.trend.trend_velocity import TrendVelocityCalculator
from iios.investment.market.trend.trend_acceleration import TrendAccelerationAnalyzer
from iios.investment.market.trend.trend_deceleration import TrendDecelerationDetector


class TrendMomentumAnalyzer:
    """
    Orchestrates velocity + acceleration + deceleration into TrendMomentumState.
    """

    def __init__(
        self,
        velocity_calc: Optional[TrendVelocityCalculator] = None,
        acceleration_analyzer: Optional[TrendAccelerationAnalyzer] = None,
        deceleration_detector: Optional[TrendDecelerationDetector] = None,
    ) -> None:
        self._velocity = velocity_calc or TrendVelocityCalculator()
        self._accel = acceleration_analyzer or TrendAccelerationAnalyzer()
        self._decel = deceleration_detector or TrendDecelerationDetector()

    def analyze(
        self,
        legs: List[TrendLegMetrics],
        direction: TrendDirection,
        trend_phase: str,
        correction_depth: float,
    ) -> TrendMomentumState:
        """
        Combines velocity, acceleration, deceleration into TrendMomentumState.
        """
        velocity = self._velocity.calculate_current(legs, direction)
        avg_velocity_unsigned = self._velocity.calculate_avg(legs, n=3)
        accel_val, is_accel, _ = self._accel.analyze(legs)
        is_decel_flag, _ = self._decel.detect(legs, trend_phase, correction_depth)

        # Latest impulse and correction quality
        impulse_legs = [l for l in legs if l.is_impulse]
        correction_legs = [l for l in legs if not l.is_impulse]
        latest_impulse_q = (
            impulse_legs[-1].impulse_quality if impulse_legs else ImpulseQuality.MODERATE
        )
        latest_correction_q = (
            correction_legs[-1].correction_quality if correction_legs else CorrectionQuality.NORMAL
        )

        # Momentum score
        score = _compute_momentum_score(
            velocity=velocity,
            avg_velocity=avg_velocity_unsigned,
            is_accelerating=is_accel,
            is_decelerating=is_decel_flag,
            impulse_quality=latest_impulse_q,
            correction_quality=latest_correction_q,
        )

        return TrendMomentumState(
            velocity=velocity,
            acceleration=accel_val,
            impulse_quality=latest_impulse_q,
            correction_quality=latest_correction_q,
            is_accelerating=is_accel,
            is_decelerating=is_decel_flag,
            momentum_score=score,
        )


def _compute_momentum_score(
    velocity: float,
    avg_velocity: float,
    is_accelerating: bool,
    is_decelerating: bool,
    impulse_quality: ImpulseQuality,
    correction_quality: CorrectionQuality,
) -> float:
    base = 50.0

    # Velocity factor: ±20
    if avg_velocity > 0:
        ratio = abs(velocity) / avg_velocity
        vf = max(-20.0, min(20.0, (ratio - 1.0) * 20.0))
    else:
        vf = 0.0
    base += vf

    # Acceleration factor
    if is_accelerating:
        base += 15.0
    if is_decelerating:
        base -= 20.0

    # Impulse quality factor
    if impulse_quality == ImpulseQuality.STRONG:
        base += 15.0
    elif impulse_quality == ImpulseQuality.WEAK:
        base -= 15.0

    # Correction quality factor
    if correction_quality == CorrectionQuality.SHALLOW:
        base += 10.0
    elif correction_quality == CorrectionQuality.DEEP:
        base -= 10.0
    elif correction_quality == CorrectionQuality.FAILED:
        base -= 20.0

    return max(0.0, min(100.0, base))
