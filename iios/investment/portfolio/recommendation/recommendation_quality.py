"""iios/investment/portfolio/recommendation/recommendation_quality.py

Quality assessment for portfolio recommendations.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from iios.investment.portfolio.recommendation.recommendation_types import (
    REC_SCORE_AVERAGE, REC_SCORE_BELOW_AVERAGE,
    REC_SCORE_EXCELLENT, REC_SCORE_GOOD,
    RecommendationGrade, RecommendationLevel,
    recommendation_score_to_grade, recommendation_score_to_level,
)


@dataclass(frozen=True)
class RecommendationQualityReport:
    """Quality assessment for a single recommendation."""

    report_id:         str                  = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:      str                  = ""
    quality_score:     float                = 0.0
    grade:             RecommendationGrade  = RecommendationGrade.F
    level:             RecommendationLevel  = RecommendationLevel.POOR
    is_acceptable:     bool                 = False
    threshold_used:    float                = 0.50
    primary_strength:  str                  = ""
    primary_weakness:  str                  = ""
    recommendation:    str                  = ""
    warnings:          tuple                = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality_score":   round(self.quality_score, 4),
            "grade":           self.grade.value,
            "level":           self.level.value,
            "is_acceptable":   self.is_acceptable,
            "recommendation":  self.recommendation,
            "warnings":        list(self.warnings),
        }


class RecommendationQualityAssessor:
    """Assess the quality of a portfolio recommendation."""

    def __init__(self, acceptable_threshold: float = 0.50) -> None:
        self.threshold = acceptable_threshold

    def assess(
        self,
        overall_score:     float,
        confidence_score:  float = 0.0,
        evidence_score:    float = 0.0,
        urgency_score:     float = 0.0,
        quality_score_dim: float = 0.0,
        confidence:        float = 0.0,
        requires_approval: bool  = False,
        portfolio_id:      str   = "",
    ) -> RecommendationQualityReport:

        grade = recommendation_score_to_grade(overall_score)
        level = recommendation_score_to_level(overall_score)
        acceptable = overall_score >= self.threshold

        scores = {
            "Confidence":    confidence_score,
            "Evidence":      evidence_score,
            "Urgency":       urgency_score,
            "Portfolio Quality": quality_score_dim,
        }
        sorted_dims = sorted(scores, key=lambda k: scores[k])
        primary_weakness = sorted_dims[0]
        primary_strength = sorted_dims[-1]

        warnings = []
        if confidence < 0.50:
            warnings.append(f"Low confidence: {confidence:.1%}")
        if requires_approval:
            warnings.append("Pending approval before action")
        if overall_score < REC_SCORE_BELOW_AVERAGE:
            warnings.append("Score below minimum institutional threshold")

        if overall_score >= REC_SCORE_EXCELLENT:
            rec = "High-quality recommendation — act promptly."
        elif overall_score >= REC_SCORE_GOOD:
            rec = f"Good recommendation — consider improving {primary_weakness}."
        elif overall_score >= REC_SCORE_AVERAGE:
            rec = f"Marginal recommendation — review {primary_weakness} before acting."
        elif overall_score >= REC_SCORE_BELOW_AVERAGE:
            rec = f"Low-quality recommendation — additional analysis required."
        else:
            rec = "Reject — recommendation does not meet institutional quality standards."

        return RecommendationQualityReport(
            portfolio_id     = portfolio_id,
            quality_score    = round(overall_score, 4),
            grade            = grade,
            level            = level,
            is_acceptable    = acceptable,
            threshold_used   = self.threshold,
            primary_strength = primary_strength,
            primary_weakness = primary_weakness,
            recommendation   = rec,
            warnings         = tuple(warnings),
        )
