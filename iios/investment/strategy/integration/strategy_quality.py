"""iios/investment/strategy/integration/strategy_quality.py
Multi-dimensional quality scoring for integrated strategy intelligence.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from iios.investment.strategy.integration.aggregation_state import StrategyAggregationState
from iios.investment.strategy.integration.aggregation_engine import AggregationEngine
from iios.investment.strategy.integration.conflict_classifier import Conflict
from iios.investment.strategy.integration.integration_constants import (
    ConflictSeverity,
    IntelligenceSource,
    QualityDimension,
    STALENESS_WARNING_SECONDS,
    STALENESS_CRITICAL_SECONDS,
)


@dataclass(frozen=True)
class QualityReport:
    """
    Immutable output of one quality-scoring pass.
    Contains per-dimension scores and an overall weighted score (0–100).
    """
    report_id:     str
    strategy_id:   str
    scores:        Dict[str, float]   # QualityDimension.value → 0–100
    overall_score: float              # 0–100
    generated_at:  datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":     self.report_id,
            "strategy_id":   self.strategy_id,
            "scores":        {k: round(v, 2) for k, v in self.scores.items()},
            "overall_score": round(self.overall_score, 2),
            "generated_at":  self.generated_at.isoformat(),
        }


class QualityFramework:
    """
    Computes 5-dimension quality scores from aggregation state.
    Dimensions: COMPLETENESS, FRESHNESS, CONSISTENCY, RELIABILITY, COVERAGE.
    Weights: 0.30 / 0.25 / 0.25 / 0.15 / 0.05 (per QualityDimension.default_weight).
    """

    def __init__(self, aggregation_engine: AggregationEngine = None) -> None:
        self._engine = aggregation_engine or AggregationEngine()

    def compute(
        self,
        strategy_id:       str,
        state:             StrategyAggregationState,
        active_conflicts:  List[Conflict],
    ) -> QualityReport:
        # --- COMPLETENESS (0–100) ---
        completeness = self._engine.completeness(strategy_id)
        completeness_score = completeness * 100.0

        # --- FRESHNESS (0–100) ---
        freshness_0to1 = self._engine.freshness_score(
            strategy_id,
            warn_seconds=STALENESS_WARNING_SECONDS,
            crit_seconds=STALENESS_CRITICAL_SECONDS,
        )
        freshness_score = freshness_0to1 * 100.0

        # --- CONSISTENCY (0–100): start 100, deduct conflict penalties ---
        consistency_score = 100.0
        for c in active_conflicts:
            if not c.is_resolved:
                consistency_score -= c.severity.score_penalty
        consistency_score = max(0.0, consistency_score)

        # --- RELIABILITY (0–100): average source confidence ---
        avg_conf = self._engine.average_confidence(strategy_id)
        reliability_score = avg_conf  # confidence already 0–100

        # --- COVERAGE (0–100): are all required sources present? ---
        required = [s for s in IntelligenceSource if s.is_required]
        latest   = state.all_latest()
        present_required = sum(1 for s in required if s in latest)
        coverage_score = (present_required / len(required) * 100.0) if required else 100.0

        scores = {
            QualityDimension.COMPLETENESS.value: round(completeness_score, 2),
            QualityDimension.FRESHNESS.value:    round(freshness_score, 2),
            QualityDimension.CONSISTENCY.value:  round(consistency_score, 2),
            QualityDimension.RELIABILITY.value:  round(reliability_score, 2),
            QualityDimension.COVERAGE.value:     round(coverage_score, 2),
        }

        overall = sum(
            scores[dim.value] * dim.default_weight
            for dim in QualityDimension
        )

        return QualityReport(
            report_id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            scores=scores,
            overall_score=round(overall, 2),
            generated_at=datetime.now(timezone.utc),
        )
