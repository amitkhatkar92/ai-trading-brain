"""iios/investment/market/trend/trend_stability.py
Computes trend stability from structure consistency.
"""
from __future__ import annotations

from typing import List

from iios.investment.market.trend.models import (
    TrendLegMetrics,
    CorrectionQuality,
)


class TrendStabilityCalculator:
    """Computes trend stability from structure consistency."""

    def calculate(
        self,
        legs: List[TrendLegMetrics],
        correction_depth: float,
        quality_score: float,
    ) -> float:
        """
        Returns stability 0-1.
        """
        base = quality_score / 100.0

        # Penalty for deep corrections
        deep_penalty = max(0.0, correction_depth - 0.618)
        base = base * (1.0 - deep_penalty)

        # Penalties and bonuses from correction quality
        failed_count = sum(
            1 for l in legs
            if l.correction_quality == CorrectionQuality.FAILED
        )
        base -= failed_count * 0.10

        shallow_count = sum(
            1 for l in legs
            if l.correction_quality == CorrectionQuality.SHALLOW
        )
        base += min(0.15, shallow_count * 0.05)

        return max(0.1, min(0.95, base))
