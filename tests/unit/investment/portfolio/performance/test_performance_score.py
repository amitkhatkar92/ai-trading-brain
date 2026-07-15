"""Tests for performance score, quality, health, confidence, forecast."""
import pytest
from iios.investment.portfolio.performance.performance_score import (
    PerformanceScoreCalculator, PerformanceScoreHistory, PerformanceScore,
)
from iios.investment.portfolio.performance.performance_quality import (
    PerformanceQualityAssessor,
)
from iios.investment.portfolio.performance.performance_health import (
    PerformanceHealthMonitor,
)
from iios.investment.portfolio.performance.performance_confidence import (
    compute_performance_confidence,
)
from iios.investment.portfolio.performance.performance_forecast import (
    forecast_performance, _cdf_approx,
)
from iios.investment.portfolio.performance.performance_types import (
    PerformanceGrade, PerformanceLevel, PerformanceTrend,
)


class TestPerformanceScoreCalculator:
    def test_excellent_score(self):
        calc = PerformanceScoreCalculator()
        s = calc.calculate(sharpe=2.0, alpha=0.06, sortino=2.5, calmar=2.0, information_ratio=1.2)
        assert s.overall >= 0.80
        assert s.is_acceptable is True

    def test_poor_score(self):
        calc = PerformanceScoreCalculator()
        s = calc.calculate(sharpe=-0.5, alpha=-0.05, sortino=-0.5, calmar=0.0, information_ratio=-0.5)
        assert s.overall < 0.40

    def test_score_range(self):
        calc = PerformanceScoreCalculator()
        for sharpe in [-1.0, 0.0, 0.5, 1.0, 2.0, 3.0]:
            s = calc.calculate(sharpe=sharpe)
            assert 0.0 <= s.overall <= 1.0

    def test_grade_assigned(self):
        calc = PerformanceScoreCalculator()
        s = calc.calculate(sharpe=2.0, alpha=0.06, sortino=2.5, calmar=2.0)
        assert s.grade in list(PerformanceGrade)

    def test_level_assigned(self):
        calc = PerformanceScoreCalculator()
        s = calc.calculate(sharpe=1.5)
        assert s.level in list(PerformanceLevel)

    def test_trend_improving(self):
        calc = PerformanceScoreCalculator()
        s1 = calc.calculate(sharpe=0.5, portfolio_id="p1")
        s2 = calc.calculate(sharpe=1.5, portfolio_id="p1", previous_score=s1.overall)
        assert s2.trend == PerformanceTrend.IMPROVING

    def test_trend_deteriorating(self):
        calc = PerformanceScoreCalculator()
        s1 = calc.calculate(sharpe=2.0)
        s2 = calc.calculate(sharpe=0.1, previous_score=s1.overall)
        assert s2.trend == PerformanceTrend.DETERIORATING

    def test_trend_stable(self):
        calc = PerformanceScoreCalculator()
        s = calc.calculate(sharpe=1.0)
        s2 = calc.calculate(sharpe=1.01, previous_score=s.overall)
        assert s2.trend == PerformanceTrend.STABLE

    def test_trend_insufficient_no_previous(self):
        calc = PerformanceScoreCalculator()
        s = calc.calculate(sharpe=1.0)
        assert s.trend == PerformanceTrend.INSUFFICIENT

    def test_dimensions_populated(self):
        calc = PerformanceScoreCalculator()
        s = calc.calculate(sharpe=1.0, alpha=0.02)
        assert len(s.dimensions) == 5

    def test_to_dict(self):
        calc = PerformanceScoreCalculator()
        s = calc.calculate(sharpe=1.0)
        d = s.to_dict()
        assert "overall" in d
        assert "grade" in d

    def test_acceptable_threshold(self):
        calc = PerformanceScoreCalculator(quality_gate=0.70)
        s = calc.calculate(sharpe=0.5)  # should score below 0.70
        assert s.is_acceptable is False


class TestPerformanceScoreHistory:
    def test_add_and_latest(self):
        hist = PerformanceScoreHistory("p1")
        calc = PerformanceScoreCalculator()
        s = calc.calculate(sharpe=1.0, portfolio_id="p1")
        hist.add(s)
        assert hist.latest() == s

    def test_best(self):
        hist = PerformanceScoreHistory("p1")
        calc = PerformanceScoreCalculator()
        s1 = calc.calculate(sharpe=0.5)
        s2 = calc.calculate(sharpe=2.0)
        hist.add(s1)
        hist.add(s2)
        assert hist.best().overall == s2.overall

    def test_bounded(self):
        hist = PerformanceScoreHistory("p1", max_size=3)
        calc = PerformanceScoreCalculator()
        for _ in range(10):
            hist.add(calc.calculate(sharpe=1.0))
        assert len(hist.recent(100)) == 3


class TestPerformanceQualityAssessor:
    def test_excellent_quality(self):
        assessor = PerformanceQualityAssessor()
        report = assessor.assess(0.85, sharpe=1.5, sortino=1.8, calmar=1.2,
                                 information_ratio=0.8, alpha=0.03)
        assert report.is_acceptable is True
        assert report.grade == PerformanceGrade.A

    def test_unacceptable_quality(self):
        assessor = PerformanceQualityAssessor()
        report = assessor.assess(0.30, sharpe=-0.2, sortino=-0.1, calmar=0.1)
        assert report.is_acceptable is False

    def test_recommendation_set(self):
        assessor = PerformanceQualityAssessor()
        report = assessor.assess(0.50)
        assert report.recommendation != ""

    def test_primary_weakness_set(self):
        assessor = PerformanceQualityAssessor()
        report = assessor.assess(0.50, sharpe=-0.5, sortino=0.8, calmar=0.5)
        assert report.primary_weakness != ""

    def test_drawdown_warning(self):
        assessor = PerformanceQualityAssessor()
        report = assessor.assess(0.60, max_drawdown=0.35)
        assert any("drawdown" in w.lower() for w in report.warnings)

    def test_to_dict(self):
        assessor = PerformanceQualityAssessor()
        d = assessor.assess(0.65).to_dict()
        assert "grade" in d
        assert "recommendation" in d


class TestPerformanceHealthMonitor:
    def test_initial_healthy(self):
        mon = PerformanceHealthMonitor()
        report = mon.check(active_portfolios=0)
        assert report.is_healthy is True
        assert report.total_runs == 0

    def test_all_success(self):
        mon = PerformanceHealthMonitor()
        for _ in range(10):
            mon.record_run(True, 50.0)
        report = mon.check()
        assert report.is_healthy is True
        assert report.success_rate == 1.0

    def test_all_failure(self):
        mon = PerformanceHealthMonitor()
        for _ in range(10):
            mon.record_run(False, 10.0)
        report = mon.check()
        assert report.is_healthy is False
        assert report.success_rate == 0.0

    def test_avg_duration(self):
        mon = PerformanceHealthMonitor()
        mon.record_run(True, 100.0)
        mon.record_run(True, 200.0)
        report = mon.check()
        assert report.avg_duration_ms == pytest.approx(150.0)

    def test_to_dict(self):
        mon = PerformanceHealthMonitor()
        mon.record_run(True, 50.0)
        d = mon.check().to_dict()
        assert "is_healthy" in d
        assert "success_rate" in d


class TestPerformanceConfidence:
    def test_high_confidence_many_positions(self, positions_diverse):
        # Add positions with non-zero returns — diverse fixture already has them
        report = compute_performance_confidence(positions_diverse, has_nav_series=True,
                                                portfolio_id="p1")
        assert report.confidence_score > 0.40

    def test_low_confidence_no_positions(self):
        report = compute_performance_confidence([])
        assert report.insufficient_data is True
        assert report.confidence_score == 0.0

    def test_without_nav_lower_than_with(self, positions_diverse):
        with_nav    = compute_performance_confidence(positions_diverse, has_nav_series=True)
        without_nav = compute_performance_confidence(positions_diverse, has_nav_series=False)
        assert with_nav.confidence_score >= without_nav.confidence_score

    def test_confidence_level_classification(self, positions_diverse):
        r = compute_performance_confidence(positions_diverse, has_nav_series=True)
        assert r.confidence_level in ("low", "medium", "high", "very_high")

    def test_to_dict(self, positions_diverse):
        r = compute_performance_confidence(positions_diverse)
        d = r.to_dict()
        assert "confidence_score" in d
        assert "confidence_level" in d


class TestPerformanceForecast:
    def test_basic(self, positions_diverse):
        f = forecast_performance(positions_diverse, current_sharpe=1.0, portfolio_id="p1")
        assert 0.0 <= f.prob_positive_1y <= 1.0
        assert f.expected_return_1y != 0.0

    def test_shorter_horizons(self, positions_diverse):
        f = forecast_performance(positions_diverse, current_sharpe=1.0)
        # 30d return < 90d return < 1y return for positive drift
        assert f.expected_return_30d < f.expected_return_90d < f.expected_return_1y

    def test_confidence_range(self, positions_diverse):
        f = forecast_performance(positions_diverse)
        assert 0.0 <= f.confidence_score <= 1.0

    def test_empty_positions(self):
        f = forecast_performance([])
        assert f.expected_return_1y == 0.0

    def test_reliability_flag(self, positions_diverse):
        f = forecast_performance(positions_diverse, current_sharpe=1.0)
        # diverse fixture has 5 positions with reasonable conviction
        assert isinstance(f.is_reliable, bool)

    def test_cdf_approx_boundaries(self):
        assert _cdf_approx(-100) == 0.0
        assert _cdf_approx(100) == 1.0
        assert _cdf_approx(0) == pytest.approx(0.5, abs=0.01)
        assert _cdf_approx(1.96) > 0.97
