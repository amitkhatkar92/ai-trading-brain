"""tests/unit/investment/strategy/portfolio/test_optimization.py
Tests for ConstraintSolver, OptimizationEngine, PortfolioOptimizer,
and optimization_statistics helpers.
"""
from __future__ import annotations

import pytest

from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioType, PortfolioState
)
from iios.investment.strategy.portfolio.strategy_allocation import StrategyAllocation
from iios.investment.strategy.portfolio.construction_constraints import (
    ConstructionConstraints, DEFAULT_CONSTRAINTS
)
from iios.investment.strategy.portfolio.constraint_solver import ConstraintSolver
from iios.investment.strategy.portfolio.optimization_engine import OptimizationEngine
from iios.investment.strategy.portfolio.portfolio_optimizer import PortfolioOptimizer
from iios.investment.strategy.portfolio.optimization_statistics import (
    portfolio_return, concentration_score, coverage_score,
    target_tracking_error, blend_weights
)
from iios.investment.strategy.portfolio.portfolio_constructor import PortfolioConstructor
from tests.unit.investment.strategy.portfolio.conftest import make_strategy


def make_simple_portfolio(n: int = 4) -> StrategyPortfolio:
    p = StrategyPortfolio("p1", "Test", PortfolioType.EQUAL_WEIGHT)
    w = 1.0 / n
    for i in range(n):
        p.add_strategy(
            StrategyAllocation(f"s{i}", f"S{i}", weight=w, target_weight=w)
        )
    return p


# ── optimization_statistics ───────────────────────────────────────────────────

class TestOptimizationStatistics:
    def test_portfolio_return_equal_weights(self):
        weights = [0.25, 0.25, 0.25, 0.25]
        returns = [0.10, 0.20, 0.30, 0.40]
        r = portfolio_return(weights, returns)
        assert abs(r - 0.25) < 1e-9

    def test_concentration_score_equal(self):
        weights = [0.25, 0.25, 0.25, 0.25]
        c = concentration_score(weights)
        assert abs(c) < 1e-6   # perfectly equal = 0 concentration

    def test_concentration_score_concentrated(self):
        weights = [0.97, 0.01, 0.01, 0.01]
        c = concentration_score(weights)
        assert c > 0.80

    def test_coverage_score_all_within(self):
        weights = [0.25, 0.25, 0.25, 0.25]
        cs = coverage_score(weights, 0.02, 0.50)
        assert abs(cs - 1.0) < 1e-9

    def test_coverage_score_none_within(self):
        weights = [0.01, 0.01, 0.01, 0.97]   # 0.01 < min_w=0.05, 0.97 > max_w=0.50
        cs = coverage_score(weights, 0.05, 0.50)
        assert cs < 1.0

    def test_target_tracking_error_zero_for_same(self):
        w = {"a": 0.5, "b": 0.5}
        assert abs(target_tracking_error(w, w)) < 1e-9

    def test_target_tracking_error_positive(self):
        actual = {"a": 0.6, "b": 0.4}
        target = {"a": 0.5, "b": 0.5}
        err = target_tracking_error(actual, target)
        assert err > 0.0

    def test_blend_weights_sum_one(self):
        w1 = {"a": 0.6, "b": 0.4}
        w2 = {"a": 0.4, "b": 0.6}
        blended = blend_weights(w1, w2, 0.5)
        assert abs(sum(blended.values()) - 1.0) < 1e-9


# ── ConstraintSolver ──────────────────────────────────────────────────────────

class TestConstraintSolver:
    def test_solve_basic(self):
        solver = ConstraintSolver()
        raw    = {"a": 0.5, "b": 0.3, "c": 0.2}
        result = solver.solve(raw, DEFAULT_CONSTRAINTS)
        assert abs(sum(result.weights.values()) - 1.0) < 1e-6

    def test_solve_min_enforced(self):
        solver = ConstraintSolver()
        c = ConstructionConstraints(min_weight=0.10, max_weight=0.60)
        raw = {"a": 0.90, "b": 0.05, "c": 0.05}
        result = solver.solve(raw, c)
        assert all(v >= 0.10 - 1e-9 for v in result.weights.values())

    def test_solve_max_enforced(self):
        solver = ConstraintSolver()
        c = ConstructionConstraints(min_weight=0.02, max_weight=0.40)
        raw = {"a": 0.90, "b": 0.05, "c": 0.05}
        result = solver.solve(raw, c)
        assert all(v <= 0.40 + 1e-9 for v in result.weights.values())

    def test_solve_empty_returns_empty(self):
        solver = ConstraintSolver()
        result = solver.solve({}, DEFAULT_CONSTRAINTS)
        assert result.weights == {}

    def test_solve_max_strategies_trim(self):
        solver = ConstraintSolver()
        c = ConstructionConstraints(max_strategies=2)
        raw = {"a": 0.4, "b": 0.3, "c": 0.3}
        result = solver.solve(raw, c)
        assert len(result.weights) == 2

    def test_check_concentration_pass(self):
        solver = ConstraintSolver()
        c = ConstructionConstraints(max_concentration=0.80)
        weights = {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}
        passes, conc = solver.check_concentration(weights, c)
        assert passes is True

    def test_check_concentration_fail(self):
        solver = ConstraintSolver()
        c = ConstructionConstraints(max_concentration=0.50)
        weights = {"a": 0.70, "b": 0.20, "c": 0.10}
        passes, conc = solver.check_concentration(weights, c)
        assert passes is False


# ── OptimizationEngine ────────────────────────────────────────────────────────

class TestOptimizationEngine:
    def test_optimize_updates_weights(self):
        eng = OptimizationEngine()
        p   = make_simple_portfolio(4)
        # Distort weights
        for a in p.active_allocations():
            a.target_weight = 0.3 if a.strategy_id == "s0" else 0.2333
        result = eng.optimize(p, DEFAULT_CONSTRAINTS)
        assert abs(sum(result.optimized_weights.values()) - 1.0) < 1e-6

    def test_optimize_empty_portfolio(self):
        eng = OptimizationEngine()
        p   = StrategyPortfolio("p1", "T", PortfolioType.EQUAL_WEIGHT)
        result = eng.optimize(p, DEFAULT_CONSTRAINTS)
        assert not result.is_valid

    def test_optimization_result_to_dict(self):
        eng = OptimizationEngine()
        p   = make_simple_portfolio(3)
        result = eng.optimize(p, DEFAULT_CONSTRAINTS)
        d = result.to_dict()
        assert "portfolio_id" in d


# ── PortfolioOptimizer ────────────────────────────────────────────────────────

class TestPortfolioOptimizer:
    def test_optimize_transitions_to_optimized(self):
        constructor = PortfolioConstructor()
        strategies  = [make_strategy(f"s{i}", eval_score=70.0 + i) for i in range(4)]
        p = constructor.build(strategies)
        assert p.state == PortfolioState.CREATED

        opt = PortfolioOptimizer()
        opt.optimize(p, DEFAULT_CONSTRAINTS)
        assert p.state == PortfolioState.OPTIMIZED

    def test_optimize_archived_raises(self):
        p = make_simple_portfolio(3)
        p.state = PortfolioState.ARCHIVED
        opt = PortfolioOptimizer()
        with pytest.raises(ValueError):
            opt.optimize(p, DEFAULT_CONSTRAINTS)

    def test_result_weights_sum_to_one(self):
        strategies = [make_strategy(f"s{i}", eval_score=70.0 + i) for i in range(4)]
        p = PortfolioConstructor().build(strategies)
        opt = PortfolioOptimizer()
        result = opt.optimize(p, DEFAULT_CONSTRAINTS)
        assert abs(sum(result.optimized_weights.values()) - 1.0) < 1e-6
