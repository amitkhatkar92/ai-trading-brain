"""
test_knowledge_integration_m6.py
---------------------------------
Comprehensive test suite for C14 M6 — Knowledge Integration.

Coverage target: ≥ 95% of iios/knowledge/integration/*.

Run:
    .venv/Scripts/python.exe -m pytest tests/unit/knowledge/test_knowledge_integration_m6.py -x --tb=short -q
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from iios.knowledge.integration import (
    # Constants
    INTEGRATION_SYSTEM_ID, VERSION, SCHEMA_VERSION, FRAMEWORK_VERSION,
    DEFAULT_MAX_HISTORY, DEFAULT_MAX_REQUESTS, DEFAULT_TIMEOUT_MS,
    COMPONENT_LIFECYCLE, COMPONENT_ENGINE, COMPONENT_GOVERNANCE,
    COMPONENT_INTELLIGENCE, COMPONENT_SNAPSHOT,
    # Enums
    IntegrationState, IntegrationEventType, IntegrationPhase,
    IntegrationRequestType, IntegrationValidationCode, ComponentStatus,
    # Exceptions
    KnowledgeIntegrationError, IntegrationRequestError,
    IntegrationValidationError, IntegrationExecutionError,
    IntegrationComponentError, IntegrationTimeoutError,
    IntegrationStateError, IntegrationCapacityError,
    IntegrationSnapshotError,
    # Context
    KnowledgeIntegrationContext, KnowledgeArtifactContext,
    # Request / Response
    KnowledgeIntegrationRequest, KnowledgeIntegrationResponse,
    # Domain objects
    KnowledgeIntegrationSnapshot,
    ComponentHealth, KnowledgeHealthSummary, KnowledgeIntegrationHealth,
    KnowledgeIntegrationStatus, KnowledgeIntegrationStatusTracker,
    KnowledgeStatistics, KnowledgeIntegrationStatistics,
    # Events
    IntegrationEvent, IntegrationEventBus,
    # Validation
    IntegrationValidationResult, IntegrationValidationReport,
    KnowledgeIntegrationValidation,
    # History & Registry
    KnowledgeIntegrationHistory, KnowledgeIntegrationRegistry,
    # Component layer
    KnowledgeComponentRegistry, KnowledgeComponentFactory,
    # Manager
    KnowledgeIntegrationManager,
    # Engine
    KnowledgeIntegrationEngine,
)
from iios.knowledge.snapshot import KnowledgeSnapshotFactory


# ════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════

def _make_request(
    session_id:    str = "sess-test",
    workflow_id:   str = "wf-test",
    enterprise_id: str = "ent-test",
    **kwargs,
) -> KnowledgeIntegrationRequest:
    return KnowledgeIntegrationRequest.create(
        session_id    = session_id,
        workflow_id   = workflow_id,
        enterprise_id = enterprise_id,
        **kwargs,
    )


def _make_engine(started: bool = True) -> KnowledgeIntegrationEngine:
    """Create an engine with only M5 (snapshot) — M1-M4 are stubs."""
    registry = KnowledgeComponentRegistry()
    registry.register_snapshot(KnowledgeSnapshotFactory())
    engine = KnowledgeIntegrationEngine(registry=registry)
    engine.initialize()
    if started:
        engine.start()
    return engine


# ════════════════════════════════════════════════════════════════════════
# 1. Constants
# ════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_system_id(self):
        assert INTEGRATION_SYSTEM_ID == "iios:knowledge:integration"

    def test_version_strings(self):
        assert VERSION and SCHEMA_VERSION and FRAMEWORK_VERSION

    def test_state_members(self):
        assert len(IntegrationState) >= 7
        assert IntegrationState.RUNNING in IntegrationState
        assert IntegrationState.STOPPED in IntegrationState

    def test_event_type_members(self):
        assert len(IntegrationEventType) == 8

    def test_phase_members(self):
        assert len(IntegrationPhase) == 9

    def test_validation_code_members(self):
        assert len(IntegrationValidationCode) == 7

    def test_component_names(self):
        assert COMPONENT_LIFECYCLE == "knowledge_lifecycle"
        assert COMPONENT_ENGINE    == "knowledge_engine"
        assert COMPONENT_SNAPSHOT  == "knowledge_snapshot"

    def test_defaults(self):
        assert DEFAULT_MAX_HISTORY  == 1_000
        assert DEFAULT_MAX_REQUESTS == 10_000
        assert DEFAULT_TIMEOUT_MS   == 30_000


# ════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_hierarchy(self):
        for cls in [
            IntegrationRequestError, IntegrationValidationError,
            IntegrationExecutionError, IntegrationComponentError,
            IntegrationTimeoutError, IntegrationStateError,
            IntegrationCapacityError, IntegrationSnapshotError,
        ]:
            assert issubclass(cls, KnowledgeIntegrationError)

    def test_error_codes(self):
        assert KnowledgeIntegrationError.error_code == "KIN-000"
        assert IntegrationRequestError.error_code    == "KIN-001"
        assert IntegrationValidationError.error_code == "KIN-002"
        assert IntegrationExecutionError.error_code  == "KIN-003"
        assert IntegrationComponentError.error_code  == "KIN-004"
        assert IntegrationTimeoutError.error_code    == "KIN-005"
        assert IntegrationStateError.error_code      == "KIN-006"
        assert IntegrationCapacityError.error_code   == "KIN-007"
        assert IntegrationSnapshotError.error_code   == "KIN-008"

    def test_validation_error_has_failed_checks(self):
        exc = IntegrationValidationError("fail", failed_checks=["A"])
        assert exc.failed_checks == ["A"]

    def test_component_error_has_component(self):
        exc = IntegrationComponentError("err", component="m4")
        assert exc.component == "m4"

    def test_timeout_error_has_timeout_ms(self):
        exc = IntegrationTimeoutError("timeout", timeout_ms=5000)
        assert exc.timeout_ms == 5000

    def test_state_error_has_current_state(self):
        exc = IntegrationStateError("err", current_state="stopped")
        assert exc.current_state == "stopped"

    def test_capacity_error_has_limit(self):
        exc = IntegrationCapacityError(limit=100)
        assert exc.limit == 100


# ════════════════════════════════════════════════════════════════════════
# 3. Context
# ════════════════════════════════════════════════════════════════════════

class TestKnowledgeIntegrationContext:
    def test_create(self):
        ctx = KnowledgeIntegrationContext.create("s", "w", "e")
        assert ctx.session_id    == "s"
        assert ctx.workflow_id   == "w"
        assert ctx.enterprise_id == "e"
        assert ctx.correlation_id.startswith("cid-")
        assert ctx.trace_id.startswith("tid-")

    def test_frozen(self):
        ctx = KnowledgeIntegrationContext.create("s", "w", "e")
        with pytest.raises((AttributeError, TypeError)):
            ctx.session_id = "x"   # type: ignore[misc]

    def test_with_phase(self):
        ctx  = KnowledgeIntegrationContext.create("s", "w", "e")
        ctx2 = ctx.with_phase(IntegrationPhase.VALIDATE)
        assert ctx2.phase == IntegrationPhase.VALIDATE
        assert ctx2.integration_id == ctx.integration_id

    def test_to_dict_from_dict(self):
        ctx  = KnowledgeIntegrationContext.create("s", "w", "e")
        ctx2 = KnowledgeIntegrationContext.from_dict(ctx.to_dict())
        assert ctx2.integration_id == ctx.integration_id

    def test_artifact_context(self):
        art = KnowledgeArtifactContext.create("market", {"price": 100})
        assert art.artifact_type == "market"
        assert art.content == {"price": 100}
        assert art.artifact_id.startswith("art-")


# ════════════════════════════════════════════════════════════════════════
# 4. Request
# ════════════════════════════════════════════════════════════════════════

class TestKnowledgeIntegrationRequest:
    def test_create(self):
        req = _make_request()
        assert req.session_id    == "sess-test"
        assert req.workflow_id   == "wf-test"
        assert req.enterprise_id == "ent-test"
        assert req.request_id.startswith("req-")
        assert req.request_type == IntegrationRequestType.FULL_INTEGRATION
        assert req.timeout_ms   == DEFAULT_TIMEOUT_MS

    def test_frozen(self):
        req = _make_request()
        with pytest.raises((AttributeError, TypeError)):
            req.session_id = "x"   # type: ignore[misc]

    def test_artifact_count(self):
        req = _make_request(artifacts=[{"id": "a1"}, {"id": "a2"}])
        assert req.artifact_count == 2

    def test_has_peer_snapshots_false(self):
        req = _make_request()
        assert req.has_peer_snapshots is False

    def test_has_peer_snapshots_true(self):
        req = _make_request(market_snapshot={"price": 100})
        assert req.has_peer_snapshots is True

    def test_to_dict_from_dict_roundtrip(self):
        req  = _make_request(artifacts=[{"id": "a1"}])
        req2 = KnowledgeIntegrationRequest.from_dict(req.to_dict())
        assert req2.request_id    == req.request_id
        assert req2.artifact_count == 1

    def test_all_peer_snapshot_fields(self):
        req = _make_request(
            execution_snapshot           = {"e": 1},
            execution_recovery_snapshot  = {"er": 1},
            execution_analytics_snapshot = {"ea": 1},
            decision_snapshot            = {"d": 1},
            portfolio_snapshot           = {"p": 1},
            risk_snapshot                = {"r": 1},
            market_snapshot              = {"m": 1},
            supervisor_snapshot          = {"s": 1},
        )
        assert req.has_peer_snapshots


# ════════════════════════════════════════════════════════════════════════
# 5. Response
# ════════════════════════════════════════════════════════════════════════

class TestKnowledgeIntegrationResponse:
    def test_success_factory(self):
        resp = KnowledgeIntegrationResponse.success(
            request_id     = "req-1",
            integration_id = "int-1",
            session_id     = "sess-1",
            workflow_id    = "wf-1",
            enterprise_id  = "ent-1",
            phases_completed = [IntegrationPhase.RECEIVE, IntegrationPhase.VALIDATE],
            snapshot_id    = "snap-abc",
        )
        assert resp.succeeded
        assert resp.snapshot_id == "snap-abc"
        assert len(resp.phases_completed) == 2

    def test_failure_factory(self):
        resp = KnowledgeIntegrationResponse.failure(
            request_id     = "req-1",
            integration_id = "int-1",
            session_id     = "sess-1",
            workflow_id    = "wf-1",
            enterprise_id  = "ent-1",
            error_message  = "something broke",
        )
        assert not resp.succeeded
        assert "broke" in resp.error_message

    def test_frozen(self):
        resp = KnowledgeIntegrationResponse.success(
            "r", "i", "s", "w", "e", phases_completed=[]
        )
        with pytest.raises((AttributeError, TypeError)):
            resp.succeeded = False   # type: ignore[misc]

    def test_to_dict_from_dict(self):
        resp = KnowledgeIntegrationResponse.success(
            "r", "i", "s", "w", "e",
            phases_completed=[IntegrationPhase.RECEIVE],
            snapshot_id="snap-1",
        )
        resp2 = KnowledgeIntegrationResponse.from_dict(resp.to_dict())
        assert resp2.response_id   == resp.response_id
        assert resp2.snapshot_id   == "snap-1"


# ════════════════════════════════════════════════════════════════════════
# 6. Events
# ════════════════════════════════════════════════════════════════════════

class TestIntegrationEvents:
    def test_event_create(self):
        evt = IntegrationEvent.create(
            IntegrationEventType.INTEGRATION_STARTED,
            "int-1", "sess-1", {"k": "v"},
        )
        assert evt.event_id.startswith("ievt-")
        assert evt.event_type == IntegrationEventType.INTEGRATION_STARTED

    def test_event_frozen(self):
        evt = IntegrationEvent.create(IntegrationEventType.INTEGRATION_COMPLETED)
        with pytest.raises((AttributeError, TypeError)):
            evt.event_id = "x"   # type: ignore[misc]

    def test_event_to_dict(self):
        evt = IntegrationEvent.create(IntegrationEventType.SNAPSHOT_PUBLISHED)
        d   = evt.to_dict()
        assert d["event_type"] == IntegrationEventType.SNAPSHOT_PUBLISHED.value

    def test_bus_emit_and_listener(self):
        bus      = IntegrationEventBus()
        received: List[IntegrationEvent] = []
        bus.add_listener(received.append)
        bus.emit(IntegrationEventType.INTEGRATION_STARTED, "i", "s", {"x": 1})
        assert len(received) == 1
        assert received[0].event_type == IntegrationEventType.INTEGRATION_STARTED

    def test_bus_remove_listener(self):
        bus = IntegrationEventBus()
        fn  = lambda e: None
        bus.add_listener(fn)
        bus.remove_listener(fn)
        assert bus.listener_count() == 0

    def test_bus_suppresses_exceptions(self):
        bus = IntegrationEventBus()
        bus.add_listener(lambda e: 1 / 0)
        bus.emit(IntegrationEventType.INTEGRATION_FAILED)  # should not raise

    def test_bus_clear(self):
        bus = IntegrationEventBus()
        bus.add_listener(lambda e: None)
        bus.clear()
        assert bus.listener_count() == 0

    def test_bus_isolation(self):
        bus1 = IntegrationEventBus()
        bus2 = IntegrationEventBus()
        received: List[IntegrationEvent] = []
        bus1.add_listener(received.append)
        bus2.emit(IntegrationEventType.SNAPSHOT_PUBLISHED)
        assert len(received) == 0


# ════════════════════════════════════════════════════════════════════════
# 7. Statistics
# ════════════════════════════════════════════════════════════════════════

class TestIntegrationStatistics:
    def test_all_counters(self):
        stats = KnowledgeIntegrationStatistics()
        stats.record_request()
        stats.record_success(processing_ms=100, response_ms=110)
        stats.record_failure()
        stats.record_knowledge_publication()
        stats.record_snapshot_publication()
        r = stats.report()
        assert r.integration_requests    == 1
        assert r.successful_integrations == 1
        assert r.failed_integrations     == 1
        assert r.knowledge_publications  == 1
        assert r.snapshot_publications   == 1
        assert r.average_processing_time_ms == 50.0  # 100/2
        assert 0.0 <= r.knowledge_availability <= 1.0

    def test_reset(self):
        stats = KnowledgeIntegrationStatistics()
        stats.record_request()
        stats.reset()
        r = stats.report()
        assert r.integration_requests == 0

    def test_report_frozen(self):
        r = KnowledgeIntegrationStatistics().report()
        with pytest.raises((AttributeError, TypeError)):
            r.integration_requests = 99   # type: ignore[misc]

    def test_report_to_dict(self):
        r = KnowledgeIntegrationStatistics().report()
        d = r.to_dict()
        assert "integration_requests" in d
        assert "knowledge_availability" in d
        assert "captured_at" in d

    def test_availability_100_percent_when_no_failures(self):
        stats = KnowledgeIntegrationStatistics()
        stats.record_success()
        stats.record_success()
        r = stats.report()
        assert r.knowledge_availability == 1.0

    def test_availability_50_percent(self):
        stats = KnowledgeIntegrationStatistics()
        stats.record_success()
        stats.record_failure()
        r = stats.report()
        assert abs(r.knowledge_availability - 0.5) < 1e-9


# ════════════════════════════════════════════════════════════════════════
# 8. Health
# ════════════════════════════════════════════════════════════════════════

class TestIntegrationHealth:
    def test_component_health_available(self):
        ch = ComponentHealth.available("m4")
        assert ch.status == ComponentStatus.AVAILABLE
        assert ch.component_name == "m4"

    def test_component_health_unavailable(self):
        ch = ComponentHealth.unavailable("m3")
        assert ch.status == ComponentStatus.UNAVAILABLE

    def test_component_health_degraded(self):
        ch = ComponentHealth.degraded("m1", "slow response")
        assert ch.status == ComponentStatus.DEGRADED

    def test_component_health_frozen(self):
        ch = ComponentHealth.available("m5")
        with pytest.raises((AttributeError, TypeError)):
            ch.status = ComponentStatus.DEGRADED   # type: ignore[misc]

    def test_component_health_to_dict(self):
        ch = ComponentHealth.available("m4")
        d  = ch.to_dict()
        assert d["status"] == ComponentStatus.AVAILABLE.value

    def test_health_summary_healthy(self):
        h = KnowledgeHealthSummary.healthy(
            IntegrationState.RUNNING,
            [ComponentHealth.available("m5")],
        )
        assert h.overall_healthy
        assert h.integration_state == IntegrationState.RUNNING

    def test_health_summary_degraded(self):
        h = KnowledgeHealthSummary.degraded(
            IntegrationState.DEGRADED,
            [ComponentHealth.unavailable("m1")],
        )
        assert not h.overall_healthy

    def test_health_summary_to_dict(self):
        h = KnowledgeHealthSummary.healthy(
            IntegrationState.RUNNING,
            [ComponentHealth.available("m5")],
        )
        d = h.to_dict()
        assert d["overall_healthy"] is True
        assert len(d["component_health"]) == 1

    def test_integration_health_tracker(self):
        tracker = KnowledgeIntegrationHealth()
        tracker.update_state(IntegrationState.RUNNING)
        summary = tracker.check([ComponentHealth.available("m5")])
        assert summary.overall_healthy

    def test_integration_health_tracker_degraded(self):
        tracker = KnowledgeIntegrationHealth()
        tracker.update_state(IntegrationState.RUNNING)
        summary = tracker.check([ComponentHealth.unavailable("m4")])
        assert not summary.overall_healthy


# ════════════════════════════════════════════════════════════════════════
# 9. Status
# ════════════════════════════════════════════════════════════════════════

class TestIntegrationStatus:
    def test_initial_status(self):
        tracker = KnowledgeIntegrationStatusTracker()
        status  = tracker.get()
        assert status.state == IntegrationState.STOPPED
        assert not status.is_running
        assert status.integration_count == 0

    def test_running_status(self):
        tracker = KnowledgeIntegrationStatusTracker()
        tracker.set_state(IntegrationState.RUNNING)
        status = tracker.get()
        assert status.is_running
        assert status.is_healthy

    def test_record_request_and_snapshot(self):
        tracker = KnowledgeIntegrationStatusTracker()
        tracker.set_state(IntegrationState.RUNNING)
        tracker.record_request("req-1")
        tracker.record_snapshot("snap-1")
        status = tracker.get()
        assert status.integration_count == 1
        assert status.last_request_id   == "req-1"
        assert status.last_snapshot_id  == "snap-1"

    def test_status_to_dict(self):
        tracker = KnowledgeIntegrationStatusTracker()
        d = tracker.get().to_dict()
        assert "state" in d
        assert "uptime_seconds" in d
        assert "is_running" in d

    def test_status_frozen(self):
        tracker = KnowledgeIntegrationStatusTracker()
        status  = tracker.get()
        with pytest.raises((AttributeError, TypeError)):
            status.is_running = True   # type: ignore[misc]


# ════════════════════════════════════════════════════════════════════════
# 10. Validation
# ════════════════════════════════════════════════════════════════════════

class TestIntegrationValidation:
    def test_valid_request_passes(self):
        req    = _make_request()
        report = KnowledgeIntegrationValidation().validate(req)
        assert isinstance(report, IntegrationValidationReport)
        assert report.passed

    def test_7_checks_present(self):
        req    = _make_request()
        report = KnowledgeIntegrationValidation().validate(req)
        assert len(report.results) == 7

    def test_missing_session_fails(self):
        req = KnowledgeIntegrationRequest.create(
            session_id    = "",
            workflow_id   = "wf",
            enterprise_id = "ent",
        )
        report = KnowledgeIntegrationValidation().validate(req)
        assert not report.passed
        assert "integration_consistency" in report.failed_checks

    def test_query_without_text_fails(self):
        req = KnowledgeIntegrationRequest.create(
            session_id    = "s",
            workflow_id   = "w",
            enterprise_id = "e",
            request_type  = IntegrationRequestType.QUERY,
            query_text    = "",
        )
        report = KnowledgeIntegrationValidation().validate(req)
        assert not report.passed

    def test_zero_timeout_fails(self):
        req = KnowledgeIntegrationRequest.create(
            session_id    = "s",
            workflow_id   = "w",
            enterprise_id = "e",
            timeout_ms    = 0,
        )
        report = KnowledgeIntegrationValidation().validate(req)
        assert not report.passed

    def test_validate_response(self):
        resp = KnowledgeIntegrationResponse.success(
            "r", "i", "s", "w", "e", phases_completed=[]
        )
        ok = KnowledgeIntegrationValidation().validate_response(resp)
        assert ok is True

    def test_report_failed_checks(self):
        req = KnowledgeIntegrationRequest.create(
            session_id="", workflow_id="w", enterprise_id="e",
        )
        report = KnowledgeIntegrationValidation().validate(req)
        assert isinstance(report.failed_checks, list)

    def test_validation_result_to_dict(self):
        r = IntegrationValidationResult(
            code    = IntegrationValidationCode.INTEGRATION_CONSISTENCY,
            passed  = True,
            message = "OK",
        )
        d = r.to_dict()
        assert d["passed"] is True

    def test_validation_report_to_dict(self):
        req    = _make_request()
        report = KnowledgeIntegrationValidation().validate(req)
        d      = report.to_dict()
        assert "passed" in d
        assert "results" in d


# ════════════════════════════════════════════════════════════════════════
# 11. History
# ════════════════════════════════════════════════════════════════════════

class TestIntegrationHistory:
    def _make_resp(self, session_id: str = "sess-1") -> KnowledgeIntegrationResponse:
        return KnowledgeIntegrationResponse.success(
            "req-1", "int-1", session_id, "wf-1", "ent-1",
            phases_completed=[],
        )

    def test_record_and_recent(self):
        hist = KnowledgeIntegrationHistory()
        r    = self._make_resp()
        hist.record(r)
        assert r in hist.recent()

    def test_by_session(self):
        hist = KnowledgeIntegrationHistory()
        r1   = self._make_resp("sess-A")
        r2   = self._make_resp("sess-A")
        r3   = self._make_resp("sess-B")
        for r in (r1, r2, r3):
            hist.record(r)
        assert len(hist.by_session("sess-A")) == 2

    def test_bounded(self):
        hist = KnowledgeIntegrationHistory(max_history=3)
        for _ in range(5):
            hist.record(self._make_resp())
        assert hist.count() == 3

    def test_latest_for_session(self):
        hist = KnowledgeIntegrationHistory()
        r1   = self._make_resp("sess-C")
        r2   = self._make_resp("sess-C")
        hist.record(r1)
        hist.record(r2)
        assert hist.latest_for_session("sess-C") is r2

    def test_clear(self):
        hist = KnowledgeIntegrationHistory()
        hist.record(self._make_resp())
        hist.clear()
        assert hist.count() == 0


# ════════════════════════════════════════════════════════════════════════
# 12. Registry
# ════════════════════════════════════════════════════════════════════════

class TestIntegrationRegistry:
    def _make_resp(self) -> KnowledgeIntegrationResponse:
        return KnowledgeIntegrationResponse.success(
            "req-1", "int-1", "sess-1", "wf-1", "ent-1",
            phases_completed=[],
        )

    def test_register_and_get(self):
        reg  = KnowledgeIntegrationRegistry()
        resp = self._make_resp()
        reg.register(resp)
        assert reg.get(resp.response_id) is resp

    def test_remove(self):
        reg  = KnowledgeIntegrationRegistry()
        resp = self._make_resp()
        reg.register(resp)
        assert reg.remove(resp.response_id) is True
        assert reg.get(resp.response_id) is None

    def test_capacity_error(self):
        reg = KnowledgeIntegrationRegistry(max_requests=1)
        reg.register(self._make_resp())
        with pytest.raises(IntegrationCapacityError):
            reg.register(self._make_resp())

    def test_by_session(self):
        reg = KnowledgeIntegrationRegistry()
        r1  = KnowledgeIntegrationResponse.success(
            "r1", "i1", "sess-X", "w", "e", phases_completed=[]
        )
        r2  = KnowledgeIntegrationResponse.success(
            "r2", "i2", "sess-Y", "w", "e", phases_completed=[]
        )
        reg.register(r1)
        reg.register(r2)
        assert len(reg.by_session("sess-X")) == 1

    def test_clear(self):
        reg = KnowledgeIntegrationRegistry()
        reg.register(self._make_resp())
        reg.clear()
        assert reg.count() == 0


# ════════════════════════════════════════════════════════════════════════
# 13. Component Registry
# ════════════════════════════════════════════════════════════════════════

class TestKnowledgeComponentRegistry:
    def test_register_and_access(self):
        reg  = KnowledgeComponentRegistry()
        mock = MagicMock()
        reg.register_snapshot(mock)
        assert reg.snapshot_factory is mock

    def test_available_names(self):
        reg = KnowledgeComponentRegistry()
        reg.register_snapshot(KnowledgeSnapshotFactory())
        assert COMPONENT_SNAPSHOT in reg.available_names()

    def test_health_checks_available(self):
        reg   = KnowledgeComponentRegistry()
        reg.register_snapshot(KnowledgeSnapshotFactory())
        checks = reg.health_checks()
        names  = [c.component_name for c in checks]
        assert COMPONENT_SNAPSHOT in names

    def test_health_checks_unavailable_when_none(self):
        reg    = KnowledgeComponentRegistry()
        checks = reg.health_checks()
        for c in checks:
            assert c.status == ComponentStatus.UNAVAILABLE

    def test_clear(self):
        reg = KnowledgeComponentRegistry()
        reg.register_snapshot(KnowledgeSnapshotFactory())
        reg.clear()
        assert reg.snapshot_factory is None


# ════════════════════════════════════════════════════════════════════════
# 14. Component Factory
# ════════════════════════════════════════════════════════════════════════

class TestKnowledgeComponentFactory:
    def test_create_snapshot_factory_always_available(self):
        factory = KnowledgeComponentFactory()
        snap    = factory.create_snapshot_factory()
        assert snap is not None

    def test_create_registry(self):
        factory  = KnowledgeComponentFactory()
        registry = factory.create_registry()
        # M5 should always be registered
        assert registry.snapshot_factory is not None

    def test_registry_has_at_least_snapshot(self):
        registry = KnowledgeComponentFactory().create_registry()
        assert COMPONENT_SNAPSHOT in registry.available_names()


# ════════════════════════════════════════════════════════════════════════
# 15. Integration Snapshot
# ════════════════════════════════════════════════════════════════════════

class TestKnowledgeIntegrationSnapshot:
    def test_capture(self):
        snap = KnowledgeIntegrationSnapshot.capture(
            integration_state = IntegrationState.RUNNING,
            statistics        = {"integration_requests": 5},
            health            = {"overall_healthy": True},
            recent_responses  = [],
            uptime_seconds    = 42.0,
        )
        assert snap.snapshot_id.startswith("isnap-")
        assert snap.integration_state == IntegrationState.RUNNING
        assert snap.uptime_seconds == 42.0

    def test_frozen(self):
        snap = KnowledgeIntegrationSnapshot.capture(
            IntegrationState.STOPPED, {}, {}, []
        )
        with pytest.raises((AttributeError, TypeError)):
            snap.uptime_seconds = 9.9   # type: ignore[misc]

    def test_to_dict(self):
        snap = KnowledgeIntegrationSnapshot.capture(
            IntegrationState.RUNNING, {"x": 1}, {"y": 2}, [{"z": 3}]
        )
        d = snap.to_dict()
        assert d["integration_state"] == IntegrationState.RUNNING.value
        assert d["statistics"] == {"x": 1}


# ════════════════════════════════════════════════════════════════════════
# 16. Integration Engine — Lifecycle
# ════════════════════════════════════════════════════════════════════════

class TestIntegrationEngineLifecycle:
    def test_initialize_and_start(self):
        engine = _make_engine(started=True)
        assert engine.status().is_running

    def test_stop(self):
        engine = _make_engine()
        engine.stop()
        assert engine.status().state == IntegrationState.STOPPED

    def test_restart(self):
        engine = _make_engine()
        engine.restart()
        assert engine.status().is_running

    def test_initialize_idempotent(self):
        engine = _make_engine(started=False)
        engine.initialize()
        engine.initialize()   # second call should not raise

    def test_start_idempotent(self):
        engine = _make_engine()
        engine.start()   # already running — should not raise

    def test_stop_idempotent(self):
        engine = _make_engine()
        engine.stop()
        engine.stop()   # already stopped — should not raise

    def test_submit_raises_when_not_running(self):
        engine = _make_engine(started=False)
        with pytest.raises(IntegrationStateError):
            engine.submit(_make_request())


# ════════════════════════════════════════════════════════════════════════
# 17. Integration Engine — Public API
# ════════════════════════════════════════════════════════════════════════

class TestIntegrationEnginePublicAPI:
    def test_submit_returns_response(self):
        engine   = _make_engine()
        request  = _make_request()
        response = engine.submit(request)
        assert isinstance(response, KnowledgeIntegrationResponse)
        assert response.request_id == request.request_id

    def test_submit_succeeds(self):
        engine   = _make_engine()
        response = engine.submit(_make_request())
        assert response.succeeded

    def test_submit_has_snapshot_id(self):
        engine   = _make_engine()
        response = engine.submit(_make_request())
        assert response.snapshot_id  # non-empty string

    def test_submit_phases_completed(self):
        engine   = _make_engine()
        response = engine.submit(_make_request())
        assert IntegrationPhase.RECEIVE.value in response.phases_completed
        assert IntegrationPhase.VALIDATE.value in response.phases_completed

    def test_query(self):
        engine   = _make_engine()
        response = engine.query("s", "w", "e", "test query")
        assert isinstance(response, KnowledgeIntegrationResponse)

    def test_search(self):
        engine   = _make_engine()
        response = engine.search("s", "w", "e", "search text", filters={"k": "v"})
        assert isinstance(response, KnowledgeIntegrationResponse)

    def test_retrieve(self):
        engine   = _make_engine()
        response = engine.retrieve("s", "w", "e", "knowledge-id-123")
        assert isinstance(response, KnowledgeIntegrationResponse)

    def test_validate(self):
        engine  = _make_engine()
        req     = _make_request()
        report  = engine.validate(req)
        assert isinstance(report, IntegrationValidationReport)

    def test_health(self):
        engine = _make_engine()
        h      = engine.health()
        assert isinstance(h, KnowledgeHealthSummary)

    def test_status(self):
        engine = _make_engine()
        s      = engine.status()
        assert isinstance(s, KnowledgeIntegrationStatus)
        assert s.is_running

    def test_statistics(self):
        engine = _make_engine()
        engine.submit(_make_request())
        stats  = engine.statistics()
        assert isinstance(stats, KnowledgeStatistics)
        assert stats.integration_requests >= 1

    def test_snapshot(self):
        engine = _make_engine()
        snap   = engine.snapshot()
        assert isinstance(snap, KnowledgeIntegrationSnapshot)

    def test_history(self):
        engine = _make_engine()
        engine.submit(_make_request())
        hist = engine.history()
        assert len(hist) >= 1


# ════════════════════════════════════════════════════════════════════════
# 18. Workflow — all 9 phases
# ════════════════════════════════════════════════════════════════════════

class TestIntegrationWorkflow:
    def test_full_workflow_phases_recorded(self):
        engine   = _make_engine()
        response = engine.submit(_make_request())
        phases   = set(response.phases_completed)
        # All 9 phases must be in completed list
        for p in IntegrationPhase:
            assert p.value in phases, f"Missing phase: {p.value}"

    def test_with_peer_snapshots(self):
        engine  = _make_engine()
        request = _make_request(
            market_snapshot    = {"nifty": 24000},
            risk_snapshot      = {"var": 0.02},
            decision_snapshot  = {"signal": "BUY"},
        )
        response = engine.submit(request)
        assert response.succeeded

    def test_with_artifacts(self):
        engine  = _make_engine()
        request = _make_request(
            artifacts=[{"id": "a1", "type": "equity", "data": {"symbol": "RELIANCE"}}]
        )
        response = engine.submit(request)
        assert response.succeeded

    def test_validation_failure_returns_failure_response(self):
        engine  = _make_engine()
        request = KnowledgeIntegrationRequest.create(
            session_id    = "",
            workflow_id   = "w",
            enterprise_id = "e",
        )
        response = engine.submit(request)
        assert not response.succeeded
        assert response.error_message


# ════════════════════════════════════════════════════════════════════════
# 19. Lifecycle Coordination
# ════════════════════════════════════════════════════════════════════════

class TestLifecycleCoordination:
    def test_engine_without_m1_still_works(self):
        registry = KnowledgeComponentRegistry()
        registry.register_snapshot(KnowledgeSnapshotFactory())
        # No M1 registered
        engine = KnowledgeIntegrationEngine(registry=registry)
        engine.initialize()
        engine.start()
        response = engine.submit(_make_request())
        assert response.succeeded

    def test_engine_without_m4_still_works(self):
        registry = KnowledgeComponentRegistry()
        registry.register_snapshot(KnowledgeSnapshotFactory())
        engine = KnowledgeIntegrationEngine(registry=registry)
        engine.initialize()
        engine.start()
        response = engine.submit(_make_request())
        assert response.succeeded
        assert response.snapshot_id


# ════════════════════════════════════════════════════════════════════════
# 20. Events during workflow
# ════════════════════════════════════════════════════════════════════════

class TestWorkflowEvents:
    def test_events_emitted_on_submit(self):
        engine   = _make_engine()
        received: List[IntegrationEvent] = []
        engine.add_listener(received.append)
        engine.submit(_make_request())
        event_types = {e.event_type for e in received}
        assert IntegrationEventType.INTEGRATION_INITIALIZED in event_types
        assert IntegrationEventType.INTEGRATION_COMPLETED  in event_types
        assert IntegrationEventType.SNAPSHOT_PUBLISHED     in event_types

    def test_events_emitted_on_start_stop(self):
        engine   = _make_engine(started=False)
        received: List[IntegrationEvent] = []
        engine.add_listener(received.append)
        engine.initialize()
        engine.start()
        engine.stop()
        types = {e.event_type for e in received}
        assert IntegrationEventType.INTEGRATION_STARTED in types
        assert IntegrationEventType.INTEGRATION_STOPPED in types

    def test_remove_listener(self):
        engine = _make_engine()
        fn     = lambda e: None
        engine.add_listener(fn)
        engine.remove_listener(fn)
        # Should not raise; listener removed


# ════════════════════════════════════════════════════════════════════════
# 21. Statistics tracking during workflow
# ════════════════════════════════════════════════════════════════════════

class TestStatisticsDuringWorkflow:
    def test_stats_increment_on_success(self):
        engine = _make_engine()
        engine.submit(_make_request())
        stats  = engine.statistics()
        assert stats.integration_requests     >= 1
        assert stats.successful_integrations  >= 1
        assert stats.knowledge_publications   >= 1
        assert stats.snapshot_publications    >= 1

    def test_stats_increment_on_failure(self):
        engine  = _make_engine()
        bad_req = KnowledgeIntegrationRequest.create(
            session_id="", workflow_id="w", enterprise_id="e"
        )
        engine.submit(bad_req)
        stats = engine.statistics()
        assert stats.failed_integrations >= 1


# ════════════════════════════════════════════════════════════════════════
# 22. Concurrency
# ════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_submit(self):
        engine = _make_engine()
        errors: List[Exception] = []

        def worker() -> None:
            try:
                req  = _make_request()
                resp = engine.submit(req)
                assert resp is not None
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_concurrent_stats(self):
        stats  = KnowledgeIntegrationStatistics()
        errors: List[Exception] = []

        def worker() -> None:
            try:
                for _ in range(10):
                    stats.record_request()
                    stats.record_success(processing_ms=5.0)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        r = stats.report()
        assert r.integration_requests    == 100
        assert r.successful_integrations == 100

    def test_concurrent_event_bus(self):
        bus    = IntegrationEventBus()
        counts = [0]
        lock   = threading.Lock()

        def listener(e: IntegrationEvent) -> None:
            with lock:
                counts[0] += 1

        bus.add_listener(listener)
        errors: List[Exception] = []

        def emitter() -> None:
            try:
                for _ in range(5):
                    bus.emit(IntegrationEventType.INTEGRATION_EXECUTED)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=emitter) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert counts[0] == 50


# ════════════════════════════════════════════════════════════════════════
# 23. Regression — M1–M5 imports unaffected, M6 importable
# ════════════════════════════════════════════════════════════════════════

class TestRegression:
    def test_m6_package_importable(self):
        import iios.knowledge.integration as m6
        assert hasattr(m6, "KnowledgeIntegrationEngine")

    def test_m5_package_unaffected(self):
        import iios.knowledge.snapshot as m5
        assert hasattr(m5, "KnowledgeSnapshot")

    def test_m4_package_unaffected(self):
        import iios.knowledge.intelligence as m4
        assert hasattr(m4, "KnowledgeIntelligenceEngine")

    def test_m2_package_unaffected(self):
        import iios.knowledge.engine as m2
        assert hasattr(m2, "KnowledgeEngine")

    def test_m1_package_unaffected(self):
        import iios.knowledge.lifecycle as m1
        assert hasattr(m1, "KnowledgeLifecycle")

    def test_all_exports_present(self):
        import iios.knowledge.integration as m6
        for name in m6.__all__:
            assert hasattr(m6, name), f"Missing export: {name!r}"
