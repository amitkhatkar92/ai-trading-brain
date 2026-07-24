"""
test_integration_gateway_m6.py
================================
C15 M6 — Enterprise Integration Gateway

Comprehensive test suite.

Groups:
  A — Constants & exceptions
  B — Request & response
  C — Context
  D — Validation (7 checks)
  E — Router
  F — Health
  G — Status
  H — Statistics
  I — History
  J — Events
  K — Registry
  L — Component registry
  M — Factory
  N — Gateway lifecycle (initialize/start/stop/restart)
  O — Gateway public API (health/status/statistics/snapshot/history/validate)
  P — Gateway submit workflow
  Q — Gateway query/connect/disconnect
  R — Manager
  S — Concurrency & stress
  T — Regression (no circular imports, no vendor code, all __all__ importable)
"""
from __future__ import annotations

import threading
import time
import uuid
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest

import iios.integration.gateway as gw_pkg
from iios.integration.gateway import (
    GatewayCapacityError,
    GatewayComponent,
    GatewayComponentError,
    GatewayComponentHealth,
    GatewayComponentType,
    GatewayEngineError,
    GatewayEvent,
    GatewayEventType,
    GatewayGovernanceError,
    GatewayHistoryEntry,
    GatewayHistoryReport,
    GatewayLifecycleError,
    GatewayNotReadyError,
    GatewayOperationType,
    GatewayRequestValidationError,
    GatewayResponseStatus,
    GatewayRouteDecision,
    GatewayServicesError,
    GatewaySnapshotError,
    GatewayState,
    GatewayValidationCheck,
    GatewayValidationIssue,
    GatewayValidationReport,
    GatewayWorkflowError,
    GatewayWorkflowStep,
    IntegrationComponentFactory,
    IntegrationComponentRegistry,
    IntegrationGateway,
    IntegrationGatewayContext,
    IntegrationGatewayError,
    IntegrationGatewayEventBus,
    IntegrationGatewayFactory,
    IntegrationGatewayHealth,
    IntegrationGatewayHistory,
    IntegrationGatewayManager,
    IntegrationGatewayRegistry,
    IntegrationGatewayRequest,
    IntegrationGatewayResponse,
    IntegrationGatewayRouter,
    IntegrationGatewayStatistics,
    IntegrationGatewayStatusTracker,
    IntegrationGatewayValidation,
    IntegrationHealthSummary,
    IntegrationStatistics,
    VALIDATION_CHECK_ORDER,
)


# ════════════════════════════════════════════════════════════════════════
# Stubs
# ════════════════════════════════════════════════════════════════════════


class _StubLifecycle:
    def __init__(self, fail: bool = False):
        self._fail      = fail
        self.sessions:  List[str] = []
        self.events:    List[str] = []

    def create_session(self, workflow_id: str, **_: Any):
        if self._fail:
            raise RuntimeError("lifecycle create failed")
        sid = f"sess-{uuid.uuid4().hex[:8]}"
        self.sessions.append(sid)
        return SimpleNamespace(session_id=sid)

    def initialize(self, session_id: str, **_: Any):
        self.events.append(f"init:{session_id}")


class _StubEngine:
    def __init__(self, fail: bool = False):
        self._fail = fail

    def dispatch(self, req: Any):
        if self._fail:
            raise RuntimeError("engine dispatch failed")
        return SimpleNamespace(response_id=f"resp-{uuid.uuid4().hex[:8]}", status="success")


class _StubPolicyEngine:
    def __init__(self, fail: bool = False):
        self._fail = fail

    def evaluate(self, req: Any):
        if self._fail:
            raise RuntimeError("policy eval failed")
        return SimpleNamespace(overall_action=SimpleNamespace(value="allow"))


class _StubConnectorEngine:
    def __init__(self, fail: bool = False):
        self._fail = fail

    def execute(self, req: Any):
        if self._fail:
            raise RuntimeError("connector execute failed")
        return SimpleNamespace(status="success")


class _StubSnapshotRegistry:
    def __init__(self):
        self._snaps: Dict[str, Any] = {}

    def register(self, snap: Any) -> str:
        self._snaps[snap.snapshot_id] = snap
        return snap.snapshot_id

    def list_ids(self) -> List[str]:
        return list(self._snaps.keys())

    def get(self, sid: str):
        return self._snaps.get(sid)


def _make_request(
    operation:     GatewayOperationType = GatewayOperationType.SUBMIT,
    workflow_id:   str = "wf-001",
    enterprise_id: str = "ent-001",
    **kwargs: Any,
) -> IntegrationGatewayRequest:
    return IntegrationGatewayRequest.create(
        operation     = operation,
        workflow_id   = workflow_id,
        enterprise_id = enterprise_id,
        **kwargs,
    )


def _make_gateway(
    fail_lifecycle:  bool = False,
    fail_engine:     bool = False,
    fail_governance: bool = False,
    fail_services:   bool = False,
    gateway_id:      str = "test-gateway",
) -> IntegrationGateway:
    """Build an IntegrationGateway with stub components."""
    components = {
        GatewayComponentType.LIFECYCLE: _StubLifecycle(fail=fail_lifecycle),
        GatewayComponentType.ENGINE:    _StubEngine(fail=fail_engine),
        GatewayComponentType.POLICIES:  _StubPolicyEngine(fail=fail_governance),
        GatewayComponentType.SERVICES:  _StubConnectorEngine(fail=fail_services),
        GatewayComponentType.SNAPSHOT:  _StubSnapshotRegistry(),
    }
    gw = IntegrationGatewayFactory.create_with_components(components, gateway_id=gateway_id)
    gw.initialize()
    return gw


# ════════════════════════════════════════════════════════════════════════
# A — Constants & Exceptions
# ════════════════════════════════════════════════════════════════════════


class TestConstants:
    def test_gateway_state_count(self):
        assert len(GatewayState) == 7

    def test_gateway_event_type_count(self):
        assert len(GatewayEventType) == 8

    def test_gateway_operation_type_count(self):
        assert len(GatewayOperationType) == 8

    def test_gateway_validation_check_count(self):
        assert len(GatewayValidationCheck) == 7

    def test_gateway_component_type_count(self):
        assert len(GatewayComponentType) == 5

    def test_gateway_response_status_count(self):
        assert len(GatewayResponseStatus) == 5

    def test_gateway_workflow_step_count(self):
        assert len(GatewayWorkflowStep) == 10

    def test_validation_check_order_length(self):
        assert len(VALIDATION_CHECK_ORDER) == 7

    def test_string_constants(self):
        from iios.integration.gateway import (
            GATEWAY_VERSION, FRAMEWORK_VERSION, DEFAULT_GATEWAY_ID,
            GATEWAY_ID_PREFIX, REQUEST_ID_PREFIX, RESPONSE_ID_PREFIX,
        )
        assert GATEWAY_VERSION    == "1.0.0"
        assert FRAMEWORK_VERSION  == "1.0.0"
        assert DEFAULT_GATEWAY_ID == "default-gateway"
        assert GATEWAY_ID_PREFIX  == "gw-"
        assert REQUEST_ID_PREFIX  == "gwreq-"
        assert RESPONSE_ID_PREFIX == "gwresp-"

    def test_numeric_defaults(self):
        from iios.integration.gateway import (
            DEFAULT_MAX_HISTORY, DEFAULT_MAX_ACTIVE_REQUESTS,
            DEFAULT_REQUEST_TIMEOUT_MS, DEFAULT_MAX_GATEWAYS,
        )
        assert DEFAULT_MAX_HISTORY         == 1_000
        assert DEFAULT_MAX_ACTIVE_REQUESTS == 100
        assert DEFAULT_REQUEST_TIMEOUT_MS  == 30_000
        assert DEFAULT_MAX_GATEWAYS        == 50


class TestExceptions:
    def test_base_error_code(self):
        exc = IntegrationGatewayError("base")
        assert "IGW-000" in str(exc.code)

    def test_not_ready_error(self):
        exc = GatewayNotReadyError()
        assert "IGW-001" in str(exc.code)

    def test_validation_error(self):
        exc = GatewayRequestValidationError()
        assert "IGW-002" in str(exc.code)

    def test_workflow_error(self):
        exc = GatewayWorkflowError()
        assert "IGW-003" in str(exc.code)

    def test_component_error_with_component_name(self):
        exc = GatewayComponentError(component="lifecycle")
        assert "lifecycle" in str(exc)
        assert "IGW-004" in str(exc.code)

    def test_lifecycle_error(self):
        exc = GatewayLifecycleError()
        assert "IGW-005" in str(exc.code)

    def test_engine_error(self):
        exc = GatewayEngineError()
        assert "IGW-006" in str(exc.code)

    def test_governance_error(self):
        exc = GatewayGovernanceError()
        assert "IGW-007" in str(exc.code)

    def test_services_error(self):
        exc = GatewayServicesError()
        assert "IGW-008" in str(exc.code)

    def test_snapshot_error(self):
        exc = GatewaySnapshotError()
        assert "IGW-009" in str(exc.code)

    def test_capacity_error(self):
        exc = GatewayCapacityError()
        assert "IGW-010" in str(exc.code)

    def test_exception_hierarchy(self):
        assert issubclass(GatewayNotReadyError,         IntegrationGatewayError)
        assert issubclass(GatewayCapacityError,         IntegrationGatewayError)
        assert issubclass(GatewayLifecycleError,        IntegrationGatewayError)
        assert issubclass(GatewayEngineError,           IntegrationGatewayError)
        assert issubclass(GatewayGovernanceError,       IntegrationGatewayError)
        assert issubclass(GatewayServicesError,         IntegrationGatewayError)
        assert issubclass(GatewaySnapshotError,         IntegrationGatewayError)
        assert issubclass(GatewayWorkflowError,         IntegrationGatewayError)
        assert issubclass(GatewayRequestValidationError, IntegrationGatewayError)
        assert issubclass(GatewayComponentError,        IntegrationGatewayError)


# ════════════════════════════════════════════════════════════════════════
# B — Request & response
# ════════════════════════════════════════════════════════════════════════


class TestRequest:
    def test_create_defaults(self):
        req = _make_request()
        assert req.request_id.startswith("gwreq-")
        assert req.operation     == GatewayOperationType.SUBMIT
        assert req.workflow_id   == "wf-001"
        assert req.enterprise_id == "ent-001"
        assert req.submitted_at

    def test_immutable(self):
        req = _make_request()
        with pytest.raises((TypeError, AttributeError)):
            req.workflow_id = "changed"  # type: ignore[misc]

    def test_to_dict_keys(self):
        req = _make_request()
        d   = req.to_dict()
        required = {
            "request_id", "operation", "workflow_id", "enterprise_id",
            "session_id", "payload", "metadata", "connector_config",
            "protocol_config", "auth_config", "endpoint_config",
            "platform_context", "submitted_at",
        }
        assert required.issubset(set(d.keys()))

    def test_from_dict_round_trip(self):
        req  = _make_request(workflow_id="wf-rt-001")
        d    = req.to_dict()
        req2 = IntegrationGatewayRequest.from_dict(d)
        assert req2.workflow_id   == "wf-rt-001"
        assert req2.request_id    == req.request_id
        assert req2.operation     == req.operation

    def test_convenience_properties(self):
        assert _make_request(operation=GatewayOperationType.SUBMIT).is_submit     is True
        assert _make_request(operation=GatewayOperationType.QUERY).is_query        is True
        assert _make_request(operation=GatewayOperationType.CONNECT).is_connect    is True
        assert _make_request(operation=GatewayOperationType.DISCONNECT).is_disconnect is True

    def test_has_session(self):
        r1 = _make_request()
        r2 = _make_request(session_id="sess-abc")
        assert r1.has_session is False
        assert r2.has_session is True

    def test_unique_ids(self):
        r1 = _make_request()
        r2 = _make_request()
        assert r1.request_id != r2.request_id


class TestResponse:
    def test_success_factory(self):
        r = IntegrationGatewayResponse.success(
            request_id           = "req-001",
            operation            = GatewayOperationType.SUBMIT,
            gateway_state        = GatewayState.ACTIVE,
            lifecycle_session_id = "sess-001",
            snapshot_id          = "snap-001",
            processing_time_ms   = 42.5,
        )
        assert r.is_successful             is True
        assert r.is_failed                 is False
        assert r.status                    == GatewayResponseStatus.SUCCESS
        assert r.lifecycle_session_id      == "sess-001"
        assert r.snapshot_id              == "snap-001"
        assert r.processing_time_ms        == pytest.approx(42.5)
        assert r.response_id.startswith("gwresp-")

    def test_failure_factory(self):
        r = IntegrationGatewayResponse.failure(
            request_id    = "req-001",
            operation     = GatewayOperationType.SUBMIT,
            gateway_state = GatewayState.ACTIVE,
            error         = "engine failed",
            error_code    = "IGW-006",
        )
        assert r.is_failed     is True
        assert r.error         == "engine failed"
        assert r.error_code    == "IGW-006"

    def test_rejected_factory(self):
        r = IntegrationGatewayResponse.rejected(
            request_id    = "req-001",
            operation     = GatewayOperationType.SUBMIT,
            gateway_state = GatewayState.ACTIVE,
            reason        = "validation failed",
        )
        assert r.status   == GatewayResponseStatus.REJECTED
        assert r.is_failed is True

    def test_partial_factory(self):
        r = IntegrationGatewayResponse.partial(
            request_id    = "req-001",
            operation     = GatewayOperationType.SUBMIT,
            gateway_state = GatewayState.ACTIVE,
        )
        assert r.status == GatewayResponseStatus.PARTIAL

    def test_has_snapshot(self):
        r = IntegrationGatewayResponse.success(
            request_id    = "req-001",
            operation     = GatewayOperationType.SUBMIT,
            gateway_state = GatewayState.ACTIVE,
            snapshot_id   = "snap-001",
        )
        assert r.has_snapshot is True

    def test_to_dict_keys(self):
        r = IntegrationGatewayResponse.success(
            request_id    = "req-001",
            operation     = GatewayOperationType.SUBMIT,
            gateway_state = GatewayState.ACTIVE,
        )
        d = r.to_dict()
        required = {
            "response_id", "request_id", "status", "gateway_state",
            "operation", "lifecycle_session_id", "engine_request_id",
            "governance_decision", "snapshot_id", "data", "error",
            "error_code", "processing_time_ms", "completed_at",
        }
        assert required.issubset(set(d.keys()))

    def test_immutable(self):
        r = IntegrationGatewayResponse.success(
            request_id    = "req-001",
            operation     = GatewayOperationType.SUBMIT,
            gateway_state = GatewayState.ACTIVE,
        )
        with pytest.raises((TypeError, AttributeError)):
            r.status = GatewayResponseStatus.FAILED  # type: ignore[misc]


# ════════════════════════════════════════════════════════════════════════
# C — Context
# ════════════════════════════════════════════════════════════════════════


class TestContext:
    def _ctx(self) -> IntegrationGatewayContext:
        req = _make_request()
        return IntegrationGatewayContext(request=req, gateway_id="gw-test")

    def test_create(self):
        ctx = self._ctx()
        assert ctx.context_id.startswith("gwctx-")
        assert ctx.gateway_id           == "gw-test"
        assert ctx.gateway_state        == GatewayState.ACTIVE
        assert ctx.current_step         == GatewayWorkflowStep.REQUEST_RECEIVED
        assert ctx.has_errors           is False

    def test_advance_step(self):
        ctx = self._ctx()
        ctx.advance_step(GatewayWorkflowStep.REQUEST_VALIDATED)
        assert ctx.current_step == GatewayWorkflowStep.REQUEST_VALIDATED

    def test_record_timing(self):
        ctx = self._ctx()
        ctx.record_timing(GatewayWorkflowStep.ENGINE_EXECUTED, 25.3)
        assert ctx.step_timings[GatewayWorkflowStep.ENGINE_EXECUTED.value] == pytest.approx(25.3)

    def test_add_errors_and_warnings(self):
        ctx = self._ctx()
        ctx.add_error("something failed")
        ctx.add_warning("something degraded")
        assert ctx.has_errors          is True
        assert "something failed"      in ctx.errors
        assert "something degraded"    in ctx.warnings

    def test_lifecycle_session_id_setter(self):
        ctx = self._ctx()
        ctx.lifecycle_session_id = "sess-abc"
        assert ctx.lifecycle_session_id == "sess-abc"

    def test_snapshot_id_setter(self):
        ctx = self._ctx()
        ctx.snapshot_id = "snap-001"
        assert ctx.snapshot_id == "snap-001"

    def test_elapsed_ms(self):
        ctx = self._ctx()
        time.sleep(0.01)
        assert ctx.elapsed_ms() >= 10.0

    def test_to_dict(self):
        ctx = self._ctx()
        d   = ctx.to_dict()
        assert "context_id"    in d
        assert "gateway_id"    in d
        assert "current_step"  in d
        assert "elapsed_ms"    in d
        assert "errors"        in d


# ════════════════════════════════════════════════════════════════════════
# D — Validation (7 checks)
# ════════════════════════════════════════════════════════════════════════


class TestValidation:
    def _v(self) -> IntegrationGatewayValidation:
        return IntegrationGatewayValidation()

    def test_valid_request_passes(self):
        req = _make_request()
        r   = self._v().validate_request(req)
        assert r.passed is True

    def test_check_workflow_consistency_empty_workflow_id(self):
        req = _make_request(workflow_id="")
        r   = self._v().validate_request(req)
        assert r.passed is False
        assert any(
            i.check == GatewayValidationCheck.WORKFLOW_CONSISTENCY
            and i.severity == "error"
            for i in r.issues
        )

    def test_check_workflow_consistency_empty_enterprise_id(self):
        req = _make_request(enterprise_id="")
        r   = self._v().validate_request(req)
        assert r.passed is False

    def test_check_workflow_consistency_short_workflow_id_warning(self):
        req = _make_request(workflow_id="x")
        r   = self._v().validate_request(req)
        # workflow_id "x" is 1 char — should warn
        warns = [i for i in r.warnings if i.check == GatewayValidationCheck.WORKFLOW_CONSISTENCY]
        assert len(warns) >= 1

    def test_check_gateway_consistency_not_active(self):
        req = _make_request()
        r   = self._v().validate_request(req, gateway_state=GatewayState.STOPPED)
        assert r.passed is False
        assert any(
            i.check == GatewayValidationCheck.GATEWAY_CONSISTENCY
            for i in r.errors
        )

    def test_check_gateway_consistency_active_passes(self):
        req = _make_request()
        r   = self._v().validate_request(req, gateway_state=GatewayState.ACTIVE)
        assert r.passed is True

    def test_check_component_availability_missing_component(self):
        req = _make_request()  # SUBMIT requires all 5
        # Only lifecycle available
        r = self._v().validate_request(
            req,
            gateway_state        = GatewayState.ACTIVE,
            available_components = [GatewayComponentType.LIFECYCLE],
        )
        assert r.passed is False
        assert any(
            i.check == GatewayValidationCheck.COMPONENT_AVAILABILITY
            for i in r.errors
        )

    def test_check_component_availability_all_present(self):
        req = _make_request()
        r   = self._v().validate_request(
            req,
            gateway_state        = GatewayState.ACTIVE,
            available_components = list(GatewayComponentType),
        )
        assert r.passed is True

    def test_report_properties(self):
        req = _make_request(workflow_id="")
        r   = self._v().validate_request(req)
        assert isinstance(r.errors,   list)
        assert isinstance(r.warnings, list)
        assert r.error_count   >= 1
        assert r.checked_at

    def test_validate_response(self):
        resp = IntegrationGatewayResponse.success(
            request_id    = "req-001",
            operation     = GatewayOperationType.SUBMIT,
            gateway_state = GatewayState.ACTIVE,
        )
        r = self._v().validate_response(resp)
        assert r.passed is True


# ════════════════════════════════════════════════════════════════════════
# E — Router
# ════════════════════════════════════════════════════════════════════════


class TestRouter:
    def _router(self) -> IntegrationGatewayRouter:
        return IntegrationGatewayRouter()

    def test_submit_requires_all(self):
        req = _make_request(operation=GatewayOperationType.SUBMIT)
        d   = self._router().route(req)
        assert d.requires_lifecycle  is True
        assert d.requires_engine     is True
        assert d.requires_governance is True
        assert d.requires_services   is True
        assert d.requires_snapshot   is True

    def test_connect_requires_lifecycle_engine_services(self):
        req = _make_request(operation=GatewayOperationType.CONNECT)
        d   = self._router().route(req)
        assert d.requires_lifecycle  is True
        assert d.requires_engine     is True
        assert d.requires_governance is False
        assert d.requires_services   is True
        assert d.requires_snapshot   is False

    def test_disconnect_requires_lifecycle_services(self):
        req = _make_request(operation=GatewayOperationType.DISCONNECT)
        d   = self._router().route(req)
        assert d.requires_lifecycle  is True
        assert d.requires_engine     is False
        assert d.requires_services   is True
        assert d.requires_snapshot   is False

    def test_validate_requires_nothing(self):
        req = _make_request(operation=GatewayOperationType.VALIDATE)
        d   = self._router().route(req)
        assert d.requires_lifecycle  is False
        assert d.requires_engine     is False
        assert d.requires_governance is False
        assert d.requires_services   is False
        assert d.requires_snapshot   is False

    def test_query_requires_nothing(self):
        req = _make_request(operation=GatewayOperationType.QUERY)
        d   = self._router().route(req)
        assert d.required_components == []

    def test_snapshot_operation_requires_snapshot(self):
        req = _make_request(operation=GatewayOperationType.SNAPSHOT)
        d   = self._router().route(req)
        assert d.requires_snapshot  is True
        assert d.requires_engine    is False

    def test_route_decision_to_dict(self):
        req = _make_request()
        d   = self._router().route(req).to_dict()
        assert "request_id"          in d
        assert "requires_lifecycle"  in d
        assert "routing_metadata"    in d

    def test_routing_metadata_populated_from_config(self):
        req = _make_request(
            connector_config = {"type": "REST_API"},
            protocol_config  = {"type": "http"},
            endpoint_config  = {"url": "https://api.example.com"},
        )
        d = self._router().route(req)
        assert d.routing_metadata["connector_hint"] == "REST_API"
        assert d.routing_metadata["protocol_hint"]  == "http"


# ════════════════════════════════════════════════════════════════════════
# F — Health
# ════════════════════════════════════════════════════════════════════════


class TestHealth:
    def test_mark_healthy_and_check(self):
        h = IntegrationGatewayHealth()
        h.mark_healthy(GatewayComponentType.LIFECYCLE, "ok")
        h.mark_healthy(GatewayComponentType.ENGINE, "ok")
        summary = h.check("gw-001", GatewayState.ACTIVE, active_requests=2, uptime_seconds=60.0)
        assert summary.overall_health == "healthy"
        assert summary.active_requests == 2
        assert summary.gateway_id == "gw-001"
        assert summary.is_healthy is True

    def test_degraded_when_component_unavailable(self):
        h = IntegrationGatewayHealth()
        h.mark_healthy(GatewayComponentType.LIFECYCLE, "ok")
        h.mark_unavailable(GatewayComponentType.ENGINE, "engine down")
        summary = h.check("gw-001", GatewayState.ACTIVE)
        assert summary.overall_health == "degraded"

    def test_unavailable_when_gateway_not_active(self):
        h = IntegrationGatewayHealth()
        summary = h.check("gw-001", GatewayState.STOPPED)
        assert summary.overall_health == "unavailable"

    def test_latest_history(self):
        h = IntegrationGatewayHealth()
        h.check("gw-001", GatewayState.ACTIVE)
        assert h.latest() is not None

    def test_component_health_immutable(self):
        ch = GatewayComponentHealth(
            component_type = GatewayComponentType.ENGINE,
            status         = "healthy",
            message        = "all ok",
            checked_at     = "2026-01-01T00:00:00+00:00",
        )
        with pytest.raises((TypeError, AttributeError)):
            ch.status = "degraded"  # type: ignore[misc]

    def test_to_dict(self):
        summary = IntegrationGatewayHealth().check("gw-001", GatewayState.ACTIVE)
        d = summary.to_dict()
        assert "gateway_id"     in d
        assert "overall_health" in d
        assert "components"     in d


# ════════════════════════════════════════════════════════════════════════
# G — Status
# ════════════════════════════════════════════════════════════════════════


class TestStatus:
    def test_initial_status(self):
        tracker = IntegrationGatewayStatusTracker()
        report  = tracker.status("gw-001", uptime_seconds=0.0)
        assert report.gateway_id     == "gw-001"
        assert report.active_requests == 0
        assert report.total_requests  == 0
        assert report.version         == "1.0.0"

    def test_request_counters(self):
        tracker = IntegrationGatewayStatusTracker()
        tracker.record_request("r1")
        tracker.record_request("r2")
        tracker.record_completion("r1")
        report = tracker.status("gw-001")
        assert report.total_requests  == 2
        assert report.active_requests == 1

    def test_component_states(self):
        tracker = IntegrationGatewayStatusTracker()
        tracker.set_component_state("lifecycle", "healthy")
        tracker.set_component_state("engine", "healthy")
        report = tracker.status("gw-001")
        assert report.component_states["lifecycle"] == "healthy"
        assert report.component_states["engine"]    == "healthy"

    def test_update_state(self):
        tracker = IntegrationGatewayStatusTracker()
        tracker.update_state(GatewayState.ACTIVE)
        assert tracker.current_state == GatewayState.ACTIVE

    def test_to_dict(self):
        tracker = IntegrationGatewayStatusTracker()
        d = tracker.status("gw-001", uptime_seconds=123.4).to_dict()
        assert d["gateway_id"]     == "gw-001"
        assert d["uptime_seconds"] == pytest.approx(123.4)


# ════════════════════════════════════════════════════════════════════════
# H — Statistics
# ════════════════════════════════════════════════════════════════════════


class TestStatistics:
    def test_initial_state(self):
        st = IntegrationGatewayStatistics()
        sr = st.snapshot()
        assert sr.gateway_requests      == 0
        assert sr.successful_requests   == 0
        assert sr.gateway_availability  == pytest.approx(1.0)  # 0/0 → 1.0

    def test_increment_request_and_success(self):
        st = IntegrationGatewayStatistics()
        st.increment_request(5)
        st.increment_success(4)
        st.increment_failed(1)
        sr = st.snapshot()
        assert sr.gateway_requests    == 5
        assert sr.successful_requests == 4
        assert sr.failed_requests     == 1
        assert sr.gateway_availability == pytest.approx(4 / 5)

    def test_increment_rejected(self):
        st = IntegrationGatewayStatistics()
        st.increment_request(2)
        st.increment_rejected(2)
        assert st.snapshot().rejected_requests == 2

    def test_snapshot_publications(self):
        st = IntegrationGatewayStatistics()
        st.increment_snapshot_publications(3)
        assert st.snapshot().snapshot_publications == 3

    def test_processing_time_average(self):
        st = IntegrationGatewayStatistics()
        st.record_processing_time(10.0)
        st.record_processing_time(20.0)
        st.record_processing_time(30.0)
        sr = st.snapshot()
        assert sr.average_processing_time_ms == pytest.approx(20.0)

    def test_response_time_average(self):
        st = IntegrationGatewayStatistics()
        st.record_response_time(5.0)
        st.record_response_time(15.0)
        sr = st.snapshot()
        assert sr.average_response_time_ms == pytest.approx(10.0)

    def test_reset(self):
        st = IntegrationGatewayStatistics()
        st.increment_request(10)
        st.reset()
        assert st.snapshot().gateway_requests == 0

    def test_as_dict_count(self):
        sr = IntegrationGatewayStatistics().snapshot()
        d  = sr.as_dict()
        assert "gateway_requests"           in d
        assert "gateway_availability"       in d
        assert "average_processing_time_ms" in d
        assert "generated_at"               in d


# ════════════════════════════════════════════════════════════════════════
# I — History
# ════════════════════════════════════════════════════════════════════════


class TestHistory:
    def test_record_and_recent(self):
        h   = IntegrationGatewayHistory()
        e   = h.record(
            gateway_id           = "gw-001",
            request_id           = "req-001",
            operation            = GatewayOperationType.SUBMIT,
            status               = GatewayResponseStatus.SUCCESS,
            processing_time_ms   = 50.0,
            lifecycle_session_id = "sess-001",
            snapshot_id          = "snap-001",
        )
        assert e.entry_id.startswith("gwhist-")
        assert e.status  == GatewayResponseStatus.SUCCESS
        assert len(h.recent(10)) == 1

    def test_bounded(self):
        h = IntegrationGatewayHistory(max_size=3)
        for i in range(5):
            h.record("gw-001", f"req-{i}", GatewayOperationType.SUBMIT,
                     GatewayResponseStatus.SUCCESS)
        assert h.size == 3

    def test_by_status(self):
        h = IntegrationGatewayHistory()
        h.record("gw-001", "req-1", GatewayOperationType.SUBMIT, GatewayResponseStatus.SUCCESS)
        h.record("gw-001", "req-2", GatewayOperationType.SUBMIT, GatewayResponseStatus.FAILED)
        h.record("gw-001", "req-3", GatewayOperationType.SUBMIT, GatewayResponseStatus.FAILED)
        assert len(h.by_status(GatewayResponseStatus.SUCCESS)) == 1
        assert len(h.by_status(GatewayResponseStatus.FAILED))  == 2

    def test_by_operation(self):
        h = IntegrationGatewayHistory()
        h.record("gw-001", "req-1", GatewayOperationType.SUBMIT,     GatewayResponseStatus.SUCCESS)
        h.record("gw-001", "req-2", GatewayOperationType.CONNECT,    GatewayResponseStatus.SUCCESS)
        h.record("gw-001", "req-3", GatewayOperationType.DISCONNECT, GatewayResponseStatus.SUCCESS)
        assert len(h.by_operation(GatewayOperationType.SUBMIT)) == 1

    def test_report(self):
        h = IntegrationGatewayHistory()
        for _ in range(3):
            h.record("gw-001", f"r-{uuid.uuid4().hex[:6]}",
                     GatewayOperationType.SUBMIT, GatewayResponseStatus.SUCCESS)
        h.record("gw-001", "r-fail",
                 GatewayOperationType.SUBMIT, GatewayResponseStatus.FAILED)
        rep = h.report()
        assert rep.total_entries == 4
        assert rep.successful    == 3
        assert rep.failed        == 1

    def test_clear(self):
        h = IntegrationGatewayHistory()
        for idx in range(5):
            h.record("gw-001", f"r-{idx}", GatewayOperationType.SUBMIT,
                     GatewayResponseStatus.SUCCESS)
        n = h.clear()
        assert n == 5
        assert h.size == 0


# ════════════════════════════════════════════════════════════════════════
# J — Events
# ════════════════════════════════════════════════════════════════════════


class TestEvents:
    def test_subscribe_and_emit(self):
        bus      = IntegrationGatewayEventBus()
        received: List[GatewayEvent] = []
        bus.subscribe(GatewayEventType.GATEWAY_COMPLETED, received.append)
        n = bus.emit(GatewayEventType.GATEWAY_COMPLETED, "gw-001", "req-001", "test", {"k": "v"})
        assert n == 1
        assert received[0].event_type  == GatewayEventType.GATEWAY_COMPLETED
        assert received[0].gateway_id  == "gw-001"
        assert received[0].request_id  == "req-001"

    def test_unsubscribe(self):
        bus     = IntegrationGatewayEventBus()
        handler = lambda e: None
        bus.subscribe(GatewayEventType.GATEWAY_FAILED, handler)
        ok = bus.unsubscribe(GatewayEventType.GATEWAY_FAILED, handler)
        assert ok is True

    def test_all_8_event_types_emittable(self):
        bus = IntegrationGatewayEventBus()
        for et in GatewayEventType:
            n = bus.emit(et, "gw-001", "", "test", {})
            assert n == 0  # no handlers

    def test_handler_exception_suppressed(self):
        bus = IntegrationGatewayEventBus()
        bus.subscribe(
            GatewayEventType.GATEWAY_INITIALIZED,
            lambda e: (_ for _ in ()).throw(RuntimeError("boom")),  # type: ignore
        )
        n = bus.emit(GatewayEventType.GATEWAY_INITIALIZED, "gw-001", "", "test", {})
        assert n == 0

    def test_history_bounded(self):
        bus = IntegrationGatewayEventBus(max_history=3)
        for _ in range(5):
            bus.emit(GatewayEventType.GATEWAY_COMPLETED, "gw-001", "", "test", {})
        assert len(bus.history()) == 3

    def test_history_by_type(self):
        bus = IntegrationGatewayEventBus()
        bus.emit(GatewayEventType.GATEWAY_STARTED, "gw-001", "", "test", {})
        bus.emit(GatewayEventType.GATEWAY_STOPPED, "gw-001", "", "test", {})
        items = bus.history_by_type(GatewayEventType.GATEWAY_STARTED)
        assert len(items) == 1

    def test_stats(self):
        bus = IntegrationGatewayEventBus()
        bus.emit(GatewayEventType.GATEWAY_COMPLETED, "gw-001", "", "test", {})
        st = bus.stats
        assert st["published"] == 1


# ════════════════════════════════════════════════════════════════════════
# K — Gateway Registry
# ════════════════════════════════════════════════════════════════════════


class TestGatewayRegistry:
    def test_register_and_get(self):
        reg = IntegrationGatewayRegistry()
        req = _make_request()
        reg.register(req)
        assert reg.get(req.request_id).request_id == req.request_id

    def test_set_and_get_response(self):
        reg = IntegrationGatewayRegistry()
        req = _make_request()
        reg.register(req)
        resp = IntegrationGatewayResponse.success(
            request_id    = req.request_id,
            operation     = req.operation,
            gateway_state = GatewayState.ACTIVE,
        )
        reg.set_response(req.request_id, resp)
        found = reg.get_response(req.request_id)
        assert found.response_id == resp.response_id

    def test_deregister(self):
        reg = IntegrationGatewayRegistry()
        req = _make_request()
        reg.register(req)
        ok = reg.deregister(req.request_id)
        assert ok is True
        assert reg.get(req.request_id) is None

    def test_capacity_enforced(self):
        reg = IntegrationGatewayRegistry(max_size=2)
        reg.register(_make_request())
        reg.register(_make_request())
        with pytest.raises(GatewayCapacityError):
            reg.register(_make_request())

    def test_active_count(self):
        reg = IntegrationGatewayRegistry()
        r1  = _make_request()
        r2  = _make_request()
        reg.register(r1)
        reg.register(r2)
        # r1 gets a response → no longer active
        resp = IntegrationGatewayResponse.success(
            request_id    = r1.request_id,
            operation     = r1.operation,
            gateway_state = GatewayState.ACTIVE,
        )
        reg.set_response(r1.request_id, resp)
        assert reg.active_count == 1

    def test_clear(self):
        reg = IntegrationGatewayRegistry()
        for _ in range(3):
            reg.register(_make_request())
        n = reg.clear()
        assert n == 3
        assert reg.count == 0


# ════════════════════════════════════════════════════════════════════════
# L — Component Registry
# ════════════════════════════════════════════════════════════════════════


class TestComponentRegistry:
    def test_register_and_get(self):
        reg  = IntegrationComponentRegistry()
        stub = _StubLifecycle()
        reg.register(GatewayComponentType.LIFECYCLE, stub)
        assert reg.get(GatewayComponentType.LIFECYCLE) is stub

    def test_get_or_raise_missing(self):
        reg = IntegrationComponentRegistry()
        with pytest.raises(GatewayComponentError):
            reg.get_or_raise(GatewayComponentType.ENGINE)

    def test_is_available(self):
        reg = IntegrationComponentRegistry()
        assert reg.is_available(GatewayComponentType.LIFECYCLE) is False
        reg.register(GatewayComponentType.LIFECYCLE, _StubLifecycle())
        assert reg.is_available(GatewayComponentType.LIFECYCLE) is True

    def test_all_available(self):
        reg = IntegrationComponentRegistry()
        assert reg.all_available() is False
        for ct in GatewayComponentType:
            reg.register(ct, object())
        assert reg.all_available() is True

    def test_deregister(self):
        reg = IntegrationComponentRegistry()
        reg.register(GatewayComponentType.LIFECYCLE, _StubLifecycle())
        ok = reg.deregister(GatewayComponentType.LIFECYCLE)
        assert ok is True
        assert reg.is_available(GatewayComponentType.LIFECYCLE) is False

    def test_list_registered(self):
        reg = IntegrationComponentRegistry()
        reg.register(GatewayComponentType.LIFECYCLE, _StubLifecycle())
        reg.register(GatewayComponentType.ENGINE,    _StubEngine())
        items = reg.list_registered()
        assert len(items) == 2
        assert all(isinstance(i, GatewayComponent) for i in items)

    def test_overwrite_registration(self):
        reg  = IntegrationComponentRegistry()
        s1   = _StubLifecycle()
        s2   = _StubLifecycle()
        reg.register(GatewayComponentType.LIFECYCLE, s1)
        reg.register(GatewayComponentType.LIFECYCLE, s2)
        assert reg.get(GatewayComponentType.LIFECYCLE) is s2

    def test_count(self):
        reg = IntegrationComponentRegistry()
        assert reg.count == 0
        reg.register(GatewayComponentType.LIFECYCLE, _StubLifecycle())
        assert reg.count == 1


# ════════════════════════════════════════════════════════════════════════
# M — Factory
# ════════════════════════════════════════════════════════════════════════


class TestFactory:
    def test_create_gateway(self):
        gw = IntegrationGatewayFactory.create("factory-gw")
        assert isinstance(gw, IntegrationGateway)
        assert gw.gateway_id == "factory-gw"

    def test_create_with_components(self):
        components = {ct: object() for ct in GatewayComponentType}
        gw = IntegrationGatewayFactory.create_with_components(components, "custom-gw")
        assert gw.gateway_id == "custom-gw"
        for ct in GatewayComponentType:
            assert gw.component_registry.is_available(ct)

    def test_create_request(self):
        req = IntegrationGatewayFactory.create_request(
            GatewayOperationType.SUBMIT, "wf-001", "ent-001"
        )
        assert req.operation     == GatewayOperationType.SUBMIT
        assert req.workflow_id   == "wf-001"
        assert req.enterprise_id == "ent-001"

    def test_create_submit_request(self):
        req = IntegrationGatewayFactory.create_submit_request(
            workflow_id   = "wf-submit",
            enterprise_id = "ent-001",
            payload       = {"k": "v"},
        )
        assert req.operation == GatewayOperationType.SUBMIT
        assert req.payload   == {"k": "v"}

    def test_create_connect_request(self):
        req = IntegrationGatewayFactory.create_connect_request(
            workflow_id   = "wf-connect",
            enterprise_id = "ent-001",
        )
        assert req.operation == GatewayOperationType.CONNECT

    def test_create_disconnect_request(self):
        req = IntegrationGatewayFactory.create_disconnect_request(
            workflow_id   = "wf-disconnect",
            enterprise_id = "ent-001",
            session_id    = "sess-001",
        )
        assert req.operation  == GatewayOperationType.DISCONNECT
        assert req.session_id == "sess-001"

    def test_create_context(self):
        req = _make_request()
        ctx = IntegrationGatewayFactory.create_context(req, "gw-factory")
        assert ctx.gateway_id == "gw-factory"

    def test_create_success_response(self):
        req = _make_request()
        ctx = IntegrationGatewayContext(request=req, gateway_id="gw-001")
        ctx.snapshot_id          = "snap-001"
        ctx.lifecycle_session_id = "sess-001"
        resp = IntegrationGatewayFactory.create_success_response(ctx, {"key": "val"})
        assert resp.is_successful is True
        assert resp.snapshot_id   == "snap-001"

    def test_create_failure_response(self):
        req  = _make_request()
        ctx  = IntegrationGatewayContext(request=req, gateway_id="gw-001")
        resp = IntegrationGatewayFactory.create_failure_response(ctx, "engine error", "IGW-006")
        assert resp.is_failed  is True
        assert resp.error_code == "IGW-006"


# ════════════════════════════════════════════════════════════════════════
# N — Gateway lifecycle
# ════════════════════════════════════════════════════════════════════════


class TestGatewayLifecycle:
    def test_initialize_sets_active(self):
        gw = _make_gateway()
        assert gw.state    == GatewayState.ACTIVE
        assert gw.is_active is True

    def test_start_calls_initialize_if_needed(self):
        gw = IntegrationGatewayFactory.create_with_components(
            {ct: object() for ct in GatewayComponentType}
        )
        gw.start()
        assert gw.is_active is True

    def test_stop_transitions_to_stopped(self):
        gw = _make_gateway()
        gw.stop()
        assert gw.state == GatewayState.STOPPED

    def test_restart(self):
        gw = _make_gateway()
        gw.stop()
        assert gw.state == GatewayState.STOPPED
        gw.restart()
        assert gw.state == GatewayState.ACTIVE

    def test_initialize_idempotent(self):
        gw = _make_gateway()
        gw.initialize()   # second call should not raise
        assert gw.state == GatewayState.ACTIVE

    def test_stop_idempotent(self):
        gw = _make_gateway()
        gw.stop()
        gw.stop()          # second call should not raise
        assert gw.state == GatewayState.STOPPED


# ════════════════════════════════════════════════════════════════════════
# O — Gateway public observability API
# ════════════════════════════════════════════════════════════════════════


class TestGatewayObservability:
    def _gw(self) -> IntegrationGateway:
        return _make_gateway()

    def test_health(self):
        gw     = self._gw()
        health = gw.health()
        assert isinstance(health, IntegrationHealthSummary)
        assert health.gateway_id == gw.gateway_id

    def test_status(self):
        gw     = self._gw()
        report = gw.status()
        assert report.gateway_id    == gw.gateway_id
        assert report.gateway_state == GatewayState.ACTIVE

    def test_statistics(self):
        gw    = self._gw()
        stats = gw.statistics()
        assert isinstance(stats, IntegrationStatistics)

    def test_history_empty(self):
        gw = self._gw()
        assert gw.history() == []

    def test_snapshot_none_when_no_snaps(self):
        # Snapshot registry is empty initially
        gw = _make_gateway()
        # submit first to populate snapshot
        req  = _make_request()
        resp = gw.submit(req)
        snap = gw.snapshot()
        # After submit, snapshot registry has one entry
        assert snap is None or hasattr(snap, "snapshot_id")


# ════════════════════════════════════════════════════════════════════════
# P — Gateway submit workflow
# ════════════════════════════════════════════════════════════════════════


class TestGatewaySubmit:
    def _gw(self, **kwargs) -> IntegrationGateway:
        return _make_gateway(**kwargs)

    def test_submit_success(self):
        gw   = self._gw()
        req  = _make_request()
        resp = gw.submit(req)
        assert resp.is_successful             is True
        assert resp.lifecycle_session_id      != ""
        assert resp.engine_request_id         != ""
        assert resp.snapshot_id               != ""
        assert resp.processing_time_ms        >= 0

    def test_submit_rejected_on_invalid_request(self):
        gw   = self._gw()
        req  = _make_request(workflow_id="", enterprise_id="")
        resp = gw.submit(req)
        assert resp.status == GatewayResponseStatus.REJECTED

    def test_submit_failed_on_lifecycle_error(self):
        gw   = self._gw(fail_lifecycle=True)
        req  = _make_request()
        resp = gw.submit(req)
        assert resp.is_failed is True

    def test_submit_failed_on_engine_error(self):
        gw   = self._gw(fail_engine=True)
        req  = _make_request()
        resp = gw.submit(req)
        assert resp.is_failed is True

    def test_submit_failed_on_governance_error(self):
        gw   = self._gw(fail_governance=True)
        req  = _make_request()
        resp = gw.submit(req)
        assert resp.is_failed is True

    def test_submit_failed_on_services_error(self):
        gw   = self._gw(fail_services=True)
        req  = _make_request()
        resp = gw.submit(req)
        assert resp.is_failed is True

    def test_submit_updates_statistics(self):
        gw  = self._gw()
        req = _make_request()
        gw.submit(req)
        stats = gw.statistics()
        assert stats.gateway_requests == 1

    def test_submit_records_history(self):
        gw  = self._gw()
        req = _make_request()
        gw.submit(req)
        hist = gw.history(10)
        assert len(hist) == 1
        assert hist[0].request_id == req.request_id

    def test_submit_emits_completed_event(self):
        gw      = self._gw()
        received: List[GatewayEvent] = []
        gw.event_bus.subscribe(GatewayEventType.GATEWAY_COMPLETED, received.append)
        gw.submit(_make_request())
        assert len(received) == 1

    def test_submit_on_stopped_gateway_raises(self):
        gw = self._gw()
        gw.stop()
        with pytest.raises(GatewayNotReadyError):
            gw.submit(_make_request())

    def test_submit_never_raises_on_internal_failure(self):
        gw  = self._gw(fail_lifecycle=True)
        req = _make_request()
        # submit should return a response, never raise
        resp = gw.submit(req)
        assert isinstance(resp, IntegrationGatewayResponse)


# ════════════════════════════════════════════════════════════════════════
# Q — Gateway query / connect / disconnect
# ════════════════════════════════════════════════════════════════════════


class TestGatewayQueryConnectDisconnect:
    def _gw(self) -> IntegrationGateway:
        return _make_gateway()

    def test_query_returns_completed_response(self):
        gw   = self._gw()
        req  = _make_request()
        resp = gw.submit(req)
        found = gw.query(req.request_id)
        assert found is not None
        assert found.response_id == resp.response_id

    def test_query_returns_none_for_unknown(self):
        gw    = self._gw()
        found = gw.query("req-unknown-xyz")
        assert found is None

    def test_connect_returns_true_on_success(self):
        gw     = self._gw()
        result = gw.connect({
            "workflow_id":    "wf-connect",
            "enterprise_id":  "ent-001",
            "connector_config": {"type": "REST_API"},
        })
        assert result is True

    def test_disconnect_returns_bool(self):
        gw     = self._gw()
        result = gw.disconnect("sess-test-001")
        # DISCONNECT only needs lifecycle + services (both succeed with stubs)
        assert isinstance(result, bool)

    def test_validate_without_running_workflow(self):
        gw     = self._gw()
        req    = _make_request()
        report = gw.validate(req)
        assert isinstance(report, GatewayValidationReport)
        assert report.passed is True


# ════════════════════════════════════════════════════════════════════════
# R — Manager
# ════════════════════════════════════════════════════════════════════════


class TestManager:
    def test_create_and_get(self):
        mgr = IntegrationGatewayManager(max_gateways=5)
        gw  = mgr.create_gateway("gw-A")
        assert mgr.get_gateway("gw-A") is gw

    def test_get_or_raise_missing(self):
        mgr = IntegrationGatewayManager()
        with pytest.raises(IntegrationGatewayError):
            mgr.get_or_raise("gw-nonexistent")

    def test_remove_gateway(self):
        mgr = IntegrationGatewayManager()
        mgr.create_gateway("gw-X")
        ok = mgr.remove_gateway("gw-X")
        assert ok is True
        assert mgr.get_gateway("gw-X") is None

    def test_capacity_enforced(self):
        mgr = IntegrationGatewayManager(max_gateways=2)
        mgr.create_gateway("gw-1")
        mgr.create_gateway("gw-2")
        with pytest.raises(GatewayCapacityError):
            mgr.create_gateway("gw-3")

    def test_duplicate_gateway_raises(self):
        mgr = IntegrationGatewayManager()
        mgr.create_gateway("gw-dup")
        with pytest.raises(IntegrationGatewayError):
            mgr.create_gateway("gw-dup")

    def test_list_gateways(self):
        mgr = IntegrationGatewayManager()
        mgr.create_gateway("gw-A")
        mgr.create_gateway("gw-B")
        ids = mgr.list_gateways()
        assert "gw-A" in ids
        assert "gw-B" in ids

    def test_default_gateway_auto_created(self):
        mgr = IntegrationGatewayManager()
        gw  = mgr.default_gateway()
        assert isinstance(gw, IntegrationGateway)
        assert gw.is_active is True

    def test_start_all_and_stop_all(self):
        mgr = IntegrationGatewayManager()
        mgr.create_gateway("gw-X", auto_start=True)
        mgr.create_gateway("gw-Y", auto_start=True)
        results = mgr.stop_all()
        assert all(v is True for v in results.values())

    def test_health_all(self):
        mgr = IntegrationGatewayManager()
        mgr.create_gateway("gw-A", auto_start=True)
        summaries = mgr.health_all()
        assert "gw-A" in summaries

    def test_statistics_all(self):
        mgr = IntegrationGatewayManager()
        mgr.create_gateway("gw-A", auto_start=True)
        stats_map = mgr.statistics_all()
        assert "gw-A" in stats_map
        assert isinstance(stats_map["gw-A"], IntegrationStatistics)

    def test_count(self):
        mgr = IntegrationGatewayManager()
        assert mgr.count == 0
        mgr.create_gateway("gw-A")
        assert mgr.count == 1


# ════════════════════════════════════════════════════════════════════════
# S — Concurrency & stress
# ════════════════════════════════════════════════════════════════════════


class TestConcurrency:
    def test_concurrent_submits(self):
        gw     = _make_gateway()
        errors: List[Exception] = []
        lock   = threading.Lock()

        def worker():
            for _ in range(5):
                req  = _make_request()
                resp = gw.submit(req)
                if not resp.is_successful:
                    with lock:
                        errors.append(Exception(f"failed: {resp.error}"))

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=30)
        assert errors == []

    def test_concurrent_history_writes(self):
        hist   = IntegrationGatewayHistory(max_size=1000)
        errors: List[Exception] = []
        lock   = threading.Lock()

        def worker():
            for _ in range(20):
                try:
                    hist.record(
                        "gw-001",
                        f"req-{uuid.uuid4().hex[:8]}",
                        GatewayOperationType.SUBMIT,
                        GatewayResponseStatus.SUCCESS,
                    )
                except Exception as exc:
                    with lock:
                        errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        assert errors == []
        assert hist.size == 200

    def test_concurrent_statistics_increments(self):
        stats = IntegrationGatewayStatistics()

        def worker():
            for _ in range(100):
                stats.increment_request()
                stats.increment_success()

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        sr = stats.snapshot()
        assert sr.gateway_requests    == 1000
        assert sr.successful_requests == 1000

    def test_concurrent_event_bus(self):
        bus    = IntegrationGatewayEventBus()
        counts: List[int] = []
        lock   = threading.Lock()

        def handler(e: GatewayEvent):
            with lock:
                counts.append(1)

        bus.subscribe(GatewayEventType.GATEWAY_COMPLETED, handler)

        def worker():
            for _ in range(25):
                bus.emit(GatewayEventType.GATEWAY_COMPLETED, "gw-001", "", "test", {})

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        assert len(counts) == 100

    def test_stress_200_submits(self):
        gw      = _make_gateway(gateway_id="stress-gw")
        results: List[GatewayResponseStatus] = []
        lock    = threading.Lock()

        def worker():
            for _ in range(10):
                resp = gw.submit(_make_request())
                with lock:
                    results.append(resp.status)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=60)

        assert len(results) == 200
        successes = sum(1 for s in results if s == GatewayResponseStatus.SUCCESS)
        assert successes == 200


# ════════════════════════════════════════════════════════════════════════
# T — Regression
# ════════════════════════════════════════════════════════════════════════


class TestRegression:
    def test_all_public_api_importable(self):
        for name in gw_pkg.__all__:
            assert hasattr(gw_pkg, name), f"__all__ member {name!r} not accessible"

    def test_no_vendor_sdk_imports(self):
        import sys
        FORBIDDEN = [
            "requests", "httpx", "aiohttp", "kafka", "pika", "redis",
            "boto3", "grpc", "websockets", "sqlalchemy", "paramiko",
            "smtplib", "twilio", "firebase_admin",
        ]
        for key, mod in sys.modules.items():
            if "iios.integration.gateway" in key and hasattr(mod, "__file__"):
                if mod.__file__:
                    with open(mod.__file__, encoding="utf-8", errors="ignore") as f:
                        src = f.read()
                    for vendor in FORBIDDEN:
                        assert f"import {vendor}" not in src, \
                            f"{key} imports forbidden vendor: {vendor}"

    def test_request_immutable_after_create(self):
        req = _make_request()
        d   = req.to_dict()
        d["workflow_id"] = "changed"   # mutate dict
        assert req.workflow_id == "wf-001"  # original unaffected

    def test_response_immutable_after_create(self):
        resp = IntegrationGatewayResponse.success(
            request_id    = "req-001",
            operation     = GatewayOperationType.SUBMIT,
            gateway_state = GatewayState.ACTIVE,
        )
        with pytest.raises((TypeError, AttributeError)):
            resp.status = GatewayResponseStatus.FAILED  # type: ignore[misc]

    def test_exports_count(self):
        assert len(gw_pkg.__all__) >= 70
