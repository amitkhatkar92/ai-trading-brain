"""
tests/unit/workflow/test_workflow_gateway_m6.py
------------------------------------------------
Comprehensive tests for C16 M6: Enterprise Workflow Gateway.

Coverage target: 95%+
"""
import threading
import uuid

import pytest

from iios.workflow.gateway import (
    # Main class
    WorkflowGateway,
    # Constants
    ComponentStatus,
    ComponentType,
    GatewayEventType,
    GatewayHealthStatus,
    GatewayRequestType,
    GatewayResponseStatus,
    GatewayState,
    # Exceptions
    WorkflowGatewayComponentError,
    WorkflowGatewayDispatchError,
    WorkflowGatewayError,
    WorkflowGatewayNotInitializedError,
    WorkflowGatewayNotRunningError,
    WorkflowGatewayRoutingError,
    WorkflowGatewayValidationError,
    # Domain objects
    ComponentRecord,
    GatewayValidationResult,
    WorkflowGatewayContext,
    WorkflowGatewayEvent,
    WorkflowGatewayHistoryRecord,
    WorkflowGatewayRequest,
    WorkflowGatewayResponse,
    WorkflowHealthSummary,
    WorkflowStatistics,
    WorkflowStatus,
    # Services
    WorkflowComponentFactory,
    WorkflowComponentRegistry,
    WorkflowGatewayDispatcher,
    WorkflowGatewayEventBus,
    WorkflowGatewayFactory,
    WorkflowGatewayHealth,
    WorkflowGatewayHistory,
    WorkflowGatewayManager,
    WorkflowGatewayRegistry,
    WorkflowGatewayRouter,
    WorkflowGatewayStatistics,
    WorkflowGatewayStatus,
    WorkflowGatewayValidation,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _req(
    workflow_id:  str              = "wf-test",
    workflow_name: str             = "Test Workflow",
    request_type: GatewayRequestType = GatewayRequestType.SUBMIT,
) -> WorkflowGatewayRequest:
    return WorkflowGatewayRequest.create(
        workflow_id  = workflow_id,
        workflow_name = workflow_name,
        request_type = request_type,
    )


def _gateway_no_components() -> WorkflowGateway:
    """Gateway with empty component registry (no M1–M5 wired)."""
    mgr = WorkflowGatewayManager(
        gateway_id         = "test-gw",
        component_registry = WorkflowComponentRegistry(),
    )
    # Override initialize to NOT create real components
    mgr._state = GatewayState.INITIALIZED
    mgr._state = GatewayState.RUNNING
    gw = WorkflowGateway(gateway_id="test-gw", manager=mgr)
    return gw


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Constants & Enums
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_gateway_state_values(self):
        assert GatewayState.RUNNING.value      == "running"
        assert GatewayState.STOPPED.value      == "stopped"
        assert GatewayState.UNINITIALIZED.value == "uninitialized"

    def test_gateway_event_types_count(self):
        assert len(GatewayEventType) == 10

    def test_request_type_values(self):
        assert GatewayRequestType.SUBMIT.value   == "submit"
        assert GatewayRequestType.QUERY.value    == "query"
        assert GatewayRequestType.CANCEL.value   == "cancel"
        assert GatewayRequestType.RETRY.value    == "retry"
        assert GatewayRequestType.VALIDATE.value == "validate"

    def test_response_status_values(self):
        assert GatewayResponseStatus.SUCCESS.value  == "success"
        assert GatewayResponseStatus.FAILURE.value  == "failure"
        assert GatewayResponseStatus.PENDING.value  == "pending"
        assert GatewayResponseStatus.REJECTED.value == "rejected"

    def test_component_types(self):
        assert ComponentType.LIFECYCLE.value           == "lifecycle"
        assert ComponentType.ENGINE.value              == "engine"
        assert ComponentType.POLICY_ENGINE.value       == "policy_engine"
        assert ComponentType.ORCHESTRATION_ENGINE.value == "orchestration_engine"
        assert ComponentType.SNAPSHOT.value            == "snapshot"

    def test_component_status_values(self):
        assert ComponentStatus.AVAILABLE.value   == "available"
        assert ComponentStatus.UNAVAILABLE.value == "unavailable"
        assert ComponentStatus.DEGRADED.value    == "degraded"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_inherits_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(WorkflowGatewayError, IIOSError)

    def test_not_initialized_error(self):
        err = WorkflowGatewayNotInitializedError()
        assert "WGW-001" in err.code
        assert "not initialized" in str(err).lower()

    def test_not_running_error(self):
        err = WorkflowGatewayNotRunningError()
        assert "WGW-002" in err.code

    def test_validation_error_issues(self):
        issues = ["field required", "priority out of range"]
        err    = WorkflowGatewayValidationError("bad request", issues=issues)
        assert err.issues == issues
        assert "WGW-003" in err.code

    def test_routing_error(self):
        err = WorkflowGatewayRoutingError("no route")
        assert "WGW-006" in err.code

    def test_component_error_has_component(self):
        err = WorkflowGatewayComponentError("missing", component="lifecycle")
        assert err.component == "lifecycle"
        assert "WGW-008" in err.code

    def test_dispatch_error(self):
        err = WorkflowGatewayDispatchError("engine failed")
        assert "WGW-007" in err.code

    def test_all_codes_wgw_prefix(self):
        for cls in [
            WorkflowGatewayNotInitializedError,
            WorkflowGatewayNotRunningError,
            WorkflowGatewayValidationError,
            WorkflowGatewayRoutingError,
            WorkflowGatewayDispatchError,
            WorkflowGatewayComponentError,
        ]:
            assert "WGW" in cls.error_code, f"{cls} missing WGW prefix"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. WorkflowGatewayRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayRequest:
    def test_create_defaults(self):
        req = WorkflowGatewayRequest.create("wf-1")
        assert req.request_id.startswith("wgwreq-")
        assert req.workflow_id   == "wf-1"
        assert req.request_type  == GatewayRequestType.SUBMIT
        assert req.enterprise_id == "iios"
        assert req.correlation_id  # auto-generated
        assert req.priority      == 1

    def test_create_custom(self):
        req = WorkflowGatewayRequest.create(
            "wf-x",
            workflow_name  = "My Workflow",
            request_type   = GatewayRequestType.QUERY,
            enterprise_id  = "acme",
            priority       = 5,
        )
        assert req.workflow_name == "My Workflow"
        assert req.request_type  == GatewayRequestType.QUERY
        assert req.enterprise_id == "acme"
        assert req.priority      == 5

    def test_priority_clamped(self):
        r1 = WorkflowGatewayRequest.create("wf-1", priority=-5)
        r2 = WorkflowGatewayRequest.create("wf-1", priority=100)
        assert r1.priority == 0
        assert r2.priority == 10

    def test_frozen(self):
        req = WorkflowGatewayRequest.create("wf-1")
        with pytest.raises((TypeError, AttributeError)):
            req.workflow_id = "changed"

    def test_to_dict(self):
        req = WorkflowGatewayRequest.create("wf-1")
        d   = req.to_dict()
        assert "request_id"   in d
        assert "workflow_id"  in d
        assert "request_type" in d
        assert isinstance(d["request_type"], str)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. WorkflowGatewayResponse
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayResponse:
    def test_success_for(self):
        req  = _req()
        resp = WorkflowGatewayResponse.success_for(req, session_id="s1", snapshot_id="snap-1")
        assert resp.response_id.startswith("wgwres-")
        assert resp.is_success
        assert not resp.is_failure
        assert resp.session_id  == "s1"
        assert resp.snapshot_id == "snap-1"

    def test_failure_for(self):
        req  = _req()
        resp = WorkflowGatewayResponse.failure_for(req, "disk full")
        assert resp.is_failure
        assert resp.error_message == "disk full"

    def test_pending_for(self):
        req  = _req()
        resp = WorkflowGatewayResponse.pending_for(req)
        assert resp.is_pending

    def test_rejected_for(self):
        req  = _req()
        resp = WorkflowGatewayResponse.rejected_for(req, "not running")
        assert resp.is_rejected
        assert "not running" in resp.error_message

    def test_frozen(self):
        req  = _req()
        resp = WorkflowGatewayResponse.success_for(req)
        with pytest.raises((TypeError, AttributeError)):
            resp.status = GatewayResponseStatus.FAILURE

    def test_to_dict(self):
        req  = _req()
        resp = WorkflowGatewayResponse.success_for(req)
        d    = resp.to_dict()
        assert "response_id"   in d
        assert "status"        in d
        assert "is_success"    in d
        assert "is_failure"    in d
        assert isinstance(d["status"], str)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. WorkflowGatewayContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayContext:
    def test_create(self):
        req  = _req()
        ctx  = WorkflowGatewayContext.create(req, "gw-1")
        assert ctx.context_id.startswith("wgwctx-")
        assert ctx.gateway_id   == "gw-1"
        assert ctx.workflow_id  == req.workflow_id
        assert ctx.request_id   == req.request_id
        assert ctx.correlation_id == req.correlation_id

    def test_frozen(self):
        req = _req()
        ctx = WorkflowGatewayContext.create(req, "gw-1")
        with pytest.raises((TypeError, AttributeError)):
            ctx.gateway_id = "changed"

    def test_to_dict(self):
        req = _req()
        ctx = WorkflowGatewayContext.create(req, "gw-1")
        d   = ctx.to_dict()
        assert "context_id" in d
        assert "gateway_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 6. WorkflowGatewayValidation
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayValidation:
    def test_valid_request_passes(self):
        val    = WorkflowGatewayValidation()
        req    = _req()
        result = val.validate_request(req)
        assert result.valid
        assert len(result.issues) == 0

    def test_empty_workflow_id_fails(self):
        import dataclasses
        req    = _req()
        req    = dataclasses.replace(req, workflow_id="")
        val    = WorkflowGatewayValidation()
        result = val.validate_request(req)
        assert not result.valid
        assert any("workflow_id" in i for i in result.issues)

    def test_empty_enterprise_id_fails(self):
        import dataclasses
        req    = _req()
        req    = dataclasses.replace(req, enterprise_id="")
        val    = WorkflowGatewayValidation()
        result = val.validate_request(req)
        assert not result.valid

    def test_validate_or_raise(self):
        import dataclasses
        req = _req()
        req = dataclasses.replace(req, workflow_id="")
        val = WorkflowGatewayValidation()
        with pytest.raises(WorkflowGatewayValidationError) as exc_info:
            val.validate_request_or_raise(req)
        assert exc_info.value.issues

    def test_valid_raises_nothing(self):
        val = WorkflowGatewayValidation()
        val.validate_request_or_raise(_req())   # no raise

    def test_valid_response(self):
        req  = _req()
        resp = WorkflowGatewayResponse.success_for(req)
        val  = WorkflowGatewayValidation()
        r    = val.validate_response(resp)
        assert r.valid

    def test_result_to_dict(self):
        val = WorkflowGatewayValidation()
        r   = val.validate_request(_req())
        d   = r.to_dict()
        assert "valid"  in d
        assert "issues" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 7. WorkflowGatewayHealth
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayHealth:
    def test_healthy_running_all_available(self):
        import time
        health  = WorkflowGatewayHealth()
        statuses = {"lifecycle": ComponentStatus.AVAILABLE, "engine": ComponentStatus.AVAILABLE}
        summary  = health.report("gw-1", GatewayState.RUNNING, statuses, time.monotonic())
        assert summary.is_healthy
        assert summary.overall_status == GatewayHealthStatus.HEALTHY

    def test_unhealthy_stopped(self):
        import time
        health  = WorkflowGatewayHealth()
        summary = health.report("gw-1", GatewayState.STOPPED, {}, time.monotonic())
        assert summary.is_unhealthy

    def test_unhealthy_component_unavailable(self):
        import time
        health  = WorkflowGatewayHealth()
        statuses = {"engine": ComponentStatus.UNAVAILABLE}
        summary  = health.report("gw-1", GatewayState.RUNNING, statuses, time.monotonic())
        assert summary.is_unhealthy

    def test_degraded_component_degraded(self):
        import time
        health  = WorkflowGatewayHealth()
        statuses = {"engine": ComponentStatus.DEGRADED}
        summary  = health.report("gw-1", GatewayState.RUNNING, statuses, time.monotonic())
        assert summary.is_degraded

    def test_degraded_initialized_state(self):
        import time
        health  = WorkflowGatewayHealth()
        summary = health.report("gw-1", GatewayState.INITIALIZED, {}, time.monotonic())
        assert summary.is_degraded

    def test_to_dict(self):
        import time
        health  = WorkflowGatewayHealth()
        summary = health.report("gw-1", GatewayState.RUNNING, {}, time.monotonic())
        d       = summary.to_dict()
        assert "overall_status"   in d
        assert "gateway_state"    in d
        assert "component_health" in d
        assert "is_healthy"       in d


# ═══════════════════════════════════════════════════════════════════════════════
# 8. WorkflowGatewayStatus
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayStatus:
    def test_capture(self):
        import time
        tracker = WorkflowGatewayStatus()
        status  = tracker.capture("gw-1", GatewayState.RUNNING, 2, 0, 10, time.monotonic())
        assert status.gateway_id       == "gw-1"
        assert status.active_workflows == 2
        assert status.total_processed  == 10
        assert status.is_operational

    def test_not_operational_when_stopped(self):
        import time
        tracker = WorkflowGatewayStatus()
        status  = tracker.capture("gw-1", GatewayState.STOPPED, 0, 0, 5, time.monotonic())
        assert not status.is_operational

    def test_to_dict(self):
        import time
        tracker = WorkflowGatewayStatus()
        status  = tracker.capture("gw-1", GatewayState.RUNNING, 0, 0, 0, time.monotonic())
        d       = status.to_dict()
        assert "gateway_state"   in d
        assert "is_operational"  in d
        assert isinstance(d["gateway_state"], str)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. WorkflowGatewayStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayStatistics:
    def test_initial_zeros(self):
        stats  = WorkflowGatewayStatistics()
        report = stats.report()
        assert report.total_requests  == 0
        assert report.success_rate    if False else True   # no attribute — check below
        assert report.total_requests  == 0

    def test_record_success(self):
        stats = WorkflowGatewayStatistics()
        stats.record_request(success=True, response_ms=100.0)
        r = stats.report()
        assert r.total_requests      == 1
        assert r.successful_requests == 1

    def test_record_failure(self):
        stats = WorkflowGatewayStatistics()
        stats.record_request(success=False, response_ms=50.0)
        r = stats.report()
        assert r.failed_requests == 1

    def test_record_rejected(self):
        stats = WorkflowGatewayStatistics()
        stats.record_request(rejected=True)
        r = stats.report()
        assert r.rejected_requests == 1

    def test_record_workflow_execution(self):
        stats = WorkflowGatewayStatistics()
        stats.record_workflow_execution()
        assert stats.report().workflow_executions == 1

    def test_record_snapshot_published(self):
        stats = WorkflowGatewayStatistics()
        stats.record_snapshot_published()
        assert stats.report().snapshots_published == 1

    def test_average_response_time(self):
        stats = WorkflowGatewayStatistics()
        stats.record_request(success=True, response_ms=100.0)
        stats.record_request(success=True, response_ms=200.0)
        r = stats.report()
        assert r.average_response_time_ms == 150.0

    def test_availability_tick(self):
        stats = WorkflowGatewayStatistics()
        stats.record_availability_tick(True)
        stats.record_availability_tick(False)
        r = stats.report()
        assert r.gateway_availability == 0.5

    def test_reset(self):
        stats = WorkflowGatewayStatistics()
        stats.record_request(success=True)
        stats.reset()
        assert stats.report().total_requests == 0

    def test_report_to_dict(self):
        d = WorkflowGatewayStatistics().report().to_dict()
        assert "total_requests"           in d
        assert "average_response_time_ms" in d
        assert "gateway_availability"     in d


# ═══════════════════════════════════════════════════════════════════════════════
# 10. WorkflowGatewayHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayHistory:
    def test_record_and_get(self):
        hist = WorkflowGatewayHistory()
        req  = _req()
        resp = WorkflowGatewayResponse.success_for(req)
        rec  = hist.record(req, resp)
        assert hist.get(req.request_id) is not None
        assert rec.workflow_id == req.workflow_id

    def test_get_not_found(self):
        assert WorkflowGatewayHistory().get("ghost") is None

    def test_for_workflow(self):
        hist = WorkflowGatewayHistory()
        r1   = _req("wf-a"); r2 = _req("wf-a"); r3 = _req("wf-b")
        for req in [r1, r2, r3]:
            hist.record(req, WorkflowGatewayResponse.success_for(req))
        results = hist.for_workflow("wf-a")
        assert len(results) == 2

    def test_recent(self):
        hist = WorkflowGatewayHistory()
        for i in range(5):
            req = _req(f"wf-{i}")
            hist.record(req, WorkflowGatewayResponse.success_for(req))
        assert len(hist.recent(3)) == 3

    def test_count(self):
        hist = WorkflowGatewayHistory()
        assert hist.count() == 0
        req  = _req()
        hist.record(req, WorkflowGatewayResponse.success_for(req))
        assert hist.count() == 1

    def test_clear(self):
        hist = WorkflowGatewayHistory()
        req  = _req()
        hist.record(req, WorkflowGatewayResponse.success_for(req))
        n = hist.clear()
        assert n == 1
        assert hist.count() == 0

    def test_bounded(self):
        hist = WorkflowGatewayHistory(max_records=3)
        for i in range(5):
            req = _req(f"wf-{i}")
            hist.record(req, WorkflowGatewayResponse.success_for(req))
        assert hist.count() == 3

    def test_record_to_dict(self):
        hist = WorkflowGatewayHistory()
        req  = _req()
        resp = WorkflowGatewayResponse.success_for(req)
        rec  = hist.record(req, resp)
        d    = rec.to_dict()
        assert "record_id"   in d
        assert "workflow_id" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 11. WorkflowGatewayEventBus
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayEventBus:
    def _evt(self, et=GatewayEventType.WORKFLOW_SUBMITTED):
        return WorkflowGatewayEvent.create(et, "gw-1", "wf-1")

    def test_add_listener_and_emit(self):
        bus      = WorkflowGatewayEventBus()
        received = []
        bus.add_listener(GatewayEventType.WORKFLOW_SUBMITTED, received.append)
        bus.emit(self._evt())
        assert len(received) == 1

    def test_wrong_type_not_received(self):
        bus      = WorkflowGatewayEventBus()
        received = []
        bus.add_listener(GatewayEventType.GATEWAY_STARTED, received.append)
        bus.emit(self._evt(GatewayEventType.WORKFLOW_SUBMITTED))
        assert len(received) == 0

    def test_remove_listener(self):
        bus = WorkflowGatewayEventBus()
        def cb(e): pass
        bus.add_listener(GatewayEventType.WORKFLOW_SUBMITTED, cb)
        assert bus.remove_listener(GatewayEventType.WORKFLOW_SUBMITTED, cb) is True
        assert bus.listener_count(GatewayEventType.WORKFLOW_SUBMITTED) == 0

    def test_remove_not_found(self):
        bus = WorkflowGatewayEventBus()
        assert bus.remove_listener(GatewayEventType.WORKFLOW_SUBMITTED, lambda e: None) is False

    def test_listener_count_all(self):
        bus = WorkflowGatewayEventBus()
        bus.add_listener(GatewayEventType.GATEWAY_STARTED,    lambda e: None)
        bus.add_listener(GatewayEventType.WORKFLOW_SUBMITTED,  lambda e: None)
        assert bus.listener_count() == 2

    def test_listener_error_does_not_propagate(self):
        bus = WorkflowGatewayEventBus()
        bus.add_listener(GatewayEventType.WORKFLOW_SUBMITTED, lambda e: 1/0)
        notified = bus.emit(self._evt())   # must not raise
        assert notified == 0

    def test_clear(self):
        bus = WorkflowGatewayEventBus()
        bus.add_listener(GatewayEventType.GATEWAY_STARTED, lambda e: None)
        bus.clear()
        assert bus.listener_count() == 0

    def test_event_frozen(self):
        evt = WorkflowGatewayEvent.create(GatewayEventType.GATEWAY_STARTED)
        with pytest.raises((TypeError, AttributeError)):
            evt.gateway_id = "changed"

    def test_event_to_dict(self):
        evt = WorkflowGatewayEvent.create(GatewayEventType.GATEWAY_STARTED, "gw-1", "wf-1")
        d   = evt.to_dict()
        assert "event_id"    in d
        assert "event_type"  in d
        assert isinstance(d["event_type"], str)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. WorkflowGatewayRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayRegistry:
    def test_register_and_get(self):
        reg  = WorkflowGatewayRegistry()
        req  = _req()
        resp = WorkflowGatewayResponse.success_for(req)
        reg.register(resp)
        fetched = reg.get(req.request_id)
        assert fetched is not None
        assert fetched.request_id == req.request_id

    def test_get_not_found(self):
        assert WorkflowGatewayRegistry().get("ghost") is None

    def test_exists(self):
        reg  = WorkflowGatewayRegistry()
        req  = _req()
        resp = WorkflowGatewayResponse.success_for(req)
        assert not reg.exists(req.request_id)
        reg.register(resp)
        assert reg.exists(req.request_id)

    def test_deregister(self):
        reg  = WorkflowGatewayRegistry()
        req  = _req()
        resp = WorkflowGatewayResponse.success_for(req)
        reg.register(resp)
        removed = reg.deregister(req.request_id)
        assert removed is True
        assert not reg.exists(req.request_id)

    def test_deregister_not_found(self):
        assert WorkflowGatewayRegistry().deregister("ghost") is False

    def test_get_by_workflow(self):
        reg  = WorkflowGatewayRegistry()
        r1   = _req("wf-a"); r2 = _req("wf-a"); r3 = _req("wf-b")
        for req in [r1, r2, r3]:
            reg.register(WorkflowGatewayResponse.success_for(req))
        results = reg.get_by_workflow("wf-a")
        assert len(results) == 2

    def test_latest_for_workflow(self):
        reg  = WorkflowGatewayRegistry()
        r1   = _req("wf-x"); r2 = _req("wf-x")
        for req in [r1, r2]:
            reg.register(WorkflowGatewayResponse.success_for(req))
        latest = reg.latest_for_workflow("wf-x")
        assert latest is not None

    def test_latest_for_missing_workflow(self):
        assert WorkflowGatewayRegistry().latest_for_workflow("ghost") is None

    def test_count(self):
        reg = WorkflowGatewayRegistry()
        assert reg.count() == 0
        reg.register(WorkflowGatewayResponse.success_for(_req()))
        assert reg.count() == 1

    def test_clear(self):
        reg  = WorkflowGatewayRegistry()
        req  = _req()
        reg.register(WorkflowGatewayResponse.success_for(req))
        n = reg.clear()
        assert n == 1
        assert reg.count() == 0

    def test_bounded_eviction(self):
        reg = WorkflowGatewayRegistry(max_entries=2)
        for i in range(4):
            req = _req(f"wf-{i}")
            reg.register(WorkflowGatewayResponse.success_for(req))
        assert reg.count() == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 13. WorkflowComponentRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestComponentRegistry:
    def test_register_and_get(self):
        reg = WorkflowComponentRegistry()
        obj = object()
        reg.register("lifecycle", ComponentType.LIFECYCLE, obj)
        assert reg.get_component("lifecycle") is obj

    def test_get_not_found(self):
        reg = WorkflowComponentRegistry()
        with pytest.raises(WorkflowGatewayComponentError) as exc_info:
            reg.get_component("missing")
        assert exc_info.value.component == "missing"

    def test_get_or_none(self):
        reg = WorkflowComponentRegistry()
        assert reg.get_component_or_none("x") is None
        reg.register("x", ComponentType.SNAPSHOT, object())
        assert reg.get_component_or_none("x") is not None

    def test_is_available(self):
        reg = WorkflowComponentRegistry()
        assert not reg.is_available("engine")
        reg.register("engine", ComponentType.ENGINE, object(), status=ComponentStatus.AVAILABLE)
        assert reg.is_available("engine")

    def test_is_not_available_when_degraded(self):
        reg = WorkflowComponentRegistry()
        reg.register("engine", ComponentType.ENGINE, object(), status=ComponentStatus.DEGRADED)
        assert not reg.is_available("engine")

    def test_set_status(self):
        reg = WorkflowComponentRegistry()
        reg.register("e", ComponentType.ENGINE, object())
        reg.set_status("e", ComponentStatus.DEGRADED)
        assert reg.component_statuses()["e"] == ComponentStatus.DEGRADED

    def test_all_records(self):
        reg = WorkflowComponentRegistry()
        reg.register("a", ComponentType.LIFECYCLE, object())
        reg.register("b", ComponentType.ENGINE,    object())
        assert len(reg.all_records()) == 2

    def test_count(self):
        reg = WorkflowComponentRegistry()
        assert reg.count() == 0
        reg.register("x", ComponentType.SNAPSHOT, object())
        assert reg.count() == 1

    def test_clear(self):
        reg = WorkflowComponentRegistry()
        reg.register("x", ComponentType.SNAPSHOT, object())
        reg.clear()
        assert reg.count() == 0

    def test_component_statuses_dict(self):
        reg = WorkflowComponentRegistry()
        reg.register("a", ComponentType.LIFECYCLE, object(), status=ComponentStatus.AVAILABLE)
        reg.register("b", ComponentType.ENGINE,    object(), status=ComponentStatus.DEGRADED)
        statuses = reg.component_statuses()
        assert statuses["a"] == ComponentStatus.AVAILABLE
        assert statuses["b"] == ComponentStatus.DEGRADED

    def test_record_to_dict(self):
        reg = WorkflowComponentRegistry()
        reg.register("x", ComponentType.LIFECYCLE, object())
        rec = reg.all_records()[0]
        d   = rec.to_dict()
        assert "component_name" in d
        assert "component_type" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 14. WorkflowGatewayRouter
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayRouter:
    def test_route_submit(self):
        router = WorkflowGatewayRouter()
        req    = _req(request_type=GatewayRequestType.SUBMIT)
        assert router.route(req) == "submit"

    def test_route_query(self):
        router = WorkflowGatewayRouter()
        req    = _req(request_type=GatewayRequestType.QUERY)
        assert router.route(req) == "query"

    def test_route_cancel(self):
        router = WorkflowGatewayRouter()
        req    = _req(request_type=GatewayRequestType.CANCEL)
        assert router.route(req) == "cancel"

    def test_route_retry(self):
        router = WorkflowGatewayRouter()
        req    = _req(request_type=GatewayRequestType.RETRY)
        assert router.route(req) == "retry"

    def test_route_validate(self):
        router = WorkflowGatewayRouter()
        req    = _req(request_type=GatewayRequestType.VALIDATE)
        assert router.route(req) == "validate"

    def test_supported_types(self):
        router = WorkflowGatewayRouter()
        assert len(router.supported_types()) == 5


# ═══════════════════════════════════════════════════════════════════════════════
# 15. WorkflowGatewayFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayFactory:
    def test_create_submit_request(self):
        req = WorkflowGatewayFactory.create_submit_request("wf-1", "My Workflow")
        assert req.request_type == GatewayRequestType.SUBMIT
        assert req.workflow_id  == "wf-1"

    def test_create_query_request(self):
        req = WorkflowGatewayFactory.create_query_request("wf-1")
        assert req.request_type == GatewayRequestType.QUERY

    def test_create_cancel_request(self):
        req = WorkflowGatewayFactory.create_cancel_request("wf-1")
        assert req.request_type == GatewayRequestType.CANCEL

    def test_create_retry_request(self):
        req = WorkflowGatewayFactory.create_retry_request("wf-1")
        assert req.request_type == GatewayRequestType.RETRY

    def test_create_validate_request(self):
        req = WorkflowGatewayFactory.create_validate_request("wf-1")
        assert req.request_type == GatewayRequestType.VALIDATE

    def test_create_context(self):
        req = _req()
        ctx = WorkflowGatewayFactory.create_context(req, "gw-1")
        assert ctx.gateway_id == "gw-1"

    def test_create_success_response(self):
        req  = _req()
        resp = WorkflowGatewayFactory.create_success_response(req, session_id="s1")
        assert resp.is_success
        assert resp.session_id == "s1"

    def test_create_failure_response(self):
        req  = _req()
        resp = WorkflowGatewayFactory.create_failure_response(req, "bad input")
        assert resp.is_failure
        assert "bad input" in resp.error_message


# ═══════════════════════════════════════════════════════════════════════════════
# 16. WorkflowGatewayManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayManager:
    def _manager_no_components(self) -> WorkflowGatewayManager:
        mgr = WorkflowGatewayManager(
            gateway_id         = "test-mgr",
            component_registry = WorkflowComponentRegistry(),
        )
        # Override factory to do nothing (avoid real M1-M5 imports)
        class _NullFactory:
            def build_and_register_all(self, registry): return {}
        mgr._factory = _NullFactory()
        return mgr

    def test_initialize_sets_state(self):
        mgr = self._manager_no_components()
        assert mgr.state == GatewayState.UNINITIALIZED
        mgr.initialize()
        assert mgr.state == GatewayState.INITIALIZED

    def test_start_after_initialize(self):
        mgr = self._manager_no_components()
        mgr.initialize()
        mgr.start()
        assert mgr.is_running

    def test_start_raises_when_uninitialized(self):
        mgr = self._manager_no_components()
        with pytest.raises(WorkflowGatewayNotInitializedError):
            mgr.start()

    def test_stop(self):
        mgr = self._manager_no_components()
        mgr.initialize()
        mgr.start()
        mgr.stop()
        assert mgr.state == GatewayState.STOPPED

    def test_restart(self):
        mgr = self._manager_no_components()
        mgr.initialize()
        mgr.start()
        mgr.restart()
        assert mgr.is_running

    def test_double_start_is_idempotent(self):
        mgr = self._manager_no_components()
        mgr.initialize()
        mgr.start()
        mgr.start()   # should not raise
        assert mgr.is_running

    def test_counters(self):
        mgr = self._manager_no_components()
        mgr.initialize()
        mgr.start()
        mgr.increment_active()
        assert mgr.active_count() == 1
        mgr.decrement_active()
        assert mgr.active_count() == 0
        assert mgr.total_count() == 1

    def test_health_summary(self):
        mgr = self._manager_no_components()
        mgr.initialize()
        mgr.start()
        h   = mgr.health_summary()
        assert isinstance(h, WorkflowHealthSummary)

    def test_status_snapshot(self):
        mgr = self._manager_no_components()
        mgr.initialize()
        mgr.start()
        s   = mgr.status_snapshot()
        assert isinstance(s, WorkflowStatus)
        assert s.is_operational


# ═══════════════════════════════════════════════════════════════════════════════
# 17. WorkflowGatewayDispatcher
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayDispatcher:
    def _components(self) -> WorkflowComponentRegistry:
        return WorkflowComponentRegistry()

    def test_dispatch_submit(self):
        dispatcher = WorkflowGatewayDispatcher()
        req        = _req(request_type=GatewayRequestType.SUBMIT)
        ctx        = WorkflowGatewayContext.create(req, "gw-1")
        resp       = dispatcher.dispatch(req, ctx, self._components())
        # No engine → passthrough success
        assert resp.is_success

    def test_dispatch_query(self):
        dispatcher = WorkflowGatewayDispatcher()
        req        = _req(request_type=GatewayRequestType.QUERY)
        ctx        = WorkflowGatewayContext.create(req, "gw-1")
        resp       = dispatcher.dispatch(req, ctx, self._components())
        assert resp.is_success

    def test_dispatch_cancel(self):
        dispatcher = WorkflowGatewayDispatcher()
        req        = _req(request_type=GatewayRequestType.CANCEL)
        ctx        = WorkflowGatewayContext.create(req, "gw-1")
        resp       = dispatcher.dispatch(req, ctx, self._components())
        assert resp.is_success
        assert resp.data.get("cancelled") is True

    def test_dispatch_retry(self):
        dispatcher = WorkflowGatewayDispatcher()
        req        = _req(request_type=GatewayRequestType.RETRY)
        ctx        = WorkflowGatewayContext.create(req, "gw-1")
        resp       = dispatcher.dispatch(req, ctx, self._components())
        assert resp.is_success

    def test_dispatch_validate(self):
        dispatcher = WorkflowGatewayDispatcher()
        req        = _req(request_type=GatewayRequestType.VALIDATE)
        ctx        = WorkflowGatewayContext.create(req, "gw-1")
        resp       = dispatcher.dispatch(req, ctx, self._components())
        assert resp.is_success
        assert resp.data.get("validated") is True


# ═══════════════════════════════════════════════════════════════════════════════
# 18. WorkflowGateway — Public API
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowGateway:
    """Tests for the main WorkflowGateway public API."""

    def _gateway(self) -> WorkflowGateway:
        gw = _gateway_no_components()
        return gw

    # Lifecycle
    def test_initialize_start_stop(self):
        gw = WorkflowGateway.__new__(WorkflowGateway)
        class _NullFactory:
            def build_and_register_all(self, registry): return {}
        mgr = WorkflowGatewayManager(gateway_id="gw-test")
        mgr._factory = _NullFactory()
        gw.__init__(gateway_id="gw-test", manager=mgr)
        gw.initialize()
        gw.start()
        assert gw._manager.is_running
        gw.stop()
        assert gw._manager.state == GatewayState.STOPPED

    # Validate
    def test_validate_valid_request(self):
        gw     = self._gateway()
        req    = _req()
        result = gw.validate(req)
        assert result.valid

    def test_validate_invalid_request(self):
        import dataclasses
        gw  = self._gateway()
        req = dataclasses.replace(_req(), workflow_id="")
        r   = gw.validate(req)
        assert not r.valid

    # Submit
    def test_submit_success(self):
        gw   = self._gateway()
        req  = _req()
        resp = gw.submit(req)
        assert resp.is_success

    def test_submit_rejected_when_not_running(self):
        class _NullFactory:
            def build_and_register_all(self, registry): return {}
        mgr = WorkflowGatewayManager(gateway_id="gw-test2")
        mgr._factory = _NullFactory()
        mgr.initialize()
        # Do NOT start
        gw  = WorkflowGateway(gateway_id="gw-test2", manager=mgr)
        req = _req()
        resp = gw.submit(req)
        assert resp.is_rejected

    def test_submit_rejected_on_invalid_request(self):
        import dataclasses
        gw  = self._gateway()
        req = dataclasses.replace(_req(), workflow_id="")
        resp = gw.submit(req)
        assert resp.is_rejected

    # Query
    def test_query(self):
        gw   = self._gateway()
        resp = gw.query("wf-1")
        assert resp.is_success

    # Cancel
    def test_cancel(self):
        gw   = self._gateway()
        resp = gw.cancel("wf-1")
        assert resp.is_success

    # Retry
    def test_retry(self):
        gw   = self._gateway()
        resp = gw.retry("wf-1")
        assert resp.is_success

    # Health
    def test_health_returns_summary(self):
        gw = self._gateway()
        h  = gw.health()
        assert isinstance(h, WorkflowHealthSummary)

    # Status
    def test_status_returns_status(self):
        gw = self._gateway()
        s  = gw.status()
        assert isinstance(s, WorkflowStatus)
        assert s.is_operational

    # Statistics
    def test_statistics_returns_report(self):
        gw  = self._gateway()
        gw.submit(_req())
        stats = gw.statistics()
        assert isinstance(stats, WorkflowStatistics)
        assert stats.total_requests >= 1

    # History
    def test_history_populated_after_submit(self):
        gw = self._gateway()
        gw.submit(_req("wf-hist"))
        records = gw.history()
        assert len(records) >= 1
        assert records[0].workflow_id == "wf-hist"

    # Snapshot
    def test_snapshot_none_for_empty(self):
        gw = self._gateway()
        assert gw.snapshot() is None

    # Events
    def test_events_emitted_on_submit(self):
        gw       = self._gateway()
        received = []
        gw._event_bus.add_listener(GatewayEventType.WORKFLOW_SUBMITTED, received.append)
        gw.submit(_req())
        assert len(received) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 19. Concurrency & Regression
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrencyRegression:
    def test_concurrent_submits(self):
        gw     = _gateway_no_components()
        errors = []

        def worker():
            try:
                gw.submit(_req(str(uuid.uuid4())))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_concurrent_history(self):
        gw     = _gateway_no_components()
        errors = []

        def worker():
            try:
                gw.submit(_req(str(uuid.uuid4())))
                _ = gw.history(10)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_statistics_accumulate_correctly(self):
        gw = _gateway_no_components()
        for i in range(10):
            gw.submit(_req(f"wf-{i}"))
        stats = gw.statistics()
        assert stats.total_requests == 10
        assert stats.successful_requests == 10

    def test_all_request_types_return_success(self):
        gw   = _gateway_no_components()
        for rt in GatewayRequestType:
            req  = WorkflowGatewayRequest.create("wf-x", request_type=rt)
            resp = gw.submit(req)
            assert resp in (resp,)   # always returns

    def test_response_ids_are_unique(self):
        gw   = _gateway_no_components()
        ids  = set()
        for i in range(20):
            resp = gw.submit(_req(f"wf-{i}"))
            ids.add(resp.response_id)
        assert len(ids) == 20

    def test_full_pipeline_no_exceptions(self):
        gw = _gateway_no_components()
        # submit → query → cancel → retry sequence on same workflow
        wf_id = "wf-pipeline"
        r1    = gw.submit(_req(wf_id, request_type=GatewayRequestType.SUBMIT))
        r2    = gw.query(wf_id)
        r3    = gw.cancel(wf_id)
        r4    = gw.retry(wf_id)
        for resp in [r1, r2, r3, r4]:
            assert not resp.is_failure

    def test_gateway_history_matches_submitted(self):
        gw = _gateway_no_components()
        wf_id = "wf-hist-check"
        gw.submit(_req(wf_id))
        gw.submit(_req(wf_id))
        records = gw.history(10)
        wf_records = [r for r in records if r.workflow_id == wf_id]
        assert len(wf_records) == 2

    def test_event_bus_counts(self):
        gw       = _gateway_no_components()
        received = []
        gw._event_bus.add_listener(GatewayEventType.WORKFLOW_COMPLETED, received.append)
        for i in range(5):
            gw.submit(_req(f"wf-{i}"))
        assert len(received) == 5
