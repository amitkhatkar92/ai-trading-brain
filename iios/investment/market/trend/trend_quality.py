"""iios/investment/market/trend/trend_quality.py
Computes TrendQualityMetrics from leg metrics, structure quality, and regime.
"""
from __future__ import annotations

import math
from typing import List

from iios.investment.market.trend.models import (
    TrendLegMetrics,
    TrendQualityMetrics,
    CorrectionQuality,
)


class TrendQualityAnalyzer:
    """
    Computes TrendQualityMetrics from leg metrics, structure quality, and regime.
    Pure computation — no state.
    """

    def analyze(
        self,
        legs: List[TrendLegMetrics],
        structure_quality: float,
        correction_depth: float,
        regime_stability: float = 0.5,
    ) -> TrendQualityMetrics:
        smoothness = _compute_smoothness(legs)
        reliability = _compute_reliability(legs)
        efficiency = _compute_efficiency(legs)
        consistency = _compute_consistency(legs)
        stability = max(0.0, min(1.0, regime_stability))
        persistence = max(0.1, min(0.9, 1.0 - correction_depth))

        overall = (
            smoothness * 15.0
            + reliability * 20.0
            + efficiency * 25.0
            + consistency * 15.0
            + stability * 10.0
            + persistence * 15.0
        ) * 100.0 / 100.0  # inputs already 0-1, weights sum=100

        overall = max(0.0, min(100.0, overall))

        return TrendQualityMetrics(
            smoothness=smoothness,
            reliability=reliability,
            efficiency=efficiency,
            consistency=consistency,
            stability=stability,
            persistence=persistence,
            overall=overall,
        )


def _compute_smoothness(legs: List[TrendLegMetrics]) -> float:
    impulse_heights = [l.displacement for l in legs if l.is_impulse]
    if len(impulse_heights) < 2:
        return 0.5
    mean = sum(impulse_heights) / len(impulse_heights)
    if mean == 0:
        return 0.5
    variance = sum((h - mean) ** 2 for h in impulse_heights) / len(impulse_heights)
    stdev = math.sqrt(variance)
    cov = stdev / mean
    return max(0.0, min(1.0, 1.0 - cov))


def _compute_reliability(legs: List[TrendLegMetrics]) -> float:
    corrections = [l for l in legs if not l.is_impulse]
    if not corrections:
        return 0.8  # no corrections seen = optimistic
    valid = sum(
        1 for l in corrections
        if l.correction_quality in (CorrectionQuality.SHALLOW, CorrectionQuality.NORMAL)
    )
    return valid / len(corrections)


def _compute_efficiency(legs: List[TrendLegMetrics]) -> float:
    if len(legs) < 2:
        return 0.5
    # net displacement: sum signed displacements
    signed_sum = 0.0
    for l in legs:
        sign = 1.0 if l.direction.value == "up" else -1.0
        signed_sum += sign * l.displacement
    net = abs(signed_sum)
    total = sum(l.displacement for l in legs)
    if total == 0:
        return 0.5
    return max(0.0, min(1.0, net / total))


def _compute_consistency(legs: List[TrendLegMetrics]) -> float:
    heights = [l.displacement for l in legs]
    if len(heights) < 2:
        return 0.5
    mean = sum(heights) / len(heights)
    if mean == 0:
        return 0.5
    import math
    variance = sum((h - mean) ** 2 for h in heights) / len(heights)
    stdev = math.sqrt(variance)
    cov = stdev / mean
    return max(0.0, min(1.0, 1.0 - cov))
