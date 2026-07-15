"""test_rebalance_quality.py — scoring, quality, health, forecast, snapshot."""
from __future__ import annotations

import pytest

from iios.investment.portfolio.rebalancing import (
    DriftLevel,
    PolicyRegistry,
    PortfolioRebalanceHistory,
    PortfolioRebalanceStatistics,
    RebalanceGrade,
    RebalanceHealthMonitor,
    RebalanceHistory,
    RebalanceLevel,
    RebalancePlan,
    RebalanceQualityAssessor,
    RebalanceRunMetric,
    RebalanceScore,
    RebalanceScoreCalculator,
    RebalanceTrigger,
    TradePlanner,
    compute_allocation_drift,
    compute_risk_drift,
    forecast_rebalance_benefit,
)


# ---------------------------------------------------------------------------
# RebalanceScoreCalculator
# ---------------------------------------------------------------------------

class TestRebalanceScoreCalculator:
    def test_returns_score(self, drifted_current, drifted_target):
        calc = RebalanceScoreCalculator()
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        risk  = compute_risk_drift(drifted_current, drifted_target, "PF")
        planner = TradePlanner()
        policy = PolicyRegistry().default_policy()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        score = calc.calculate(alloc, risk, plan, portfolio_id="PF")
        assert isinstance(score, RebalanceScore)

    def test_overall_in_range(self, drifted_current, drifted_target):
        calc = RebalanceScoreCalculator()
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        risk  = compute_risk_drift(drifted_current, drifted_target, "PF")
        planner = TradePlanner()
        policy = PolicyRegistry().default_policy()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        score = calc.calculate(alloc, risk, plan, portfolio_id="PF")
        assert 0.0 <= score.overall <= 1.0

    def test_grade_assigned(self, drifted_current, drifted_target):
        calc = RebalanceScoreCalculator()
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        risk  = compute_risk_drift(drifted_current, drifted_target, "PF")
        planner = TradePlanner()
        policy = PolicyRegistry().default_policy()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        score = calc.calculate(alloc, risk, plan, portfolio_id="PF")
        assert isinstance(score.grade, RebalanceGrade)

    def test_balanced_portfolio_low_drift_score(self, balanced_current, balanced_target):
        calc = RebalanceScoreCalculator()
        alloc = compute_allocation_drift(balanced_current, balanced_target, "PF")
        risk  = compute_risk_drift(balanced_current, balanced_target, "PF")
        planner = TradePlanner()
        policy = PolicyRegistry().default_policy()
        plan = planner.plan(balanced_current, balanced_target, policy, "PF", 10_000_000)
        score = calc.calculate(alloc, risk, plan, portfolio_id="PF")
        # Very little drift to reduce → drift reduction score should be near 0
        assert score.drift_red_score < 0.10

    def test_dimensions_tuple(self, drifted_current, drifted_target):
        calc = RebalanceScoreCalculator()
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        risk  = compute_risk_drift(drifted_current, drifted_target, "PF")
        planner = TradePlanner()
        policy = PolicyRegistry().default_policy()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        score = calc.calculate(alloc, risk, plan, portfolio_id="PF")
        assert isinstance(score.dimensions, tuple)
        assert len(score.dimensions) == 5


# ---------------------------------------------------------------------------
# RebalanceQualityAssessor
# ---------------------------------------------------------------------------

class TestRebalanceQualityAssessor:
    def test_high_score_acceptable(self):
        assessor = RebalanceQualityAssessor(acceptable_threshold=0.50)
        report = assessor.assess(overall_score=0.75, portfolio_id="PF")
        assert report.is_acceptable is True
        assert report.grade == RebalanceGrade.A

    def test_low_score_not_acceptable(self):
        assessor = RebalanceQualityAssessor(acceptable_threshold=0.50)
        report = assessor.assess(overall_score=0.20, portfolio_id="PF")
        assert report.is_acceptable is False

    def test_recommendation_present(self):
        assessor = RebalanceQualityAssessor()
        report = assessor.assess(0.65)
        assert len(report.recommendation) > 0

    def test_high_cost_warning(self):
        assessor = RebalanceQualityAssessor()
        report = assessor.assess(0.60, total_cost_pct=0.015)
        assert any("cost" in w.lower() for w in report.warnings)

    def test_frozen(self):
        assessor = RebalanceQualityAssessor()
        report = assessor.assess(0.65)
        with pytest.raises((TypeError, AttributeError)):
            report.is_acceptable = False  # type: ignore


# ---------------------------------------------------------------------------
# RebalanceHealthMonitor
# ---------------------------------------------------------------------------

class TestRebalanceHealthMonitor:
    def test_initial_healthy(self):
        monitor = RebalanceHealthMonitor()
        report = monitor.check()
        assert report.is_healthy is True  # no runs = healthy
        assert report.total_runs == 0

    def test_record_success(self):
        monitor = RebalanceHealthMonitor()
        monitor.record_run(succeeded=True, duration_ms=50.0, plan_created=True)
        report = monitor.check()
        assert report.total_runs == 1
        assert report.success_runs == 1
        assert report.plans_generated == 1

    def test_record_failure(self):
        monitor = RebalanceHealthMonitor()
        for _ in range(8):
            monitor.record_run(True, 50.0)
        for _ in range(2):
            monitor.record_run(False, 10.0)
        report = monitor.check()
        assert report.success_rate == 0.8
        assert report.is_healthy is True

    def test_unhealthy_below_threshold(self):
        monitor = RebalanceHealthMonitor()
        for _ in range(5):
            monitor.record_run(False, 10.0)
        report = monitor.check()
        assert report.is_healthy is False

    def test_avg_duration(self):
        monitor = RebalanceHealthMonitor()
        monitor.record_run(True, 100.0)
        monitor.record_run(True, 200.0)
        report = monitor.check()
        assert abs(report.avg_duration_ms - 150.0) < 1e-6

    def test_active_portfolios_passed_through(self):
        monitor = RebalanceHealthMonitor()
        report = monitor.check(active_portfolios=7)
        assert report.active_portfolios == 7

    def test_thread_safety(self):
        import threading
        monitor = RebalanceHealthMonitor()
        errors = []

        def worker():
            try:
                for _ in range(100):
                    monitor.record_run(True, 10.0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert monitor.check().total_runs == 500


# ---------------------------------------------------------------------------
# RebalanceForecast
# ---------------------------------------------------------------------------

class TestRebalanceForecast:
    def test_returns_forecast(self, drifted_current, drifted_target):
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        planner = TradePlanner()
        policy = PolicyRegistry().default_policy()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        forecast = forecast_rebalance_benefit(alloc, plan, portfolio_id="PF")
        assert forecast is not None

    def test_drift_reduction_in_range(self, drifted_current, drifted_target):
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        planner = TradePlanner()
        policy = PolicyRegistry().default_policy()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        forecast = forecast_rebalance_benefit(alloc, plan, portfolio_id="PF")
        assert 0.0 <= forecast.expected_drift_reduction_pct <= 1.0

    def test_frozen(self, drifted_current, drifted_target):
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        planner = TradePlanner()
        policy = PolicyRegistry().default_policy()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        forecast = forecast_rebalance_benefit(alloc, plan, portfolio_id="PF")
        with pytest.raises((TypeError, AttributeError)):
            forecast.forecast_confidence = 99.0  # type: ignore

    def test_confidence_in_range(self, drifted_current, drifted_target):
        alloc = compute_allocation_drift(drifted_current, drifted_target, "PF")
        planner = TradePlanner()
        policy = PolicyRegistry().default_policy()
        plan = planner.plan(drifted_current, drifted_target, policy, "PF", 10_000_000)
        forecast = forecast_rebalance_benefit(alloc, plan, portfolio_id="PF")
        assert 0.0 <= forecast.forecast_confidence <= 1.0


# ---------------------------------------------------------------------------
# RebalanceHistory (snapshot)
# ---------------------------------------------------------------------------

class TestRebalanceHistory:
    def _make_record(self, pid: str = "PF"):
        from iios.investment.portfolio.rebalancing import RebalanceRecord, RebalanceTrigger
        return RebalanceRecord(portfolio_id=pid)

    def test_add_and_latest(self):
        hist = RebalanceHistory("PF")
        rec = self._make_record()
        hist.add(rec)
        assert hist.latest() is rec

    def test_empty_latest(self):
        hist = RebalanceHistory("PF")
        assert hist.latest() is None

    def test_bounded(self):
        hist = RebalanceHistory("PF", max_size=3)
        for _ in range(5):
            hist.add(self._make_record())
        assert hist.count() == 3

    def test_recent(self):
        hist = RebalanceHistory("PF", max_size=50)
        for _ in range(10):
            hist.add(self._make_record())
        recent = hist.recent(3)
        assert len(recent) == 3


# ---------------------------------------------------------------------------
# PortfolioRebalanceHistory
# ---------------------------------------------------------------------------

class TestPortfolioRebalanceHistory:
    def test_add_and_count(self):
        hist = PortfolioRebalanceHistory()
        hist.add("PF1", object())
        assert hist.count("PF1") == 1

    def test_latest(self):
        hist = PortfolioRebalanceHistory()
        obj = object()
        hist.add("PF1", obj)
        assert hist.latest("PF1") is obj

    def test_empty_latest(self):
        hist = PortfolioRebalanceHistory()
        assert hist.latest("UNKNOWN") is None

    def test_bounded(self):
        hist = PortfolioRebalanceHistory(max_per_portfolio=3)
        for _ in range(5):
            hist.add("PF1", object())
        assert hist.count("PF1") == 3

    def test_multiple_portfolios(self):
        hist = PortfolioRebalanceHistory()
        hist.add("PF1", object())
        hist.add("PF2", object())
        assert hist.count("PF1") == 1
        assert hist.count("PF2") == 1
        assert set(hist.all_portfolio_ids()) == {"PF1", "PF2"}


# ---------------------------------------------------------------------------
# PortfolioRebalanceStatistics
# ---------------------------------------------------------------------------

class TestPortfolioRebalanceStatistics:
    def test_empty_snapshot(self):
        stats = PortfolioRebalanceStatistics()
        snap = stats.snapshot()
        assert snap.total_runs == 0

    def test_records_and_snapshot(self):
        stats = PortfolioRebalanceStatistics()
        stats.record(RebalanceRunMetric(portfolio_id="PF", succeeded=True, duration_ms=50, rebalance_score=0.7))
        stats.record(RebalanceRunMetric(portfolio_id="PF", succeeded=True, duration_ms=100, rebalance_score=0.8))
        snap = stats.snapshot()
        assert snap.total_runs == 2
        assert snap.success_rate == 1.0
        assert abs(snap.avg_duration_ms - 75.0) < 1e-6

    def test_failure_rate(self):
        stats = PortfolioRebalanceStatistics()
        for _ in range(8):
            stats.record(RebalanceRunMetric(succeeded=True, duration_ms=10))
        for _ in range(2):
            stats.record(RebalanceRunMetric(succeeded=False, duration_ms=5))
        snap = stats.snapshot()
        assert snap.failed_runs == 2
        assert abs(snap.success_rate - 0.8) < 1e-6

    def test_bounded(self):
        stats = PortfolioRebalanceStatistics(max_runs=5)
        for _ in range(10):
            stats.record(RebalanceRunMetric(succeeded=True, duration_ms=10))
        snap = stats.snapshot()
        assert snap.total_runs == 5
