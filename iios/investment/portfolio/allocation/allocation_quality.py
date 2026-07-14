"""iios/investment/portfolio/allocation/allocation_quality.py

Quality scoring for AllocationPlan objects.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.allocation.allocation_types import AllocationQualityGrade
from iios.investment.portfolio.allocation.allocation_validator import AllocationValidationReport
from iios.investment.portfolio.allocation.exposure_limits import ExposureCheck, ExposureOutcome


# ---------------------------------------------------------------------------
# Dimension score
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AllocationDimensionScore:
    """Score for one quality dimension."""

    dimension: str   = ""
    score:     float = 0.0    # 0.0 – 1.0
    passed:    bool  = False
    message:   str   = ""
    details:   Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score":     round(self.score, 4),
            "passed":    self.passed,
            "message":   self.message,
            "details":   dict(self.details),
        }


def _grade(score: float) -> AllocationQualityGrade:
    if score >= 0.90:
        return AllocationQualityGrade.A
    if score >= 0.75:
        return AllocationQualityGrade.B
    if score >= 0.60:
        return AllocationQualityGrade.C
    if score >= 0.45:
        return AllocationQualityGrade.D
    return AllocationQualityGrade.F


# ---------------------------------------------------------------------------
# Quality report
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AllocationQualityReport:
    """Comprehensive quality assessment for one AllocationPlan."""

    report_id:                str                              = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:             str                              = ""
    plan_id:                  str                              = ""
    dimension_scores:         Tuple[AllocationDimensionScore, ...]= field(default_factory=tuple)
    overall_score:            float                           = 0.0
    grade:                    AllocationQualityGrade          = AllocationQualityGrade.F
    is_acceptable:            bool                            = False
    threshold:                float                           = 0.60

    # Dimension breakdown (also in dimension_scores, here as convenience floats)
    capital_utilisation_score:  float = 0.0
    constraint_compliance_score:float = 0.0
    cash_adequacy_score:        float = 0.0
    exposure_compliance_score:  float = 0.0
    consistency_score:          float = 0.0

    assessed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":                   self.report_id,
            "portfolio_id":                self.portfolio_id,
            "plan_id":                     self.plan_id,
            "overall_score":               round(self.overall_score, 4),
            "grade":                       self.grade.value,
            "is_acceptable":               self.is_acceptable,
            "threshold":                   self.threshold,
            "capital_utilisation_score":   round(self.capital_utilisation_score, 4),
            "constraint_compliance_score": round(self.constraint_compliance_score, 4),
            "cash_adequacy_score":         round(self.cash_adequacy_score, 4),
            "exposure_compliance_score":   round(self.exposure_compliance_score, 4),
            "consistency_score":           round(self.consistency_score, 4),
            "dimension_scores":            [d.to_dict() for d in self.dimension_scores],
            "assessed_at":                 self.assessed_at,
        }


# ---------------------------------------------------------------------------
# Assessor
# ---------------------------------------------------------------------------

class AllocationQualityAssessor:
    """
    Scores an AllocationPlan across 5 dimensions.

    Weights:
        capital_utilisation   30 %
        constraint_compliance 25 %
        cash_adequacy         20 %
        exposure_compliance   15 %
        consistency           10 %
    """

    _WEIGHTS = {
        "capital_utilisation":   0.30,
        "constraint_compliance": 0.25,
        "cash_adequacy":         0.20,
        "exposure_compliance":   0.15,
        "consistency":           0.10,
    }

    def __init__(self, acceptable_threshold: float = 0.60) -> None:
        self._threshold = acceptable_threshold

    def assess(
        self,
        plan:              Any,                        # AllocationPlan (duck-typed)
        validator_report:  AllocationValidationReport,
        exposure_checks:   Optional[List[ExposureCheck]] = None,
    ) -> AllocationQualityReport:

        dims: List[AllocationDimensionScore] = []

        # ---- 1. Capital utilisation (target: 80–100%) -------------------
        util      = getattr(plan, "utilisation_rate", 0.0)
        util_score = _utilisation_score(util)
        dims.append(AllocationDimensionScore(
            dimension = "capital_utilisation",
            score     = util_score,
            passed    = util_score >= 0.60,
            message   = f"Utilisation {util:.1%}",
        ))

        # ---- 2. Constraint compliance (from validator report) ----------
        pass_rate     = validator_report.pass_rate
        compliance    = _compliance_score(validator_report)
        dims.append(AllocationDimensionScore(
            dimension = "constraint_compliance",
            score     = compliance,
            passed    = compliance >= 0.60,
            message   = f"Validator pass rate {pass_rate:.1%}",
        ))

        # ---- 3. Cash adequacy -----------------------------------------
        cash_pct  = getattr(plan, "cash_capital", 0.0) / max(getattr(plan, "total_capital", 1.0), 1.0)
        cash_score= _cash_adequacy_score(cash_pct)
        dims.append(AllocationDimensionScore(
            dimension = "cash_adequacy",
            score     = cash_score,
            passed    = cash_score >= 0.60,
            message   = f"Cash {cash_pct:.1%}",
        ))

        # ---- 4. Exposure compliance -----------------------------------
        exp_checks = exposure_checks or []
        exp_score  = _exposure_score(exp_checks)
        dims.append(AllocationDimensionScore(
            dimension = "exposure_compliance",
            score     = exp_score,
            passed    = exp_score >= 0.60,
            message   = f"{len(exp_checks)} exposure check(s)",
        ))

        # ---- 5. Consistency (position count vs blueprint) -------------
        n_alloc    = len(getattr(plan, "allocations", []))
        cons_score = 1.0 if n_alloc > 0 else 0.5
        dims.append(AllocationDimensionScore(
            dimension = "consistency",
            score     = cons_score,
            passed    = cons_score >= 0.50,
            message   = f"{n_alloc} position(s) allocated",
        ))

        # ---- Overall weighted score -----------------------------------
        dim_map = {d.dimension: d.score for d in dims}
        overall = sum(self._WEIGHTS[k] * dim_map.get(k, 0.0) for k in self._WEIGHTS)

        return AllocationQualityReport(
            portfolio_id                 = getattr(plan, "portfolio_id", ""),
            plan_id                      = getattr(plan, "plan_id", ""),
            dimension_scores             = tuple(dims),
            overall_score                = overall,
            grade                        = _grade(overall),
            is_acceptable                = overall >= self._threshold,
            threshold                    = self._threshold,
            capital_utilisation_score    = dim_map.get("capital_utilisation", 0.0),
            constraint_compliance_score  = dim_map.get("constraint_compliance", 0.0),
            cash_adequacy_score          = dim_map.get("cash_adequacy", 0.0),
            exposure_compliance_score    = dim_map.get("exposure_compliance", 0.0),
            consistency_score            = dim_map.get("consistency", 0.0),
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _utilisation_score(util: float) -> float:
    """Score capital utilisation. Target range 0.80–1.00."""
    if util < 0:
        return 0.0
    if util > 1.02:   # Over-leveraged
        return max(0.0, 1.0 - (util - 1.0) * 5)
    if util >= 0.80:
        return 1.0
    if util >= 0.50:
        return 0.5 + (util - 0.50) / 0.30 * 0.5
    return util / 0.50 * 0.5


def _compliance_score(report: AllocationValidationReport) -> float:
    if report.failures > 0:
        return 0.0
    if report.warnings > 0:
        return max(0.50, report.pass_rate)
    return 1.0


def _cash_adequacy_score(cash_pct: float) -> float:
    """
    Best when 5–20% cash.
    < 2% → very low (risk of shortfall).
    > 30% → excess cash drag.
    """
    if cash_pct < 0:
        return 0.0
    if cash_pct < 0.02:
        return cash_pct / 0.02 * 0.50
    if cash_pct <= 0.20:
        return 1.0
    if cash_pct <= 0.30:
        return 1.0 - (cash_pct - 0.20) / 0.10 * 0.40
    return max(0.0, 0.60 - (cash_pct - 0.30) * 2)


def _exposure_score(checks: List[ExposureCheck]) -> float:
    if not checks:
        return 1.0
    violations = sum(1 for c in checks if c.outcome == ExposureOutcome.VIOLATED)
    warnings   = sum(1 for c in checks if c.outcome == ExposureOutcome.WARNING)
    n          = len(checks)
    if violations >= n:
        return 0.0
    score = 1.0 - (violations / n) * 0.70 - (warnings / n) * 0.20
    return max(0.0, score)
