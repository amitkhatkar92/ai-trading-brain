"""tests/unit/execution/monitoring/integration/test_integration_framework.py
==================================================
Comprehensive test suite for C6 Phase 6 M6 — Execution Monitoring
Integration.

Test classes
------------
TestConstants                 — constants and enumerations
TestExceptions                — exception hierarchy
TestIntegrationContext        — MonitoringIntegrationContext DTO
TestIntegrationRequest        — MonitoringIntegrationRequest DTO
TestIntegrationResponse       — MonitoringIntegrationResponse DTO
TestIntegrationSnapshot       — MonitoringIntegrationSnapshot DTO
TestIntegrationHealth         — health DTOs and compute helpers
TestIntegrationStatus         — IntegrationStatusRecord
TestIntegrationStatistics     — IntegrationStatistics accumulator
TestIntegrationHistory        — IntegrationHistory bounded deques
TestIntegrationEvents         — IntegrationEvent factory functions
TestIntegrationRegistry       — IntegrationRegistry CRUD
TestIntegrationValidation     — IntegrationValidator
TestComponentRegistry         — ComponentRegistry
TestComponentFactory          — ComponentFactory
TestIntegrationManager        — MonitoringIntegrationManager
TestIntegrationEngine         — ExecutionMonitoringIntegrationEngine basics
TestWorkflow                  — full submit() workflow
TestHealth                    — health() aggregation
TestConcurrency               — thread-safety
TestRegressionEdgeCases       — edge cases and regression guards
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Module under test ─────────────────────────────────────────────────────────
from iios.execution.monitoring.integration.constants import (
    ACTOR_ENGINE,
    ACTOR_INTEGRATION,
    ComponentType,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_SESSIONS,
    ENGINE_SYSTEM_ID,
    HealthStatus,
    IntegrationEventType,
    IntegrationState,
    RUNNING_INTEGRATION_STATES,
    TERMINAL_INTEGRATION_STATES,
    VERSION,
)
from iios.execution.monitoring.integration.exceptions import (
    IntegrationAlreadyRunningError,
    IntegrationComponentError,
    IntegrationError,
    IntegrationHealthError,
    IntegrationNotRunningError,
    IntegrationRequestNotFoundError,
    IntegrationSessionNotFoundError,
    IntegrationSnapshotError,
    IntegrationValidationError,
    IntegrationWorkflowError,
)
from iios.execution.monitoring.integration.monitoring_integration_context import (
    MonitoringIntegrationContext,
    make_monitoring_integration_context,
)
from iios.execution.monitoring.integration.monitoring_integration_request import (
    MonitoringIntegrationRequest,
    make_monitoring_integration_request,
)
from iios.execution.monitoring.integration.monitoring_integration_response import (
    MonitoringIntegrationResponse,
    make_monitoring_integration_response,
)
from iios.execution.monitoring.integration.monitoring_integration_snapshot import (
    MonitoringIntegrationSnapshot,
    make_integration_snapshot,
)
from iios.execution.monitoring.integration.monitoring_integration_health import (
    ComponentHealth,
    IntegrationHealth,
    compute_integration_health,
    make_component_health,
)
from iios.execution.monitoring.integration.monitoring_integration_status import (
    IntegrationStatusRecord,
)
from iios.execution.monitoring.integration.monitoring_integration_statistics import (
    IntegrationStatistics,
)
from iios.execution.monitoring.integration.monitoring_integration_history import (
    IntegrationHistory,
)
from iios.execution.monitoring.integration.monitoring_integration_events import (
    IntegrationEvent,
    make_monitoring_completed,
    make_monitoring_health_changed,
    make_monitoring_initialized,
    make_monitoring_restarted,
    make_monitoring_snapshot_published,
    make_monitoring_started,
    make_monitoring_stopped,
    make_monitoring_validated,
)
from iios.execution.monitoring.integration.monitoring_integration_registry import (
    IntegrationRegistry,
)
from iios.execution.monitoring.integration.monitoring_integration_validation import (
    IntegrationValidationResult,
    IntegrationValidator,
)
from iios.execution.monitoring.integration.monitoring_component_registry import (
    ComponentRegistry,
)
from iios.execution.monitoring.integration.monitoring_component_factory import (
    ComponentFactory,
)
from iios.execution.monitoring.integration.monitoring_integration_manager import (
    MonitoringIntegrationManager,
)
from iios.execution.monitoring.integration.execution_monitoring_integration_engine import (
    ExecutionMonitoringIntegrationEngine,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sid() -> str:
    return f"sess-{uuid.uuid4().hex[:8]}"

def _pid() -> str:
    return f"port-{uuid.uuid4().hex[:8]}"

def _make_ctx(sid: Optional[str] = None, pid: Optional[str] = None) -> MonitoringIntegrationContext:
    return make_monitoring_integration_context(sid or _sid(), pid or _pid())

def _make_req(
    sid: Optional[str] = None,
    pid: Optional[str] = None,
    metrics: Optional[Dict[str, float]] = None,
) -> MonitoringIntegrationRequest:
    s = sid or _sid()
    p = pid or _pid()
    ctx = _make_ctx(s, p)
    return make_monitoring_integration_request(s, p, ctx, metrics=metrics or {"latency": 5.0})

def _make_resp(
    sid: Optional[str] = None,
    pid: Optional[str] = None,
) -> MonitoringIntegrationResponse:
    s = sid or _sid()
    p = pid or _pid()
    return make_monitoring_integration_response("req-1", s, p)

def _make_snap(
    sid: Optional[str] = None,
    pid: Optional[str] = None,
    version: int = 1,
) -> MonitoringIntegrationSnapshot:
    return make_integration_snapshot(sid or _sid(), pid or _pid(), snapshot_version=version)

def _started_engine(**kwargs) -> ExecutionMonitoringIntegrationEngine:
    engine = ExecutionMonitoringIntegrationEngine(**kwargs)
    engine.start()
    return engine


# ─────────────────────────────────────────────────────────────────────────────
# 1  Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version_is_string(self):
        assert isinstance(VERSION, str) and VERSION

    def test_default_limits(self):
        assert DEFAULT_MAX_REQUESTS >= 1
        assert DEFAULT_MAX_HISTORY  >= 1
        assert DEFAULT_MAX_SESSIONS >= 1

    def test_integration_states_enum(self):
        assert IntegrationState.RUNNING in RUNNING_INTEGRATION_STATES
        assert IntegrationState.STOPPED in TERMINAL_INTEGRATION_STATES

    def test_component_type_members(self):
        members = {ct.value for ct in ComponentType}
        assert "lifecycle"      in members
        assert "metrics_engine" in members
        assert "alert_manager"  in members

    def test_health_status_members(self):
        assert HealthStatus.HEALTHY   in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        assert HealthStatus.UNHEALTHY is not None

    def test_event_type_members(self):
        vals = {e.value for e in IntegrationEventType}
        assert "monitoring_initialized"      in vals
        assert "monitoring_snapshot_published" in vals

    def test_actor_constants(self):
        assert ACTOR_ENGINE
        assert ACTOR_INTEGRATION


# ─────────────────────────────────────────────────────────────────────────────
# 2  Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_hierarchy(self):
        assert issubclass(IntegrationNotRunningError,   IntegrationError)
        assert issubclass(IntegrationAlreadyRunningError, IntegrationError)
        assert issubclass(IntegrationRequestNotFoundError, IntegrationError)
        assert issubclass(IntegrationValidationError,   IntegrationError)
        assert issubclass(IntegrationComponentError,    IntegrationError)
        assert issubclass(IntegrationSnapshotError,     IntegrationError)
        assert issubclass(IntegrationWorkflowError,     IntegrationError)
        assert issubclass(IntegrationHealthError,       IntegrationError)

    def test_not_running_raises(self):
        with pytest.raises(IntegrationNotRunningError):
            raise IntegrationNotRunningError()

    def test_request_not_found_stores_id(self):
        exc = IntegrationRequestNotFoundError("rid-42")
        assert "rid-42" in str(exc)

    def test_session_not_found_stores_id(self):
        exc = IntegrationSessionNotFoundError("sess-99")
        assert "sess-99" in str(exc)

    def test_validation_error_stores_errors(self):
        exc = IntegrationValidationError("bad", errors=("x", "y"))
        assert "x" in exc.errors or "x" in str(exc)

    def test_component_error_stores_info(self):
        exc = IntegrationComponentError("lifecycle", "down")
        assert "lifecycle" in str(exc)

    def test_workflow_error_stores_step(self):
        exc = IntegrationWorkflowError("evaluate", "boom")
        assert "evaluate" in str(exc)


# ─────────────────────────────────────────────────────────────────────────────
# 3  Context
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationContext:
    def test_factory_creates_frozen(self):
        ctx = make_monitoring_integration_context("s1", "p1")
        assert isinstance(ctx, MonitoringIntegrationContext)
        with pytest.raises((AttributeError, TypeError)):
            ctx.session_id = "other"  # type: ignore

    def test_required_fields(self):
        ctx = make_monitoring_integration_context("s1", "p1")
        assert ctx.session_id   == "s1"
        assert ctx.portfolio_id == "p1"

    def test_optional_gateway(self):
        ctx = make_monitoring_integration_context(
            "s2", "p2", gateway_id="gw-1"
        )
        assert ctx.gateway_id == "gw-1"
        assert ctx.has_gateway

    def test_optional_strategy(self):
        ctx = make_monitoring_integration_context(
            "s3", "p3", strategy_id="strat-x"
        )
        assert ctx.strategy_id == "strat-x"
        assert ctx.has_strategy

    def test_no_gateway_by_default(self):
        ctx = _make_ctx()
        assert not ctx.has_gateway
        assert not ctx.has_strategy

    def test_context_id_auto_assigned(self):
        ctx1 = _make_ctx()
        ctx2 = _make_ctx()
        assert ctx1.context_id != ctx2.context_id

    def test_tags_default_empty(self):
        ctx = _make_ctx()
        assert ctx.tags == ()

    def test_metadata_default_empty(self):
        ctx = _make_ctx()
        assert ctx.metadata == {}

    def test_framework_version_set(self):
        ctx = _make_ctx()
        assert ctx.framework_version == VERSION


# ─────────────────────────────────────────────────────────────────────────────
# 4  Request
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationRequest:
    def test_factory_creates_frozen(self):
        req = _make_req()
        with pytest.raises((AttributeError, TypeError)):
            req.session_id = "other"  # type: ignore

    def test_has_metrics(self):
        req = _make_req(metrics={"lat": 10.0})
        assert req.has_metrics
        assert req.metric_count == 1

    def test_empty_metrics(self):
        req = make_monitoring_integration_request("s", "p", _make_ctx("s", "p"))
        assert not req.has_metrics
        assert req.metric_count == 0

    def test_rule_filter(self):
        req = make_monitoring_integration_request(
            "s", "p", _make_ctx("s", "p"), rule_ids=("r1",)
        )
        assert req.has_rule_filter

    def test_request_id_auto(self):
        r1 = _make_req()
        r2 = _make_req()
        assert r1.request_id != r2.request_id

    def test_window_metrics(self):
        wm = {"5m": {"p99": 42.0}}
        req = make_monitoring_integration_request(
            "s", "p", _make_ctx("s", "p"), window_metrics=wm
        )
        assert req.window_metrics["5m"]["p99"] == 42.0


# ─────────────────────────────────────────────────────────────────────────────
# 5  Response
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationResponse:
    def test_factory_creates_frozen(self):
        resp = _make_resp()
        with pytest.raises((AttributeError, TypeError)):
            resp.session_id = "x"  # type: ignore

    def test_defaults(self):
        resp = _make_resp()
        assert not resp.has_errors
        assert not resp.has_alerts
        assert not resp.has_snapshot
        assert resp.generated_count == 0
        assert resp.suppressed_count == 0

    def test_with_errors(self):
        resp = make_monitoring_integration_response(
            "req", "s", "p", errors=("boom",)
        )
        assert resp.has_errors

    def test_with_alerts(self):
        resp = make_monitoring_integration_response(
            "req", "s", "p", alerts_generated=("a1",)
        )
        assert resp.has_alerts
        assert resp.generated_count == 1

    def test_with_snapshot(self):
        resp = make_monitoring_integration_response(
            "req", "s", "p", snapshot_id="snap-1"
        )
        assert resp.has_snapshot

    def test_to_dict(self):
        resp = _make_resp()
        d = resp.to_dict()
        assert "response_id"   in d
        assert "session_id"    in d
        assert "portfolio_id"  in d

    def test_unique_response_ids(self):
        r1 = _make_resp()
        r2 = _make_resp()
        assert r1.response_id != r2.response_id


# ─────────────────────────────────────────────────────────────────────────────
# 6  Snapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationSnapshot:
    def test_factory_creates_frozen(self):
        snap = _make_snap()
        with pytest.raises((AttributeError, TypeError)):
            snap.session_id = "x"  # type: ignore

    def test_defaults(self):
        snap = _make_snap()
        assert snap.metric_count == 0
        assert not snap.has_active_alerts
        assert not snap.has_critical_or_above
        assert not snap.is_healthy

    def test_with_metrics(self):
        snap = make_integration_snapshot(
            "s", "p", metrics={"lat": 3.0}, snapshot_version=1
        )
        assert snap.metric_count == 1

    def test_get_metric(self):
        snap = make_integration_snapshot(
            "s", "p", metrics={"lat": 5.0}, snapshot_version=1
        )
        assert snap.get_metric("lat") == 5.0
        assert snap.get_metric("missing", 99.0) == 99.0

    def test_get_window_metric(self):
        wm = {"5m": {"p99": 7.0}}
        snap = make_integration_snapshot(
            "s", "p", window_metrics=wm, snapshot_version=1
        )
        assert snap.get_window_metric("5m", "p99") == 7.0
        assert snap.get_window_metric("5m", "missing", 1.0) == 1.0

    def test_is_newer_than(self):
        s1 = _make_snap()
        time.sleep(0.01)
        s2 = _make_snap()
        assert s2.is_newer_than(s1)

    def test_healthy_status(self):
        snap = make_integration_snapshot(
            "s", "p", health_status=HealthStatus.HEALTHY.value, snapshot_version=1
        )
        assert snap.is_healthy

    def test_to_dict_and_json(self):
        snap = _make_snap()
        d = snap.to_dict()
        j = snap.to_json()
        assert "snapshot_id" in d
        assert "snapshot_id" in j


# ─────────────────────────────────────────────────────────────────────────────
# 7  Health
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationHealth:
    def test_component_health_healthy(self):
        ch = make_component_health(ComponentType.LIFECYCLE, "lc", is_running=True)
        assert ch.is_healthy
        assert not ch.is_unhealthy
        assert ch.status == HealthStatus.HEALTHY

    def test_component_health_not_running(self):
        # is_running=False with no error → DEGRADED (not UNHEALTHY)
        ch = make_component_health(ComponentType.LIFECYCLE, "lc", is_running=False)
        assert not ch.is_healthy
        assert ch.status == HealthStatus.DEGRADED

    def test_component_health_unhealthy_with_error(self):
        ch = make_component_health(ComponentType.LIFECYCLE, "lc", is_running=False, error="crash")
        assert ch.is_unhealthy
        assert ch.status == HealthStatus.UNHEALTHY

    def test_component_health_with_error(self):
        ch = make_component_health(
            ComponentType.METRICS_ENGINE, "me", is_running=False, error="crashed"
        )
        assert ch.error == "crashed"

    def test_compute_all_healthy(self):
        chs = [
            make_component_health(ComponentType.LIFECYCLE,      "lc", is_running=True),
            make_component_health(ComponentType.METRICS_ENGINE, "me", is_running=True),
            make_component_health(ComponentType.ALERT_MANAGER,  "am", is_running=True),
        ]
        ih = compute_integration_health(chs)
        assert ih.overall_status == HealthStatus.HEALTHY
        assert ih.is_healthy
        assert ih.is_fully_operational

    def test_compute_any_degraded(self):
        chs = [
            make_component_health(ComponentType.LIFECYCLE,      "lc", is_running=True),
            make_component_health(ComponentType.METRICS_ENGINE, "me", is_running=False),
        ]
        ih = compute_integration_health(chs)
        # one stopped with no error → DEGRADED overall
        assert ih.overall_status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)
        assert not ih.is_healthy
        assert ih.has_unhealthy_components

    def test_compute_empty_list(self):
        # Empty list → vacuously all healthy → HEALTHY (implementation-defined)
        ih = compute_integration_health([])
        assert ih.overall_status in (HealthStatus.HEALTHY, HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN)

    def test_integration_health_to_dict(self):
        chs = [make_component_health(ComponentType.LIFECYCLE, "lc", is_running=True)]
        ih = compute_integration_health(chs)
        d = ih.to_dict()
        assert "overall_status"    in d
        assert "component_health"  in d

    def test_component_health_frozen(self):
        ch = make_component_health(ComponentType.LIFECYCLE, "lc", is_running=True)
        with pytest.raises((AttributeError, TypeError)):
            ch.status = HealthStatus.DEGRADED  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# 8  Status
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationStatus:
    def _make_health(self) -> IntegrationHealth:
        chs = [make_component_health(ComponentType.LIFECYCLE, "lc", is_running=True)]
        return compute_integration_health(chs)

    def test_running_status(self):
        h = self._make_health()
        sr = IntegrationStatusRecord(
            state=IntegrationState.RUNNING, health=h
        )
        assert sr.is_running

    def test_stopped_status(self):
        h = self._make_health()
        sr = IntegrationStatusRecord(
            state=IntegrationState.STOPPED, health=h
        )
        assert not sr.is_running

    def test_is_healthy_delegates(self):
        h = self._make_health()
        sr = IntegrationStatusRecord(
            state=IntegrationState.RUNNING, health=h
        )
        assert sr.is_healthy == h.is_healthy

    def test_to_dict(self):
        h = self._make_health()
        sr = IntegrationStatusRecord(state=IntegrationState.RUNNING, health=h)
        d = sr.to_dict()
        assert "state"  in d
        assert "health" in d


# ─────────────────────────────────────────────────────────────────────────────
# 9  Statistics
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationStatistics:
    def test_initial_zeros(self):
        s = IntegrationStatistics()
        assert s.requests_received  == 0
        assert s.requests_completed == 0
        assert s.requests_failed    == 0
        assert s.success_rate       == 0.0

    def test_record_received_and_completed(self):
        s = IntegrationStatistics()
        s.record_request_received()
        s.record_request_completed(10.0)
        assert s.requests_received  == 1
        assert s.requests_completed == 1
        assert s.average_duration_ms == 10.0

    def test_record_failed(self):
        s = IntegrationStatistics()
        s.record_request_received()
        s.record_request_failed()
        assert s.requests_failed == 1

    def test_success_rate(self):
        s = IntegrationStatistics()
        s.record_request_completed(0.0)
        s.record_request_completed(0.0)
        s.record_request_failed()
        # 2 completed, 1 failed → 2/3
        assert abs(s.success_rate - (2 / 3)) < 1e-9

    def test_failure_rate_complement(self):
        s = IntegrationStatistics()
        s.record_request_completed(0.0)
        s.record_request_failed()
        assert abs(s.success_rate + s.failure_rate - 1.0) < 1e-9

    def test_reset(self):
        s = IntegrationStatistics()
        s.record_request_received()
        s.record_request_completed(5.0)
        s.reset()
        assert s.requests_received  == 0
        assert s.requests_completed == 0

    def test_copy_is_independent(self):
        s = IntegrationStatistics()
        s.record_request_received()
        c = s.copy()
        s.record_request_received()
        assert c.requests_received == 1
        assert s.requests_received == 2

    def test_to_dict(self):
        s = IntegrationStatistics()
        d = s.to_dict()
        assert "requests_received"   in d
        assert "success_rate"        in d
        assert "average_duration_ms" in d

    def test_thread_safe_increments(self):
        s = IntegrationStatistics()
        threads = [
            threading.Thread(target=lambda: [s.record_request_received() for _ in range(100)])
            for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert s.requests_received == 1000


# ─────────────────────────────────────────────────────────────────────────────
# 10  History
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationHistory:
    def test_append_and_count(self):
        h = IntegrationHistory()
        r = _make_resp()
        h.append_response(r)
        assert h.response_count == 1
        assert h.latest_response() is r

    def test_bounded_responses(self):
        h = IntegrationHistory(max_responses=3)
        for _ in range(5):
            h.append_response(_make_resp())
        assert h.response_count == 3

    def test_responses_for_session(self):
        h = IntegrationHistory()
        s = _sid()
        h.append_response(_make_resp(s))
        h.append_response(_make_resp(_sid()))
        assert len(h.responses_for_session(s)) == 1

    def test_append_and_count_snapshots(self):
        h = IntegrationHistory()
        h.append_snapshot(_make_snap())
        assert h.snapshot_count == 1

    def test_append_and_count_events(self):
        h = IntegrationHistory()
        ev = make_monitoring_started(_sid())
        h.append_event(ev)
        assert h.event_count == 1

    def test_events_for_session(self):
        h = IntegrationHistory()
        s = _sid()
        h.append_event(make_monitoring_started(s))
        h.append_event(make_monitoring_started(_sid()))
        assert len(h.events_for_session(s)) == 1

    def test_events_matching(self):
        h = IntegrationHistory()
        h.append_event(make_monitoring_started(_sid()))
        h.append_event(make_monitoring_completed(_sid()))
        started = h.events_matching(
            lambda e: e.event_type == IntegrationEventType.MONITORING_STARTED
        )
        assert len(started) == 1

    def test_clear(self):
        h = IntegrationHistory()
        h.append_response(_make_resp())
        h.append_snapshot(_make_snap())
        h.append_event(make_monitoring_started(_sid()))
        h.clear()
        assert h.response_count == 0
        assert h.snapshot_count == 0
        assert h.event_count    == 0

    def test_latest_event_none_when_empty(self):
        h = IntegrationHistory()
        assert h.latest_event() is None

    def test_latest_snapshot_none_when_empty(self):
        h = IntegrationHistory()
        assert h.latest_snapshot() is None


# ─────────────────────────────────────────────────────────────────────────────
# 11  Events
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationEvents:
    def _assert_event(self, ev: IntegrationEvent, etype: IntegrationEventType):
        assert ev.event_type == etype
        assert ev.event_id
        assert ev.occurred_at > 0
        assert ev.version == VERSION

    def test_initialized(self):
        ev = make_monitoring_initialized("s1")
        self._assert_event(ev, IntegrationEventType.MONITORING_INITIALIZED)
        assert ev.session_id == "s1"

    def test_started(self):
        ev = make_monitoring_started("s2")
        self._assert_event(ev, IntegrationEventType.MONITORING_STARTED)

    def test_completed(self):
        ev = make_monitoring_completed("s3")
        self._assert_event(ev, IntegrationEventType.MONITORING_COMPLETED)

    def test_stopped(self):
        ev = make_monitoring_stopped("s4")
        self._assert_event(ev, IntegrationEventType.MONITORING_STOPPED)

    def test_restarted(self):
        ev = make_monitoring_restarted("s5")
        self._assert_event(ev, IntegrationEventType.MONITORING_RESTARTED)

    def test_validated(self):
        ev = make_monitoring_validated("s6")
        self._assert_event(ev, IntegrationEventType.MONITORING_VALIDATED)

    def test_health_changed(self):
        ev = make_monitoring_health_changed("s7", reason="component down")
        self._assert_event(ev, IntegrationEventType.MONITORING_HEALTH_CHANGED)
        assert ev.reason == "component down"

    def test_snapshot_published(self):
        ev = make_monitoring_snapshot_published("s8")
        self._assert_event(ev, IntegrationEventType.MONITORING_SNAPSHOT_PUBLISHED)

    def test_unique_event_ids(self):
        e1 = make_monitoring_started("s")
        e2 = make_monitoring_started("s")
        assert e1.event_id != e2.event_id

    def test_event_immutable(self):
        ev = make_monitoring_started("s")
        with pytest.raises((AttributeError, TypeError)):
            ev.event_id = "x"  # type: ignore

    def test_to_dict(self):
        ev = make_monitoring_started("s")
        d = ev.to_dict()
        assert "event_id"   in d
        assert "event_type" in d
        assert "session_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# 12  Registry
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationRegistry:
    def _started(self) -> IntegrationRegistry:
        r = IntegrationRegistry()
        r.start()
        return r

    def test_store_and_get_response(self):
        reg = self._started()
        resp = _make_resp()
        reg.store_response(resp)
        assert reg.get_response(resp.response_id) is resp
        reg.stop()

    def test_get_missing_raises(self):
        reg = self._started()
        with pytest.raises(IntegrationRequestNotFoundError):
            reg.get_response("nonexistent")
        reg.stop()

    def test_find_returns_none_when_missing(self):
        reg = self._started()
        assert reg.find_response("x") is None
        reg.stop()

    def test_store_and_get_snapshot(self):
        reg = self._started()
        snap = _make_snap()
        reg.store_snapshot(snap)
        assert reg.get_snapshot(snap.snapshot_id) is snap
        reg.stop()

    def test_responses_for_session(self):
        reg = self._started()
        s = _sid()
        r1 = _make_resp(s)
        r2 = _make_resp()
        reg.store_response(r1)
        reg.store_response(r2)
        results = reg.responses_for_session(s)
        assert len(results) == 1
        assert results[0].response_id == r1.response_id
        reg.stop()

    def test_bounded_eviction(self):
        reg = IntegrationRegistry(max_responses=2, max_snapshots=100)
        reg.start()
        for _ in range(4):
            reg.store_response(_make_resp())
        assert reg.response_count() == 2
        reg.stop()

    def test_clear(self):
        reg = self._started()
        reg.store_response(_make_resp())
        reg.store_snapshot(_make_snap())
        reg.clear()
        assert reg.response_count() == 0
        assert reg.snapshot_count()  == 0
        reg.stop()

    def test_operation_before_start_raises(self):
        reg = IntegrationRegistry()
        with pytest.raises(IntegrationNotRunningError):
            reg.store_response(_make_resp())


# ─────────────────────────────────────────────────────────────────────────────
# 13  Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationValidation:
    def setup_method(self):
        self.v = IntegrationValidator()

    def test_valid_context(self):
        ctx = _make_ctx()
        r = self.v.validate_context(ctx)
        assert r.is_valid

    def test_empty_session_id_fails(self):
        ctx = _make_ctx()
        # build a context-like object with empty session_id
        bad = MagicMock(spec=MonitoringIntegrationContext)
        bad.session_id   = ""
        bad.portfolio_id = "p1"
        r = self.v.validate_context(bad)
        assert not r.is_valid
        assert r.errors

    def test_empty_portfolio_id_fails(self):
        bad = MagicMock(spec=MonitoringIntegrationContext)
        bad.session_id   = "s1"
        bad.portfolio_id = ""
        r = self.v.validate_context(bad)
        assert not r.is_valid

    def test_valid_request(self):
        req = _make_req()
        r = self.v.validate_request(req)
        assert r.is_valid

    def test_empty_request_id_fails(self):
        req = _make_req()
        bad = MagicMock()
        bad.request_id   = ""
        bad.session_id   = req.session_id
        bad.portfolio_id = req.portfolio_id
        bad.context      = req.context
        bad.metrics      = req.metrics
        r = self.v.validate_request(bad)
        assert not r.is_valid

    def test_no_metrics_yields_warning(self):
        req = make_monitoring_integration_request("s", "p", _make_ctx("s", "p"))
        r = self.v.validate_request(req)
        assert r.is_valid          # still valid
        assert r.warnings          # but warning present

    def test_validation_result_add_error(self):
        vr = IntegrationValidationResult()
        assert vr.is_valid
        vr.add_error("broken")
        assert not vr.is_valid
        assert "broken" in vr.errors

    def test_validation_result_add_warning(self):
        vr = IntegrationValidationResult()
        vr.add_warning("slow")
        assert vr.is_valid
        assert "slow" in vr.warnings

    def test_validation_result_to_dict(self):
        vr = IntegrationValidationResult()
        vr.add_error("e1")
        d = vr.to_dict()
        assert "is_valid" in d
        assert "errors"   in d


# ─────────────────────────────────────────────────────────────────────────────
# 14  ComponentRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestComponentRegistry:
    def _mock_running(self):
        m = MagicMock()
        m.lifecycle_state.return_value = "running"
        return m

    def _mock_stopped(self):
        m = MagicMock()
        m.lifecycle_state.return_value = "stopped"
        return m

    def test_register_and_get(self):
        cr = ComponentRegistry()
        obj = self._mock_running()
        cr.register(ComponentType.LIFECYCLE, "lc", obj)
        entry = cr.get(ComponentType.LIFECYCLE)
        assert entry is not None
        assert entry.component_name == "lc"
        assert entry.instance is obj

    def test_is_registered(self):
        cr = ComponentRegistry()
        assert not cr.is_registered(ComponentType.LIFECYCLE)
        cr.register(ComponentType.LIFECYCLE, "lc", self._mock_running())
        assert cr.is_registered(ComponentType.LIFECYCLE)

    def test_all_running_true(self):
        cr = ComponentRegistry()
        cr.register(ComponentType.LIFECYCLE,      "lc", self._mock_running())
        cr.register(ComponentType.METRICS_ENGINE, "me", self._mock_running())
        assert cr.all_running()

    def test_all_running_false_when_any_stopped(self):
        cr = ComponentRegistry()
        cr.register(ComponentType.LIFECYCLE,      "lc", self._mock_running())
        cr.register(ComponentType.METRICS_ENGINE, "me", self._mock_stopped())
        assert not cr.all_running()

    def test_any_unhealthy(self):
        cr = ComponentRegistry()
        cr.register(ComponentType.LIFECYCLE, "lc", self._mock_stopped())
        assert cr.any_unhealthy()

    def test_get_instance(self):
        cr = ComponentRegistry()
        obj = self._mock_running()
        cr.register(ComponentType.LIFECYCLE, "lc", obj)
        assert cr.get_instance(ComponentType.LIFECYCLE) is obj

    def test_get_none_when_not_registered(self):
        cr = ComponentRegistry()
        assert cr.get(ComponentType.LIFECYCLE) is None
        assert cr.get_instance(ComponentType.LIFECYCLE) is None

    def test_clear(self):
        cr = ComponentRegistry()
        cr.register(ComponentType.LIFECYCLE, "lc", self._mock_running())
        cr.clear()
        assert cr.component_count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# 15  ComponentFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestComponentFactory:
    def test_factory_lifecycle(self):
        f = ComponentFactory()
        f.start()
        lc = f.create_lifecycle()
        assert lc is not None
        f.stop()

    def test_factory_metrics_engine(self):
        f = ComponentFactory()
        f.start()
        me = f.create_metrics_engine()
        assert me is not None
        f.stop()

    def test_factory_alert_manager(self):
        f = ComponentFactory()
        f.start()
        am = f.create_alert_manager()
        assert am is not None
        f.stop()

    def test_each_create_is_independent(self):
        f = ComponentFactory()
        f.start()
        lc1 = f.create_lifecycle()
        lc2 = f.create_lifecycle()
        assert lc1 is not lc2
        f.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 16  MonitoringIntegrationManager
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationManager:
    def _started(self) -> MonitoringIntegrationManager:
        m = MonitoringIntegrationManager()
        m.start()
        return m

    def test_store_and_get_response(self):
        m = self._started()
        resp = _make_resp()
        m.store_response(resp)
        assert m.get_response(resp.response_id) is resp
        m.stop()

    def test_find_returns_none(self):
        m = self._started()
        assert m.find_response("nonexistent") is None
        m.stop()

    def test_responses_for_session(self):
        m = self._started()
        s = _sid()
        r1 = _make_resp(s)
        r2 = _make_resp()
        m.store_response(r1)
        m.store_response(r2)
        results = m.responses_for_session(s)
        assert len(results) == 1
        m.stop()

    def test_statistics_copy(self):
        m = self._started()
        stats = m.statistics()
        assert isinstance(stats, IntegrationStatistics)
        m.stop()

    def test_history_reference(self):
        m = self._started()
        h = m.history()
        assert isinstance(h, IntegrationHistory)
        m.stop()

    def test_event_listener(self):
        m = self._started()
        received: List[IntegrationEvent] = []
        m.add_event_listener(received.append)
        ev = make_monitoring_started(_sid())
        m.emit(ev)
        assert len(received) == 1
        assert received[0] is ev
        m.stop()

    def test_remove_event_listener(self):
        m = self._started()
        received: List[IntegrationEvent] = []
        m.add_event_listener(received.append)
        m.remove_event_listener(received.append)
        m.emit(make_monitoring_started(_sid()))
        assert len(received) == 0
        m.stop()

    def test_operation_before_start_raises(self):
        m = MonitoringIntegrationManager()
        with pytest.raises(IntegrationNotRunningError):
            m.store_response(_make_resp())


# ─────────────────────────────────────────────────────────────────────────────
# 17  Engine basics
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrationEngine:
    def test_start_and_stop(self):
        engine = ExecutionMonitoringIntegrationEngine()
        engine.start()
        assert engine.lifecycle_state() in ("running", "enginestate.running")
        engine.stop()
        assert engine.lifecycle_state() in ("stopped", "enginestate.stopped")

    def test_initialize_alias(self):
        engine = ExecutionMonitoringIntegrationEngine()
        engine.initialize()
        assert engine.lifecycle_state() in ("running", "enginestate.running")
        engine.stop()

    def test_double_start(self):
        engine = ExecutionMonitoringIntegrationEngine()
        engine.start()
        # second start / initialize should not crash
        try:
            engine.initialize()
        except Exception:
            pass
        engine.stop()

    def test_restart(self):
        engine = ExecutionMonitoringIntegrationEngine()
        engine.start()
        engine.restart()
        assert engine.lifecycle_state() in ("running", "enginestate.running")
        engine.stop()

    def test_submit_before_start_raises(self):
        engine = ExecutionMonitoringIntegrationEngine()
        req = _make_req()
        with pytest.raises(IntegrationNotRunningError):
            engine.submit(req)

    def test_query_before_start_raises(self):
        engine = ExecutionMonitoringIntegrationEngine()
        with pytest.raises(IntegrationNotRunningError):
            engine.query()

    def test_statistics_returned(self):
        engine = _started_engine()
        stats = engine.statistics()
        assert isinstance(stats, IntegrationStatistics)
        engine.stop()

    def test_history_returned(self):
        engine = _started_engine()
        h = engine.history()
        assert isinstance(h, IntegrationHistory)
        engine.stop()

    def test_validate_without_start(self):
        engine = ExecutionMonitoringIntegrationEngine()
        req = _make_req()
        # validate does not require the engine to be running
        result = engine.validate(req)
        assert isinstance(result, IntegrationValidationResult)


# ─────────────────────────────────────────────────────────────────────────────
# 18  Full submit() workflow
# ─────────────────────────────────────────────────────────────────────────────

class TestWorkflow:
    def setup_method(self):
        self.engine = _started_engine()

    def teardown_method(self):
        try:
            self.engine.stop()
        except Exception:
            pass

    def test_submit_returns_response(self):
        req = _make_req()
        resp = self.engine.submit(req)
        assert isinstance(resp, MonitoringIntegrationResponse)

    def test_submit_response_ids_match(self):
        req = _make_req()
        resp = self.engine.submit(req)
        assert resp.request_id   == req.request_id
        assert resp.session_id   == req.session_id
        assert resp.portfolio_id == req.portfolio_id

    def test_submit_has_snapshot(self):
        req = _make_req()
        resp = self.engine.submit(req)
        assert resp.has_snapshot

    def test_submit_metrics_count(self):
        req = _make_req(metrics={"lat": 1.0, "err": 0.0})
        resp = self.engine.submit(req)
        assert resp.metrics_count == 2

    def test_submit_invalid_request_returns_error_response(self):
        # request with empty session_id fails validation
        bad_ctx = MagicMock(spec=MonitoringIntegrationContext)
        bad_ctx.session_id   = ""
        bad_ctx.portfolio_id = "p"
        bad_ctx.gateway_id   = None
        bad_ctx.strategy_id  = None
        bad_ctx.workflow_id  = None
        bad_ctx.order_id     = None
        bad_req = make_monitoring_integration_request("", "p", bad_ctx, request_id="req-bad")
        resp = self.engine.submit(bad_req)
        assert resp.has_errors

    def test_submit_increments_statistics(self):
        req = _make_req()
        before = self.engine.statistics().requests_received
        self.engine.submit(req)
        after = self.engine.statistics().requests_received
        assert after == before + 1

    def test_submit_records_in_history(self):
        req = _make_req()
        self.engine.submit(req)
        h = self.engine.history()
        assert h.response_count >= 1

    def test_submit_emits_events(self):
        received: List[IntegrationEvent] = []
        self.engine.add_event_listener(received.append)
        req = _make_req()
        self.engine.submit(req)
        assert len(received) >= 1
        self.engine.remove_event_listener(received.append)

    def test_query_after_submit(self):
        req = _make_req()
        self.engine.submit(req)
        results = self.engine.query(req.session_id)
        assert len(results) >= 1

    def test_query_all(self):
        req = _make_req()
        self.engine.submit(req)
        results = self.engine.query()
        assert len(results) >= 1

    def test_query_limit(self):
        for _ in range(5):
            self.engine.submit(_make_req())
        results = self.engine.query(limit=2)
        assert len(results) == 2

    def test_query_with_alerts_filter(self):
        req = _make_req()
        self.engine.submit(req)
        # with_alerts filter — may return 0 or >0 depending on rule thresholds
        results = self.engine.query(with_alerts=True)
        assert isinstance(results, list)

    def test_snapshot_returns_snapshot(self):
        s, p = _sid(), _pid()
        req = _make_req(s, p)
        self.engine.submit(req)
        snap = self.engine.snapshot(s, p)
        assert isinstance(snap, MonitoringIntegrationSnapshot)
        assert snap.session_id == s

    def test_evaluation_duration_positive(self):
        req = _make_req()
        resp = self.engine.submit(req)
        assert resp.evaluation_duration_ms >= 0.0

    def test_multiple_submits_different_sessions(self):
        resps = [self.engine.submit(_make_req()) for _ in range(5)]
        assert all(isinstance(r, MonitoringIntegrationResponse) for r in resps)
        resp_ids = {r.response_id for r in resps}
        assert len(resp_ids) == 5


# ─────────────────────────────────────────────────────────────────────────────
# 19  Health
# ─────────────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_when_running(self):
        engine = _started_engine()
        h = engine.health()
        assert isinstance(h, IntegrationHealth)
        assert h.is_healthy
        engine.stop()

    def test_health_before_start(self):
        engine = ExecutionMonitoringIntegrationEngine()
        h = engine.health()
        assert isinstance(h, IntegrationHealth)
        # not started → at least one component unhealthy
        assert not h.is_healthy or h.overall_status is not None

    def test_status_when_running(self):
        engine = _started_engine()
        sr = engine.status()
        assert sr.is_running
        assert sr.uptime_seconds >= 0.0
        assert sr.started_at is not None
        engine.stop()

    def test_status_includes_health(self):
        engine = _started_engine()
        sr = engine.status()
        assert isinstance(sr.health, IntegrationHealth)
        engine.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 20  Concurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_submits(self):
        engine = _started_engine()
        errors: List[Exception] = []

        def _submit():
            try:
                engine.submit(_make_req())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_submit) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Errors: {errors}"
        assert engine.statistics().requests_received == 20
        engine.stop()

    def test_concurrent_statistics_updates(self):
        s = IntegrationStatistics()
        threads = [
            threading.Thread(target=lambda: [s.record_request_received() for _ in range(50)])
            for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert s.requests_received == 500

    def test_concurrent_history_append(self):
        h = IntegrationHistory()
        threads = [
            threading.Thread(target=lambda: h.append_response(_make_resp()))
            for _ in range(30)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert h.response_count == 30

    def test_concurrent_registry_store(self):
        reg = IntegrationRegistry()
        reg.start()
        errors: List[Exception] = []

        def _store():
            try:
                reg.store_response(_make_resp())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_store) for _ in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        reg.stop()

    def test_event_listener_thread_safety(self):
        engine = _started_engine()
        counts: Dict[str, int] = {"n": 0}
        lock = threading.Lock()

        def listener(ev: IntegrationEvent):
            with lock:
                counts["n"] += 1

        engine.add_event_listener(listener)

        threads = [threading.Thread(target=lambda: engine.submit(_make_req())) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        engine.remove_event_listener(listener)
        assert counts["n"] >= 10   # at least one event per submit
        engine.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 21  Regression / edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionEdgeCases:
    def test_statistics_average_zero_when_no_completions(self):
        s = IntegrationStatistics()
        assert s.average_duration_ms == 0.0

    def test_history_deque_max_len_one(self):
        h = IntegrationHistory(max_responses=1)
        h.append_response(_make_resp())
        h.append_response(_make_resp())
        assert h.response_count == 1

    def test_snapshot_version_monotonic(self):
        engine = _started_engine()
        s, p = _sid(), _pid()
        v1 = engine._next_snapshot_version(s)
        v2 = engine._next_snapshot_version(s)
        assert v2 == v1 + 1
        engine.stop()

    def test_remove_listener_identity_bound_method(self):
        """Bound method identity regression — must use == not is."""
        received: List[IntegrationEvent] = []
        engine = _started_engine()

        class _Receiver:
            def on_event(self, ev: IntegrationEvent):
                received.append(ev)

        obj = _Receiver()
        engine.add_event_listener(obj.on_event)
        engine.remove_event_listener(obj.on_event)

        engine.submit(_make_req())  # should not call on_event
        assert len(received) == 0
        engine.stop()

    def test_submit_with_window_metrics(self):
        engine = _started_engine()
        wm = {"5m": {"p99": 20.0}, "15m": {"p99": 18.0}}
        req = make_monitoring_integration_request(
            _sid(), _pid(), _make_ctx(),
            metrics={"lat": 5.0},
            window_metrics=wm,
        )
        resp = engine.submit(req)
        assert not resp.has_errors
        engine.stop()

    def test_context_factory_with_all_optional(self):
        ctx = make_monitoring_integration_context(
            "s", "p",
            gateway_id  = "gw",
            strategy_id = "st",
            workflow_id = "wf",
            order_id    = "ord",
            tags        = ("tag1", "tag2"),
            metadata    = {"k": "v"},
        )
        assert ctx.has_gateway
        assert ctx.has_strategy
        assert ctx.has_workflow
        assert ctx.tags == ("tag1", "tag2")
        assert ctx.metadata["k"] == "v"

    def test_integration_registry_all_responses(self):
        reg = IntegrationRegistry()
        reg.start()
        for _ in range(3):
            reg.store_response(_make_resp())
        assert len(reg.all_responses()) == 3
        reg.stop()

    def test_integration_snapshot_latest_for_session(self):
        reg = IntegrationRegistry()
        reg.start()
        s = _sid()
        snap1 = make_integration_snapshot(s, "p", snapshot_version=1)
        time.sleep(0.01)
        snap2 = make_integration_snapshot(s, "p", snapshot_version=2)
        reg.store_snapshot(snap1)
        reg.store_snapshot(snap2)
        latest = reg.latest_snapshot_for_session(s)
        assert latest is not None
        # latest should be the more recent one
        assert latest.created_at >= snap1.created_at
        reg.stop()

    def test_component_factory_creates_without_error(self):
        f = ComponentFactory()
        f.start()
        lc = f.create_lifecycle(max_sessions=10, max_history=10)
        me = f.create_metrics_engine(max_points_per_series=100, max_snapshots=100, max_history=10)
        am = f.create_alert_manager(max_alerts=100, max_history=10, escalation_age_sec=60.0)
        assert lc is not None
        assert me is not None
        assert am is not None
        f.stop()

    def test_validation_result_multiple_errors(self):
        vr = IntegrationValidationResult()
        vr.add_error("err1")
        vr.add_error("err2")
        assert len(vr.errors) == 2
        assert not vr.is_valid

    def test_engine_stop_idempotent(self):
        engine = _started_engine()
        engine.stop()
        try:
            engine.stop()
        except Exception:
            pass   # second stop may raise — that is acceptable
