"""iios/investment/strategy/portfolio/redundancy_detector.py
RedundancyDetector — flags highly correlated strategy pairs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from iios.investment.strategy.portfolio.strategy_correlation import (
    CorrelationMatrix, StrategyCorrelation
)

DEFAULT_REDUNDANCY_THRESHOLD = 0.70


@dataclass(frozen=True)
class RedundantPair:
    strategy_id_a: str
    strategy_id_b: str
    similarity:    float
    recommendation: str   # "remove_lower_score" | "reduce_weight_a" | "reduce_weight_b"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id_a":  self.strategy_id_a,
            "strategy_id_b":  self.strategy_id_b,
            "similarity":     round(self.similarity, 4),
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class RedundancyReport:
    redundant_pairs:       List[RedundantPair]
    threshold:             float
    total_pairs_checked:   int
    redundancy_ratio:      float   # redundant / total checked

    @property
    def has_redundancy(self) -> bool:
        return len(self.redundant_pairs) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_redundancy":      self.has_redundancy,
            "redundant_count":     len(self.redundant_pairs),
            "total_pairs_checked": self.total_pairs_checked,
            "redundancy_ratio":    round(self.redundancy_ratio, 4),
            "threshold":           self.threshold,
            "pairs":               [p.to_dict() for p in self.redundant_pairs],
        }


class RedundancyDetector:
    """
    Detects highly correlated (effectively redundant) strategy pairs.
    Uses CorrelationMatrix similarity scores.
    """

    def __init__(
        self,
        threshold:  float = DEFAULT_REDUNDANCY_THRESHOLD,
    ) -> None:
        self._threshold = threshold

    def detect(
        self,
        correlation_matrix: CorrelationMatrix,
        evaluation_scores:  Dict[str, float],   # strategy_id → evaluation_score
    ) -> RedundancyReport:
        all_pairs = correlation_matrix.all_pairs()
        redundant: List[RedundantPair] = []

        for corr in all_pairs:
            if corr.similarity >= self._threshold:
                score_a = evaluation_scores.get(corr.strategy_id_a, 0.0)
                score_b = evaluation_scores.get(corr.strategy_id_b, 0.0)
                if score_a >= score_b:
                    rec = "remove_lower_score"  # remove b
                else:
                    rec = "remove_lower_score"  # remove a
                redundant.append(
                    RedundantPair(
                        strategy_id_a=corr.strategy_id_a,
                        strategy_id_b=corr.strategy_id_b,
                        similarity=corr.similarity,
                        recommendation=rec,
                    )
                )

        n_pairs = len(all_pairs)
        return RedundancyReport(
            redundant_pairs=redundant,
            threshold=self._threshold,
            total_pairs_checked=n_pairs,
            redundancy_ratio=len(redundant) / max(n_pairs, 1),
        )
