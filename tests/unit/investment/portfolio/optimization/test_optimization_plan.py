"""test_optimization_plan.py — Tests for OptimizationPlan and related dataclasses."""
import pytest

from iios.investment.portfolio.optimization.optimization_plan import (
    OptimizationObjective,
    OptimizationPlan,
    OptimizationRequest,
    OptimizationResult,
    OptimizedPosition,
)
from iios.investment.portfolio.optimization.optimization_types import (
    ConvergenceStatus,
    ObjectiveType,
    OptimizationMethod,
    OptimizationRunStatus,
    WeightChangeStatus,
)


class TestOptimizationObjective:
    def test_default_primary(self):
        obj = OptimizationObjective()
        assert obj.primary == ObjectiveType.MAXIMIZE_SHARPE

    def test_risk_aversion_default(self):
        obj = OptimizationObjective()
        assert obj.risk_aversion >= 0

    def test_frozen(self):
        obj = OptimizationObjective()
        with pytest.raises((AttributeError, TypeError)):
            obj.primary = ObjectiveType.MINIMIZE_RISK  # type: ignore


class TestOptimizedPosition:
    def test_default_construction(self):
        p = OptimizedPosition(symbol="TEST", name="Test Co",
                              prior_weight=0.20, optimized_weight=0.25,
                              weight_change=0.05)
        assert p.symbol == "TEST"
        assert p.is_increased
        assert not p.is_decreased

    def test_decreased(self):
        p = OptimizedPosition(symbol="X", weight_change=-0.05)
        assert p.is_decreased

    def test_unchanged(self):
        p = OptimizedPosition(symbol="X", weight_change=0.0)
        assert p.is_unchanged

    def test_frozen(self):
        p = OptimizedPosition(symbol="X")
        with pytest.raises((AttributeError, TypeError)):
            p.symbol = "Y"  # type: ignore


class TestOptimizationRequest:
    def test_default_construction(self):
        req = OptimizationRequest(portfolio_id="p1", total_capital=1_000_000.0)
        assert req.total_capital == 1_000_000.0
        assert req.method in OptimizationMethod

    def test_unique_ids(self):
        r1 = OptimizationRequest(portfolio_id="p1", total_capital=500_000.0)
        r2 = OptimizationRequest(portfolio_id="p1", total_capital=500_000.0)
        assert r1.request_id != r2.request_id

    def test_cash_reserve_default_in_range(self):
        req = OptimizationRequest(portfolio_id="p", total_capital=1_000_000.0)
        assert 0.0 <= req.cash_reserve_pct < 1.0


class TestOptimizationPlan:
    def _make_plan(self, n_positions=3):
        positions = tuple(
            OptimizedPosition(
                symbol=f"SYM{i}",
                prior_weight=1/n_positions,
                optimized_weight=1/n_positions,
            )
            for i in range(n_positions)
        )
        return OptimizationPlan(
            portfolio_id="p1",
            positions=positions,
            total_capital=1_000_000.0,
        )

    def test_total_positions(self):
        plan = self._make_plan(4)
        assert plan.total_positions == 4

    def test_symbols_tuple(self):
        plan = self._make_plan(3)
        assert len(plan.symbols) == 3
        assert all(s.startswith("SYM") for s in plan.symbols)

    def test_is_empty_false(self):
        plan = self._make_plan(1)
        assert not plan.is_empty

    def test_is_empty_true(self):
        plan = OptimizationPlan(portfolio_id="p1")
        assert plan.is_empty

    def test_get_position_hit(self):
        plan = self._make_plan(3)
        p = plan.get_position("SYM1")
        assert p is not None
        assert p.symbol == "SYM1"

    def test_get_position_miss(self):
        plan = self._make_plan(3)
        assert plan.get_position("NOTEXIST") is None

    def test_schema_version_set(self):
        plan = self._make_plan(2)
        assert plan.schema_version

    def test_unique_plan_ids(self):
        p1 = OptimizationPlan(portfolio_id="p")
        p2 = OptimizationPlan(portfolio_id="p")
        assert p1.plan_id != p2.plan_id


class TestOptimizationResult:
    def test_succeeded_true(self):
        r = OptimizationResult(
            portfolio_id="p",
            status=OptimizationRunStatus.CONVERGED,
        )
        assert r.succeeded

    def test_failed_true(self):
        r = OptimizationResult(
            portfolio_id="p",
            status=OptimizationRunStatus.FAILED,
        )
        assert r.failed

    def test_has_plan_false(self):
        r = OptimizationResult(portfolio_id="p", status=OptimizationRunStatus.FAILED)
        assert not r.has_plan

    def test_has_plan_true(self):
        plan = OptimizationPlan(portfolio_id="p")
        r = OptimizationResult(
            portfolio_id="p",
            status=OptimizationRunStatus.CONVERGED,
            plan=plan,
        )
        assert r.has_plan
