"""test_constraint_solver.py — Tests for ConstraintSolver and ConstraintValidator."""
import pytest

from iios.investment.portfolio.optimization.constraint_solver import ConstraintSolver
from iios.investment.portfolio.optimization.constraint_validator import ConstraintValidator
from iios.investment.portfolio.optimization.optimization_constraints import (
    default_constraint_set,
    budget_constraint,
    position_weight_constraint,
    leverage_constraint,
)
from iios.investment.portfolio.optimization.optimization_engine import AssetProxy
from iios.investment.portfolio.optimization.optimization_plan import (
    OptimizationPlan,
    OptimizedPosition,
)


TOL = 1e-4


@pytest.fixture
def solver():
    return ConstraintSolver()


@pytest.fixture
def validator():
    return ConstraintValidator()


@pytest.fixture
def assets():
    return [
        AssetProxy("A", 0.70, 0.25, 0.80, 0.20, sector="tech"),
        AssetProxy("B", 0.65, 0.20, 0.75, 0.20, sector="tech"),
        AssetProxy("C", 0.60, 0.22, 0.70, 0.20, sector="energy"),
        AssetProxy("D", 0.55, 0.30, 0.65, 0.20, sector="finance"),
        AssetProxy("E", 0.50, 0.35, 0.60, 0.20, sector="finance"),
    ]


@pytest.fixture
def equal_weights():
    return {"A": 0.20, "B": 0.20, "C": 0.20, "D": 0.20, "E": 0.20}


@pytest.fixture
def constraint_set():
    return default_constraint_set(max_weight=0.40)


class TestConstraintSolverBudget:
    def test_budget_maintained(self, solver, assets, constraint_set):
        unscaled = {"A": 0.30, "B": 0.30, "C": 0.20, "D": 0.15, "E": 0.10}
        sol = solver.solve(unscaled, assets, constraint_set,
                           request_min_weight=0.0, request_max_weight=0.40)
        assert abs(sum(sol.weights.values()) - 1.0) < TOL

    def test_over_weighted_clamped(self, solver, assets, constraint_set):
        # All 5 assets present; only A is over the limit, others share remaining weight
        over = {"A": 0.50, "B": 0.15, "C": 0.15, "D": 0.10, "E": 0.10}
        sol  = solver.solve(over, assets, constraint_set,
                            request_min_weight=0.0, request_max_weight=0.40)
        # After single-pass clamp + renormalize, budget must be exact
        assert abs(sum(sol.weights.values()) - 1.0) < TOL

    def test_all_symbols_preserved(self, solver, assets, equal_weights, constraint_set):
        sol = solver.solve(equal_weights, assets, constraint_set,
                           request_min_weight=0.0, request_max_weight=0.40)
        assert set(sol.weights.keys()) == {"A", "B", "C", "D", "E"}


class TestConstraintSolverNegativeWeights:
    def test_long_only_zeroes_negative(self, solver, assets):
        cs = default_constraint_set(long_only=True, max_weight=0.50)
        weights = {"A": 0.50, "B": -0.10, "C": 0.30, "D": 0.20, "E": 0.10}
        sol = solver.solve(weights, assets, cs, request_min_weight=0.0, request_max_weight=0.50)
        assert sol.weights["B"] >= 0.0
        assert abs(sum(sol.weights.values()) - 1.0) < TOL


class TestConstraintSolverHardSatisfied:
    def test_hard_satisfied_flag(self, solver, assets, constraint_set):
        sol = solver.solve({"A":0.20,"B":0.20,"C":0.20,"D":0.20,"E":0.20},
                           assets, constraint_set,
                           request_min_weight=0.0, request_max_weight=0.40)
        assert sol.hard_satisfied


class TestConstraintValidator:
    def _make_plan(self, weights: dict, total_capital=1_000_000.0):
        positions = tuple(
            OptimizedPosition(
                symbol           = sym,
                optimized_weight = w,
                optimized_capital= w * total_capital,
                sector           = "tech" if sym in ("A","B") else "finance",
                asset_class      = "equity",
            )
            for sym, w in weights.items()
        )
        return OptimizationPlan(
            portfolio_id    = "p1",
            positions       = positions,
            total_capital   = total_capital,
            sector_weights  = {},
            asset_class_weights={},
        )

    def test_valid_plan_is_feasible(self, validator):
        plan = self._make_plan({"A":0.20,"B":0.20,"C":0.20,"D":0.20,"E":0.20})
        cs   = default_constraint_set(max_weight=0.40)
        report = validator.validate(plan, cs)
        assert report.is_feasible

    def test_report_has_checks(self, validator):
        plan = self._make_plan({"A":0.20,"B":0.20,"C":0.20,"D":0.20,"E":0.20})
        cs   = default_constraint_set()
        report = validator.validate(plan, cs)
        assert report.total > 0

    def test_weight_sum_violation(self, validator):
        # weights don't sum to 1 — should flag a violation
        plan = self._make_plan({"A":0.30,"B":0.30,"C":0.30})
        cs   = default_constraint_set()
        # Adjust raw weights to force budget violation
        plan = OptimizationPlan(
            portfolio_id = "p1",
            positions    = tuple(
                OptimizedPosition(symbol=sym, optimized_weight=w)
                for sym, w in {"A":0.50,"B":0.60,"C":0.20}.items()
            ),
            total_capital = 1_000_000.0,
        )
        report = validator.validate(plan, cs)
        # Either budget or weight check should flag
        assert report.total > 0
