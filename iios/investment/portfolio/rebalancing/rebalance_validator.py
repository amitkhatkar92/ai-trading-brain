"""iios/investment/portfolio/rebalancing/rebalance_validator.py

Main rebalancing validator: orchestrates all validation checks.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from iios.investment.portfolio.rebalancing.allocation_drift import AllocationDrift
from iios.investment.portfolio.rebalancing.cost_validator import CostValidator
from iios.investment.portfolio.rebalancing.execution_estimator import ExecutionEstimate
from iios.investment.portfolio.rebalancing.policy_validator import PolicyValidator
from iios.investment.portfolio.rebalancing.rebalance_policy import RebalancePolicy
from iios.investment.portfolio.rebalancing.rebalancing_types import (
    CurrentPosition, TargetPosition, ValidationStatus, now_utc,
)
from iios.investment.portfolio.rebalancing.trade_planner import TradePlan
from iios.investment.portfolio.rebalancing.validation_report import (
    ValidationCheck, ValidationReport, build_validation_report,
)


@dataclass(frozen=True)
class MasterValidationReport:
    """Combined validation report from all validators."""

    report_id:       str              = field(default_factory=lambda: str(uuid.uuid4()))
    portfolio_id:    str              = ""
    created_at:      str              = field(default_factory=now_utc)

    overall_status:  ValidationStatus = ValidationStatus.PASSED
    is_valid:        bool             = True

    policy_report:   Optional[ValidationReport] = None
    cost_report:     Optional[ValidationReport] = None
    integrity_check: Optional[ValidationCheck]  = None

    # Aggregate
    total_checks:    int   = 0
    n_passed:        int   = 0
    n_warnings:      int   = 0
    n_failed:        int   = 0

    blocking_issues: tuple = field(default_factory=tuple)  # str
    advisory_issues: tuple = field(default_factory=tuple)  # str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status":  self.overall_status.value,
            "is_valid":        self.is_valid,
            "n_passed":        self.n_passed,
            "n_warnings":      self.n_warnings,
            "n_failed":        self.n_failed,
            "blocking_issues": list(self.blocking_issues),
            "advisory_issues": list(self.advisory_issues),
        }


class RebalanceValidator:
    """Orchestrates all rebalancing validation checks."""

    def __init__(
        self,
        policy_validator: Optional[PolicyValidator] = None,
        cost_validator:   Optional[CostValidator]   = None,
    ) -> None:
        self._policy_val = policy_validator or PolicyValidator()
        self._cost_val   = cost_validator   or CostValidator()

    def validate(
        self,
        trade_plan:    TradePlan,
        policy:        RebalancePolicy,
        current:       List[CurrentPosition],
        target:        List[TargetPosition],
        alloc_drift:   AllocationDrift,
        execution_est: Optional[ExecutionEstimate] = None,
        portfolio_id:  str = "",
    ) -> MasterValidationReport:

        if execution_est is None:
            execution_est = trade_plan.execution_estimate

        from iios.investment.portfolio.rebalancing.execution_estimator import ExecutionEstimate as EE
        if execution_est is None:
            execution_est = EE()

        # Policy validation
        pol_report = self._policy_val.validate(
            trade_plan, policy, current, target, execution_est
        )

        # Cost validation
        cost_report = self._cost_val.validate(
            trade_plan, execution_est, alloc_drift, portfolio_id
        )

        # Portfolio integrity
        integrity = _check_integrity(current, target, trade_plan)

        # Aggregate
        all_reports = [pol_report, cost_report]
        n_pass = sum(r.n_passed for r in all_reports) + (1 if integrity.status == ValidationStatus.PASSED else 0)
        n_warn = sum(r.n_warnings for r in all_reports) + (1 if integrity.status == ValidationStatus.WARNING else 0)
        n_fail = sum(r.n_failed for r in all_reports) + (1 if integrity.status == ValidationStatus.FAILED else 0)

        is_valid = n_fail == 0

        if n_fail > 0:
            overall = ValidationStatus.FAILED
        elif n_warn > 0:
            overall = ValidationStatus.WARNING
        else:
            overall = ValidationStatus.PASSED

        blockers = (
            tuple(f for r in all_reports for f in [r.primary_failure] if f)
            + ((integrity.detail,) if integrity.status == ValidationStatus.FAILED else ())
        )
        advisories = tuple(w for r in all_reports for w in r.warnings)

        return MasterValidationReport(
            portfolio_id    = portfolio_id,
            overall_status  = overall,
            is_valid        = is_valid,
            policy_report   = pol_report,
            cost_report     = cost_report,
            integrity_check = integrity,
            total_checks    = n_pass + n_warn + n_fail,
            n_passed        = n_pass,
            n_warnings      = n_warn,
            n_failed        = n_fail,
            blocking_issues = blockers,
            advisory_issues = advisories,
        )


def _check_integrity(
    current:    List[CurrentPosition],
    target:     List[TargetPosition],
    trade_plan: TradePlan,
) -> ValidationCheck:
    """Basic integrity checks on the rebalancing plan."""
    if not target:
        return ValidationCheck(
            check_id    = "integrity",
            description = "Portfolio integrity check",
            status      = ValidationStatus.FAILED,
            detail      = "No target positions provided",
            severity    = "error",
        )
    if not trade_plan.changes:
        return ValidationCheck(
            check_id    = "integrity",
            description = "Portfolio integrity check",
            status      = ValidationStatus.WARNING,
            detail      = "No trades required — portfolio already at target",
            severity    = "warning",
        )
    return ValidationCheck(
        check_id    = "integrity",
        description = "Portfolio integrity check",
        status      = ValidationStatus.PASSED,
        detail      = f"{len(trade_plan.changes)} trades planned",
    )
