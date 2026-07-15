"""tests/unit/investment/portfolio/recommendation/test_engine_integration.py

Integration tests for the PortfolioRecommendationEngine.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.recommendation.portfolio_recommendation import (
    PortfolioRecommendation,
)
from iios.investment.portfolio.recommendation.portfolio_recommendation_engine import (
    PortfolioRecommendationEngine,
)
from iios.investment.portfolio.recommendation.recommendation_types import (
    LifecycleState,
    RecommendationAction,
    RecommendationStatus,
)


@pytest.fixture()
def engine():
    e = PortfolioRecommendationEngine()
    e.start()
    return e


class TestEngineBasics:
    def test_engine_starts(self, engine):
        assert engine.is_running

    def test_engine_stops(self, engine):
        engine.stop()
        assert not engine.is_running

    def test_version(self, engine):
        assert engine.VERSION == "1.0.0"

    def test_register_portfolio(self, engine):
        engine.register_portfolio("P-001")
        assert engine.is_registered("P-001")

    def test_deregister_portfolio(self, engine):
        engine.register_portfolio("P-002")
        engine.deregister_portfolio("P-002")
        assert not engine.is_registered("P-002")


class TestEngineEvaluate:
    def test_evaluate_returns_list(self, engine, default_intel):
        recs = engine.evaluate("P-001", default_intel)
        assert isinstance(recs, list)
        assert len(recs) >= 1

    def test_recommendations_are_frozen(self, engine, default_intel):
        recs = engine.evaluate("P-001", default_intel)
        rec = recs[0]
        with pytest.raises((AttributeError, TypeError)):
            rec.confidence = 0.0  # type: ignore

    def test_recommendations_have_portfolio_id(self, engine, default_intel):
        recs = engine.evaluate("P-001", default_intel)
        for rec in recs:
            assert rec.portfolio_id == "P-001"

    def test_recommendations_have_policy_name(self, engine, default_intel):
        recs = engine.evaluate("P-001", default_intel)
        for rec in recs:
            assert rec.policy_name

    def test_stress_generates_multiple_recs(self, engine, stressed_intel):
        recs = engine.evaluate("P-STRESS", stressed_intel)
        assert len(recs) >= 3

    def test_healthy_gets_no_action(self, engine, default_intel):
        recs = engine.evaluate("P-001", default_intel)
        actions = {r.action for r in recs}
        assert RecommendationAction.NO_ACTION in actions

    def test_auto_register(self, engine, default_intel):
        # Portfolio not registered; auto_register=True (default) should work
        assert not engine.is_registered("P-AUTO")
        recs = engine.evaluate("P-AUTO", default_intel, auto_register=True)
        assert engine.is_registered("P-AUTO")

    def test_evaluate_accepts_dict_intelligence(self, engine):
        intel_dict = {"portfolio_id": "P-D", "n_positions": 10}
        recs = engine.evaluate("P-D", intel_dict)
        assert len(recs) >= 1


class TestEngineQueryAPIs:
    def test_current_recommendations(self, engine, stressed_intel):
        engine.evaluate("P-Q", stressed_intel)
        current = engine.current_recommendations("P-Q")
        assert isinstance(current, list)

    def test_latest_recommendation(self, engine, default_intel):
        engine.evaluate("P-L", default_intel)
        latest = engine.latest_recommendation("P-L")
        assert latest is not None
        assert isinstance(latest, PortfolioRecommendation)

    def test_recommendation_history(self, engine, default_intel):
        for _ in range(3):
            engine.evaluate("P-H", default_intel)
        history = engine.recommendation_history("P-H", n=5)
        assert len(history) >= 1

    def test_best_recommendation(self, engine, stressed_intel):
        engine.evaluate("P-B", stressed_intel)
        best = engine.best_recommendation("P-B")
        # May return None if history empty, but shouldn't raise
        assert best is None or isinstance(best, PortfolioRecommendation)


class TestEngineStatisticsAndHealth:
    def test_statistics_snapshot(self, engine, default_intel):
        engine.evaluate("P-S", default_intel)
        snap = engine.statistics_snapshot()
        assert snap.total_runs >= 1

    def test_health_report(self, engine, default_intel):
        engine.evaluate("P-H2", default_intel)
        report = engine.health()
        assert report.total_runs >= 1

    def test_health_initially_healthy(self, engine, default_intel):
        engine.evaluate("P-H3", default_intel)
        report = engine.health()
        assert report.is_healthy

    def test_monitor_active(self, engine, default_intel):
        engine.evaluate("P-M", default_intel)
        report = engine.monitor_active()
        assert report.n_portfolios_checked >= 1


class TestEngineEventCallback:
    def test_callback_invoked(self, default_intel):
        events = []
        def callback(event_type, data):
            events.append((event_type, data))
        engine = PortfolioRecommendationEngine(event_callback=callback)
        engine.start()
        engine.evaluate("P-CB", default_intel)
        assert len(events) >= 1
        assert events[0][0] == "recommendation_published"

    def test_callback_receives_recommendation(self, default_intel):
        recs_received = []
        def callback(event_type, data):
            if event_type == "recommendation_published":
                recs_received.append(data)
        engine = PortfolioRecommendationEngine(event_callback=callback)
        engine.start()
        engine.evaluate("P-CB2", default_intel)
        assert all(isinstance(r, PortfolioRecommendation) for r in recs_received)


class TestEnginePolicySelection:
    def test_custom_policy_applied(self, default_intel):
        from iios.investment.portfolio.recommendation.recommendation_registry import (
            RecommendationPolicyRegistry,
        )
        registry = RecommendationPolicyRegistry()
        conservative = next(
            p for p in registry.all() if p.policy_type.value == "conservative"
        )
        engine = PortfolioRecommendationEngine(policy_registry=registry)
        engine.start()
        recs = engine.evaluate("P-CP", default_intel, policy_id=conservative.policy_id)
        for rec in recs:
            assert rec.policy_name == conservative.name

    def test_unknown_policy_falls_back_to_default(self, engine, default_intel):
        recs = engine.evaluate("P-UNK", default_intel, policy_id="non-existent-id")
        assert len(recs) >= 1
        # Uses default policy
        assert recs[0].policy_name  # not empty


class TestEngineValidationAndQuality:
    def test_validate_recommendation(self, engine, default_intel):
        recs = engine.evaluate("P-V", default_intel)
        rec = recs[0]
        report = engine.validate_recommendation(rec, default_intel)
        assert report is not None

    def test_assess_quality(self, engine, default_intel):
        recs = engine.evaluate("P-AQ", default_intel)
        rec = recs[0]
        report = engine.assess_quality(rec)
        assert 0.0 <= report.quality_score <= 1.0

    def test_search_by_action(self, engine, stressed_intel):
        engine.evaluate("P-SA", stressed_intel)
        recs = engine.search_recommendations(
            portfolio_id="P-SA",
            action=RecommendationAction.REBALANCE_PORTFOLIO,
        )
        for r in recs:
            assert r.action == RecommendationAction.REBALANCE_PORTFOLIO


class TestEngineDeterminism:
    def test_same_intel_same_actions(self, engine, stressed_intel):
        recs1 = engine.evaluate("P-DET1", stressed_intel)
        recs2 = engine.evaluate("P-DET2", stressed_intel)
        actions1 = sorted(r.action.value for r in recs1)
        actions2 = sorted(r.action.value for r in recs2)
        assert actions1 == actions2
