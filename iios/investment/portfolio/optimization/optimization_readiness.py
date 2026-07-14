"""iios/investment/portfolio/optimization/optimization_readiness.py

Determines whether an OptimizationPlan is ready to be passed downstream.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.optimization.optimization_validator import (
    OptimizationValidationReport,
)
from iios.investment.portfolio.optimization.constraint_validator import (
    ConstraintValidationReport,
)


@dataclass(frozen=True)
class OptimizationReadinessAssessment:
    """Binary readiness decision for an OptimizationPlan."""

    assessment_id:       str               = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str               = ""
    plan_id:             str               = ""
    is_ready:            bool              = False

    weights_valid:       bool              = False
    constraints_feasible:bool              = False
    converged:           bool              = False
    no_hard_violations:  bool              = False

    blocking_reasons:    Tuple[str, ...]   = field(default_factory=tuple)
    warnings:            Tuple[str, ...]   = field(default_factory=tuple)

    assessed_at:         float             = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id":       self.assessment_id,
            "portfolio_id":        self.portfolio_id,
            "plan_id":             self.plan_id,
            "is_ready":            self.is_ready,
            "weights_valid":       self.weights_valid,
            "constraints_feasible":self.constraints_feasible,
            "converged":           self.converged,
            "no_hard_violations":  self.no_hard_violations,
            "blocking_reasons":    list(self.blocking_reasons),
            "warnings":            list(self.warnings),
            "assessed_at":         self.assessed_at,
        }


class OptimizationReadinessValidator:
    """Aggregates validation + constraint reports into a readiness decision."""

    def validate(
        self,
        plan:                Any,   # OptimizationPlan (duck-typed)
        validation_report:   OptimizationValidationReport,
        constraint_report:   Optional[ConstraintValidationReport] = None,
    ) -> OptimizationReadinessAssessment:
        blocking: List[str] = []
        warnings: List[str] = []

        # -- Weight integrity --------------------------------------------
        weights_ok = validation_report.failures == 0
        if not weights_ok:
            blocking.append(
                f"{validation_report.failures} validation failure(s): "
                + "; ".join(f.message for f in validation_report.failed_findings[:3])
            )

        # -- Convergence -------------------------------------------------
        converged = getattr(plan, "converged", True)
        if not converged:
            warnings.append("Optimization did not fully converge")

        # -- Constraint feasibility --------------------------------------
        if constraint_report is not None:
            constraints_ok = constraint_report.is_feasible
            if not constraints_ok:
                blocking.append(
                    f"{constraint_report.violations} constraint violation(s)"
                )
        else:
            constraints_ok = True

        # -- Validation warnings ----------------------------------------
        for f in validation_report.findings:
            if f.outcome.value == "warning":
                warnings.append(f.message)

        is_ready = len(blocking) == 0

        return OptimizationReadinessAssessment(
            portfolio_id        = getattr(plan, "portfolio_id", ""),
            plan_id             = getattr(plan, "plan_id", ""),
            is_ready            = is_ready,
            weights_valid       = weights_ok,
            constraints_feasible= constraints_ok,
            converged           = converged,
            no_hard_violations  = constraints_ok,
            blocking_reasons    = tuple(blocking),
            warnings            = tuple(warnings),
        )
