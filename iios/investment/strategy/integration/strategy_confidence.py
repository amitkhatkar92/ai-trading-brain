"""iios/investment/strategy/integration/strategy_confidence.py
Computes the composite confidence score for a strategy intelligence snapshot.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from iios.investment.strategy.integration.aggregation_state import StrategyAggregationState
from iios.investment.strategy.integration.conflict_classifier import Conflict
from iios.investment.strategy.integration.integration_constants import ConflictSeverity


@dataclass(frozen=True)
class ConfidenceComponents:
    """Breakdown of how the final confidence score was derived."""
    base_confidence:       float   # raw average confidence from all sources
    conflict_penalty:      float   # subtracted due to active conflicts
    staleness_penalty:     float   # subtracted due to stale updates
    completeness_bonus:    float   # added when completeness >= 0.9
    final_confidence:      float   # clamped 0–100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_confidence":    round(self.base_confidence, 2),
            "conflict_penalty":   round(self.conflict_penalty, 2),
            "staleness_penalty":  round(self.staleness_penalty, 2),
            "completeness_bonus": round(self.completeness_bonus, 2),
            "final_confidence":   round(self.final_confidence, 2),
        }


class ConfidenceCalculator:
    """
    Computes per-strategy confidence.
    Inputs come from the aggregation layer — never from raw strategy evaluation logic.
    """

    def compute(
        self,
        state:          StrategyAggregationState,
        active_conflicts: List[Conflict],
        completeness:   float,   # 0–1
        freshness_score: float,  # 0–1
    ) -> ConfidenceComponents:
        # Base: average confidence across all source updates
        latest = state.all_latest()
        if latest:
            base = sum(u.confidence for u in latest.values()) / len(latest)
        else:
            base = 0.0

        # Conflict penalty
        penalty = sum(
            c.severity.score_penalty
            for c in active_conflicts
            if not c.is_resolved
        )

        # Staleness penalty: map freshness_score 0-1 → penalty 0-30
        staleness_penalty = (1.0 - freshness_score) * 30.0

        # Completeness bonus: up to +10 if >= 90%
        completeness_bonus = 10.0 if completeness >= 0.90 else 0.0

        final = base - penalty - staleness_penalty + completeness_bonus
        final = max(0.0, min(100.0, final))

        return ConfidenceComponents(
            base_confidence=round(base, 2),
            conflict_penalty=round(penalty, 2),
            staleness_penalty=round(staleness_penalty, 2),
            completeness_bonus=round(completeness_bonus, 2),
            final_confidence=round(final, 2),
        )
