"""test_engine_integration.py — end-to-end PortfolioRebalancingEngine tests."""
from __future__ import annotations

import threading

import pytest

from iios.investment.portfolio.rebalancing import (
    PolicyRegistry,
    PortfolioRebalancingEngine,
    RebalancePlan,
    RebalanceStatus,
    RebalanceTrigger,
    RebalancingIntegrationRefs,
)


# ---------------------------------------------------------------------------
# Basic lifecycle
# ---------------------------------------------------------------------------

class TestEngineLifecycle:
    def test_initial_not_running(self):
        engine = PortfolioRebalancingEngine()
        assert engine.is_running is False

    def test_start_stop(self):
        engine = PortfolioRebalancingEngine()
        engine.start()
        assert engine.is_running is True
        engine.stop()
        assert engine.is_running is False

    def test_version_string(self):
        assert PortfolioRebalancingEngine.VERSION == "1.0.0"


# ---------------------------------------------------------------------------
# Portfolio registration
# ---------------------------------------------------------------------------

class TestPortfolioRegistration:
    def test_register_and_query(self):
        engine = PortfolioRebalancingEngine()
        engine.register_portfolio("PF-A")
        assert engine.is_registered("PF-A") is True
        assert engine.is_registered("UNKNOWN") is False

    def test_deregister(self):
        engine = PortfolioRebalancingEngine()
        engine.register_portfolio("PF-A")
        engine.deregister_portfolio("PF-A")
        assert engine.is_registered("PF-A") is False

    def test_deregister_nonexistent(self):
        engine = PortfolioRebalancingEngine()
        engine.deregister_portfolio("NEVER_REGISTERED")  # should not raise


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------

class TestEvaluate:
    def test_returns_plan(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        plan = engine.evaluate("PF1", drifted_current, drifted_target)
        assert isinstance(plan, RebalancePlan)

    def test_plan_frozen(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        plan = engine.evaluate("PF1", drifted_current, drifted_target)
        with pytest.raises((TypeError, AttributeError)):
            plan.rebalance_score = 99.0  # type: ignore

    def test_plan_has_portfolio_id(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        plan = engine.evaluate("MY_PF", drifted_current, drifted_target)
        assert plan.portfolio_id == "MY_PF"

    def test_plan_has_valid_score(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        plan = engine.evaluate("PF", drifted_current, drifted_target)
        assert 0.0 <= plan.rebalance_score <= 1.0

    def test_plan_to_dict(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        plan = engine.evaluate("PF", drifted_current, drifted_target)
        d = plan.to_dict()
        assert "plan_id" in d
        assert "is_recommended" in d

    def test_balanced_not_recommended(self, balanced_current, balanced_target):
        engine = PortfolioRebalancingEngine()
        plan = engine.evaluate("PF", balanced_current, balanced_target,
                               days_since_rebalance=10.0)
        # No drift → should not be recommended
        assert plan.is_recommended is False

    def test_drifted_has_trades(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        plan = engine.evaluate("PF", drifted_current, drifted_target,
                               days_since_rebalance=95.0)
        assert plan.n_buys + plan.n_sells > 0

    def test_auto_register(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        assert engine.is_registered("NEW_PF") is False
        engine.evaluate("NEW_PF", drifted_current, drifted_target, auto_register=True)
        assert engine.is_registered("NEW_PF") is True

    def test_custom_policy(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        plan = engine.evaluate("PF", drifted_current, drifted_target, policy_id="conservative")
        assert plan.policy_name != ""

    def test_concentrated_portfolio(self, concentrated_current, concentrated_target):
        engine = PortfolioRebalancingEngine()
        plan = engine.evaluate("PF", concentrated_current, concentrated_target,
                               days_since_rebalance=95.0)
        assert isinstance(plan, RebalancePlan)
        assert plan.n_buys + plan.n_sells > 0

    def test_diverse_portfolio_new_positions(self, diverse_current, diverse_target):
        engine = PortfolioRebalancingEngine()
        plan = engine.evaluate("PF", diverse_current, diverse_target,
                               days_since_rebalance=95.0)
        assert plan.n_buys >= 1  # WIPRO is new

    def test_event_callback(self, drifted_current, drifted_target):
        events = []
        engine = PortfolioRebalancingEngine(event_callback=lambda e, p: events.append(e))
        engine.evaluate("PF", drifted_current, drifted_target)
        assert "plan_evaluated" in events


# ---------------------------------------------------------------------------
# Query APIs
# ---------------------------------------------------------------------------

class TestQueryAPIs:
    def test_current_plan_after_evaluate(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        engine.evaluate("PF", drifted_current, drifted_target)
        plan = engine.current_plan("PF")
        assert plan is not None

    def test_current_plan_none_before_evaluate(self):
        engine = PortfolioRebalancingEngine()
        assert engine.current_plan("NEVER_EVALUATED") is None

    def test_plan_history_grows(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        engine.evaluate("PF", drifted_current, drifted_target)
        engine.evaluate("PF", drifted_current, drifted_target)
        history = engine.plan_history("PF", n=10)
        assert len(history) >= 2

    def test_best_plan(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        engine.evaluate("PF", drifted_current, drifted_target)
        best = engine.best_plan("PF")
        assert best is not None

    def test_drift_report(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        report = engine.drift_report("PF", drifted_current, drifted_target)
        assert report is not None
        assert report.rebalance_required is True

    def test_statistics_snapshot(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        engine.evaluate("PF", drifted_current, drifted_target)
        snap = engine.statistics_snapshot()
        assert snap.total_runs >= 1

    def test_health_report(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        engine.evaluate("PF", drifted_current, drifted_target)
        health = engine.health()
        assert health.is_healthy is True
        assert health.total_runs >= 1


# ---------------------------------------------------------------------------
# Integration refs
# ---------------------------------------------------------------------------

class TestIntegrationRefs:
    def test_configure_integrations(self):
        engine = PortfolioRebalancingEngine()
        refs = RebalancingIntegrationRefs()
        engine.configure_integrations(refs)  # should not raise


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

class TestConcurrency:
    def test_concurrent_evaluations(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        results = []
        errors  = []

        def worker(pid: str):
            try:
                plan = engine.evaluate(pid, drifted_current, drifted_target)
                results.append(plan)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(f"PF-{i}",))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(results) == 10

    def test_same_portfolio_concurrent(self, drifted_current, drifted_target):
        engine = PortfolioRebalancingEngine()
        results = []
        errors  = []

        def worker():
            try:
                plan = engine.evaluate("SHARED_PF", drifted_current, drifted_target)
                results.append(plan)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert len(results) == 5
