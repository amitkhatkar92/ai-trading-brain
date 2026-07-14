"""iios/investment/portfolio/optimization/optimization_quality.py

Quality scoring for OptimizationPlan.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.optimization.optimization_types import (
    ConstraintOutcome,
    OptimizationQualityGrade,
)
from iios.investment.portfolio.optimization.optimization_validator import (
    OptimizationValidationReport,
)
from iios.investment.portfolio.optimization.constraint_validator import (
    ConstraintValidationReport,
)


def _grade(score: float) -> OptimizationQualityGrade:
    if score >= 0.90:
        return OptimizationQualityGrade.A
    if score >= 0.75:
        return OptimizationQualityGrade.B
    if score >= 0.60:
        return OptimizationQualityGrade.C
    if score >= 0.45:
        return OptimizationQualityGrade.D
    return OptimizationQualityGrade.F


@dataclass(frozen=True)
class OptimizationDimensionScore:
    """Score for one quality dimension."""

    dimension: str   = ""
    score:     float = 0.0    # 0.0–1.0
    passed:    bool  = False
    message:   str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score":     round(self.score, 4),
            "passed":    self.passed,
            "message":   self.message,
        }


@dataclass(frozen=True)
class OptimizationQualityReport:
    """Comprehensive quality assessment for one OptimizationPlan."""

    report_id:                str                                  = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:             str                                  = ""
    plan_id:                  str                                  = ""
    dimension_scores:         Tuple[OptimizationDimensionScore, ...]= field(default_factory=tuple)
    overall_score:            float                               = 0.0
    grade:                    OptimizationQualityGrade            = OptimizationQualityGrade.F
    is_acceptable:            bool                                = False
    threshold:                float                               = 0.60

    # Dimension scores (convenience)
    objective_achievement:    float = 0.0
    constraint_compliance:    float = 0.0
    convergence_quality:      float = 0.0
    diversification_quality:  float = 0.0
    stability_score:          float = 0.0

    assessed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":              self.report_id,
            "portfolio_id":           self.portfolio_id,
            "plan_id":                self.plan_id,
            "overall_score":          round(self.overall_score, 4),
            "grade":                  self.grade.value,
            "is_acceptable":          self.is_acceptable,
            "threshold":              self.threshold,
            "objective_achievement":  round(self.objective_achievement, 4),
            "constraint_compliance":  round(self.constraint_compliance, 4),
            "convergence_quality":    round(self.convergence_quality, 4),
            "diversification_quality":round(self.diversification_quality, 4),
            "stability_score":        round(self.stability_score, 4),
            "dimension_scores":       [d.to_dict() for d in self.dimension_scores],
            "assessed_at":            self.assessed_at,
        }


class OptimizationQualityAssessor:
    """
    Scores an OptimizationPlan across 5 dimensions.

    Weights:
        objective_achievement   35 %
        constraint_compliance   25 %
        convergence_quality     20 %
        diversification_quality 12 %
        stability_score          8 %
    """

    _WEIGHTS = {
        "objective_achievement":   0.35,
        "constraint_compliance":   0.25,
        "convergence_quality":     0.20,
        "diversification_quality": 0.12,
        "stability_score":         0.08,
    }

    def __init__(self, acceptable_threshold: float = 0.60) -> None:
        self._threshold = acceptable_threshold

    def assess(
        self,
        plan:                 Any,   # OptimizationPlan (duck-typed)
        validation_report:    OptimizationValidationReport,
        constraint_report:    Optional[ConstraintValidationReport] = None,
    ) -> OptimizationQualityReport:

        dims: List[OptimizationDimensionScore] = []

        # --- 1. Objective achievement -----------------------------------
        obj_impr   = getattr(plan, "objective_improvement", 0.0)
        obj_score  = _objective_score(obj_impr)
        dims.append(OptimizationDimensionScore(
            dimension = "objective_achievement",
            score     = obj_score,
            passed    = obj_score >= 0.50,
            message   = f"Objective improvement {obj_impr:+.4f}",
        ))

        # --- 2. Constraint compliance -----------------------------------
        if constraint_report is not None:
            cpl_score = constraint_report.satisfaction_rate if constraint_report.is_feasible else 0.0
        else:
            cpl_score = 1.0 if validation_report.failures == 0 else 0.0
        dims.append(OptimizationDimensionScore(
            dimension = "constraint_compliance",
            score     = cpl_score,
            passed    = cpl_score >= 0.60,
            message   = f"Constraint compliance {cpl_score:.1%}",
        ))

        # --- 3. Convergence quality -------------------------------------
        converged  = getattr(plan, "converged", True)
        conv_score = 1.0 if converged else 0.40
        dims.append(OptimizationDimensionScore(
            dimension = "convergence_quality",
            score     = conv_score,
            passed    = converged,
            message   = f"Convergence: {getattr(plan, 'convergence', '?')}",
        ))

        # --- 4. Diversification quality ---------------------------------
        div_ratio  = getattr(plan, "diversification_ratio", 1.0)
        div_score  = min(1.0, div_ratio)
        dims.append(OptimizationDimensionScore(
            dimension = "diversification_quality",
            score     = div_score,
            passed    = div_score >= 0.40,
            message   = f"Diversification ratio {div_ratio:.3f}",
        ))

        # --- 5. Stability score (based on validation pass rate) ---------
        stab_score = validation_report.pass_rate if validation_report.failures == 0 else 0.30
        dims.append(OptimizationDimensionScore(
            dimension = "stability_score",
            score     = stab_score,
            passed    = stab_score >= 0.50,
            message   = f"Validation pass rate {validation_report.pass_rate:.1%}",
        ))

        dim_map = {d.dimension: d.score for d in dims}
        overall = sum(self._WEIGHTS[k] * dim_map.get(k, 0.0) for k in self._WEIGHTS)

        return OptimizationQualityReport(
            portfolio_id             = getattr(plan, "portfolio_id", ""),
            plan_id                  = getattr(plan, "plan_id", ""),
            dimension_scores         = tuple(dims),
            overall_score            = overall,
            grade                    = _grade(overall),
            is_acceptable            = overall >= self._threshold,
            threshold                = self._threshold,
            objective_achievement    = dim_map.get("objective_achievement", 0.0),
            constraint_compliance    = dim_map.get("constraint_compliance", 0.0),
            convergence_quality      = dim_map.get("convergence_quality", 0.0),
            diversification_quality  = dim_map.get("diversification_quality", 0.0),
            stability_score          = dim_map.get("stability_score", 0.0),
        )


def _objective_score(improvement: float) -> float:
    """Convert objective improvement into a 0–1 quality score."""
    if improvement >= 0.10:
        return 1.0
    if improvement >= 0.05:
        return 0.90
    if improvement >= 0.01:
        return 0.75
    if improvement >= 0.0:
        return 0.60    # No change — at minimum acceptable
    if improvement >= -0.02:
        return 0.40    # Tiny degradation
    return max(0.0, 0.40 + improvement * 5)
