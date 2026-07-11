"""iios/investment/market/trend/trend_score.py
Computes TrendScore from sub-components.
"""
from __future__ import annotations

from iios.investment.market.trend.models import (
    TrendStage,
    TrendQualityMetrics,
    TrendMomentumState,
    TrendScore,
)
from iios.investment.market.trend.trend_stage import STAGE_LIFECYCLE_SCORES


class TrendScorer:
    """Computes TrendScore from sub-components."""

    def score(
        self,
        quality: TrendQualityMetrics,
        momentum: TrendMomentumState,
        stage: TrendStage,
        regime_aligned: bool,
        regime_confidence: float = 0.5,
    ) -> TrendScore:
        quality_score = quality.overall
        momentum_score = momentum.momentum_score
        lifecycle_score = STAGE_LIFECYCLE_SCORES.get(stage, 50.0)

        if regime_aligned:
            regime_alignment_score = 80.0 + regime_confidence * 20.0
        else:
            regime_alignment_score = max(0.0, 50.0 - (1.0 - regime_confidence) * 30.0)

        overall = (
            quality_score * 0.30
            + momentum_score * 0.25
            + lifecycle_score * 0.25
            + regime_alignment_score * 0.20
        )
        overall = max(0.0, min(100.0, overall))

        return TrendScore(
            overall=overall,
            quality_score=quality_score,
            momentum_score=momentum_score,
            lifecycle_score=lifecycle_score,
            regime_alignment_score=regime_alignment_score,
        )
