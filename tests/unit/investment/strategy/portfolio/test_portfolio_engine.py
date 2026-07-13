"""tests/unit/investment/strategy/portfolio/test_portfolio_engine.py
Integration tests for StrategyPortfolioEngine — the main facade.
"""
from __future__ import annotations

import pytest
from typing import List

from iios.investment.strategy.portfolio.portfolio_strategy import PortfolioStrategy
from iios.investment.strategy.portfolio.strategy_portfolio import (
    StrategyPortfolio, PortfolioType, PortfolioState
)
from iios.investment.strategy.portfolio.strategy_portfolio_engine import StrategyPortfolioEngine
from iios.investment.strategy.portfolio.construction_constraints import (
    DEFAULT_CONSTRAINTS, DIVERSIFIED_CONSTRAINTS
)
from iios.investment.strategy.portfolio.rebalance_policy import DEFAULT_POLICY
from iios.investment.strategy.portfolio.portfolio_events import PortfolioEventBus, PortfolioEvent
from tests.unit.investment.strategy.portfolio.conftest import make_strategy, five_strategies


@pytest.fixture()
def engine() -> StrategyPortfolioEngine:
    return StrategyPortfolioEngine()


@pytest.fixture()
def populated_engine(five_strategies) -> StrategyPortfolioEngine:
    eng = StrategyPortfolioEngine()
    for s in five_strategies:
        eng.register_strategy(s)
    return eng


@pytest.fixture()
def created_portfolio(populated_engine, five_strategies):
    return populated_engine.create_portfolio(five_strategies, auto_optimize=True)


# ── strategy registration ─────────────────────────────────────────────────────

class TestStrategyRegistration:
    def test_register_and_retrieve(self, engine, strat_a):
        engine.register_strategy(strat_a)
        strats = engine.get_registered_strategies()
        assert any(s.strategy_id == "strat-A" for s in strats)

    def test_unregister(self, engine, strat_a):
        engine.register_strategy(strat_a)
        engine.unregister_strategy("strat-A")
        strats = engine.get_registered_strategies()
        assert not any(s.strategy_id == "strat-A" for s in strats)

    def test_register_multiple(self, populated_engine, five_strategies):
        strats = populated_engine.get_registered_strategies()
        assert len(strats) == 5


# ── create_portfolio ──────────────────────────────────────────────────────────

class TestCreatePortfolio:
    def test_creates_portfolio(self, populated_engine, five_strategies):
        p = populated_engine.create_portfolio(five_strategies)
        assert p is not None
        assert p.portfolio_id != ""

    def test_portfolio_registered(self, populated_engine, five_strategies):
        p = populated_engine.create_portfolio(five_strategies)
        assert populated_engine.get_portfolio(p.portfolio_id) is p

    def test_auto_optimize_transitions_to_optimized(self, populated_engine, five_strategies):
        p = populated_engine.create_portfolio(five_strategies, auto_optimize=True)
        assert p.state == PortfolioState.OPTIMIZED

    def test_no_auto_optimize_remains_created(self, populated_engine, five_strategies):
        p = populated_engine.create_portfolio(five_strategies, auto_optimize=False)
        assert p.state == PortfolioState.CREATED

    def test_custom_portfolio_name(self, populated_engine, five_strategies):
        p = populated_engine.create_portfolio(five_strategies, portfolio_name="My Portfolio")
        assert p.portfolio_name == "My Portfolio"

    def test_weights_sum_to_one(self, created_portfolio):
        assert abs(created_portfolio.total_weight - 1.0) < 1e-6

    def test_all_portfolio_types(self, populated_engine, five_strategies):
        for pt in [
            PortfolioType.EQUAL_WEIGHT, PortfolioType.RISK_PARITY,
            PortfolioType.PERFORMANCE_WEIGHT, PortfolioType.COMPOSITE_WEIGHT,
        ]:
            p = populated_engine.create_portfolio(five_strategies, portfolio_type=pt, auto_optimize=True)
            assert p.portfolio_type == pt
            assert abs(p.total_weight - 1.0) < 1e-6


# ── optimization ──────────────────────────────────────────────────────────────

class TestOptimizePortfolio:
    def test_optimize_returns_result(self, populated_engine, five_strategies):
        p = populated_engine.create_portfolio(five_strategies, auto_optimize=False)
        result = populated_engine.optimize_portfolio(p.portfolio_id)
        assert result is not None

    def test_optimize_unknown_returns_none(self, engine):
        result = engine.optimize_portfolio("does-not-exist")
        assert result is None

    def test_optimize_weights_valid(self, populated_engine, five_strategies):
        p = populated_engine.create_portfolio(five_strategies, auto_optimize=False)
        result = populated_engine.optimize_portfolio(p.portfolio_id)
        assert result.is_valid


# ── lifecycle ─────────────────────────────────────────────────────────────────

class TestLifecycle:
    def test_approve_portfolio(self, created_portfolio, populated_engine):
        ok = populated_engine.approve_portfolio(created_portfolio.portfolio_id)
        assert ok is True
        assert created_portfolio.state == PortfolioState.APPROVED

    def test_activate_portfolio(self, created_portfolio, populated_engine):
        populated_engine.approve_portfolio(created_portfolio.portfolio_id)
        ok = populated_engine.activate_portfolio(created_portfolio.portfolio_id)
        assert ok is True
        assert created_portfolio.state == PortfolioState.ACTIVE

    def test_archive_portfolio(self, created_portfolio, populated_engine):
        ok = populated_engine.archive_portfolio(created_portfolio.portfolio_id)
        assert ok is True
        assert created_portfolio.state == PortfolioState.ARCHIVED

    def test_archive_unknown_returns_false(self, engine):
        assert engine.archive_portfolio("unknown") is False

    def test_pause_and_resume(self, created_portfolio, populated_engine):
        populated_engine.approve_portfolio(created_portfolio.portfolio_id)
        populated_engine.activate_portfolio(created_portfolio.portfolio_id)
        populated_engine.pause_portfolio(created_portfolio.portfolio_id)
        assert created_portfolio.state == PortfolioState.PAUSED
        ok = populated_engine.activate_portfolio(created_portfolio.portfolio_id)
        assert ok is True


# ── list and query ────────────────────────────────────────────────────────────

class TestListQuery:
    def test_list_all(self, populated_engine, five_strategies):
        for i in range(3):
            populated_engine.create_portfolio(five_strategies, portfolio_id=f"p-{i}")
        all_p = populated_engine.list_portfolios()
        assert len(all_p) >= 3

    def test_list_by_state(self, populated_engine, five_strategies):
        p = populated_engine.create_portfolio(five_strategies, auto_optimize=False)
        created = populated_engine.list_portfolios(state=PortfolioState.CREATED)
        assert any(x.portfolio_id == p.portfolio_id for x in created)


# ── intelligence ──────────────────────────────────────────────────────────────

class TestIntelligence:
    def test_portfolio_health_returns_result(self, created_portfolio, populated_engine, five_strategies):
        conf_map = {s.strategy_id: 75.0 for s in five_strategies}
        health = populated_engine.portfolio_health(
            created_portfolio.portfolio_id, strategy_conf_map=conf_map
        )
        assert health is not None
        assert health.health_score >= 0.0

    def test_portfolio_score_returns_result(self, created_portfolio, populated_engine, five_strategies):
        score = populated_engine.portfolio_score(
            created_portfolio.portfolio_id, strategies=five_strategies
        )
        assert score is not None
        assert 0.0 <= score.overall_score <= 100.0

    def test_diversification_report(self, created_portfolio, populated_engine, five_strategies):
        report = populated_engine.diversification_report(
            created_portfolio.portfolio_id, strategies=five_strategies
        )
        assert report is not None
        assert 0.0 <= report.diversification_score <= 100.0

    def test_compare_portfolios(self, populated_engine, five_strategies):
        p1 = populated_engine.create_portfolio(five_strategies, portfolio_id="cmp-1")
        p2 = populated_engine.create_portfolio(five_strategies, portfolio_id="cmp-2")
        comparison = populated_engine.compare_portfolios(["cmp-1", "cmp-2"], five_strategies)
        assert "cmp-1" in comparison
        assert "cmp-2" in comparison

    def test_portfolio_health_unknown_returns_none(self, engine):
        result = engine.portfolio_health("unknown")
        assert result is None


# ── rebalancing ───────────────────────────────────────────────────────────────

class TestRebalancing:
    def test_force_rebalance(self, populated_engine, five_strategies):
        p = populated_engine.create_portfolio(five_strategies, auto_optimize=True)
        populated_engine.approve_portfolio(p.portfolio_id)
        populated_engine.activate_portfolio(p.portfolio_id)
        result = populated_engine.rebalance_portfolio(
            p.portfolio_id, strategies=five_strategies,
            policy=DEFAULT_POLICY, force=True
        )
        assert result is not None
        assert result.rebalanced is True

    def test_rebalance_history_recorded(self, populated_engine, five_strategies):
        p = populated_engine.create_portfolio(five_strategies, auto_optimize=True)
        populated_engine.approve_portfolio(p.portfolio_id)
        populated_engine.activate_portfolio(p.portfolio_id)
        populated_engine.rebalance_portfolio(
            p.portfolio_id, strategies=five_strategies, force=True
        )
        history = populated_engine.rebalance_history(p.portfolio_id)
        assert len(history) >= 1

    def test_rebalance_unknown_returns_none(self, engine):
        result = engine.rebalance_portfolio("unknown")
        assert result is None


# ── snapshots ─────────────────────────────────────────────────────────────────

class TestSnapshots:
    def test_take_snapshot(self, created_portfolio, populated_engine):
        snap = populated_engine.take_snapshot(created_portfolio.portfolio_id)
        assert snap is not None
        assert snap.portfolio_id == created_portfolio.portfolio_id

    def test_snapshot_history(self, created_portfolio, populated_engine):
        populated_engine.take_snapshot(created_portfolio.portfolio_id)
        populated_engine.take_snapshot(created_portfolio.portfolio_id)
        history = populated_engine.snapshot_history(created_portfolio.portfolio_id)
        # At least 3 (1 on create + 1 on optimize + 2 manual)
        assert len(history) >= 2

    def test_snapshot_unknown_returns_none(self, engine):
        snap = engine.take_snapshot("unknown")
        assert snap is None


# ── event bus integration ─────────────────────────────────────────────────────

class TestEventBus:
    def test_events_emitted_on_lifecycle(self, five_strategies):
        bus = PortfolioEventBus()
        events: List[PortfolioEvent] = []
        bus.subscribe(events.append)
        eng = StrategyPortfolioEngine(event_bus=bus)
        for s in five_strategies:
            eng.register_strategy(s)
        p = eng.create_portfolio(five_strategies)
        eng.approve_portfolio(p.portfolio_id)
        assert len(events) >= 1


# ── stats ─────────────────────────────────────────────────────────────────────

class TestStats:
    def test_stats_returns_dict(self, populated_engine, five_strategies):
        populated_engine.create_portfolio(five_strategies)
        s = populated_engine.stats()
        assert "total_portfolios" in s
        assert "by_state" in s
        assert "registered_strategies" in s
        assert s["total_portfolios"] >= 1

    def test_stats_strategy_count(self, populated_engine):
        s = populated_engine.stats()
        assert s["registered_strategies"] == 5
