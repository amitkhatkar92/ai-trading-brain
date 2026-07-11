"""tests/unit/investment/market/integration/test_health.py"""
from __future__ import annotations

import time

import pytest

from iios.investment.market.integration.aggregation_engine import AggregationEngine
from iios.investment.market.integration.coverage_monitor import CoverageMonitor
from iios.investment.market.integration.dependency_monitor import DependencyMonitor
from iios.investment.market.integration.engine_health import EngineHealthTracker
from iios.investment.market.integration.health_monitor import HealthMonitor
from iios.investment.market.integration.models import HealthStatus


class TestEngineHealthTracker:
    def test_register_creates_record(self):
        tracker = EngineHealthTracker()
        tracker.register("market_regime")
        rec = tracker.get("market_regime")
        assert rec is not None
        assert rec.status is HealthStatus.MISSING

    def test_record_update_sets_healthy(self):
        tracker = EngineHealthTracker()
        tracker.register("trend")
        tracker.record_update("trend", bar_index=1)
        rec = tracker.get("trend")
        assert rec.status is HealthStatus.HEALTHY
        assert rec.staleness_bars == 0

    def test_record_error_sets_failed(self):
        tracker = EngineHealthTracker()
        tracker.register("breadth")
        tracker.record_error("breadth", "Connection refused")
        rec = tracker.get("breadth")
        assert rec.status is HealthStatus.FAILED
        assert rec.error_count == 1
        assert rec.last_error == "Connection refused"

    def test_advance_bar_increases_staleness(self):
        tracker = EngineHealthTracker(stale_threshold_bars=3)
        tracker.register("volatility")
        tracker.record_update("volatility", bar_index=1)
        # Advance without new update
        tracker.advance_bar(current_bar=2)
        rec = tracker.get("volatility")
        assert rec.staleness_bars == 1

    def test_advance_bar_sets_stale(self):
        tracker = EngineHealthTracker(stale_threshold_bars=2)
        tracker.register("correlation")
        tracker.record_update("correlation", bar_index=1)
        for bar in range(2, 5):
            tracker.advance_bar(current_bar=bar)
        rec = tracker.get("correlation")
        assert rec.status is HealthStatus.STALE

    def test_healthy_count(self):
        tracker = EngineHealthTracker()
        for name in ("a", "b", "c"):
            tracker.register(name)
        tracker.record_update("a", bar_index=1)
        tracker.record_update("b", bar_index=1)
        assert tracker.healthy_count() == 2

    def test_degraded_engines_list(self):
        tracker = EngineHealthTracker(stale_threshold_bars=2)
        tracker.register("stale_eng")
        tracker.record_update("stale_eng", bar_index=1)
        for bar in range(2, 5):
            tracker.advance_bar(bar)
        degraded = tracker.degraded_engines()
        assert "stale_eng" in degraded

    def test_all_records(self):
        tracker = EngineHealthTracker()
        tracker.register("a")
        tracker.register("b")
        records = tracker.all_records()
        assert set(records.keys()) == {"a", "b"}


class TestCoverageMonitor:
    def test_coverage_rate_single_bar(self):
        monitor = CoverageMonitor(["a", "b", "c"])
        monitor.record({"a", "b"})
        assert monitor.coverage_rate("a") == pytest.approx(1.0)
        assert monitor.coverage_rate("c") == pytest.approx(0.0)

    def test_overall_coverage(self):
        monitor = CoverageMonitor(["a", "b"])
        monitor.record({"a", "b"})
        monitor.record({"a"})
        assert monitor.overall_coverage() == pytest.approx(0.75)

    def test_missing_this_bar(self):
        monitor = CoverageMonitor(["a", "b", "c"])
        missing = monitor.missing_this_bar({"a"})
        assert missing == {"b", "c"}

    def test_consistently_missing(self):
        monitor = CoverageMonitor(["a", "b"])
        for _ in range(4):
            monitor.record({"a"})
        missing = monitor.consistently_missing(threshold=0.5)
        assert "b" in missing
        assert "a" not in missing

    def test_coverage_report_keys(self):
        monitor = CoverageMonitor(["x", "y"])
        monitor.record({"x"})
        report = monitor.coverage_report()
        assert set(report.keys()) == {"x", "y"}


class TestDependencyMonitor:
    def test_cascade_affected_when_upstream_down(self):
        monitor  = DependencyMonitor()
        affected = monitor.cascade_affected({"market_regime"})
        # trend depends on market_regime, breadth depends on market_regime
        assert "trend" in affected or "breadth" in affected

    def test_cascade_affected_empty(self):
        monitor  = DependencyMonitor()
        affected = monitor.cascade_affected(set())
        assert affected == {}

    def test_reliability_factor_all_healthy(self):
        from iios.investment.market.integration.models import EngineHealthRecord
        monitor  = DependencyMonitor()
        records  = {
            "market_regime": EngineHealthRecord(
                "market_regime", HealthStatus.HEALTHY, 1, 1.0)
        }
        factor = monitor.reliability_factor("trend", records)
        assert factor == pytest.approx(1.0)

    def test_reliability_factor_missing_dep(self):
        monitor = DependencyMonitor()
        factor  = monitor.reliability_factor("trend", {})
        assert factor < 1.0

    def test_reliability_factor_stale_dep(self):
        from iios.investment.market.integration.models import EngineHealthRecord
        monitor  = DependencyMonitor()
        records  = {
            "market_regime": EngineHealthRecord(
                "market_regime", HealthStatus.STALE, 1, 1.0)
        }
        factor = monitor.reliability_factor("trend", records)
        assert factor < 1.0


class TestHealthMonitor:
    def test_update_records_engines(self, full_bundle):
        engine  = AggregationEngine()
        state   = engine.aggregate(full_bundle)
        monitor = HealthMonitor(expected_engines=["market_regime", "trend", "breadth"])
        monitor.update(state)
        rec = monitor.engine_health("market_regime")
        assert rec is not None
        assert rec.status is HealthStatus.HEALTHY

    def test_overall_health_healthy(self, full_bundle):
        engine  = AggregationEngine()
        state   = engine.aggregate(full_bundle)
        monitor = HealthMonitor(expected_engines=["market_regime"])
        monitor.update(state)
        assert monitor.overall_health() is HealthStatus.HEALTHY

    def test_healthy_count(self, full_bundle):
        engine  = AggregationEngine()
        state   = engine.aggregate(full_bundle)
        expected = list(state.engines_received)
        monitor  = HealthMonitor(expected_engines=expected)
        monitor.update(state)
        assert monitor.healthy_count() == len(expected)

    def test_coverage_report_non_empty(self, full_bundle):
        engine  = AggregationEngine()
        state   = engine.aggregate(full_bundle)
        monitor = HealthMonitor(expected_engines=["market_regime", "trend"])
        monitor.update(state)
        report = monitor.coverage_report()
        assert "market_regime" in report
        assert "trend" in report

    def test_degraded_after_stale(self, full_bundle, make_bundle):
        engine   = AggregationEngine()
        state    = engine.aggregate(full_bundle)
        monitor  = HealthMonitor(expected_engines=["market_regime"], stale_threshold=2)
        monitor.update(state)
        # Simulate 3 bars without market_regime
        for i in range(2, 5):
            partial_state = engine.aggregate(make_bundle(bar_index=i, regime="bull"))
            # Manually remove market_regime from received to simulate missing
            partial_state.engines_received.discard("market_regime")
            monitor.update(partial_state)
        degraded = monitor.degraded_engines()
        assert "market_regime" in degraded
