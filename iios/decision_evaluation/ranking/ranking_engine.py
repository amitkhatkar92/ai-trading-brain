"""iios/decision_evaluation/ranking/ranking_engine.py"""
from __future__ import annotations

import copy

from ..evaluation_constants import DEFAULT_RANKING_METHOD, RankingMethod
from ..scoring.score_calculator import AlternativeScore
from .ranking_algorithm import ParetoRanking, RankingAlgorithm, ScoreBasedRanking
from .ranking_registry import RankingRegistry, get_ranking_registry
from .ranking_report import RankingReport, build_ranking_report


class RankingEngine:
    """Orchestrates ranking of scored alternatives."""

    def __init__(self, registry: RankingRegistry | None = None) -> None:
        self._registry = registry or get_ranking_registry()

    def rank(
        self,
        alternatives: list[AlternativeScore],
        method:       RankingMethod        = DEFAULT_RANKING_METHOD,
        algorithm:    RankingAlgorithm | None = None,
    ) -> list[AlternativeScore]:
        if not alternatives:
            return []

        # Work on copies so callers aren't surprised by rank mutation
        clones = [copy.copy(a) for a in alternatives]

        if algorithm is not None:
            return algorithm.rank(clones)

        if method == RankingMethod.PARETO:
            return self._registry.get("pareto").rank(clones)
        if method == RankingMethod.UTILITY:
            return self._registry.get("utility").rank(clones)

        # Default: SCORE or DOMINANCE → score-based
        return self._registry.get("score_based").rank(clones)

    def top(self, ranked: list[AlternativeScore]) -> AlternativeScore | None:
        return ranked[0] if ranked else None

    def pareto_frontier(self, alternatives: list[AlternativeScore]) -> list[str]:
        pareto_ranked = ParetoRanking().rank([copy.copy(a) for a in alternatives])
        return [a.alternative_id for a in pareto_ranked if a.rank == 1]

    def build_report(
        self,
        ranked: list[AlternativeScore],
        method: RankingMethod = DEFAULT_RANKING_METHOD,
    ) -> RankingReport:
        pareto = [a.alternative_id for a in ranked if a.rank == 1]
        return build_ranking_report(ranked, method, pareto_frontier=pareto)

    def summary(self, ranked: list[AlternativeScore]) -> dict:
        if not ranked:
            return {"total": 0, "top_id": None}
        return {
            "total":  len(ranked),
            "top_id": ranked[0].alternative_id,
            "top_score": ranked[0].composite_score,
        }
