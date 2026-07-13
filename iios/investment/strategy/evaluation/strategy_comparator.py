"""iios/investment/strategy/evaluation/strategy_comparator.py
Side-by-side comparison of two or more StrategyScore objects.
"""
from __future__ import annotations

from typing import Any

from iios.investment.strategy.evaluation.strategy_score import StrategyScore

_DIMS = (
    "overall_score",
    "performance_score",
    "risk_score",
    "stability_score",
    "regime_score",
    "confidence_score",
    "win_rate",
    "sharpe_ratio",
    "max_drawdown",
)


class StrategyComparator:
    """Produces structured comparisons between StrategyScore objects."""

    def compare(
        self,
        score_a: StrategyScore,
        score_b: StrategyScore,
    ) -> dict[str, Any]:
        """Compare two scores; returns winner per dimension and overall."""
        dims: dict[str, dict] = {}
        for dim in _DIMS:
            a_val = getattr(score_a, dim, 0.0)
            b_val = getattr(score_b, dim, 0.0)
            # For max_drawdown lower is better
            if dim == "max_drawdown":
                better = "A" if a_val <= b_val else "B"
            else:
                better = "A" if a_val >= b_val else "B"
            dims[dim] = {"A": a_val, "B": b_val, "better": better}

        a_wins = sum(1 for v in dims.values() if v["better"] == "A")
        b_wins = len(dims) - a_wins
        overall_winner = "A" if a_wins >= b_wins else "B"

        return {
            "strategy_A":      score_a.strategy_id,
            "strategy_B":      score_b.strategy_id,
            "dimensions":      dims,
            "A_wins":          a_wins,
            "B_wins":          b_wins,
            "overall_winner":  overall_winner,
            "recommended":     (
                score_a.strategy_id if overall_winner == "A"
                else score_b.strategy_id
            ),
        }

    def compare_many(
        self,
        scores: list[StrategyScore],
    ) -> list[dict[str, Any]]:
        """
        All-pairs comparison.
        Returns a list of comparison dicts sorted by overall_score of winner.
        """
        results = []
        n = len(scores)
        for i in range(n):
            for j in range(i + 1, n):
                results.append(self.compare(scores[i], scores[j]))
        return results

    def best_of(
        self,
        scores: list[StrategyScore],
    ) -> StrategyScore | None:
        """Return the strategy with the highest overall_score."""
        if not scores:
            return None
        return max(scores, key=lambda s: s.overall_score)
