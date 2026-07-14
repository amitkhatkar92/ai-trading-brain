"""tests/unit/investment/decision/integration/test_health.py
Tests for EngineHealthMonitor, DependencyMonitor, CoverageMonitor,
IntegrationHealthMonitor.
"""
from __future__ import annotations

import pytest

from iios.investment.decision.integration.coverage_monitor import CoverageMonitor
from iios.investment.decision.integration.dependency_monitor import DependencyMonitor
from iios.investment.decision.integration.engine_health import (
    EngineHealthMonitor,
    EngineHealthRecord,
)
from iios.investment.decision.integration.health_monitor import (
    IntegrationHealthMonitor,
    IntegrationHealthReport,
)
from iios.investment.decision.integration.integration_constants import (
    ComponentId,
    HealthStatus,
    IntegrationStatus,
)


class TestEngineHealthMonitor:
    def test_initial_all_healthy(self):
        m = EngineHealthMonitor()
        for h in m.all_health():
            assert h.status == HealthStatus.HEALTHY

    def test_record_update(self):
        m = EngineHealthMonitor()
        m.record_update(ComponentId.EVIDENCE)
        h = m.get_health(ComponentId.EVIDENCE)
        assert h.is_responsive
        assert h.total_updates == 1

    def test_consecutive_failures_degrade(self):
        m = EngineHealthMonitor()
        from iios.investment.decision.integration.integration_constants import (
            HEALTH_CONSECUTIVE_FAIL_DEGRADED,
        )
        for _ in range(HEALTH_CONSECUTIVE_FAIL_DEGRADED):
            m.record_failure(ComponentId.EVIDENCE)
        h = m.get_health(ComponentId.EVIDENCE)
        assert h.status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)

    def test_update_resets_failures(self):
        m = EngineHealthMonitor()
        m.record_failure(ComponentId.EVIDENCE)
        m.record_failure(ComponentId.EVIDENCE)
        m.record_update(ComponentId.EVIDENCE)
        h = m.get_health(ComponentId.EVIDENCE)
        assert h.consecutive_failures == 0

    def test_to_dict(self):
        m = EngineHealthMonitor()
        d = m.get_health(ComponentId.REASONING).to_dict()
        assert "component" in d
        assert "status"    in d


class TestDependencyMonitor:
    def test_record_received(self):
        m = DependencyMonitor()
        m.record_received(ComponentId.EVIDENCE, 50.0)
        s = m.status(ComponentId.EVIDENCE)
        assert s.is_fresh
        assert s.update_count == 1

    def test_no_stale_immediately(self):
        m = DependencyMonitor()
        m.record_received(ComponentId.REASONING, 30.0)
        stale = m.stale_components()
        assert ComponentId.REASONING not in stale

    def test_all_statuses_count(self):
        m = DependencyMonitor()
        all_s = m.all_statuses()
        assert len(all_s) == len(list(ComponentId))

    def test_avg_latency(self):
        m = DependencyMonitor()
        m.record_received(ComponentId.RISK, 100.0)
        m.record_received(ComponentId.RISK, 200.0)
        avg = m.avg_latency_ms(ComponentId.RISK)
        assert avg == pytest.approx(150.0)

    def test_to_dict(self):
        m = DependencyMonitor()
        m.record_received(ComponentId.COMMITTEE, 60.0)
        d = m.status(ComponentId.COMMITTEE).to_dict()
        assert "component"    in d
        assert "is_fresh"     in d
        assert "update_count" in d


class TestCoverageMonitor:
    def test_full_coverage(self):
        m   = CoverageMonitor()
        rep = m.evaluate(ComponentId.required())
        assert rep.is_full_coverage
        assert rep.coverage_fraction == pytest.approx(1.0)

    def test_partial_coverage(self):
        m   = CoverageMonitor()
        rep = m.evaluate(frozenset({ComponentId.EVIDENCE, ComponentId.REASONING}))
        assert not rep.is_full_coverage
        assert rep.coverage_fraction < 1.0

    def test_empty_coverage(self):
        m   = CoverageMonitor()
        rep = m.evaluate(frozenset())
        assert rep.coverage_fraction == 0.0

    def test_full_coverage_rate(self):
        m = CoverageMonitor()
        m.evaluate(ComponentId.required())  # full
        m.evaluate(frozenset())             # empty
        rate = m.full_coverage_rate()
        assert rate == pytest.approx(0.5)

    def test_to_dict(self):
        m   = CoverageMonitor()
        rep = m.evaluate(ComponentId.required())
        d   = rep.to_dict()
        assert "coverage_fraction" in d
        assert "is_full_coverage"  in d


class TestIntegrationHealthMonitor:
    def test_initial_status_initializing(self):
        m = IntegrationHealthMonitor()
        r = m.report()
        assert r.integration_status == IntegrationStatus.INITIALIZING

    def test_set_ready(self):
        m = IntegrationHealthMonitor()
        m.set_status(IntegrationStatus.READY)
        assert m.report().integration_status == IntegrationStatus.READY

    def test_record_success(self):
        m = IntegrationHealthMonitor()
        m.set_status(IntegrationStatus.RUNNING)
        m.record_success(250.0)
        r = m.report()
        assert r.successful == 1
        assert r.avg_duration_ms == pytest.approx(250.0, abs=1.0)

    def test_record_failure(self):
        m = IntegrationHealthMonitor()
        m.set_status(IntegrationStatus.RUNNING)
        m.record_failure()
        assert m.report().failed == 1

    def test_is_healthy_when_running(self):
        m = IntegrationHealthMonitor()
        m.set_status(IntegrationStatus.RUNNING)
        assert m.report().is_healthy

    def test_not_healthy_when_stopped(self):
        m = IntegrationHealthMonitor()
        m.set_status(IntegrationStatus.STOPPED)
        assert not m.report().is_healthy

    def test_to_dict(self):
        m = IntegrationHealthMonitor()
        m.set_status(IntegrationStatus.READY)
        d = m.report().to_dict()
        assert "integration_status" in d
        assert "is_healthy"         in d
        assert "engine_health"      in d

    def test_reset(self):
        m = IntegrationHealthMonitor()
        m.set_status(IntegrationStatus.RUNNING)
        m.record_success(100.0)
        m.reset()
        assert m.report().total_sessions == 0
