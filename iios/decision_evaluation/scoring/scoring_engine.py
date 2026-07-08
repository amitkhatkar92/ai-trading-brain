"""iios/decision_evaluation/scoring/scoring_engine.py — Full scoring pipeline."""
from __future__ import annotations

from ..evaluation_constants import (
    DEFAULT_NORMALIZATION,
    DEFAULT_SCORING_METHOD,
    NormalizationMethod,
    ScoringMethod,
)
from ..evaluation_context import Alternative
from ..criteria.criterion import Criterion
from ..weighting.weight_manager import WeightManager
from .score_aggregator import ScoreAggregator
from .score_calculator import AlternativeScore, ScoreCalculator
from .score_normalizer import ScoreNormalizer
from .score_report import ScoreReport, build_score_report


class ScoringEngine:
    """
    Orchestrates the complete scoring pipeline:
    calculate → normalize → aggregate → report.
    """

    def __init__(self) -> None:
        self._calculator  = ScoreCalculator()
        self._normalizer  = ScoreNormalizer()
        self._aggregator  = ScoreAggregator()
        self._weight_mgr  = WeightManager()

    def score(
        self,
        alternatives: list[Alternative],
        criteria:     list[Criterion],
        weights:      dict[str, float] | None    = None,
        normalization: NormalizationMethod        = DEFAULT_NORMALIZATION,
        method:        ScoringMethod              = DEFAULT_SCORING_METHOD,
    ) -> list[AlternativeScore]:
        if not alternatives or not criteria:
            return []

        resolved_weights = self._weight_mgr.resolve(criteria, weights)
        raw_scores       = self._calculator.calculate(alternatives, criteria)
        norm_scores      = self._normalizer.normalize(raw_scores, criteria, normalization)
        scored           = self._aggregator.aggregate(
            alternatives, criteria, norm_scores, resolved_weights, method
        )
        # Back-fill raw_score from raw_scores dict
        for alt_score in scored:
            for cs in alt_score.criterion_scores:
                cs.raw_score = raw_scores.get(alt_score.alternative_id, {}).get(cs.criterion_id, 0.0)

        return scored

    def build_report(
        self,
        scored:       list[AlternativeScore],
        criteria:     list[Criterion],
        normalization: NormalizationMethod = DEFAULT_NORMALIZATION,
        method:        ScoringMethod       = DEFAULT_SCORING_METHOD,
    ) -> ScoreReport:
        return build_score_report(
            scored_alternatives = scored,
            total_criteria      = len(criteria),
            scoring_method      = method,
            normalization       = normalization,
        )

    def summary(self, scored: list[AlternativeScore]) -> dict:
        if not scored:
            return {"total": 0, "min": 0.0, "max": 0.0, "avg": 0.0}
        vals = [a.composite_score for a in scored]
        return {
            "total": len(scored),
            "min":   min(vals),
            "max":   max(vals),
            "avg":   sum(vals) / len(vals),
        }
