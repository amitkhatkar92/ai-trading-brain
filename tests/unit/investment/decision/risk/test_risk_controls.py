"""tests/unit/investment/decision/risk/test_risk_controls.py
Tests for RiskControl, ControlRegistry, ControlEngine, PolicyValidator.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.risk.control_engine import ControlEngine
from iios.investment.decision.risk.control_registry import ControlRegistry
from iios.investment.decision.risk.decision_risk import build_decision_risk
from iios.investment.decision.risk.risk_constants import (
    RiskControlStatus,
    RiskDimension,
    RiskPolicyStatus,
)
from iios.investment.decision.risk.risk_controls import ControlViolation, RiskControl
from iios.investment.decision.risk.risk_policies import PolicyValidator


def _make_dr(overall_risk: float = 40.0, controls_breached: bool = False):
    return build_decision_risk(
        decision_id="D1", subject_id="INFY", subject_type="equity",
        market_risk=overall_risk, company_risk=overall_risk,
        strategy_risk=overall_risk, execution_risk=overall_risk,
        confidence_risk=overall_risk,
        controls_breached=controls_breached,
        scenarios_evaluated=0, version=1,
    )


# ─── RiskControl ─────────────────────────────────────────────────────────────

class TestRiskControl:
    def test_to_dict_has_required_keys(self):
        ctrl = RiskControl(
            control_id="c1", name="Test", description="desc",
            dimension=RiskDimension.MARKET, max_allowed=70.0,
        )
        d = ctrl.to_dict()
        assert "control_id" in d and "max_allowed" in d

    def test_hard_limit_default_true(self):
        ctrl = RiskControl("c1", "T", "d", RiskDimension.MARKET, 70.0)
        assert ctrl.is_hard_limit is True


# ─── ControlViolation ────────────────────────────────────────────────────────

class TestControlViolation:
    def test_hard_limit_breach_property(self):
        ctrl = RiskControl("c1", "T", "d", RiskDimension.MARKET, 70.0, is_hard_limit=True)
        v = ControlViolation(control=ctrl, actual_value=80.0)
        assert v.is_hard_limit_breach is True

    def test_soft_limit_not_hard_breach(self):
        ctrl = RiskControl("c1", "T", "d", RiskDimension.MARKET, 70.0, is_hard_limit=False)
        v = ControlViolation(control=ctrl, actual_value=80.0, status=RiskControlStatus.WARNING)
        assert v.is_hard_limit_breach is False

    def test_to_dict_has_actual_value(self):
        ctrl = RiskControl("c1", "T", "d", RiskDimension.MARKET, 70.0)
        v = ControlViolation(control=ctrl, actual_value=80.0)
        assert "actual_value" in v.to_dict()


# ─── ControlRegistry ─────────────────────────────────────────────────────────

class TestControlRegistry:
    def test_loads_defaults(self):
        reg = ControlRegistry()
        assert reg.count() >= 3

    def test_register_and_get(self):
        reg = ControlRegistry(load_defaults=False)
        ctrl = RiskControl("c1", "T", "d", RiskDimension.MARKET, 70.0)
        reg.register(ctrl)
        assert reg.get("c1") is ctrl

    def test_get_missing_returns_none(self):
        reg = ControlRegistry(load_defaults=False)
        assert reg.get("nonexistent") is None

    def test_remove(self):
        reg = ControlRegistry()
        reg.remove("ctrl_overall_max")
        assert reg.get("ctrl_overall_max") is None

    def test_all_controls_returns_list(self):
        reg = ControlRegistry()
        all_c = reg.all_controls()
        assert isinstance(all_c, list) and len(all_c) >= 3


# ─── ControlEngine ───────────────────────────────────────────────────────────

class TestControlEngine:
    def setup_method(self):
        self.engine = ControlEngine()

    def test_no_violation_when_risk_low(self):
        dr = _make_dr(overall_risk=20.0)
        result = self.engine.evaluate(dr)
        assert not result.hard_breach
        assert len(result.violations) == 0

    def test_hard_breach_when_risk_exceeds_max(self):
        dr = _make_dr(overall_risk=75.0)
        result = self.engine.evaluate(dr)
        assert result.hard_breach

    def test_controls_checked_positive(self):
        dr = _make_dr(overall_risk=20.0)
        result = self.engine.evaluate(dr)
        assert result.controls_checked > 0

    def test_to_dict_structure(self):
        dr = _make_dr(overall_risk=20.0)
        d = self.engine.evaluate(dr).to_dict()
        assert "hard_breach" in d and "violations" in d

    def test_soft_violation_goes_to_warnings(self):
        reg = ControlRegistry(load_defaults=False)
        soft = RiskControl("soft1", "Soft", "d", RiskDimension.EXECUTION, 30.0, is_hard_limit=False)
        reg.register(soft)
        engine = ControlEngine(reg)
        dr = _make_dr(overall_risk=50.0)
        result = engine.evaluate(dr)
        assert len(result.warnings) >= 1
        assert not result.hard_breach

    def test_custom_registry_no_defaults(self):
        reg = ControlRegistry(load_defaults=False)
        engine = ControlEngine(reg)
        dr = _make_dr(overall_risk=90.0)
        result = engine.evaluate(dr)
        assert not result.hard_breach  # no controls registered


# ─── PolicyValidator ─────────────────────────────────────────────────────────

class TestPolicyValidator:
    def setup_method(self):
        self.validator = PolicyValidator()

    def test_compliant_when_low_risk(self):
        dr = _make_dr(overall_risk=30.0)
        r = self.validator.validate(dr)
        assert r.status == RiskPolicyStatus.COMPLIANT

    def test_warning_when_high(self):
        dr = _make_dr(overall_risk=65.0)
        r = self.validator.validate(dr)
        # Could be violation (>=70) or warning (>=60): depends on exact weights
        assert r.status in (RiskPolicyStatus.WARNING, RiskPolicyStatus.VIOLATION)

    def test_violation_when_at_max(self):
        dr = _make_dr(overall_risk=72.0)
        r = self.validator.validate(dr)
        assert r.status == RiskPolicyStatus.VIOLATION

    def test_controls_breached_triggers_violation(self):
        dr = _make_dr(overall_risk=30.0, controls_breached=True)
        r = self.validator.validate(dr)
        assert r.status == RiskPolicyStatus.VIOLATION

    def test_violation_does_not_allow_execution(self):
        dr = _make_dr(overall_risk=72.0)
        r = self.validator.validate(dr)
        assert not r.allows_execution

    def test_compliant_allows_execution(self):
        dr = _make_dr(overall_risk=30.0)
        r = self.validator.validate(dr)
        assert r.allows_execution

    def test_custom_max_allowed(self):
        validator = PolicyValidator(max_allowed_risk=50.0)
        dr = _make_dr(overall_risk=55.0)
        r = validator.validate(dr)
        assert r.status == RiskPolicyStatus.VIOLATION

    def test_to_dict_keys(self):
        dr = _make_dr(overall_risk=30.0)
        d = self.validator.validate(dr).to_dict()
        assert "status" in d and "violations" in d
