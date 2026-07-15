"""test_trade_planner.py — position changes, prioritization, estimation, planning."""
from __future__ import annotations

import pytest

from iios.investment.portfolio.rebalancing import (
    ExecutionEstimate,
    ExecutionEstimator,
    PolicyRegistry,
    TradePlan,
    TradePlanner,
    TradePriority,
    TradeSide,
    assign_trade_priority,
    compute_position_changes,
    prioritize_trades,
)


# ---------------------------------------------------------------------------
# PositionChange
# ---------------------------------------------------------------------------

class TestPositionChanges:
    def test_returns_list(self, drifted_current, drifted_target):
        changes = compute_position_changes(drifted_current, drifted_target, 0.005)
        assert isinstance(changes, list)

    def test_buys_and_sells(self, drifted_current, drifted_target):
        changes = compute_position_changes(drifted_current, drifted_target, 0.005)
        sides = {c.trade_side for c in changes}
        assert TradeSide.BUY in sides
        assert TradeSide.SELL in sides

    def test_abs_change_positive(self, drifted_current, drifted_target):
        changes = compute_position_changes(drifted_current, drifted_target, 0.005)
        for c in changes:
            assert c.abs_change >= 0.0

    def test_no_micro_trades(self, balanced_current, balanced_target):
        changes = compute_position_changes(balanced_current, balanced_target, 0.005)
        for c in changes:
            assert c.abs_change >= 0.005 or c.trade_side == TradeSide.HOLD

    def test_new_position_detected(self, diverse_current, diverse_target):
        changes = compute_position_changes(diverse_current, diverse_target, 0.001)
        new_syms = {c.symbol for c in changes if c.is_new_position}
        assert "WIPRO" in new_syms

    def test_exit_position_detected(self, diverse_current, diverse_target):
        changes = compute_position_changes(diverse_current, diverse_target, 0.001)
        exit_syms = {c.symbol for c in changes if c.is_full_exit}
        assert "DRREDDY" in exit_syms

    def test_frozen(self, drifted_current, drifted_target):
        changes = compute_position_changes(drifted_current, drifted_target, 0.005)
        if changes:
            with pytest.raises((TypeError, AttributeError)):
                changes[0].abs_change = 99.0  # type: ignore

    def test_empty_inputs(self):
        changes = compute_position_changes([], [], 0.005)
        assert changes == []


# ---------------------------------------------------------------------------
# Trade priority
# ---------------------------------------------------------------------------

class TestTradePriority:
    def test_prioritize_returns_sorted(self, drifted_current, drifted_target):
        reg = PolicyRegistry()
        policy = reg.default_policy()
        changes = compute_position_changes(drifted_current, drifted_target, 0.005)
        if not changes:
            return
        ordered = prioritize_trades(changes, policy)
        assert len(ordered) == len(changes)

    def test_buys_before_sells(self, concentrated_current, concentrated_target):
        reg = PolicyRegistry()
        policy = reg.default_policy()
        changes = compute_position_changes(concentrated_current, concentrated_target, 0.005)
        ordered = prioritize_trades(changes, policy)
        # Among same-priority changes, buys should precede sells
        prio_groups: dict = {}
        for c in ordered:
            prio_groups.setdefault(c.priority, []).append(c.trade_side)
        for grp in prio_groups.values():
            buy_positions = [i for i, s in enumerate(grp) if s == TradeSide.BUY]
            sell_positions = [i for i, s in enumerate(grp) if s == TradeSide.SELL]
            if buy_positions and sell_positions:
                assert min(buy_positions) < max(sell_positions)


# ---------------------------------------------------------------------------
# ExecutionEstimator
# ---------------------------------------------------------------------------

class TestExecutionEstimator:
    def test_estimate_returns_result(self, drifted_current, drifted_target):
        estimator = ExecutionEstimator()
        changes = compute_position_changes(drifted_current, drifted_target, 0.005)
        result = estimator.estimate(changes, portfolio_value=10_000_000)
        assert isinstance(result, ExecutionEstimate)

    def test_cost_positive(self, drifted_current, drifted_target):
        estimator = ExecutionEstimator()
        changes = compute_position_changes(drifted_current, drifted_target, 0.005)
        result = estimator.estimate(changes, 10_000_000)
        if changes:
            assert result.total_cost_pct > 0.0

    def test_turnover_matches_changes(self, drifted_current, drifted_target):
        estimator = ExecutionEstimator()
        changes = compute_position_changes(drifted_current, drifted_target, 0.005)
        result = estimator.estimate(changes, 10_000_000)
        # turnover = Σ abs_change / 2 (no double-counting buys+sells)
        expected_turnover = sum(c.abs_change for c in changes) / 2.0
        assert abs(result.total_turnover - expected_turnover) < 1e-6

    def test_empty_changes(self):
        estimator = ExecutionEstimator()
        result = estimator.estimate([], 10_000_000)
        assert result.total_cost_pct == 0.0
        assert result.n_trades == 0

    def test_frozen(self, drifted_current, drifted_target):
        estimator = ExecutionEstimator()
        changes = compute_position_changes(drifted_current, drifted_target, 0.005)
        result = estimator.estimate(changes, 10_000_000)
        with pytest.raises((TypeError, AttributeError)):
            result.total_cost_pct = 99.0  # type: ignore


# ---------------------------------------------------------------------------
# TradePlanner
# ---------------------------------------------------------------------------

class TestTradePlanner:
    def _policy(self):
        return PolicyRegistry().default_policy()

    def test_plan_returns_result(self, drifted_current, drifted_target):
        planner = TradePlanner()
        plan = planner.plan(
            current=drifted_current,
            target=drifted_target,
            policy=self._policy(),
            portfolio_id="PF",
            portfolio_value=10_000_000,
        )
        assert isinstance(plan, TradePlan)

    def test_plan_has_buys_and_sells(self, drifted_current, drifted_target):
        planner = TradePlanner()
        plan = planner.plan(
            current=drifted_current,
            target=drifted_target,
            policy=self._policy(),
            portfolio_id="PF",
            portfolio_value=10_000_000,
        )
        assert plan.n_buys > 0
        assert plan.n_sells > 0

    def test_plan_total_turnover(self, drifted_current, drifted_target):
        planner = TradePlanner()
        plan = planner.plan(
            current=drifted_current,
            target=drifted_target,
            policy=self._policy(),
            portfolio_id="PF",
            portfolio_value=10_000_000,
        )
        assert plan.total_turnover > 0.0

    def test_balanced_plan_minimal_changes(self, balanced_current, balanced_target):
        planner = TradePlanner()
        plan = planner.plan(
            current=balanced_current,
            target=balanced_target,
            policy=self._policy(),
            portfolio_id="PF",
            portfolio_value=10_000_000,
        )
        assert plan.total_turnover < 0.01   # very small

    def test_plan_frozen(self, drifted_current, drifted_target):
        planner = TradePlanner()
        plan = planner.plan(
            current=drifted_current,
            target=drifted_target,
            policy=self._policy(),
            portfolio_id="PF",
            portfolio_value=10_000_000,
        )
        with pytest.raises((TypeError, AttributeError)):
            plan.total_turnover = 99.0  # type: ignore

    def test_plan_changes_tuple(self, drifted_current, drifted_target):
        planner = TradePlanner()
        plan = planner.plan(
            current=drifted_current,
            target=drifted_target,
            policy=self._policy(),
            portfolio_id="PF",
            portfolio_value=10_000_000,
        )
        assert isinstance(plan.changes, tuple)

    def test_plan_execution_estimate(self, drifted_current, drifted_target):
        planner = TradePlanner()
        plan = planner.plan(
            current=drifted_current,
            target=drifted_target,
            policy=self._policy(),
            portfolio_id="PF",
            portfolio_value=10_000_000,
        )
        assert plan.execution_estimate is not None

    def test_diverse_plan_new_positions(self, diverse_current, diverse_target):
        planner = TradePlanner()
        plan = planner.plan(
            current=diverse_current,
            target=diverse_target,
            policy=self._policy(),
            portfolio_id="PF",
            portfolio_value=10_000_000,
        )
        assert len(plan.new_positions) >= 1

    def test_diverse_plan_exits(self, diverse_current, diverse_target):
        planner = TradePlanner()
        plan = planner.plan(
            current=diverse_current,
            target=diverse_target,
            policy=self._policy(),
            portfolio_id="PF",
            portfolio_value=10_000_000,
        )
        assert len(plan.exits) >= 1
