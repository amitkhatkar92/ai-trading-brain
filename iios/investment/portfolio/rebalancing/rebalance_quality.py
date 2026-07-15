"""iios/investment/portfolio/rebalancing/rebalance_quality.py

Quality assessment for rebalancing plans.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from iios.investment.portfolio.rebalancing.rebalancing_types import (
    REBAL_SCORE_AVERAGE, REBAL_SCORE_BELOW_AVERAGE,
    REBAL_SCORE_EXCELLENT, REBAL_SCORE_GOOD,
    RebalanceGrade, RebalanceLevel,
    rebalance_score_to_grade, rebalance_score_to_level,
)


@dataclass(frozen=True)
class RebalanceQualityReport:
    """Quality assessment for a rebalancing plan."""

    report_id:          str            = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:       str            = ""
    quality_score:      float          = 0.0
    grade:              RebalanceGrade = RebalanceGrade.F
    level:              RebalanceLevel = RebalanceLevel.POOR
    is_acceptable:      bool           = False
    threshold_used:     float          = 0.50
    primary_weakness:   str            = ""
    primary_strength:   str            = ""
    recommendation:     str            = ""
    warnings:           tuple          = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality_score":   round(self.quality_score, 4),
            "grade":           self.grade.value,
            "level":           self.level.value,
            "is_acceptable":   self.is_acceptable,
            "primary_weakness":self.primary_weakness,
            "recommendation":  self.recommendation,
        }


class RebalanceQualityAssessor:
    """Assess quality of a rebalancing plan."""

    def __init__(self, acceptable_threshold: float = 0.50) -> None:
        self.threshold = acceptable_threshold

    def assess(
        self,
        overall_score:     float,
        drift_red_score:   float = 0.0,
        cost_eff_score:    float = 0.0,
        risk_imp_score:    float = 0.0,
        div_score:         float = 0.0,
        tax_eff_score:     float = 0.0,
        total_cost_pct:    float = 0.0,
        total_turnover:    float = 0.0,
        portfolio_id:      str   = "",
    ) -> RebalanceQualityReport:

        grade = rebalance_score_to_grade(overall_score)
        level = rebalance_score_to_level(overall_score)
        acceptable = overall_score >= self.threshold

        scores = {
            "Drift Reduction": drift_red_score,
            "Cost Efficiency": cost_eff_score,
            "Risk Improvement":risk_imp_score,
            "Diversification": div_score,
            "Tax Efficiency":  tax_eff_score,
        }
        sorted_dims = sorted(scores.keys(), key=lambda k: scores[k])
        primary_weakness = sorted_dims[0]
        primary_strength = sorted_dims[-1]

        warnings = []
        if total_cost_pct > 0.008:
            warnings.append(f"High rebalancing cost: {total_cost_pct:.2%}")
        if total_turnover > 0.30:
            warnings.append(f"High turnover: {total_turnover:.1%}")
        if drift_red_score < 0.30:
            warnings.append("Low drift reduction — consider wider scope")

        if overall_score >= REBAL_SCORE_EXCELLENT:
            rec = "Highly recommended — plan efficiently resolves portfolio drift."
        elif overall_score >= REBAL_SCORE_GOOD:
            rec = f"Recommended — consider improving {primary_weakness}."
        elif overall_score >= REBAL_SCORE_AVERAGE:
            rec = f"Marginal — review {primary_weakness} and cost efficiency before proceeding."
        elif overall_score >= REBAL_SCORE_BELOW_AVERAGE:
            rec = f"Not recommended — {primary_weakness} is a significant concern."
        else:
            rec = "Reject — plan does not meet institutional quality standards."

        return RebalanceQualityReport(
            portfolio_id     = portfolio_id,
            quality_score    = round(overall_score, 4),
            grade            = grade,
            level            = level,
            is_acceptable    = acceptable,
            threshold_used   = self.threshold,
            primary_weakness = primary_weakness,
            primary_strength = primary_strength,
            recommendation   = rec,
            warnings         = tuple(warnings),
        )
