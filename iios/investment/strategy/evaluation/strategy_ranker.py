"""iios/investment/strategy/evaluation/strategy_ranker.py
Ranks a collection of StrategyScore objects.
"""
from __future__ import annotations

from typing import Any

from iios.investment.strategy.evaluation.strategy_score import StrategyScore


class StrategyRanker:
    """Sorts and filters strategy scores by composite or dimension scores."""

    def rank(
        self,
        scores: list[StrategyScore],
        key:    str = "overall_score",
    ) -> list[StrategyScore]:
        """Return scores sorted descending by ``key``."""
        valid_keys = {
            "overall_score", "performance_score", "risk_score",
            "stability_score", "regime_score", "confidence_score",
            "win_rate", "sharpe_ratio",
        }
        if key not in valid_keys:
            key = "overall_score"
        return sorted(scores, key=lambda s: getattr(s, key, 0.0), reverse=True)

    def top_n(
        self,
        scores: list[StrategyScore],
        n:      int  = 5,
        key:    str  = "overall_score",
    ) -> list[StrategyScore]:
        """Return the top-N strategies sorted by ``key``."""
        return self.rank(scores, key)[:n]

    def filter_by_threshold(
        self,
        scores:    list[StrategyScore],
        min_score: float = 50.0,
    ) -> list[StrategyScore]:
        """Return only strategies above the overall_score threshold."""
        return [s for s in scores if s.overall_score >= min_score]

    def filter_by_confidence(
        self,
        scores:         list[StrategyScore],
        min_confidence: float = 30.0,
    ) -> list[StrategyScore]:
        """Return strategies with sufficient confidence."""
        return [s for s in scores if s.confidence_score >= min_confidence]

    def ranked_summary(self, scores: list[StrategyScore]) -> list[dict[str, Any]]:
        """Return lightweight summary dicts (id, name, score, grade) in rank order."""
        ranked = self.rank(scores)
        return [
            {
                "rank":           i + 1,
                "strategy_id":    s.strategy_id,
                "strategy_name":  s.strategy_name,
                "overall_score":  s.overall_score,
                "grade":          s.grade.value,
                "recommendation": s.recommendation.value,
                "confidence":     s.confidence_score,
            }
            for i, s in enumerate(ranked)
        ]
