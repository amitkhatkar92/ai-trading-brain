"""iios/investment/portfolio/performance/performance_quality.py

Quality assessment for portfolio performance.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.portfolio.performance.performance_types import (
    SCORE_AVERAGE, SCORE_BELOW_AVERAGE, SCORE_EXCELLENT, SCORE_GOOD,
    PerformanceGrade, PerformanceLevel, performance_score_to_grade,
    performance_score_to_level,
)


@dataclass(frozen=True)
class PerformanceQualityReport:
    """Assessment of performance quality."""

    report_id:              str             = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:           str             = ""
    quality_score:          float           = 0.0
    grade:                  PerformanceGrade   = PerformanceGrade.F
    level:                  PerformanceLevel   = PerformanceLevel.POOR
    is_acceptable:          bool            = False
    threshold_used:         float           = 0.55
    dimensions_assessed:    int             = 0
    dimensions_above:       int             = 0
    primary_weakness:       str             = ""
    primary_strength:       str             = ""
    recommendation:         str             = ""
    warnings:               tuple           = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality_score":    round(self.quality_score, 4),
            "grade":            self.grade.value,
            "level":            self.level.value,
            "is_acceptable":    self.is_acceptable,
            "primary_weakness": self.primary_weakness,
            "recommendation":   self.recommendation,
        }


class PerformanceQualityAssessor:
    """Assess portfolio performance quality against thresholds."""

    def __init__(self, acceptable_threshold: float = 0.55) -> None:
        self.threshold = acceptable_threshold

    def assess(
        self,
        overall_score:    float,
        sharpe:           float = 0.0,
        sortino:          float = 0.0,
        calmar:           float = 0.0,
        information_ratio:float = 0.0,
        alpha:            float = 0.0,
        max_drawdown:     float = 0.0,
        portfolio_id:     str   = "",
    ) -> PerformanceQualityReport:
        """
        Produce quality report from an overall performance score and key metrics.
        """
        grade   = performance_score_to_grade(overall_score)
        level   = performance_score_to_level(overall_score)
        acceptable = overall_score >= self.threshold

        # Identify dimensions
        dimensions = {
            "Sharpe":           sharpe >= 0.5,
            "Sortino":          sortino >= 0.5,
            "Calmar":           calmar >= 0.3,
            "Information Ratio":information_ratio >= 0.3,
            "Alpha":            alpha >= 0.0,
        }
        above = sum(1 for v in dimensions.values() if v)
        total = len(dimensions)

        # Find weaknesses and strengths
        ratios = {
            "Sharpe": sharpe,
            "Sortino": sortino,
            "Calmar": calmar,
            "Information Ratio": information_ratio,
            "Alpha": alpha,
        }
        thresholds = {
            "Sharpe": 0.5,
            "Sortino": 0.5,
            "Calmar": 0.3,
            "Information Ratio": 0.3,
            "Alpha": 0.0,
        }

        sorted_gaps = sorted(
            ratios.keys(),
            key=lambda k: ratios[k] - thresholds[k]
        )
        primary_weakness = sorted_gaps[0]
        primary_strength = sorted_gaps[-1]

        # Recommendation
        if overall_score >= SCORE_EXCELLENT:
            rec = "Excellent performance — maintain current strategy allocation."
        elif overall_score >= SCORE_GOOD:
            rec = f"Good performance — consider improving {primary_weakness}."
        elif overall_score >= SCORE_AVERAGE:
            rec = f"Average performance — review {primary_weakness} and {sorted_gaps[1]}."
        elif overall_score >= SCORE_BELOW_AVERAGE:
            rec = f"Below average — significant improvement needed in {primary_weakness}."
        else:
            rec = "Poor performance — strategic overhaul recommended."

        # Drawdown warning
        warnings = []
        if max_drawdown > 0.20:
            warnings.append(f"Max drawdown {max_drawdown:.1%} exceeds 20% threshold.")
        if sharpe < 0:
            warnings.append("Negative Sharpe ratio — portfolio underperforms risk-free rate.")

        return PerformanceQualityReport(
            portfolio_id         = portfolio_id,
            quality_score        = round(overall_score, 4),
            grade                = grade,
            level                = level,
            is_acceptable        = acceptable,
            threshold_used       = self.threshold,
            dimensions_assessed  = total,
            dimensions_above     = above,
            primary_weakness     = primary_weakness,
            primary_strength     = primary_strength,
            recommendation       = rec,
            warnings             = tuple(warnings),
        )
