"""tests/unit/investment/strategy/portfolio/test_construction.py
Tests for construction constraints, WeightOptimizer, AllocationEngine,
and PortfolioConstructor.
"""
from __future__ import annotations

import pytest
from typing import List

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_allocation import AllocationMethod
from iios.investment.strategy.portfolio.construction_constraints import (
    ConstructionConstraints, DEFAULT_CONSTRAINTS,
    CONCENTRATED_CONSTRAINTS, DIVERSIFIED_CONSTRAINTS, INSTITUTIONAL_CONSTRAINTS,
)
from iios.investment.strategy.portfolio.weight_optimizer import WeightOptimizer
from iios.investment.strategy.portfolio.allocation_engine import AllocationEngine
from iios.investment.strategy.portfolio.portfolio_constructor import (
    PortfolioConstructor, PortfolioConstructionError
)
from iios.investment.strategy.portfolio.strategy_portfolio import PortfolioType, PortfolioState
from tests.unit.investment.strategy.portfolio.conftest import make_strategy


@pytest.fixture()
def three_strategies():
    return [
        make_strategy("s1", eval_score=70.0, sharpe=1.2, ann_vol=0.12),
        make_strategy("s2", eval_score=65.0, sharpe=0.9, ann_vol=0.15),
        make_strategy("s3", eval_score=80.0, sharpe=1.5, ann_vol=0.10),
    ]


# ── ConstructionConstraints ───────────────────────────────────────────────────

class TestConstructionConstraints:
    def test_default_min_max(self):
        c = DEFAULT_CONSTRAINTS
        assert c.min_weight == 0.02
        assert c.max_weight == 0.40

    def test_validate_strategy_count_pass(self):
        c = DEFAULT_CONSTRAINTS
        assert c.validate_strategy_count(5) is True

    def test_validate_strategy_count_fail_low(self):
        c = DEFAULT_CONSTRAINTS
        assert c.validate_strategy_count(1) is False

    def test_validate_weight_pass(self):
        c = DEFAULT_CONSTRAINTS
        assert c.validate_weight(0.20) is True

    def test_validate_weight_fail_high(self):
        c = DEFAULT_CONSTRAINTS
        assert c.validate_weight(0.95) is False

    def test_institutional_requires_approved(self):
        assert INSTITUTIONAL_CONSTRAINTS.require_approved is True

    def test_to_dict_has_policy_name(self):
        d = DEFAULT_CONSTRAINTS.to_dict()
        assert d["policy_name"] == "default"


# ── WeightOptimizer ───────────────────────────────────────────────────────────

class TestWeightOptimizer:
    def _opt(self, strategies, method):
        opt = WeightOptimizer()
        return opt.compute(strategies, method, DEFAULT_CONSTRAINTS)

    def test_equal_weight_sum(self, three_strategies):
        w = self._opt(three_strategies, AllocationMethod.EQUAL_WEIGHT)
        assert abs(sum(w.values()) - 1.0) < 1e-6

    def test_equal_weight_values(self, three_strategies):
        w = self._opt(three_strategies, AllocationMethod.EQUAL_WEIGHT)
        for v in w.values():
            assert abs(v - 1.0 / 3.0) < 0.02

    def test_risk_parity_sum(self, three_strategies):
        w = self._opt(three_strategies, AllocationMethod.RISK_PARITY)
        assert abs(sum(w.values()) - 1.0) < 1e-6

    def test_performance_weight_sum(self, three_strategies):
        w = self._opt(three_strategies, AllocationMethod.PERFORMANCE_WEIGHT)
        assert abs(sum(w.values()) - 1.0) < 1e-6

    def test_performance_higher_sharpe_gets_more_weight(self, three_strategies):
        # s3 has highest sharpe (1.5), s2 lowest (0.9)
        w = self._opt(three_strategies, AllocationMethod.PERFORMANCE_WEIGHT)
        assert w["s3"] > w["s2"]

    def test_confidence_weight_sum(self, three_strategies):
        w = self._opt(three_strategies, AllocationMethod.CONFIDENCE_WEIGHT)
        assert abs(sum(w.values()) - 1.0) < 1e-6

    def test_composite_weight_sum(self, three_strategies):
        w = self._opt(three_strategies, AllocationMethod.COMPOSITE_WEIGHT)
        assert abs(sum(w.values()) - 1.0) < 1e-6

    def test_min_weight_enforced(self, three_strategies):
        constraints = ConstructionConstraints(min_weight=0.10, max_weight=0.50)
        opt = WeightOptimizer()
        w = opt.compute(three_strategies, AllocationMethod.PERFORMANCE_WEIGHT, constraints)
        assert all(v >= 0.10 - 1e-9 for v in w.values())

    def test_max_weight_enforced(self, three_strategies):
        constraints = ConstructionConstraints(min_weight=0.02, max_weight=0.50)
        opt = WeightOptimizer()
        w = opt.compute(three_strategies, AllocationMethod.PERFORMANCE_WEIGHT, constraints)
        assert all(v <= 0.50 + 1e-9 for v in w.values())

    def test_empty_returns_empty(self):
        opt = WeightOptimizer()
        w = opt.compute([], AllocationMethod.EQUAL_WEIGHT, DEFAULT_CONSTRAINTS)
        assert w == {}

    def test_register_custom_algorithm(self, three_strategies):
        opt = WeightOptimizer()
        custom_fn = lambda strats, constraints: {s.strategy_id: 1.0 / len(strats) for s in strats}
        opt.register_algorithm(AllocationMethod.CUSTOM, custom_fn)
        w = opt.compute(three_strategies, AllocationMethod.CUSTOM, DEFAULT_CONSTRAINTS)
        assert abs(sum(w.values()) - 1.0) < 1e-6


# ── AllocationEngine ──────────────────────────────────────────────────────────

class TestAllocationEngine:
    def test_basic_allocation(self, three_strategies):
        eng = AllocationEngine()
        result = eng.allocate(three_strategies, AllocationMethod.EQUAL_WEIGHT, DEFAULT_CONSTRAINTS)
        assert result.strategy_count == 3
        assert result.is_valid

    def test_rejects_ineligible(self, three_strategies):
        rejected = make_strategy("s-rej", approval="rejected")
        strategies = three_strategies + [rejected]
        eng = AllocationEngine()
        result = eng.allocate(strategies, AllocationMethod.EQUAL_WEIGHT, DEFAULT_CONSTRAINTS)
        assert "s-rej" in result.rejected_ids
        assert result.strategy_count == 3

    def test_min_eval_score_filter(self, three_strategies):
        constraints = ConstructionConstraints(min_eval_score=75.0)
        eng = AllocationEngine()
        result = eng.allocate(three_strategies, AllocationMethod.EQUAL_WEIGHT, constraints)
        # Only s3 (eval=80) passes
        assert result.strategy_count == 1

    def test_max_strategies_trim(self):
        strategies = [make_strategy(f"s{i}", eval_score=60.0 + i) for i in range(10)]
        constraints = ConstructionConstraints(min_strategies=2, max_strategies=3)
        eng = AllocationEngine()
        result = eng.allocate(strategies, AllocationMethod.EQUAL_WEIGHT, constraints)
        assert result.strategy_count == 3

    def test_total_weight_sums_to_one(self, three_strategies):
        eng = AllocationEngine()
        result = eng.allocate(three_strategies, AllocationMethod.EQUAL_WEIGHT, DEFAULT_CONSTRAINTS)
        assert abs(result.total_weight - 1.0) < 1e-6


# ── PortfolioConstructor ──────────────────────────────────────────────────────

class TestPortfolioConstructor:
    def test_build_creates_portfolio(self, five_strategies):
        c = PortfolioConstructor()
        p = c.build(five_strategies)
        assert p.active_count >= 2

    def test_build_state_is_created(self, five_strategies):
        c = PortfolioConstructor()
        p = c.build(five_strategies)
        assert p.state == PortfolioState.CREATED

    def test_build_respects_portfolio_type(self, five_strategies):
        c = PortfolioConstructor()
        p = c.build(five_strategies, portfolio_type=PortfolioType.RISK_PARITY)
        assert p.portfolio_type == PortfolioType.RISK_PARITY

    def test_build_raises_if_insufficient(self):
        c = PortfolioConstructor()
        strategies = [make_strategy("s1")]  # only 1, min is 2
        with pytest.raises(PortfolioConstructionError):
            c.build(strategies, constraints=ConstructionConstraints(min_strategies=2))

    def test_build_with_custom_id(self, five_strategies):
        c = PortfolioConstructor()
        p = c.build(five_strategies, portfolio_id="custom-id-1")
        assert p.portfolio_id == "custom-id-1"

    def test_build_with_custom_name(self, five_strategies):
        c = PortfolioConstructor()
        p = c.build(five_strategies, portfolio_name="My Test Portfolio")
        assert p.portfolio_name == "My Test Portfolio"

    def test_all_allocation_methods(self, five_strategies):
        c = PortfolioConstructor()
        for pt in [
            PortfolioType.EQUAL_WEIGHT,
            PortfolioType.RISK_PARITY,
            PortfolioType.PERFORMANCE_WEIGHT,
            PortfolioType.COMPOSITE_WEIGHT,
        ]:
            p = c.build(five_strategies, portfolio_type=pt)
            assert abs(p.total_weight - 1.0) < 1e-6
