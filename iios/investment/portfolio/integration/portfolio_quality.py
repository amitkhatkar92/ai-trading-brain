"""iios/investment/portfolio/integration/portfolio_quality.py

Portfolio intelligence quality assessment across five dimensions:
completeness, consistency, freshness, confidence, coverage.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.integration.integration_types import (
    IntegrationParameters, QualityGrade, now_utc, score_to_grade,
)


@dataclass(frozen=True)
class PortfolioQualityReport:
    report_id:          str          = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str          = ""
    generated_at:       str          = field(default_factory=now_utc)
    completeness_score: float        = 0.0
    consistency_score:  float        = 0.0
    freshness_score:    float        = 0.0
    confidence_score:   float        = 0.0
    coverage_score:     float        = 0.0
    overall_score:      float        = 0.0
    grade:              QualityGrade = QualityGrade.F
    is_publishable:     bool         = False
    min_to_publish:     float        = 0.60
    primary_weakness:   str          = ""
    warnings:           Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score":    round(self.overall_score, 4),
            "grade":            self.grade.value,
            "completeness":     round(self.completeness_score, 4),
            "consistency":      round(self.consistency_score, 4),
            "freshness":        round(self.freshness_score, 4),
            "confidence":       round(self.confidence_score, 4),
            "coverage":         round(self.coverage_score, 4),
            "is_publishable":   self.is_publishable,
            "primary_weakness": self.primary_weakness,
        }


class PortfolioQualityAssessor:
    """Calculates the Portfolio Intelligence Quality Score."""

    def __init__(self, params: Optional[IntegrationParameters] = None) -> None:
        self._params = params or IntegrationParameters()

    def assess(
        self,
        completeness_score: float,
        consistency_score:  float,
        freshness_score:    float,
        confidence_score:   float,
        coverage_score:     float,
        portfolio_id:       str = "",
    ) -> PortfolioQualityReport:
        p = self._params
        weighted = (
            completeness_score * p.weight_completeness
            + consistency_score * p.weight_consistency
            + freshness_score   * p.weight_freshness
            + confidence_score  * p.weight_confidence
            + coverage_score    * p.weight_coverage
        )
        overall = round(min(1.0, max(0.0, weighted)), 4)
        grade   = score_to_grade(overall)

        dim_scores = {
            "completeness": completeness_score,
            "consistency":  consistency_score,
            "freshness":    freshness_score,
            "confidence":   confidence_score,
            "coverage":     coverage_score,
        }
        primary_weakness = min(dim_scores, key=lambda k: dim_scores[k])

        warnings: List[str] = []
        if completeness_score < p.min_completeness:
            warnings.append(
                f"Completeness {completeness_score:.1%} below minimum {p.min_completeness:.1%}"
            )
        if consistency_score < p.min_consistency:
            warnings.append(
                f"Consistency {consistency_score:.1%} below minimum {p.min_consistency:.1%}"
            )
        if freshness_score < 0.60:
            warnings.append(f"Intelligence freshness is low: {freshness_score:.1%}")

        return PortfolioQualityReport(
            portfolio_id       = portfolio_id,
            completeness_score = completeness_score,
            consistency_score  = consistency_score,
            freshness_score    = freshness_score,
            confidence_score   = confidence_score,
            coverage_score     = coverage_score,
            overall_score      = overall,
            grade              = grade,
            is_publishable     = overall >= p.min_quality_to_publish,
            min_to_publish     = p.min_quality_to_publish,
            primary_weakness   = primary_weakness,
            warnings           = tuple(warnings),
        )
