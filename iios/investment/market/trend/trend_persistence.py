"""iios/investment/market/trend/trend_persistence.py
Estimates probability that the trend persists for at least one more bar.
"""
from __future__ import annotations

from typing import ClassVar, Dict

from iios.investment.market.trend.models import (
    TrendStage,
    TrendQualityMetrics,
)


class TrendPersistenceCalculator:
    """
    Estimates probability that the trend persists for at least one more bar.
    Returns float in [0.05, 0.95].
    """

    _STAGE_BASE: ClassVar[Dict[TrendStage, float]] = {
        TrendStage.EMERGING:    0.55,
        TrendStage.DEVELOPING:  0.65,
        TrendStage.ESTABLISHED: 0.75,
        TrendStage.MATURE:      0.60,
        TrendStage.EXHAUSTING:  0.40,
        TrendStage.FAILING:     0.25,
        TrendStage.REVERSING:   0.15,
        TrendStage.COMPLETED:   0.10,
    }

    def calculate(
        self,
        stage: TrendStage,
        quality: TrendQualityMetrics,
        regime_aligned: bool,
        is_accelerating: bool,
        is_decelerating: bool,
    ) -> float:
        base = self._STAGE_BASE.get(stage, 0.50)

        adj = 0.0
        adj += 0.08 if regime_aligned else -0.08
        adj += 0.05 if is_accelerating else 0.0
        adj -= 0.10 if is_decelerating else 0.0
        adj += (quality.overall / 100.0 - 0.5) * 0.10

        return max(0.05, min(0.95, base + adj))
