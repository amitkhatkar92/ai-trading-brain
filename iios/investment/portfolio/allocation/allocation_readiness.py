"""iios/investment/portfolio/allocation/allocation_readiness.py

Determines whether an AllocationPlan is ready to be passed downstream.
Readiness is a HARD gate: plan MUST be structurally valid, cash-adequate,
and capital-conserving.  Quality is advisory.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from iios.investment.portfolio.allocation.allocation_validator import AllocationValidationReport
from iios.investment.portfolio.allocation.exposure_limits import ExposureCheck, ExposureOutcome


@dataclass(frozen=True)
class AllocationReadinessAssessment:
    """
    Binary readiness decision plus supporting detail.
    """

    assessment_id:       str                    = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:        str                    = ""
    plan_id:             str                    = ""
    is_ready:            bool                   = False

    # Hard gates
    capital_conserved:   bool                   = False
    constraints_satisfied:bool                  = False
    cash_adequate:       bool                   = False
    no_blocking_violations:bool                 = False

    # Summaries
    blocking_reasons:    Tuple[str, ...]        = field(default_factory=tuple)
    warnings:            Tuple[str, ...]        = field(default_factory=tuple)
    health_status:       str                    = "unknown"

    assessed_at:         float                  = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id":        self.assessment_id,
            "portfolio_id":         self.portfolio_id,
            "plan_id":              self.plan_id,
            "is_ready":             self.is_ready,
            "capital_conserved":    self.capital_conserved,
            "constraints_satisfied":self.constraints_satisfied,
            "cash_adequate":        self.cash_adequate,
            "no_blocking_violations":self.no_blocking_violations,
            "blocking_reasons":     list(self.blocking_reasons),
            "warnings":             list(self.warnings),
            "health_status":        self.health_status,
            "assessed_at":          self.assessed_at,
        }


class AllocationReadinessValidator:
    """
    Aggregates validator report + exposure checks into a readiness decision.
    """

    def validate(
        self,
        plan:              Any,                        # AllocationPlan (duck-typed)
        validator_report:  AllocationValidationReport,
        exposure_checks:   Optional[List[ExposureCheck]] = None,
    ) -> AllocationReadinessAssessment:
        blocking: List[str] = []
        warnings: List[str] = []

        # -- Capital conservation -----------------------------------------
        capital_conserved = validator_report.is_valid and not any(
            f.category == "capital_conservation" and f.is_blocking
            for f in validator_report.findings
        )
        if not capital_conserved:
            blocking.append("Capital not conserved")

        # -- Constraint compliance ----------------------------------------
        constraints_ok = validator_report.failures == 0
        if not constraints_ok:
            blocking.append(
                f"{validator_report.failures} constraint failure(s): "
                + "; ".join(f.message for f in validator_report.failed_findings[:3])
            )

        # -- Cash adequacy -----------------------------------------------
        cash_cap = getattr(plan, "cash_capital", -1.0)
        cash_ok  = cash_cap >= 0
        if not cash_ok:
            blocking.append(f"Negative cash ${cash_cap:.2f}")

        # -- Exposure violations -----------------------------------------
        exp_checks = exposure_checks or []
        hard_violations = [c for c in exp_checks if c.outcome == ExposureOutcome.VIOLATED]
        no_hard_exp     = len(hard_violations) == 0
        if not no_hard_exp:
            blocking.append(
                f"{len(hard_violations)} hard exposure violation(s): "
                + "; ".join(c.message for c in hard_violations[:2])
            )

        # -- Warnings from validator ------------------------------------
        for f in validator_report.warning_findings:
            warnings.append(f.message)
        soft_exp = [c for c in exp_checks if c.outcome.value == "warning"]
        for c in soft_exp:
            warnings.append(c.message)

        is_ready = len(blocking) == 0

        return AllocationReadinessAssessment(
            portfolio_id          = getattr(plan, "portfolio_id", ""),
            plan_id               = getattr(plan, "plan_id", ""),
            is_ready              = is_ready,
            capital_conserved     = capital_conserved,
            constraints_satisfied = constraints_ok,
            cash_adequate         = cash_ok,
            no_blocking_violations= no_hard_exp,
            blocking_reasons      = tuple(blocking),
            warnings              = tuple(warnings),
            health_status         = "ready" if is_ready else "not_ready",
        )
