"""tests/unit/investment/strategy/lifecycle/test_monitoring.py
Tests for: ExecutionTracker, PerformanceTracker, ExecutionMonitor
"""
from __future__ import annotations

import time
import threading

import pytest

from iios.investment.strategy.lifecycle.execution_tracker import (
    ExecutionRecord,
    ExecutionStatus,
    ExecutionTracker,
)
from iios.investment.strategy.lifecycle.performance_tracker import (
    PerformanceMetrics,
    PerformanceTracker,
)
from iios.investment.strategy.lifecycle.execution_monitor import (
    EngineHealthReport,
    ExecutionMonitor,
    HealthStatus,
    StrategyHealth,
)


# ── ExecutionRecord ───────────────────────────────────────────────────────────

class TestExecutionRecord:
    def test_initial_status_running(self):
        rec = ExecutionRecord(strategy_id="s1", status=ExecutionStatus.RUNNING)
        assert not rec.is_complete

    def test_complete_sets_duration(self):
        rec = ExecutionRecord(strategy_id="s1", status=ExecutionStatus.RUNNING)
        time.sleep(0.01)
        rec.complete(ExecutionStatus.SUCCESS)
        assert rec.duration_ms >= 0
        assert rec.succeeded is True
        assert rec.is_complete is True

    def test_complete_failure(self):
        rec = ExecutionRecord(strategy_id="s1", status=ExecutionStatus.RUNNING)
        rec.complete(ExecutionStatus.FAILED, error_type="ValueError", error_message="bad")
        assert rec.failed is True
        assert rec.error_type == "ValueError"

    def test_complete_timeout_is_failure(self):
        rec = ExecutionRecord(strategy_id="s1", status=ExecutionStatus.RUNNING)
        rec.complete(ExecutionStatus.TIMEOUT)
        assert rec.failed is True

    def test_to_dict_shape(self):
        rec = ExecutionRecord(strategy_id="s1")
        rec.complete(ExecutionStatus.SUCCESS)
        d = rec.to_dict()
        assert "record_id" in d
        assert "strategy_id" in d
        assert "status" in d
        assert "duration_ms" in d

    def test_unique_record_ids(self):
        ids = {ExecutionRecord(strategy_id="s1").record_id for _ in range(20)}
        assert len(ids) == 20


# ── ExecutionTracker ──────────────────────────────────────────────────────────

class TestExecutionTracker:
    def test_start_record_creates_running(self):
        t = ExecutionTracker()
        rec = t.start_record("strat-a", cycle_id="c1")
        assert rec.status == ExecutionStatus.RUNNING
        assert rec.strategy_id == "strat-a"

    def test_get_recent(self):
        t = ExecutionTracker()
        for i in range(5):
            t.start_record(f"s{i}")
        recent = t.get_recent(3)
        assert len(recent) == 3

    def test_get_for_strategy(self):
        t = ExecutionTracker()
        t.start_record("alpha")
        t.start_record("beta")
        t.start_record("alpha")
        recs = t.get_for_strategy("alpha")
        assert all(r.strategy_id == "alpha" for r in recs)
        assert len(recs) == 2

    def test_get_failures(self):
        t = ExecutionTracker()
        r1 = t.start_record("s1")
        r1.complete(ExecutionStatus.FAILED)
        r2 = t.start_record("s2")
        r2.complete(ExecutionStatus.SUCCESS)
        failures = t.get_failures()
        assert len(failures) == 1
        assert failures[0].strategy_id == "s1"

    def test_get_failures_by_strategy(self):
        t = ExecutionTracker()
        r1 = t.start_record("s1")
        r1.complete(ExecutionStatus.FAILED)
        failures = t.get_failures("s1")
        assert failures

    def test_count_by_status(self):
        t = ExecutionTracker()
        r1 = t.start_record("s1")
        r1.complete(ExecutionStatus.SUCCESS)
        r2 = t.start_record("s1")
        r2.complete(ExecutionStatus.FAILED)
        counts = t.count_by_status("s1")
        assert counts.get("success", 0) == 1
        assert counts.get("failed", 0) == 1

    def test_last_execution(self):
        t = ExecutionTracker()
        assert t.last_execution("unknown") is None
        r = t.start_record("s1")
        assert t.last_execution("s1") is r

    def test_known_strategy_ids(self):
        t = ExecutionTracker()
        t.start_record("alpha")
        t.start_record("beta")
        ids = t.known_strategy_ids()
        assert "alpha" in ids
        assert "beta" in ids

    def test_thread_safe(self):
        t = ExecutionTracker(max_records=10_000)
        errors = []

        def worker(sid):
            try:
                for _ in range(20):
                    r = t.start_record(sid)
                    r.complete(ExecutionStatus.SUCCESS)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"s{i}",)) for i in range(10)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert not errors

    def test_ring_buffer_limit(self):
        t = ExecutionTracker(max_records=5)
        for i in range(10):
            t.start_record(f"s{i}")
        recent = t.get_recent(100)
        assert len(recent) <= 5


# ── PerformanceTracker ────────────────────────────────────────────────────────

class TestPerformanceTracker:
    def _tracker_with_records(self, success_ms, fail_count=0):
        t = ExecutionTracker()
        pt = PerformanceTracker(t)
        for ms in success_ms:
            rec = t.start_record("s1")
            time.sleep(ms / 1_000)
            rec.complete(ExecutionStatus.SUCCESS)
        for _ in range(fail_count):
            rec = t.start_record("s1")
            rec.complete(ExecutionStatus.FAILED)
        return pt

    def test_empty_tracker_returns_defaults(self):
        t = ExecutionTracker()
        pt = PerformanceTracker(t)
        m = pt.compute()
        assert m.sample_count == 0
        assert m.success_rate == 1.0

    def test_success_rate_all_success(self):
        t = ExecutionTracker()
        pt = PerformanceTracker(t)
        for _ in range(5):
            r = t.start_record("s1")
            r.complete(ExecutionStatus.SUCCESS)
        m = pt.compute("s1")
        assert m.success_rate == pytest.approx(1.0)

    def test_failure_rate(self):
        t = ExecutionTracker()
        pt = PerformanceTracker(t)
        for _ in range(4):
            r = t.start_record("s1")
            r.complete(ExecutionStatus.SUCCESS)
        r = t.start_record("s1")
        r.complete(ExecutionStatus.FAILED)
        m = pt.compute("s1")
        assert m.failure_rate == pytest.approx(0.2)

    def test_latency_metrics(self):
        t = ExecutionTracker()
        pt = PerformanceTracker(t)
        for _ in range(5):
            r = t.start_record("s1")
            time.sleep(0.01)
            r.complete(ExecutionStatus.SUCCESS)
        m = pt.compute("s1")
        assert m.p50_ms > 0
        assert m.p95_ms >= m.p50_ms

    def test_all_strategy_metrics(self):
        t = ExecutionTracker()
        pt = PerformanceTracker(t)
        for sid in ["a", "b", "c"]:
            r = t.start_record(sid)
            r.complete(ExecutionStatus.SUCCESS)
        all_m = pt.all_strategy_metrics()
        assert set(all_m.keys()) == {"a", "b", "c"}

    def test_to_dict(self):
        t = ExecutionTracker()
        pt = PerformanceTracker(t)
        d = pt.compute().to_dict()
        assert "success_rate" in d
        assert "p95_ms" in d
        assert "sample_count" in d


# ── ExecutionMonitor ──────────────────────────────────────────────────────────

class TestExecutionMonitor:
    def test_start_record(self):
        m = ExecutionMonitor()
        rec = m.start_record("s1", cycle_id="c1")
        assert rec.strategy_id == "s1"
        assert rec.status == ExecutionStatus.RUNNING

    def test_assess_strategy_unknown_returns_unknown(self):
        m = ExecutionMonitor(min_samples=5)
        health = m.assess_strategy("no-history")
        assert health.health == HealthStatus.UNKNOWN

    def test_assess_strategy_healthy(self):
        m = ExecutionMonitor(min_samples=3)
        for _ in range(5):
            r = m.start_record("s1")
            r.complete(ExecutionStatus.SUCCESS)
        health = m.assess_strategy("s1")
        assert health.health == HealthStatus.HEALTHY

    def test_assess_strategy_degraded_high_failure_rate(self):
        # failure_rate_warn = 0.10, need > 10% failures
        m = ExecutionMonitor(failure_rate_warn=0.10, min_samples=5)
        # 2 success, 4 fail → 66% failure rate → CRITICAL
        for _ in range(2):
            r = m.start_record("s1")
            r.complete(ExecutionStatus.SUCCESS)
        for _ in range(4):
            r = m.start_record("s1")
            r.complete(ExecutionStatus.FAILED)
        health = m.assess_strategy("s1")
        assert health.health in (HealthStatus.DEGRADED, HealthStatus.CRITICAL)

    def test_alert_handler_fired_on_degraded(self):
        alerts = []
        m = ExecutionMonitor(failure_rate_warn=0.01, min_samples=2)
        m.add_alert_handler(lambda h: alerts.append(h))
        for _ in range(2):
            r = m.start_record("s1")
            r.complete(ExecutionStatus.FAILED)
        m.assess_strategy("s1")
        assert len(alerts) >= 1

    def test_alert_handler_exception_does_not_crash(self):
        def bad_handler(h):
            raise RuntimeError("boom")

        m = ExecutionMonitor(failure_rate_warn=0.01, min_samples=2)
        m.add_alert_handler(bad_handler)
        for _ in range(2):
            r = m.start_record("s1")
            r.complete(ExecutionStatus.FAILED)
        m.assess_strategy("s1")  # should not raise

    def test_engine_health_report_empty(self):
        m = ExecutionMonitor()
        report = m.engine_health_report()
        assert isinstance(report, EngineHealthReport)
        assert report.health == HealthStatus.UNKNOWN

    def test_engine_health_report_all_healthy(self):
        m = ExecutionMonitor(min_samples=3)
        for sid in ["a", "b"]:
            for _ in range(5):
                r = m.start_record(sid)
                r.complete(ExecutionStatus.SUCCESS)
        report = m.engine_health_report()
        assert report.health == HealthStatus.HEALTHY
        assert report.healthy_strategies == 2

    def test_strategy_health_to_dict(self):
        m = ExecutionMonitor()
        r = m.start_record("s1")
        r.complete(ExecutionStatus.SUCCESS)
        h = m.assess_strategy("s1")
        d = h.to_dict()
        assert "strategy_id" in d
        assert "health" in d

    def test_engine_health_report_to_dict(self):
        m = ExecutionMonitor()
        report = m.engine_health_report()
        d = report.to_dict()
        assert "health" in d
        assert "total_strategies" in d
