"""iios/decision_evaluation/ranking/ranking_algorithm.py"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..scoring.score_calculator import AlternativeScore


class RankingAlgorithm(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def rank(self, alternatives: list[AlternativeScore]) -> list[AlternativeScore]:
        """
        Assign integer ranks (1 = best) and return sorted list.
        Must set .rank on each AlternativeScore in-place.
        """
        ...


class ScoreBasedRanking(RankingAlgorithm):
    """Sort by composite_score descending; assign sequential ranks."""

    @property
    def name(self) -> str:
        return "score_based"

    def rank(self, alternatives: list[AlternativeScore]) -> list[AlternativeScore]:
        sorted_alts = sorted(alternatives, key=lambda a: a.composite_score, reverse=True)
        for i, alt in enumerate(sorted_alts, start=1):
            alt.rank = i
        return sorted_alts


class ParetoRanking(RankingAlgorithm):
    """
    Assigns Pareto ranks: Pareto rank 1 = not dominated by anyone.
    Rank 2 = dominated only by rank-1 alternatives, etc.
    Uses criterion_scores for dominance comparison.
    """

    @property
    def name(self) -> str:
        return "pareto"

    def rank(self, alternatives: list[AlternativeScore]) -> list[AlternativeScore]:
        remaining   = list(alternatives)
        current_rank = 1
        result: list[AlternativeScore] = []

        while remaining:
            non_dominated = [a for a in remaining if not self._is_dominated(a, remaining)]
            if not non_dominated:
                non_dominated = remaining  # break cycle

            non_dominated.sort(key=lambda a: a.composite_score, reverse=True)
            for alt in non_dominated:
                alt.rank = current_rank
            result.extend(non_dominated)

            remaining = [a for a in remaining if a not in non_dominated]
            current_rank += 1

        return result

    def _is_dominated(
        self, target: AlternativeScore, pool: list[AlternativeScore]
    ) -> bool:
        """True if any other alternative dominates target."""
        target_scores = {cs.criterion_id: cs.normalized_score for cs in target.criterion_scores}
        for other in pool:
            if other.alternative_id == target.alternative_id:
                continue
            other_scores = {cs.criterion_id: cs.normalized_score for cs in other.criterion_scores}
            crit_ids = list(target_scores.keys())
            if not crit_ids:
                continue
            at_least_as_good = all(
                other_scores.get(cid, 0.0) >= target_scores.get(cid, 0.0)
                for cid in crit_ids
            )
            strictly_better = any(
                other_scores.get(cid, 0.0) > target_scores.get(cid, 0.0)
                for cid in crit_ids
            )
            if at_least_as_good and strictly_better:
                return True
        return False


class UtilityRanking(RankingAlgorithm):
    """Applies a utility transformation to composite_score then ranks by score."""

    def __init__(self, utility_fn=None) -> None:
        # utility_fn: Callable[[float], float] | None
        self._utility_fn = utility_fn

    @property
    def name(self) -> str:
        return "utility"

    def rank(self, alternatives: list[AlternativeScore]) -> list[AlternativeScore]:
        if self._utility_fn is not None:
            for alt in alternatives:
                try:
                    alt.composite_score = self._utility_fn(alt.composite_score)
                except Exception:  # noqa: BLE001
                    pass
        sorted_alts = sorted(alternatives, key=lambda a: a.composite_score, reverse=True)
        for i, alt in enumerate(sorted_alts, start=1):
            alt.rank = i
        return sorted_alts
