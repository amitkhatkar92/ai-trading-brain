"""End-to-end integration tests for PortfolioPerformanceEngine."""
import pytest
from iios.investment.portfolio.performance.portfolio_performance_engine import (
    PortfolioPerformanceEngine, PerformanceIntegrationRefs,
)
from iios.investment.portfolio.performance.performance_profile import PerformanceProfile
from iios.investment.portfolio.performance.performance_quality import PerformanceQualityAssessor
from iios.investment.portfolio.performance.performance_score import PerformanceScoreCalculator
from iios.investment.portfolio.performance.performance_types import PerformanceGrade, PerformanceLevel


@pytest.fixture
def engine():
    eng = PortfolioPerformanceEngine()
    eng.start()
    return eng


class TestEngineLifecycle:
    def test_start_stop(self):
        eng = PortfolioPerformanceEngine()
        assert not eng.is_running
        eng.start()
        assert eng.is_running
        eng.stop()
        assert not eng.is_running

    def test_version(self):
        assert PortfolioPerformanceEngine.VERSION == "1.0.0"


class TestPortfolioRegistration:
    def test_register(self, engine):
        engine.register_portfolio("p1")
        assert engine.is_registered("p1")

    def test_deregister(self, engine):
        engine.register_portfolio("p1")
        engine.deregister_portfolio("p1")
        assert not engine.is_registered("p1")

    def test_auto_register(self, engine, positions_diverse):
        profile = engine.evaluate("auto_p", positions_diverse,
                                  period_years=1.0, benchmark_id="nifty50")
        assert engine.is_registered("auto_p")


class TestEvaluate:
    def test_returns_profile(self, engine, positions_diverse):
        profile = engine.evaluate("p1", positions_diverse)
        assert isinstance(profile, PerformanceProfile)

    def test_profile_fields_set(self, engine, positions_diverse):
        profile = engine.evaluate("p1", positions_diverse)
        assert profile.portfolio_id == "p1"
        assert profile.n_positions == 5
        assert isinstance(profile.performance_grade, PerformanceGrade)
        assert isinstance(profile.performance_level, PerformanceLevel)

    def test_sharpe_present(self, engine, positions_diverse):
        profile = engine.evaluate("p1", positions_diverse)
        assert isinstance(profile.sharpe_ratio, float)

    def test_alpha_present(self, engine, positions_diverse):
        profile = engine.evaluate("p1", positions_diverse)
        assert isinstance(profile.alpha, float)

    def test_benchmark_fields(self, engine, positions_diverse):
        profile = engine.evaluate("p1", positions_diverse, benchmark_id="nifty50")
        assert profile.benchmark_id == "nifty50"
        assert isinstance(profile.beta, float)
        assert isinstance(profile.tracking_error, float)

    def test_attribution_fields(self, engine, positions_diverse):
        profile = engine.evaluate("p1", positions_diverse)
        assert profile.top_sector != ""
        assert profile.dominant_factor != ""

    def test_confidence_set(self, engine, positions_diverse):
        profile = engine.evaluate("p1", positions_diverse)
        assert 0.0 <= profile.confidence_score <= 1.0

    def test_with_nav_series(self, engine, positions_diverse, nav_series_growing):
        profile = engine.evaluate("p1", positions_diverse,
                                  period_years=2.0, nav_series=nav_series_growing)
        assert profile.annualized_return > 0.0

    def test_with_plan_object(self, engine, mock_plan_with_positions):
        profile = engine.evaluate("p_plan", mock_plan_with_positions)
        assert profile.n_positions == 5

    def test_concentrated_portfolio(self, engine, positions_concentrated):
        profile = engine.evaluate("conc", positions_concentrated)
        assert profile.n_positions == 2

    def test_single_position(self, engine, positions_single):
        profile = engine.evaluate("single", positions_single)
        assert profile.n_positions == 1

    def test_negative_return_portfolio(self, engine, positions_negative_return):
        profile = engine.evaluate("neg", positions_negative_return)
        assert profile.sharpe_ratio < 0.0

    def test_to_dict(self, engine, positions_diverse):
        profile = engine.evaluate("p1", positions_diverse)
        d = profile.to_dict()
        assert "overall_performance_score" in d
        assert "sharpe_ratio" in d

    def test_multiple_evaluations_same_portfolio(self, engine, positions_diverse):
        p1 = engine.evaluate("p1", positions_diverse)
        p2 = engine.evaluate("p1", positions_diverse)
        assert p1.profile_id != p2.profile_id  # unique per run


class TestHistory:
    def test_current_profile(self, engine, positions_diverse):
        engine.evaluate("p1", positions_diverse)
        profile = engine.current_profile("p1")
        assert profile is not None

    def test_history_grows(self, engine, positions_diverse):
        for _ in range(5):
            engine.evaluate("p1", positions_diverse)
        history = engine.history("p1", 10)
        assert len(history) == 5

    def test_best_profile(self, engine, positions_diverse):
        for _ in range(3):
            engine.evaluate("p1", positions_diverse)
        best = engine.best_profile("p1")
        assert best is not None

    def test_quality_score(self, engine, positions_diverse):
        engine.evaluate("p1", positions_diverse)
        qs = engine.quality_score("p1")
        assert qs is not None
        assert 0.0 <= qs <= 1.0

    def test_no_history_returns_none(self, engine):
        assert engine.current_profile("nonexistent") is None


class TestStatisticsAndHealth:
    def test_statistics_snapshot(self, engine, positions_diverse):
        engine.evaluate("p1", positions_diverse)
        snap = engine.statistics_snapshot()
        assert snap.total_runs >= 1

    def test_health_check(self, engine, positions_diverse):
        engine.evaluate("p1", positions_diverse)
        report = engine.health()
        assert report.is_healthy is True
        assert report.total_runs >= 1

    def test_health_active_portfolios(self, engine, positions_diverse):
        engine.evaluate("p1", positions_diverse)
        engine.evaluate("p2", positions_diverse)
        report = engine.health()
        assert report.active_portfolios == 2


class TestMonitorPortfolio:
    def test_monitor_returns_health(self, engine, positions_diverse):
        report = engine.monitor_portfolio("p1", positions_diverse)
        assert report.is_healthy is True


class TestIntegrationRefs:
    def test_configure_integrations(self, engine):
        refs = PerformanceIntegrationRefs(portfolio_framework="mock_fw")
        engine.configure_integrations(refs)
        # No exception should be raised


class TestCustomComponents:
    def test_custom_quality_gate(self, positions_diverse):
        strict = PortfolioPerformanceEngine(
            quality_assessor=PerformanceQualityAssessor(acceptable_threshold=0.90)
        )
        strict.start()
        profile = strict.evaluate("p1", positions_diverse)
        # strict gate — most portfolios will not be acceptable
        assert isinstance(profile.is_acceptable, bool)

    def test_custom_score_calculator(self, positions_diverse):
        eng = PortfolioPerformanceEngine(
            score_calculator=PerformanceScoreCalculator(quality_gate=0.30)
        )
        eng.start()
        profile = eng.evaluate("p1", positions_diverse)
        # Low gate — many portfolios should pass
        assert isinstance(profile.is_acceptable, bool)
