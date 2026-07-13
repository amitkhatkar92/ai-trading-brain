"""tests/unit/investment/strategy/portfolio/test_rebalancing.py
Tests for RebalancePolicy, RebalanceScheduler, RebalanceHistory,
and RebalancingEngine.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from typing import List

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioType, PortfolioState
)
from iios.investment.strategy.portfolio.strategy_allocation import (
    StrategyAllocation, AllocationMethod
)
from iios.investment.strategy.portfolio.rebalance_policy import (
    RebalancePolicy, RebalanceTrigger, DEFAULT_POLICY, AGGRESSIVE_POLICY
)
from iios.investment.strategy.portfolio.rebalance_scheduler import RebalanceScheduler
from iios.investment.strategy.portfolio.rebalance_history import (
    RebalanceHistory, RebalanceStatus
)
from iios.investment.strategy.portfolio.rebalancing_engine import RebalancingEngine
from iios.investment.strategy.portfolio.construction_constraints import DEFAULT_CONSTRAINTS
from iios.investment.strategy.portfolio.portfolio_lifecycle import PortfolioLifecycle
from tests.unit.investment.strategy.portfolio.conftest import make_strategy


def _make_active_portfolio(n: int = 3) -> StrategyPortfolio:
    p = StrategyPortfolio("p1", "Test", PortfolioType.EQUAL_WEIGHT, state=PortfolioState.ACTIVE)
    w = 1.0 / n
    for i in range(n):
        p.add_strategy(
            StrategyAllocation(f"s{i}", f"S{i}", w, w, allocation_method=AllocationMethod.EQUAL_WEIGHT)
        )
    return p


def _strategies_for_portfolio(p: StrategyPortfolio) -> List[PortfolioStrategy]:
    return [
        make_strategy(a.strategy_id, name=a.strategy_name)
        for a in p.active_allocations()
    ]


# ── RebalancePolicy ───────────────────────────────────────────────────────────

class TestRebalancePolicy:
    def test_default_policy_has_triggers(self):
        triggers = DEFAULT_POLICY.active_triggers()
        assert len(triggers) >= 1

    def test_aggressive_policy_more_triggers(self):
        assert len(AGGRESSIVE_POLICY.active_triggers()) >= len(DEFAULT_POLICY.active_triggers())

    def test_custom_policy_no_triggers(self):
        p = RebalancePolicy(enable_time_trigger=False, enable_drift_trigger=False)
        assert len(p.active_triggers()) == 0

    def test_to_dict_keys(self):
        d = DEFAULT_POLICY.to_dict()
        assert "policy_name" in d
        assert "time_based_days" in d


# ── RebalanceScheduler ────────────────────────────────────────────────────────

class TestRebalanceScheduler:
    def test_time_trigger_fires(self):
        p = _make_active_portfolio()
        # Set created_at to 31 days ago
        p.created_at = datetime.now(timezone.utc) - timedelta(days=31)
        p.last_rebalanced = None
        scheduler = RebalanceScheduler()
        policy = RebalancePolicy(time_based_days=30, enable_drift_trigger=False)
        dec = scheduler.is_due(p, policy)
        assert dec.is_due
        assert RebalanceTrigger.TIME_BASED.value in dec.triggers

    def test_time_trigger_not_fired_recently(self):
        p = _make_active_portfolio()
        p.created_at = datetime.now(timezone.utc) - timedelta(days=5)
        p.last_rebalanced = None
        scheduler = RebalanceScheduler()
        policy = RebalancePolicy(time_based_days=30, enable_drift_trigger=False)
        dec = scheduler.is_due(p, policy)
        assert not dec.is_due

    def test_drift_trigger_fires(self):
        p = _make_active_portfolio()
        # Force large drift
        a = list(p.allocations.values())[0]
        a.weight      = 0.70
        a.target_weight = 0.33

        scheduler = RebalanceScheduler()
        policy = RebalancePolicy(drift_threshold=0.05, enable_time_trigger=False)
        dec = scheduler.is_due(p, policy)
        assert dec.is_due
        assert RebalanceTrigger.THRESHOLD_BASED.value in dec.triggers

    def test_cooldown_prevents_rebalance(self):
        h = RebalanceHistory()
        rec = h.record("p1", "time_based", {}, {}, 0.05, "test")
        scheduler = RebalanceScheduler(history=h)
        p = _make_active_portfolio()
        p.portfolio_id = "p1"
        policy = RebalancePolicy(cooldown_days=7)
        dec = scheduler.is_due(p, policy)
        assert not dec.is_due

    def test_decision_to_dict(self):
        p = _make_active_portfolio()
        scheduler = RebalanceScheduler()
        dec = scheduler.is_due(p, DEFAULT_POLICY)
        d = dec.to_dict()
        assert "is_due" in d
        assert "triggers" in d


# ── RebalanceHistory ──────────────────────────────────────────────────────────

class TestRebalanceHistory:
    def test_record_and_latest(self):
        h = RebalanceHistory()
        rec = h.record("p1", "time_based", {"s1": 0.5}, {"s1": 0.5}, 0.0, "test")
        assert h.latest("p1") == rec

    def test_history_n(self):
        h = RebalanceHistory()
        for _ in range(5):
            h.record("p1", "time_based", {}, {}, 0.0)
        assert len(h.history("p1", n=3)) == 3

    def test_none_for_unknown(self):
        h = RebalanceHistory()
        assert h.latest("unknown") is None


# ── RebalancingEngine ─────────────────────────────────────────────────────────

class TestRebalancingEngine:
    def test_rebalance_not_due_returns_false(self):
        eng = RebalancingEngine()
        p   = _make_active_portfolio()
        # No time or drift trigger should fire for a new portfolio with no drift
        strats = _strategies_for_portfolio(p)
        policy = RebalancePolicy(
            time_based_days=30, drift_threshold=0.05,
            enable_drift_trigger=True, enable_time_trigger=True,
        )
        result = eng.rebalance(p, strats, policy, DEFAULT_CONSTRAINTS, force=False)
        # drift is 0 and created < 30 days ago → not due
        assert result.rebalanced is False

    def test_force_rebalance_executes(self):
        eng = RebalancingEngine()
        p   = _make_active_portfolio()
        strats = _strategies_for_portfolio(p)
        result = eng.rebalance(p, strats, DEFAULT_POLICY, DEFAULT_CONSTRAINTS, force=True)
        assert result.rebalanced is True

    def test_rebalance_weights_sum_to_one(self):
        eng = RebalancingEngine()
        p   = _make_active_portfolio()
        strats = _strategies_for_portfolio(p)
        result = eng.rebalance(p, strats, DEFAULT_POLICY, DEFAULT_CONSTRAINTS, force=True)
        if result.rebalanced:
            assert abs(sum(result.weight_after.values()) - 1.0) < 1e-6

    def test_rebalance_recorded_in_history(self):
        h   = RebalanceHistory()
        eng = RebalancingEngine(history=h)
        p   = _make_active_portfolio()
        strats = _strategies_for_portfolio(p)
        eng.rebalance(p, strats, DEFAULT_POLICY, DEFAULT_CONSTRAINTS, force=True)
        assert h.count("p1") >= 1

    def test_rebalance_transitions_to_rebalanced(self):
        lc  = PortfolioLifecycle()
        h   = RebalanceHistory()
        eng = RebalancingEngine(lifecycle=lc, history=h)
        p   = _make_active_portfolio()
        strats = _strategies_for_portfolio(p)
        result = eng.rebalance(p, strats, DEFAULT_POLICY, DEFAULT_CONSTRAINTS, force=True)
        if result.rebalanced:
            assert p.state == PortfolioState.REBALANCED

    def test_rebalance_archived_raises(self):
        eng = RebalancingEngine()
        p   = _make_active_portfolio()
        p.state = PortfolioState.ARCHIVED
        with pytest.raises(ValueError):
            eng.rebalance(p, [], DEFAULT_POLICY, DEFAULT_CONSTRAINTS)

    def test_result_to_dict(self):
        eng = RebalancingEngine()
        p   = _make_active_portfolio()
        strats = _strategies_for_portfolio(p)
        result = eng.rebalance(p, strats, DEFAULT_POLICY, DEFAULT_CONSTRAINTS, force=True)
        d = result.to_dict()
        assert "portfolio_id" in d
        assert "rebalanced" in d
