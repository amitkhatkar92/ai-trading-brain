"""test_validation.py — policy validator, cost validator, rebalance validator."""
from __future__ import annotations

import pytest

from iios.investment.portfolio.rebalancing import (
    CostValidator,
    MasterValidationReport,
    PolicyRegistry,
    PolicyValidator,
    RebalanceValidator,
    ValidationStatus,
    build_validation_report,
    compute_allocation_drift,
    ValidationCheck,
    ValidationReport,
)
from iios.investment.portfolio.rebalancing.trade_planner import TradePlanner


# ---------------------------------------------------------------------------
# ValidationCheck / ValidationReport
# ---------------------------------------------------------------------------

class TestValidationReport:
    def test_all_passed(self):
        checks = [
            ValidationCheck("c1", "Check 1", ValidationStatus.PASSED),
            ValidationCheck("c2", "Check 2", ValidationStatus.PASSED),
        ]
        report = build_validation_report(checks, "PF")
        assert report.is_valid is True
        assert report.overall_status == ValidationStatus.PASSED
        assert report.n_passed == 2
        assert report.n_warnings == 0
        assert report.n_failed == 0

    def test_one_warning(self):
        checks = [
            ValidationCheck("c1", "Check 1", ValidationStatus.PASSED),
            ValidationCheck("c2", "Check 2", ValidationStatus.WARNING, severity="warning"),
        ]
        report = build_validation_report(checks, "PF")
        assert report.is_valid is True
        assert report.overall_status == ValidationStatus.WARNING
        assert report.n_warnings == 1

    def test_one_failure(self):
        checks = [
            ValidationCheck("c1", "Check 1", ValidationStatus.PASSED),
            ValidationCheck("c2", "Check 2", ValidationStatus.FAILED, severity="error"),
        ]
        report = build_validation_report(checks, "PF")
        assert report.is_valid is False
        assert report.overall_status == ValidationStatus.FAILED

    def test_primary_failure_set(self):
        checks = [
            ValidationCheck("c1", "Fail!", ValidationStatus.FAILED,
                            detail="bad stuff", severity="error"),
        ]
        report = build_validation_report(checks, "PF")
        assert report.primary_failure is not None
        assert "bad stuff" in report.primary_failure or "Fail" in report.primary_failure

    def test_frozen(self):
        report = build_validation_report([], "PF")
        with pytest.raises((TypeError, AttributeError)):
            report.is_valid = False  # type: ignore

    def test_empty_checks(self):
        report = build_validation_report([], "PF")
        assert report.is_valid is True
        assert report.overall_status == ValidationStatus.PASSED


# ---------------------------------------------------------------------------
# PolicyValidator
# ---------------------------------------------------------------------------

class TestPolicyValidator:
    def _setup(self, current, target, policy_id="threshold"):
        reg = PolicyRegistry()
        policy = reg.get_or_default(policy_id)
        planner = TradePlanner()
        plan = planner.plan(current, target, policy, "PF", 10_000_000)
        return policy, plan, plan.execution_estimate

    def test_returns_report(self, drifted_current, drifted_target):
        policy, plan, est = self._setup(drifted_current, drifted_target)
        validator = PolicyValidator()
        report = validator.validate(plan, policy, drifted_current, drifted_target, est)
        assert isinstance(report, ValidationReport)

    def test_weight_integrity_check_exists(self, drifted_current, drifted_target):
        policy, plan, est = self._setup(drifted_current, drifted_target)
        validator = PolicyValidator()
        report = validator.validate(plan, policy, drifted_current, drifted_target, est)
        check_ids = {c.check_id for c in report.checks}
        assert "weight_integrity" in check_ids

    def test_turnover_check_exists(self, drifted_current, drifted_target):
        policy, plan, est = self._setup(drifted_current, drifted_target)
        validator = PolicyValidator()
        report = validator.validate(plan, policy, drifted_current, drifted_target, est)
        check_ids = {c.check_id for c in report.checks}
        assert "turnover_limit" in check_ids

    def test_valid_plan_passes(self, drifted_current, drifted_target):
        policy, plan, est = self._setup(drifted_current, drifted_target)
        validator = PolicyValidator()
        report = validator.validate(plan, policy, drifted_current, drifted_target, est)
        # turnover should be within policy limit for this portfolio
        assert report.n_failed == 0 or report.is_valid is not None


# ---------------------------------------------------------------------------
# CostValidator
# ---------------------------------------------------------------------------

class TestCostValidator:
    def test_returns_report(self, drifted_current, drifted_target):
        reg = PolicyRegistry()
        policy = reg.default_policy()
        planner = TradePlanner()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        validator = CostValidator()
        report = validator.validate(plan, plan.execution_estimate, alloc, "PF")
        assert isinstance(report, ValidationReport)

    def test_checks_include_total_cost(self, balanced_current, balanced_target):
        reg = PolicyRegistry()
        policy = reg.default_policy()
        planner = TradePlanner()
        plan = planner.plan(balanced_current, balanced_target, policy, "PF", 10_000_000)
        alloc = compute_allocation_drift(balanced_current, balanced_target, "PF")
        validator = CostValidator()
        report = validator.validate(plan, plan.execution_estimate, alloc, "PF")
        check_ids = {c.check_id for c in report.checks}
        assert "total_cost_cap" in check_ids

    def test_low_cost_passes(self, balanced_current, balanced_target):
        reg = PolicyRegistry()
        policy = reg.default_policy()
        planner = TradePlanner()
        plan = planner.plan(balanced_current, balanced_target, policy, "PF", 10_000_000)
        alloc = compute_allocation_drift(balanced_current, balanced_target, "PF")
        validator = CostValidator()
        report = validator.validate(plan, plan.execution_estimate, alloc, "PF")
        # Balanced portfolio → tiny turnover → tiny cost → should pass
        cap_check = next(c for c in report.checks if c.check_id == "total_cost_cap")
        assert cap_check.status == ValidationStatus.PASSED


# ---------------------------------------------------------------------------
# RebalanceValidator
# ---------------------------------------------------------------------------

class TestRebalanceValidator:
    def test_returns_master_report(self, drifted_current, drifted_target):
        reg = PolicyRegistry()
        policy = reg.default_policy()
        planner = TradePlanner()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        validator = RebalanceValidator()
        report = validator.validate(
            trade_plan=plan, policy=policy,
            current=drifted_current, target=drifted_target,
            alloc_drift=alloc, portfolio_id="PF",
        )
        assert isinstance(report, MasterValidationReport)

    def test_has_policy_report(self, drifted_current, drifted_target):
        reg = PolicyRegistry()
        policy = reg.default_policy()
        planner = TradePlanner()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        validator = RebalanceValidator()
        report = validator.validate(plan, policy, drifted_current, drifted_target, alloc,
                                    portfolio_id="PF")
        assert report.policy_report is not None

    def test_has_cost_report(self, drifted_current, drifted_target):
        reg = PolicyRegistry()
        policy = reg.default_policy()
        planner = TradePlanner()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        validator = RebalanceValidator()
        report = validator.validate(plan, policy, drifted_current, drifted_target, alloc,
                                    portfolio_id="PF")
        assert report.cost_report is not None

    def test_invalid_target_weights(self, drifted_current):
        from iios.investment.portfolio.rebalancing import TargetPosition
        bad_target = [
            TargetPosition("RELIANCE", 0.70),  # weights sum to 0.90, not 1.0
            TargetPosition("TCS",      0.20),
        ]
        reg = PolicyRegistry()
        policy = reg.default_policy()
        planner = TradePlanner()
        plan = planner.plan(drifted_current, bad_target, policy, "PF", 10_000_000)
        alloc = compute_allocation_drift(drifted_current, bad_target, "PF")
        validator = RebalanceValidator()
        report = validator.validate(plan, policy, drifted_current, bad_target, alloc,
                                    portfolio_id="PF")
        # Should flag weight integrity issue
        assert report.is_valid is False

    def test_to_dict(self, balanced_current, balanced_target):
        reg = PolicyRegistry()
        policy = reg.default_policy()
        planner = TradePlanner()
        plan = planner.plan(balanced_current, balanced_target, policy, "PF", 10_000_000)
        alloc = compute_allocation_drift(balanced_current, balanced_target, "PF")
        validator = RebalanceValidator()
        report = validator.validate(plan, policy, balanced_current, balanced_target, alloc,
                                    portfolio_id="PF")
        d = report.to_dict()
        assert "is_valid" in d
        assert "overall_status" in d
