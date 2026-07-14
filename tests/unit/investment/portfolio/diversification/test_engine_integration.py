"""test_engine_integration.py — PortfolioDiversificationEngine end-to-end tests."""
import threading
import pytest

from iios.investment.portfolio.diversification.portfolio_diversification_engine import (
    DiversificationIntegrationRefs,
    PortfolioDiversificationEngine,
)
from iios.investment.portfolio.diversification.diversification_types import DiversificationGrade


class TestEngineLifecycle:
    def test_start_stop(self):
        e = PortfolioDiversificationEngine()
        e.start()
        assert e.is_running
        e.stop()
        assert not e.is_running

    def test_double_start_idempotent(self):
        e = PortfolioDiversificationEngine()
        e.start()
        e.start()
        assert e.is_running

    def test_evaluate_without_start_returns_empty_profile(self, plan_5_diverse):
        e = PortfolioDiversificationEngine()
        p = e.evaluate("P1", plan_5_diverse)
        assert not p.is_acceptable

    def test_version_constant(self):
        assert PortfolioDiversificationEngine.VERSION == "1.0.0"


class TestPortfolioRegistration:
    def setup_method(self):
        self.engine = PortfolioDiversificationEngine()
        self.engine.start()

    def teardown_method(self):
        self.engine.stop()

    def test_register_and_list(self):
        self.engine.register_portfolio("P1")
        assert "P1" in self.engine.list_portfolios()

    def test_deregister(self):
        self.engine.register_portfolio("P2")
        self.engine.deregister_portfolio("P2")
        assert "P2" not in self.engine.list_portfolios()

    def test_is_registered(self):
        self.engine.register_portfolio("P3")
        assert self.engine.is_registered("P3")
        assert not self.engine.is_registered("MISSING")

    def test_auto_register_on_evaluate(self, plan_5_diverse):
        self.engine.evaluate("AUTO_P", plan_5_diverse, auto_register=True)
        assert self.engine.is_registered("AUTO_P")

    def test_portfolio_count(self):
        self.engine.register_portfolio("C1")
        self.engine.register_portfolio("C2")
        assert self.engine.portfolio_count() >= 2


class TestEvaluate:
    def setup_method(self):
        self.engine = PortfolioDiversificationEngine()
        self.engine.start()

    def teardown_method(self):
        self.engine.stop()

    def test_basic_evaluate(self, plan_5_diverse):
        p = self.engine.evaluate("P1", plan_5_diverse)
        assert p.n_positions == 5
        assert p.portfolio_id == "P1"

    def test_grade_assigned(self, plan_5_diverse):
        p = self.engine.evaluate("P1", plan_5_diverse)
        assert p.grade in DiversificationGrade

    def test_version_increments(self, plan_5_diverse):
        p1 = self.engine.evaluate("P1", plan_5_diverse)
        p2 = self.engine.evaluate("P1", plan_5_diverse)
        assert p2.version == p1.version + 1

    def test_concentrated_lower_score(self, plan_5_diverse, plan_3_concentrated):
        pd = self.engine.evaluate("PD", plan_5_diverse)
        pc = self.engine.evaluate("PC", plan_3_concentrated)
        assert pd.overall_score >= pc.overall_score

    def test_10_balanced_acceptable(self, plan_10_balanced):
        e = PortfolioDiversificationEngine(
            quality_assessor=__import__(
                "iios.investment.portfolio.diversification.diversification_quality",
                fromlist=["DiversificationQualityAssessor"]
            ).DiversificationQualityAssessor(acceptable_threshold=0.40)
        )
        e.start()
        p = e.evaluate("P10", plan_10_balanced)
        e.stop()
        assert p.is_acceptable

    def test_single_position_handled(self, plan_single):
        p = self.engine.evaluate("PS", plan_single)
        assert p.n_positions == 1

    def test_has_concentration_risk(self, plan_3_concentrated):
        p = self.engine.evaluate("PC", plan_3_concentrated)
        # TCS at 60% — should flag at least one risk
        assert p.has_concentration_risk or p.has_correlation_risk

    def test_hhi_in_range(self, plan_5_diverse):
        p = self.engine.evaluate("P1", plan_5_diverse)
        assert 0.0 < p.hhi <= 1.0

    def test_entropy_ratio_in_range(self, plan_5_diverse):
        p = self.engine.evaluate("P1", plan_5_diverse)
        assert 0.0 <= p.entropy_ratio <= 1.0 + 1e-4

    def test_avg_correlation_in_range(self, plan_5_diverse):
        p = self.engine.evaluate("P1", plan_5_diverse)
        assert 0.0 <= p.avg_correlation <= 1.0

    def test_diversification_ratio_positive(self, plan_5_diverse):
        p = self.engine.evaluate("P1", plan_5_diverse)
        assert p.diversification_ratio > 0


class TestQueryAPIs:
    def setup_method(self):
        self.engine = PortfolioDiversificationEngine()
        self.engine.start()

    def teardown_method(self):
        self.engine.stop()

    def test_current_profile(self, plan_5_diverse):
        self.engine.evaluate("P1", plan_5_diverse)
        p = self.engine.current_profile("P1")
        assert p is not None
        assert p.portfolio_id == "P1"

    def test_current_profile_none_for_unknown(self):
        assert self.engine.current_profile("UNKNOWN") is None

    def test_history_grows(self, plan_5_diverse):
        for _ in range(3):
            self.engine.evaluate("P1", plan_5_diverse)
        hist = self.engine.history("P1", 10)
        assert len(hist) == 3

    def test_best_profile(self, plan_5_diverse, plan_3_concentrated):
        self.engine.evaluate("P1", plan_5_diverse)
        self.engine.evaluate("P1", plan_3_concentrated)
        best = self.engine.best_profile("P1")
        assert best is not None

    def test_quality_score(self, plan_5_diverse):
        self.engine.evaluate("P1", plan_5_diverse)
        s = self.engine.quality_score("P1")
        assert s is not None
        assert 0.0 <= s.overall <= 1.0

    def test_trends(self, plan_5_diverse):
        for _ in range(4):
            self.engine.evaluate("P1", plan_5_diverse)
        t = self.engine.trends("P1")
        assert t.portfolio_id == "P1"

    def test_metrics(self, plan_5_diverse):
        self.engine.evaluate("P1", plan_5_diverse)
        m = self.engine.metrics("P1")
        assert m is not None
        assert m.n_positions == 5

    def test_statistics_snapshot(self, plan_5_diverse):
        self.engine.evaluate("P1", plan_5_diverse)
        snap = self.engine.statistics_snapshot()
        assert snap.total_runs >= 1

    def test_health(self):
        h = self.engine.health()
        assert h is not None


class TestEventCallback:
    def test_callback_called_on_evaluate(self, plan_5_diverse):
        events = []

        def cb(event, data):
            events.append(event)

        e = PortfolioDiversificationEngine(event_callback=cb)
        e.start()
        e.evaluate("P1", plan_5_diverse)
        e.stop()
        assert "evaluation_completed" in events
        assert "engine_started" in events
        assert "engine_stopped" in events

    def test_callback_on_failure(self, plan_5_diverse):
        events = []

        def cb(event, data):
            events.append(event)

        e = PortfolioDiversificationEngine(event_callback=cb)
        # Not started
        e.evaluate("P1", plan_5_diverse)
        assert "evaluation_failed" in events

    def test_broken_callback_does_not_crash(self, plan_5_diverse):
        def bad_cb(event, data):
            raise RuntimeError("kaboom")

        e = PortfolioDiversificationEngine(event_callback=bad_cb)
        e.start()
        p = e.evaluate("P1", plan_5_diverse)
        e.stop()
        # Engine should still return a profile despite bad callback
        assert p is not None


class TestIntegrationRefs:
    def test_refs_default_all_none(self):
        refs = DiversificationIntegrationRefs()
        d = refs.to_dict()
        assert all(v is False for v in d.values())

    def test_refs_with_mock(self):
        class _FakeEngine:
            pass
        refs = DiversificationIntegrationRefs(optimization_engine=_FakeEngine())
        d    = refs.to_dict()
        assert d["optimization_engine"] is True

    def test_configure_integrations(self):
        e    = PortfolioDiversificationEngine()
        refs = DiversificationIntegrationRefs()
        e.configure_integrations(refs)
        assert e._integrations is refs


class TestConcurrency:
    def test_concurrent_evaluations(self, plan_5_diverse):
        e = PortfolioDiversificationEngine()
        e.start()
        results = []
        errors  = []

        def run(pid):
            try:
                p = e.evaluate(pid, plan_5_diverse)
                results.append(p.portfolio_id)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=run, args=(f"P{i}",)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        e.stop()
        assert len(errors) == 0
        assert len(results) == 8

    def test_concurrent_register(self):
        e = PortfolioDiversificationEngine()
        e.start()
        threads = [
            threading.Thread(target=e.register_portfolio, args=(f"P{i}",))
            for i in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        e.stop()
        assert e.portfolio_count() == 20
