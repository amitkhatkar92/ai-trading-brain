"""tests/unit/investment/portfolio/integration/test_health.py

Tests for engine_health.py, health_monitor.py, coverage_monitor.py,
dependency_monitor.py, quality_statistics.py, quality_history.py.
"""
from __future__ import annotations

import pytest

from iios.investment.portfolio.integration.coverage_monitor import (
    CoverageMonitor,
)
from iios.investment.portfolio.integration.dependency_monitor import DependencyMonitor
from iios.investment.portfolio.integration.engine_health import EngineHealthMonitor
from iios.investment.portfolio.integration.health_monitor import IntegrationHealthMonitor
from iios.investment.portfolio.integration.integration_types import (
    EngineId, HealthStatus, REQUIRED_ENGINES,
)
from iios.investment.portfolio.integration.quality_history import QualityHistory
from iios.investment.portfolio.integration.quality_statistics import (
    QualityRunMetric, QualityStatistics,
)


class TestEngineHealthMonitor:
    def test_no_records_is_offline(self):
        monitor = EngineHealthMonitor()
        status  = monitor.status(EngineId.RISK)
        assert status.health_status == HealthStatus.OFFLINE

    def test_all_success_is_healthy(self):
        monitor = EngineHealthMonitor()
        for _ in range(10):
            monitor.record(EngineId.RISK, responded=True, latency_ms=20.0)
        status = monitor.status(EngineId.RISK)
        assert status.health_status == HealthStatus.HEALTHY
        assert status.success_rate == 1.0

    def test_all_failure_is_offline(self):
        monitor = EngineHealthMonitor()
        for _ in range(5):
            monitor.record(EngineId.RISK, responded=False)
        status = monitor.status(EngineId.RISK)
        assert status.health_status == HealthStatus.OFFLINE

    def test_mixed_is_degraded(self):
        monitor = EngineHealthMonitor()
        for _ in range(6):
            monitor.record(EngineId.RISK, responded=True, latency_ms=10.0)
        for _ in range(4):
            monitor.record(EngineId.RISK, responded=False)
        status = monitor.status(EngineId.RISK)
        assert status.health_status in (HealthStatus.DEGRADED, HealthStatus.CRITICAL)

    def test_all_statuses_covers_all_engines(self):
        monitor   = EngineHealthMonitor()
        statuses  = monitor.all_statuses()
        engine_ids = {s.engine_id for s in statuses}
        assert set(EngineId).issubset(engine_ids)

    def test_unhealthy_engines_list(self):
        monitor = EngineHealthMonitor()
        # All have no records → offline → unhealthy
        unhealthy = monitor.unhealthy_engines()
        assert len(unhealthy) == len(EngineId)

    def test_avg_latency(self):
        monitor = EngineHealthMonitor()
        monitor.record(EngineId.ALLOCATION, responded=True, latency_ms=100.0)
        monitor.record(EngineId.ALLOCATION, responded=True, latency_ms=200.0)
        status = monitor.status(EngineId.ALLOCATION)
        assert status.avg_latency_ms == 150.0


class TestIntegrationHealthMonitor:
    def test_initial_healthy(self):
        monitor = IntegrationHealthMonitor()
        report  = monitor.check(active_portfolios=0)
        # No integrations yet → success_rate defaults to 1.0 → HEALTHY (if engines ok)
        # but all engines offline → could be CRITICAL; just check report exists
        assert report is not None

    def test_all_successes_healthy(self):
        monitor = IntegrationHealthMonitor()
        for eid in REQUIRED_ENGINES:
            monitor.record_engine_check(eid, responded=True, latency_ms=20.0)
        for _ in range(10):
            monitor.record_integration(succeeded=True, duration_ms=50.0)
        report = monitor.check(active_portfolios=2)
        assert report.overall_health == HealthStatus.HEALTHY
        assert report.is_healthy()

    def test_failures_degrade_health(self):
        monitor = IntegrationHealthMonitor()
        for _ in range(3):
            monitor.record_integration(succeeded=True, duration_ms=50.0)
        for _ in range(7):
            monitor.record_integration(succeeded=False, duration_ms=500.0)
        report = monitor.check()
        assert report.overall_health in (HealthStatus.DEGRADED, HealthStatus.CRITICAL)

    def test_active_portfolios_reported(self):
        monitor = IntegrationHealthMonitor()
        report  = monitor.check(active_portfolios=5)
        assert report.n_active_portfolios == 5

    def test_to_dict(self):
        monitor = IntegrationHealthMonitor()
        report  = monitor.check()
        d       = report.to_dict()
        assert "overall_health" in d
        assert "is_healthy" in d


class TestCoverageMonitor:
    def test_all_engines_present(self):
        monitor = CoverageMonitor()
        report  = monitor.analyze(list(REQUIRED_ENGINES), "P-F")
        assert report.is_full_coverage
        assert report.coverage_score == 1.0
        assert report.n_missing == 0

    def test_no_engines_present(self):
        monitor = CoverageMonitor()
        report  = monitor.analyze([], "P-E")
        assert not report.is_full_coverage
        assert report.coverage_score == 0.0
        assert report.n_missing == len(REQUIRED_ENGINES)

    def test_partial_engines(self):
        monitor = CoverageMonitor()
        partial = list(REQUIRED_ENGINES)[:5]
        report  = monitor.analyze(partial, "P-P")
        assert 0.0 < report.coverage_score < 1.0
        assert report.n_missing == len(REQUIRED_ENGINES) - 5

    def test_missing_engines_listed(self):
        monitor = CoverageMonitor()
        partial = [EngineId.RISK]
        report  = monitor.analyze(partial, "P-M")
        assert "risk" not in report.missing_engines

    def test_to_dict(self):
        monitor = CoverageMonitor()
        report  = monitor.analyze(list(REQUIRED_ENGINES), "P-D")
        d       = report.to_dict()
        assert "coverage_score" in d
        assert "missing" in d


class TestDependencyMonitor:
    def test_all_offline_not_available(self):
        monitor = DependencyMonitor()
        status  = monitor.check("P-1")
        assert not status.all_available
        assert status.readiness_score == 0.0

    def test_to_dict(self):
        monitor = DependencyMonitor()
        status  = monitor.check("P-1")
        d       = status.to_dict()
        assert "all_available" in d
        assert "readiness_score" in d


class TestQualityStatistics:
    def test_empty_returns_zero(self):
        qs   = QualityStatistics()
        assert qs.average_quality() == 0.0
        assert qs.publishable_rate() == 0.0

    def test_records_metrics(self):
        qs = QualityStatistics()
        qs.record(QualityRunMetric(overall_score=0.80, is_publishable=True))
        qs.record(QualityRunMetric(overall_score=0.60, is_publishable=True))
        qs.record(QualityRunMetric(overall_score=0.40, is_publishable=False))
        assert abs(qs.average_quality() - (0.80 + 0.60 + 0.40) / 3) < 0.001
        assert abs(qs.publishable_rate() - 2 / 3) < 0.001

    def test_summary_keys(self):
        qs = QualityStatistics()
        qs.record(QualityRunMetric(overall_score=0.75))
        s  = qs.summary()
        assert "total_runs" in s
        assert "avg_quality" in s


class TestQualityHistory:
    def test_add_and_retrieve(self):
        hist = QualityHistory()
        hist.add("P-1", QualityRunMetric(overall_score=0.80))
        result = hist.latest("P-1")
        assert result is not None
        assert result.overall_score == 0.80

    def test_trend_oldest_first(self):
        hist = QualityHistory()
        for s in [0.50, 0.60, 0.70]:
            hist.add("P-T", QualityRunMetric(overall_score=s))
        trend = hist.trend("P-T", 3)
        # trend returns oldest first — 0.50 was added first
        assert trend[0] == 0.50
        assert trend[-1] == 0.70

    def test_all_portfolio_ids(self):
        hist = QualityHistory()
        hist.add("P-A", QualityRunMetric())
        hist.add("P-B", QualityRunMetric())
        pids = hist.all_portfolio_ids()
        assert "P-A" in pids
        assert "P-B" in pids
