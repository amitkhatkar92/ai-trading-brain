"""test_policy.py — policy, registry, rules, policy engine."""
from __future__ import annotations

import pytest

from iios.investment.portfolio.rebalancing import (
    PolicyEngine,
    PolicyEngineResult,
    PolicyParameters,
    PolicyRegistry,
    RebalancePolicy,
    RebalanceTrigger,
    compute_allocation_drift,
    compute_risk_drift,
    evaluate_benefit_cost_rule,
    evaluate_calendar_rule,
    evaluate_cashflow_rule,
    evaluate_risk_rule,
    evaluate_threshold_rule,
    evaluate_volatility_rule,
)


# ---------------------------------------------------------------------------
# PolicyParameters
# ---------------------------------------------------------------------------

class TestPolicyParameters:
    def test_defaults(self):
        p = PolicyParameters()
        assert p.drift_threshold == 0.05
        assert p.max_turnover_per_rebal == 0.30
        assert p.min_benefit_cost_ratio == 1.5

    def test_frozen(self):
        p = PolicyParameters()
        with pytest.raises((TypeError, AttributeError)):
            p.drift_threshold = 0.99  # type: ignore


# ---------------------------------------------------------------------------
# RebalancePolicy
# ---------------------------------------------------------------------------

class TestRebalancePolicy:
    def test_frozen(self):
        p = PolicyParameters()
        pol = RebalancePolicy(
            policy_id="test", name="Test", policy_type="threshold",
            trigger=RebalanceTrigger.THRESHOLD, parameters=p,
        )
        with pytest.raises((TypeError, AttributeError)):
            pol.name = "other"  # type: ignore


# ---------------------------------------------------------------------------
# PolicyRegistry
# ---------------------------------------------------------------------------

class TestPolicyRegistry:
    def test_has_default(self):
        reg = PolicyRegistry()
        default = reg.default_policy()
        assert default is not None
        assert default.is_default is True

    def test_get_by_id(self):
        reg = PolicyRegistry()
        pol = reg.get("threshold")
        assert pol is not None
        assert pol.name == "Threshold Rebalancing"

    def test_get_unknown_returns_none(self):
        reg = PolicyRegistry()
        assert reg.get("nonexistent") is None

    def test_get_or_default_known(self):
        reg = PolicyRegistry()
        pol = reg.get_or_default("calendar_quarterly")
        assert pol.name == "Quarterly Calendar Rebalancing"

    def test_get_or_default_unknown(self):
        reg = PolicyRegistry()
        pol = reg.get_or_default("nonexistent_xyz")
        assert pol.is_default is True

    def test_get_or_default_none(self):
        reg = PolicyRegistry()
        pol = reg.get_or_default(None)
        assert pol.is_default is True

    def test_list_ids(self):
        reg = PolicyRegistry()
        ids = reg.list_ids()
        assert "threshold" in ids
        assert "hybrid" in ids
        assert "conservative" in ids

    def test_all_policies(self):
        reg = PolicyRegistry()
        policies = reg.all()
        assert len(policies) >= 8

    def test_register_custom(self):
        reg = PolicyRegistry()
        params = PolicyParameters(drift_threshold=0.03)
        custom = RebalancePolicy(
            policy_id="my_custom",
            name="My Custom",
            policy_type="threshold",
            trigger=RebalanceTrigger.THRESHOLD,
            parameters=params,
        )
        reg.register(custom)
        assert reg.get("my_custom") is custom

    def test_register_overwrites(self):
        reg = PolicyRegistry()
        params = PolicyParameters()
        p1 = RebalancePolicy(
            policy_id="dup", name="V1", policy_type="threshold",
            trigger=RebalanceTrigger.THRESHOLD, parameters=params,
        )
        p2 = RebalancePolicy(
            policy_id="dup", name="V2", policy_type="threshold",
            trigger=RebalanceTrigger.THRESHOLD, parameters=params,
        )
        reg.register(p1)
        reg.register(p2)
        assert reg.get("dup").name == "V2"


# ---------------------------------------------------------------------------
# Policy rules (pure functions)
# ---------------------------------------------------------------------------

class TestPolicyRules:
    def _make_alloc_drift(self, max_drift: float, total_drift: float):
        from iios.investment.portfolio.rebalancing.allocation_drift import AllocationDrift
        from iios.investment.portfolio.rebalancing.rebalancing_types import DriftLevel
        return AllocationDrift(
            portfolio_id="PF",
            total_abs_drift=total_drift,
            max_abs_drift=max_drift,
            mean_abs_drift=total_drift,
            drift_level=DriftLevel.CRITICAL if max_drift >= 0.10 else DriftLevel.NONE,
        )

    def _make_risk_drift(self, current_risk: float, current_liquidity: float):
        from iios.investment.portfolio.rebalancing.risk_drift import RiskDrift
        from iios.investment.portfolio.rebalancing.rebalancing_types import DriftLevel
        return RiskDrift(
            portfolio_id="PF",
            current_risk=current_risk,
            target_risk=0.5,
            risk_drift=current_risk - 0.5,
            abs_risk_drift=abs(current_risk - 0.5),
            drift_level=DriftLevel.MODERATE,
            current_liquidity=current_liquidity,
            target_liquidity=0.7,
            liquidity_drift=current_liquidity - 0.7,
        )

    def test_threshold_triggered(self):
        alloc = self._make_alloc_drift(0.10, 0.10)
        triggered, reason = evaluate_threshold_rule(alloc, 0.05)
        assert triggered is True
        assert reason != ""

    def test_threshold_not_triggered(self):
        alloc = self._make_alloc_drift(0.03, 0.03)
        triggered, _ = evaluate_threshold_rule(alloc, 0.05)
        assert triggered is False

    def test_calendar_triggered(self):
        triggered, _ = evaluate_calendar_rule(95, 91, 14)
        assert triggered is True

    def test_calendar_not_triggered_too_soon(self):
        triggered, _ = evaluate_calendar_rule(5, 91, 14)
        assert triggered is False

    def test_calendar_not_triggered_min_days(self):
        # Enough calendar days but min_days not yet met
        triggered, _ = evaluate_calendar_rule(10, 7, 14)
        assert triggered is False

    def test_risk_rule_triggered_high_risk(self):
        risk = self._make_risk_drift(0.80, 0.60)
        triggered, _ = evaluate_risk_rule(risk, 0.70, 0.40)
        assert triggered is True

    def test_risk_rule_triggered_low_liquidity(self):
        risk = self._make_risk_drift(0.60, 0.35)
        triggered, _ = evaluate_risk_rule(risk, 0.70, 0.50)
        assert triggered is True

    def test_risk_rule_not_triggered(self):
        risk = self._make_risk_drift(0.50, 0.65)
        triggered, _ = evaluate_risk_rule(risk, 0.70, 0.60)
        assert triggered is False

    def test_volatility_rule_triggered(self):
        triggered, _ = evaluate_volatility_rule(0.30, 0.25)
        assert triggered is True

    def test_volatility_rule_not_triggered(self):
        triggered, _ = evaluate_volatility_rule(0.10, 0.25)
        assert triggered is False

    def test_cashflow_rule_triggered(self):
        triggered, _ = evaluate_cashflow_rule(0.10, 0.03)
        assert triggered is True

    def test_benefit_cost_rule_pass(self):
        triggered, _ = evaluate_benefit_cost_rule(0.03, 0.01, 1.5)
        assert triggered is True

    def test_benefit_cost_rule_fail(self):
        triggered, _ = evaluate_benefit_cost_rule(0.01, 0.02, 1.5)
        assert triggered is False


# ---------------------------------------------------------------------------
# PolicyEngine
# ---------------------------------------------------------------------------

class TestPolicyEngine:
    def _make_policy(self, policy_id: str = "threshold") -> RebalancePolicy:
        reg = PolicyRegistry()
        return reg.get_or_default(policy_id)

    def test_triggered_on_drift(self, drifted_current, drifted_target):
        engine = PolicyEngine()
        policy = self._make_policy()
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        risk  = compute_risk_drift(drifted_current, drifted_target, "PF")
        result = engine.evaluate(
            policy=policy,
            allocation_drift=alloc,
            risk_drift=risk,
            current_positions=drifted_current,
            days_since_rebalance=91.0,
            portfolio_vol=0.15,
            net_cash_flow_pct=0.0,
            estimated_cost=0.001,
            expected_benefit=0.002,
        )
        assert isinstance(result, PolicyEngineResult)
        assert result.triggered is True

    def test_not_triggered_on_balanced(self, balanced_current, balanced_target):
        engine = PolicyEngine()
        policy = self._make_policy()
        alloc = compute_allocation_drift(balanced_current, balanced_target, "PF")
        risk  = compute_risk_drift(balanced_current, balanced_target, "PF")
        result = engine.evaluate(
            policy=policy,
            allocation_drift=alloc,
            risk_drift=risk,
            current_positions=balanced_current,
            days_since_rebalance=30.0,
            portfolio_vol=0.10,
            net_cash_flow_pct=0.0,
            estimated_cost=0.001,
            expected_benefit=0.0001,
        )
        assert result.triggered is False

    def test_result_frozen(self, balanced_current, balanced_target):
        engine = PolicyEngine()
        policy = self._make_policy()
        alloc = compute_allocation_drift(balanced_current, balanced_target, "PF")
        risk  = compute_risk_drift(balanced_current, balanced_target, "PF")
        result = engine.evaluate(
            policy=policy,
            allocation_drift=alloc,
            risk_drift=risk,
            current_positions=balanced_current,
            days_since_rebalance=30.0,
            portfolio_vol=0.10,
            net_cash_flow_pct=0.0,
            estimated_cost=0.001,
            expected_benefit=0.0001,
        )
        with pytest.raises((TypeError, AttributeError)):
            result.triggered = True  # type: ignore

    def test_confidence_in_range(self, drifted_current, drifted_target):
        engine = PolicyEngine()
        policy = self._make_policy()
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        risk  = compute_risk_drift(drifted_current, drifted_target, "PF")
        result = engine.evaluate(
            policy=policy,
            allocation_drift=alloc,
            risk_drift=risk,
            current_positions=drifted_current,
            days_since_rebalance=91.0,
            portfolio_vol=0.15,
            net_cash_flow_pct=0.0,
            estimated_cost=0.001,
            expected_benefit=0.002,
        )
        assert 0.0 <= result.confidence <= 1.0

    def test_hybrid_policy_evaluates(self, drifted_current, drifted_target):
        engine = PolicyEngine()
        policy = self._make_policy("hybrid")
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        risk  = compute_risk_drift(drifted_current, drifted_target, "PF")
        result = engine.evaluate(
            policy=policy,
            allocation_drift=alloc,
            risk_drift=risk,
            current_positions=drifted_current,
            days_since_rebalance=91.0,
            portfolio_vol=0.15,
            net_cash_flow_pct=0.0,
            estimated_cost=0.001,
            expected_benefit=0.002,
        )
        assert isinstance(result, PolicyEngineResult)
