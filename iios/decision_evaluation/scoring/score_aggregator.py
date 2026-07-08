"""iios/decision_evaluation/scoring/score_aggregator.py"""
from __future__ import annotations

import math

from ..evaluation_constants import ScoringMethod
from ..evaluation_context import Alternative
from ..criteria.criterion import Criterion
from .score_calculator import AlternativeScore, CriterionScore


class ScoreAggregator:
    """Applies weights to normalized scores and computes composite AlternativeScores."""

    def aggregate(
        self,
        alternatives:      list[Alternative],
        criteria:          list[Criterion],
        normalized_scores: dict[str, dict[str, float]],
        weights:           dict[str, float],
        method:            ScoringMethod = ScoringMethod.WEIGHTED_SUM,
    ) -> list[AlternativeScore]:
        results: list[AlternativeScore] = []

        for alt in alternatives:
            aid            = alt.alternative_id
            crit_scores:   list[CriterionScore] = []

            for crit in criteria:
                cid    = crit.criterion_id
                norm   = normalized_scores.get(aid, {}).get(cid, 0.0)
                w      = weights.get(cid, 1.0 / len(criteria) if criteria else 1.0)
                cs     = CriterionScore(
                    criterion_id     = cid,
                    criterion_name   = crit.name,
                    alternative_id   = aid,
                    raw_score        = 0.0,  # raw is in normalized_scores already
                    normalized_score = norm,
                    weight           = w,
                    weighted_score   = norm * w,
                    direction        = crit.direction,
                )
                crit_scores.append(cs)

            composite = self._composite(crit_scores, method)
            results.append(AlternativeScore(
                alternative_id   = aid,
                alternative_name = alt.name,
                criterion_scores = crit_scores,
                composite_score  = composite,
            ))

        return results

    def _composite(self, scores: list[CriterionScore], method: ScoringMethod) -> float:
        if not scores:
            return 0.0
        if method == ScoringMethod.WEIGHTED_PRODUCT:
            return math.prod(
                max(cs.normalized_score, 1e-9) ** cs.weight for cs in scores
            )
        # WEIGHTED_SUM (default) — also used for SIMPLE and TOPSIS
        return sum(cs.weighted_score for cs in scores)
