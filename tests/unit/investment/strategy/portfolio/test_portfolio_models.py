"""tests/unit/investment/strategy/portfolio/test_portfolio_models.py
Tests for PortfolioStrategy, StrategyAllocation, StrategyPortfolio,
PortfolioSnapshot, PortfolioHistory, PortfolioRegistry, and statistics.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_allocation import (
    StrategyAllocation, AllocationStatus, AllocationMethod
)
from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioType, PortfolioState
)
from iios.investment.strategy.portfolio.portfolio_snapshot import PortfolioSnapshot
from iios.investment.strategy.portfolio.portfolio_history import PortfolioHistory
from iios.investment.strategy.portfolio.portfolio_registry import PortfolioRegistry
from iios.investment.strategy.portfolio.portfolio_statistics import (
    project_weights, normalize_weights, jaccard, herfindahl_index,
    effective_n, gini_coefficient, weighted_average
)
from tests.unit.investment.strategy.portfolio.conftest import make_strategy


# ── PortfolioStrategy ─────────────────────────────────────────────────────────

class TestPortfolioStrategy:
    def test_is_eligible_approved(self):
        s = make_strategy("s1", approval="approved")
        assert s.is_eligible is True

    def test_is_eligible_conditional(self):
        s = make_strategy("s1", approval="conditional")
        assert s.is_eligible is True

    def test_not_eligible_rejected(self):
        s = make_strategy("s1", approval="rejected")
        assert s.is_eligible is False

    def test_risk_adjusted_score_positive(self):
        s = make_strategy("s1", eval_score=70.0, sharpe=1.2, max_dd=0.10)
        assert s.risk_adjusted_score > 0.0

    def test_to_dict_has_strategy_id(self):
        s = make_strategy("s1")
        d = s.to_dict()
        assert d["strategy_id"] == "s1"

    def test_frozen_immutable(self):
        s = make_strategy("s1")
        with pytest.raises((AttributeError, TypeError)):
            s.evaluation_score = 99.0  # type: ignore[misc]


# ── StrategyAllocation ────────────────────────────────────────────────────────

class TestStrategyAllocation:
    def test_weight_drift(self):
        a = StrategyAllocation(
            strategy_id="s1", strategy_name="S1",
            weight=0.25, target_weight=0.30,
        )
        assert abs(a.weight_drift - 0.05) < 1e-9

    def test_is_active_true(self):
        a = StrategyAllocation("s1", "S1", 0.25, 0.25)
        assert a.is_active is True

    def test_is_active_false_removed(self):
        a = StrategyAllocation(
            "s1", "S1", 0.25, 0.25, status=AllocationStatus.REMOVED
        )
        assert a.is_active is False

    def test_to_dict_has_status(self):
        a = StrategyAllocation("s1", "S1", 0.25, 0.25)
        assert "status" in a.to_dict()


# ── StrategyPortfolio ─────────────────────────────────────────────────────────

class TestStrategyPortfolio:
    def _make_portfolio(self) -> StrategyPortfolio:
        return StrategyPortfolio(
            portfolio_id="p1", portfolio_name="Test",
            portfolio_type=PortfolioType.EQUAL_WEIGHT,
        )

    def test_add_and_count(self):
        p = self._make_portfolio()
        a = StrategyAllocation("s1", "S1", 0.50, 0.50)
        p.add_strategy(a)
        assert p.active_count == 1

    def test_remove_marks_removed(self):
        p = self._make_portfolio()
        p.add_strategy(StrategyAllocation("s1", "S1", 0.50, 0.50))
        p.remove_strategy("s1")
        assert p.allocations["s1"].status == AllocationStatus.REMOVED

    def test_total_weight(self):
        p = self._make_portfolio()
        p.add_strategy(StrategyAllocation("s1", "S1", 0.40, 0.40))
        p.add_strategy(StrategyAllocation("s2", "S2", 0.60, 0.60))
        assert abs(p.total_weight - 1.0) < 1e-9

    def test_state_transition_valid(self):
        p = self._make_portfolio()
        assert p.can_transition_to(PortfolioState.OPTIMIZED)
        p.apply_transition(PortfolioState.OPTIMIZED)
        assert p.state == PortfolioState.OPTIMIZED

    def test_state_transition_invalid(self):
        p = self._make_portfolio()
        with pytest.raises(ValueError):
            p.apply_transition(PortfolioState.ACTIVE)   # must go through OPTIMIZED→APPROVED first

    def test_version_increments_on_transition(self):
        p = self._make_portfolio()
        v0 = p.version
        p.apply_transition(PortfolioState.OPTIMIZED)
        assert p.version == v0 + 1

    def test_to_dict(self):
        p = self._make_portfolio()
        d = p.to_dict()
        assert d["portfolio_id"] == "p1"
        assert "allocations" in d


# ── PortfolioSnapshot ─────────────────────────────────────────────────────────

class TestPortfolioSnapshot:
    def test_from_portfolio(self):
        p = StrategyPortfolio("p1", "Test", PortfolioType.EQUAL_WEIGHT)
        p.add_strategy(StrategyAllocation("s1", "S1", 0.50, 0.50))
        snap = PortfolioSnapshot.from_portfolio(p, "snap-1")
        assert snap.portfolio_id == "p1"
        assert snap.active_count == 1
        assert len(snap.allocations) == 1

    def test_snapshot_is_frozen(self):
        p = StrategyPortfolio("p1", "Test", PortfolioType.EQUAL_WEIGHT)
        snap = PortfolioSnapshot.from_portfolio(p, "snap-1")
        with pytest.raises((AttributeError, TypeError)):
            snap.portfolio_id = "other"  # type: ignore[misc]

    def test_to_dict(self):
        p = StrategyPortfolio("p1", "Test", PortfolioType.EQUAL_WEIGHT)
        snap = PortfolioSnapshot.from_portfolio(p, "snap-1")
        d = snap.to_dict()
        assert "captured_at" in d


# ── PortfolioHistory ──────────────────────────────────────────────────────────

class TestPortfolioHistory:
    def test_capture_and_latest(self):
        h = PortfolioHistory()
        p = StrategyPortfolio("p1", "Test", PortfolioType.EQUAL_WEIGHT)
        h.capture(p)
        snap = h.latest("p1")
        assert snap is not None
        assert snap.portfolio_id == "p1"

    def test_history_length(self):
        h = PortfolioHistory()
        p = StrategyPortfolio("p1", "Test", PortfolioType.EQUAL_WEIGHT)
        for _ in range(5):
            h.capture(p)
        assert len(h.history("p1", n=10)) == 5

    def test_returns_none_for_unknown(self):
        h = PortfolioHistory()
        assert h.latest("unknown") is None


# ── PortfolioRegistry ─────────────────────────────────────────────────────────

class TestPortfolioRegistry:
    def test_register_and_get(self):
        r = PortfolioRegistry()
        p = StrategyPortfolio("p1", "Test", PortfolioType.EQUAL_WEIGHT)
        r.register(p)
        assert r.get("p1") is p

    def test_all_returns_list(self):
        r = PortfolioRegistry()
        r.register(StrategyPortfolio("p1", "T", PortfolioType.EQUAL_WEIGHT))
        r.register(StrategyPortfolio("p2", "T", PortfolioType.EQUAL_WEIGHT))
        assert r.count() == 2

    def test_remove(self):
        r = PortfolioRegistry()
        p = StrategyPortfolio("p1", "T", PortfolioType.EQUAL_WEIGHT)
        r.register(p)
        r.remove("p1")
        assert r.get("p1") is None


# ── portfolio_statistics ──────────────────────────────────────────────────────

class TestPortfolioStatistics:
    def test_project_weights_sums_to_one(self):
        raw = {"a": 0.5, "b": 0.3, "c": 0.2}
        pw = project_weights(raw, min_w=0.05, max_w=0.60)
        assert abs(sum(pw.values()) - 1.0) < 1e-6

    def test_project_weights_respects_min(self):
        raw = {"a": 0.99, "b": 0.01}
        pw = project_weights(raw, min_w=0.10, max_w=0.90)
        assert all(v >= 0.10 - 1e-9 for v in pw.values())

    def test_project_weights_respects_max(self):
        raw = {"a": 0.99, "b": 0.01}
        pw = project_weights(raw, min_w=0.05, max_w=0.60)
        assert all(v <= 0.60 + 1e-9 for v in pw.values())

    def test_jaccard_identical(self):
        assert abs(jaccard(["a", "b"], ["a", "b"]) - 1.0) < 1e-9

    def test_jaccard_disjoint(self):
        assert abs(jaccard(["a"], ["b"]) - 0.0) < 1e-9

    def test_jaccard_partial(self):
        j = jaccard(["a", "b"], ["b", "c"])
        assert abs(j - 1.0 / 3.0) < 1e-9

    def test_hhi_equal_weights(self):
        weights = [0.25, 0.25, 0.25, 0.25]
        assert abs(herfindahl_index(weights) - 0.25) < 1e-9

    def test_effective_n_equal_weights(self):
        weights = [0.25, 0.25, 0.25, 0.25]
        assert abs(effective_n(weights) - 4.0) < 1e-6

    def test_gini_equal_zero(self):
        weights = [0.5, 0.5]
        assert abs(gini_coefficient(weights)) < 1e-9

    def test_weighted_average(self):
        vals = [10.0, 20.0]
        weights = [0.5, 0.5]
        assert abs(weighted_average(vals, weights) - 15.0) < 1e-9
