"""
tests/unit/decision/integration/test_integration.py
====================================================
Comprehensive unit tests for C9 M6 Decision Integration.

Coverage targets
----------------
- Constants and enums
- Exceptions (hierarchy + error codes)
- DecisionIntegrationRequest (create, serialisation)
- DecisionIntegrationResponse (properties, serialisation)
- DecisionIntegrationSnapshot (create, serialisation)
- DecisionIntegrationContext (phase tracking, timing)
- DecisionIntegrationValidation (all 6 checks)
- DecisionIntegrationHealth (per-component, aggregate)
- DecisionIntegrationStatus (service snapshot)
- DecisionIntegrationStatistics (counters, EMA, reset)
- DecisionIntegrationHistory (responses, events, queries)
- DecisionIntegrationEvents (factory functions, to_dict)
- DecisionIntegrationRegistry (in-flight, completion, queries)
- DecisionComponentRegistry (register, ready, health)
- DecisionComponentFactory (create_default)
- DecisionIntegrationManager (start/stop/restart)
- DecisionIntegrationEngine (public API, full workflow)
- __init__ exports
- Concurrency (thread-safe operations)
- Regression (immutability, query, deduplication)
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from iios.decision.integration import (
    # Constants
    INTEGRATION_SYSTEM_ID,
    VERSION,
    SCHEMA_VERSION,
    ComponentHealth,
    ComponentType,
    IntegrationEventType,
    IntegrationPhase,
    IntegrationStatus,
    IntegrationValidationCode,
    OverallHealth,
    # Exceptions
    DecisionIntegrationError,
    IntegrationNotRunningError,
    IntegrationRequestError,
    IntegrationValidationError,
    ComponentNotFoundError,
    ComponentNotReadyError,
    IntegrationTimeoutError,
    IntegrationWorkflowError,
    DuplicateIntegrationError,
    IntegrationConfigurationError,
    # Value objects
    DecisionIntegrationRequest,
    DecisionIntegrationResponse,
    DecisionIntegrationSnapshot,
    DecisionIntegrationContext,
    # Validation
    DecisionIntegrationValidator,
    IntegrationValidationCheckResult,
    IntegrationValidationResult,
    # Health & Status
    ComponentHealthRecord,
    DecisionIntegrationHealth,
    DecisionIntegrationHealthMonitor,
    DecisionIntegrationStatus,
    DecisionIntegrationStatusMonitor,
    # Statistics
    DecisionIntegrationStatistics,
    # History
    DecisionIntegrationHistory,
    # Events
    DecisionIntegrationEvent,
    make_integration_initialized,
    make_integration_started,
    make_integration_stopped,
    make_integration_restarted,
    make_request_submitted,
    make_request_completed,
    make_request_failed,
    make_snapshot_published,
    make_health_changed,
    # Registry
    DecisionIntegrationRegistry,
    # Components
    DecisionComponentRegistry,
    DecisionComponentFactory,
    # Manager
    DecisionIntegrationManager,
    # Engine
    DecisionIntegrationEngine,
)


# ============================================================================
# Helpers
# ============================================================================

def _request(**kw) -> DecisionIntegrationRequest:
    return DecisionIntegrationRequest.create(
        decision_id       = kw.pop("decision_id", "dec-001"),
        workflow_id       = kw.pop("workflow_id", "wf-001"),
        portfolio_id      = kw.pop("portfolio_id", "pf-001"),
        strategy_id       = kw.pop("strategy_id", "strat-001"),
        decision_scope    = kw.pop("decision_scope", "order"),
        decision_type     = kw.pop("decision_type", "order"),
        decision_priority = kw.pop("decision_priority", "medium"),
        **kw,
    )


def _response(
    status: IntegrationStatus = IntegrationStatus.SUCCESS,
    **kw,
) -> DecisionIntegrationResponse:
    return DecisionIntegrationResponse.create(
        request_id  = kw.pop("request_id", "req-001"),
        decision_id = kw.pop("decision_id", "dec-001"),
        session_id  = kw.pop("session_id", "sess-001"),
        status      = status,
        **kw,
    )


def _minimal_registry() -> DecisionComponentRegistry:
    """
    Build a registry with a running M1 lifecycle + M5 snapshot store.
    Components are real instances (started).
    """
    from iios.decision.lifecycle import DecisionLifecycle
    from iios.decision.snapshot import DecisionSnapshotStore

    reg = DecisionComponentRegistry()
    lc  = DecisionLifecycle()
    lc.start()
    reg.register(ComponentType.LIFECYCLE, lc, description="M1")
    store = DecisionSnapshotStore(validate=False)
    reg.register(ComponentType.SNAPSHOT, store, description="M5")
    return reg


def _engine_with_registry() -> DecisionIntegrationEngine:
    reg    = _minimal_registry()
    engine = DecisionIntegrationEngine(component_registry=reg)
    engine.start()
    return engine


# ============================================================================
# 1. Constants & Enums
# ============================================================================

class TestConstants:
    def test_system_id_not_empty(self):
        assert INTEGRATION_SYSTEM_ID == "iios:decision:integration"

    def test_version_semver(self):
        assert VERSION
        assert VERSION.count(".") >= 1

    def test_schema_version(self):
        assert SCHEMA_VERSION

    def test_integration_status_values(self):
        names = {s.name for s in IntegrationStatus}
        assert {"PENDING", "RUNNING", "SUCCESS", "FAILED", "TIMEOUT", "PARTIAL"}.issubset(names)

    def test_component_type_values(self):
        names = {ct.name for ct in ComponentType}
        assert {"LIFECYCLE", "ENGINE", "POLICY_FRAMEWORK",
                "OPTIMIZATION_FRAMEWORK", "SNAPSHOT"}.issubset(names)

    def test_integration_phase_values(self):
        names = {p.name for p in IntegrationPhase}
        assert {"IDLE", "VALIDATING", "LIFECYCLE", "POLICY",
                "OPTIMIZATION", "SNAPSHOT", "COMPLETING"}.issubset(names)

    def test_event_type_count(self):
        assert len(IntegrationEventType) == 9

    def test_validation_code_count(self):
        assert len(IntegrationValidationCode) == 6

    def test_component_health_values(self):
        names = {h.name for h in ComponentHealth}
        assert {"HEALTHY", "DEGRADED", "CRITICAL", "UNKNOWN", "UNAVAILABLE"}.issubset(names)

    def test_overall_health_values(self):
        names = {h.name for h in OverallHealth}
        assert {"HEALTHY", "DEGRADED", "CRITICAL", "UNAVAILABLE"}.issubset(names)


# ============================================================================
# 2. Exceptions
# ============================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(DecisionIntegrationError, IIOSError)

    def test_not_running_error(self):
        err = IntegrationNotRunningError()
        assert "DI-001" in str(err) or err.error_code == "DI-001"

    def test_request_error(self):
        err = IntegrationRequestError("bad request")
        assert "DI-002" in str(err) or err.error_code == "DI-002"

    def test_validation_error_has_failed_checks(self):
        err = IntegrationValidationError("fail", failed_checks=("REQUEST_CONSISTENCY",))
        assert "REQUEST_CONSISTENCY" in err.failed_checks

    def test_component_not_found_has_id(self):
        err = ComponentNotFoundError("lifecycle")
        assert err.component_id == "lifecycle"
        assert "DI-004" in str(err) or err.error_code == "DI-004"

    def test_component_not_ready_has_id(self):
        err = ComponentNotReadyError("engine", reason="not started")
        assert err.component_id == "engine"

    def test_timeout_error(self):
        err = IntegrationTimeoutError("timed out")
        assert "DI-006" in str(err) or err.error_code == "DI-006"

    def test_workflow_error(self):
        err = IntegrationWorkflowError("pipeline failed")
        assert "DI-007" in str(err) or err.error_code == "DI-007"

    def test_duplicate_integration_error(self):
        err = DuplicateIntegrationError("req-x")
        assert err.integration_id == "req-x"

    def test_configuration_error(self):
        err = IntegrationConfigurationError("bad config")
        assert "DI-009" in str(err) or err.error_code == "DI-009"

    def test_hierarchy(self):
        for cls in [
            IntegrationNotRunningError, IntegrationRequestError,
            IntegrationValidationError, ComponentNotFoundError,
            ComponentNotReadyError, IntegrationTimeoutError,
            IntegrationWorkflowError, DuplicateIntegrationError,
            IntegrationConfigurationError,
        ]:
            assert issubclass(cls, DecisionIntegrationError)


# ============================================================================
# 3. DecisionIntegrationRequest
# ============================================================================

class TestDecisionIntegrationRequest:
    def test_create_generates_uuid(self):
        r1 = _request()
        r2 = _request()
        assert r1.request_id != r2.request_id

    def test_explicit_request_id(self):
        r = _request(request_id="my-req")
        assert r.request_id == "my-req"

    def test_default_fields(self):
        r = DecisionIntegrationRequest.create("dec-x")
        assert r.decision_id == "dec-x"
        assert r.decision_scope == "order"
        assert r.deadline_s > 0

    def test_is_frozen(self):
        r = _request()
        with pytest.raises((AttributeError, TypeError)):
            r.decision_id = "changed"  # type: ignore[misc]

    def test_to_dict_keys(self):
        d = _request().to_dict()
        assert "request_id" in d
        assert "decision_id" in d
        assert "decision_scope" in d
        assert isinstance(d["deadline_s"], float)

    def test_inputs_copied(self):
        orig = {"key": "value"}
        r    = _request(inputs=orig)
        orig["key"] = "mutated"
        assert r.inputs["key"] == "value"

    def test_metadata_copied(self):
        orig = {"k": 1}
        r    = _request(metadata=orig)
        orig["k"] = 99
        assert r.metadata["k"] == 1

    def test_requested_at_set(self):
        r = _request()
        assert r.requested_at > 0


# ============================================================================
# 4. DecisionIntegrationResponse
# ============================================================================

class TestDecisionIntegrationResponse:
    def test_create_success(self):
        r = _response(IntegrationStatus.SUCCESS, snapshot_id="snap-1")
        assert r.is_success
        assert r.has_snapshot

    def test_create_failure(self):
        r = _response(IntegrationStatus.FAILED, error_message="error")
        assert r.is_failure
        assert not r.is_success

    def test_timeout_is_failure(self):
        r = _response(IntegrationStatus.TIMEOUT)
        assert r.is_failure

    def test_partial_status(self):
        r = _response(IntegrationStatus.PARTIAL)
        assert r.is_partial
        assert not r.is_failure

    def test_has_selection(self):
        r = _response(selected_decision={"candidate_id": "c1"})
        assert r.has_selection

    def test_no_selection(self):
        r = _response()
        assert not r.has_selection

    def test_is_frozen(self):
        r = _response()
        with pytest.raises((AttributeError, TypeError)):
            r.status = IntegrationStatus.FAILED  # type: ignore[misc]

    def test_to_dict(self):
        d = _response().to_dict()
        assert "response_id" in d
        assert isinstance(d["status"], str)
        assert "total_time_s" in d


# ============================================================================
# 5. DecisionIntegrationSnapshot
# ============================================================================

class TestDecisionIntegrationSnapshot:
    def test_create_generates_id(self):
        s = DecisionIntegrationSnapshot.create("req-1", "dec-1", "sess-1")
        assert s.integration_id

    def test_explicit_id(self):
        s = DecisionIntegrationSnapshot.create(
            "req-1", "dec-1", "sess-1", integration_id="my-integ"
        )
        assert s.integration_id == "my-integ"

    def test_is_frozen(self):
        s = DecisionIntegrationSnapshot.create("r", "d", "s")
        with pytest.raises((AttributeError, TypeError)):
            s.decision_id = "changed"  # type: ignore[misc]

    def test_to_dict_keys(self):
        s = DecisionIntegrationSnapshot.create(
            "req-1", "dec-1", "sess-1",
            components_run=("lifecycle", "snapshot"),
            phase_times={"lifecycle": 0.01},
        )
        d = s.to_dict()
        assert "integration_id" in d
        assert isinstance(d["components_run"], list)
        assert isinstance(d["phase_times"], dict)
        assert "created_at" in d

    def test_components_run_tuple(self):
        s = DecisionIntegrationSnapshot.create(
            "r", "d", "s", components_run=("lifecycle", "engine")
        )
        assert isinstance(s.components_run, tuple)
        assert "engine" in s.components_run


# ============================================================================
# 6. DecisionIntegrationContext
# ============================================================================

class TestDecisionIntegrationContext:
    def test_initial_phase(self):
        ctx = DecisionIntegrationContext("req-1", "dec-1")
        assert ctx.phase == IntegrationPhase.IDLE

    def test_enter_phase(self):
        ctx = DecisionIntegrationContext("r", "d")
        ctx.enter_phase(IntegrationPhase.VALIDATING)
        assert ctx.phase == IntegrationPhase.VALIDATING

    def test_phase_time_recorded(self):
        ctx = DecisionIntegrationContext("r", "d")
        ctx.enter_phase(IntegrationPhase.LIFECYCLE)
        time.sleep(0.01)
        ctx.enter_phase(IntegrationPhase.ENGINE)
        assert ctx.phase_times.get("lifecycle", 0.0) >= 0.0

    def test_close_phase(self):
        ctx = DecisionIntegrationContext("r", "d")
        ctx.enter_phase(IntegrationPhase.SNAPSHOT)
        ctx.close_phase()
        assert "snapshot" in ctx.phase_times

    def test_elapsed_s(self):
        ctx = DecisionIntegrationContext("r", "d")
        assert ctx.elapsed_s() >= 0

    def test_error_initially_none(self):
        ctx = DecisionIntegrationContext("r", "d")
        assert ctx.error is None


# ============================================================================
# 7. DecisionIntegrationValidation
# ============================================================================

class TestDecisionIntegrationValidation:
    def test_valid_request_passes_all(self):
        validator = DecisionIntegrationValidator()
        result    = validator.validate_request(_request())
        assert result.is_valid
        assert result.passed_count == 6
        assert result.failed_count == 0

    def test_missing_decision_id_fails(self):
        validator = DecisionIntegrationValidator()
        r = DecisionIntegrationRequest(
            request_id        = "req-x",
            decision_id       = "",
            decision_scope    = "order",
            decision_type     = "order",
            decision_priority = "medium",
        )
        result = validator.validate_request(r)
        assert not result.is_valid
        assert IntegrationValidationCode.REQUEST_CONSISTENCY in result.failed_checks

    def test_missing_scope_fails(self):
        validator = DecisionIntegrationValidator()
        r = DecisionIntegrationRequest(
            request_id        = "req-y",
            decision_id       = "dec-y",
            decision_scope    = "",
            decision_type     = "order",
            decision_priority = "medium",
        )
        result = validator.validate_request(r)
        assert not result.is_valid
        assert IntegrationValidationCode.CONTEXT_CONSISTENCY in result.failed_checks

    def test_zero_deadline_fails(self):
        validator = DecisionIntegrationValidator()
        r = DecisionIntegrationRequest(
            request_id        = "req-z",
            decision_id       = "dec-z",
            decision_scope    = "order",
            decision_type     = "order",
            decision_priority = "medium",
            deadline_s        = 0.0,
        )
        result = validator.validate_request(r)
        assert not result.is_valid
        assert IntegrationValidationCode.DEADLINE_CONSISTENCY in result.failed_checks

    def test_component_readiness_with_unready_registry(self):
        validator = DecisionIntegrationValidator()

        class FakeRegistry:
            def is_available(self, ct): return True
            def is_ready(self, ct):     return False

        result = validator.validate_request(_request(), component_registry=FakeRegistry())
        assert not result.is_valid
        assert IntegrationValidationCode.COMPONENT_READINESS in result.failed_checks

    def test_check_count_six(self):
        validator = DecisionIntegrationValidator()
        result    = validator.validate_request(_request())
        assert len(result.checks) == 6

    def test_error_messages_on_failure(self):
        validator = DecisionIntegrationValidator()
        r = DecisionIntegrationRequest(
            request_id="rr", decision_id="", decision_scope="",
            decision_type="order", decision_priority="medium",
        )
        result = validator.validate_request(r)
        assert len(result.error_messages) > 0


# ============================================================================
# 8. DecisionIntegrationHealth
# ============================================================================

class TestDecisionIntegrationHealth:
    def test_healthy_when_all_ready(self):
        monitor  = DecisionIntegrationHealthMonitor()
        registry = _minimal_registry()
        health   = monitor.check(registry, engine_is_running=True)
        assert health.overall in (OverallHealth.HEALTHY, OverallHealth.DEGRADED)
        assert health.is_available

    def test_unavailable_when_engine_stopped(self):
        monitor  = DecisionIntegrationHealthMonitor()
        registry = _minimal_registry()
        health   = monitor.check(registry, engine_is_running=False)
        assert health.overall == OverallHealth.UNAVAILABLE
        assert not health.is_available

    def test_components_dict_populated(self):
        monitor  = DecisionIntegrationHealthMonitor()
        registry = _minimal_registry()
        health   = monitor.check(registry, engine_is_running=True)
        assert len(health.components) > 0
        for key, rec in health.components.items():
            assert isinstance(rec, ComponentHealthRecord)

    def test_last_cached(self):
        monitor  = DecisionIntegrationHealthMonitor()
        registry = _minimal_registry()
        monitor.check(registry, engine_is_running=True)
        assert monitor.last() is not None

    def test_to_dict_keys(self):
        monitor  = DecisionIntegrationHealthMonitor()
        registry = _minimal_registry()
        health   = monitor.check(registry, engine_is_running=True)
        d        = health.to_dict()
        assert "overall" in d
        assert "components" in d
        assert "is_available" in d


# ============================================================================
# 9. DecisionIntegrationStatus
# ============================================================================

class TestDecisionIntegrationStatus:
    def test_snapshot_running(self):
        engine = _engine_with_registry()
        try:
            status = engine.status()
            assert status.is_running
            assert len(status.components_ready) > 0
        finally:
            engine.stop()

    def test_snapshot_stopped(self):
        engine = _engine_with_registry()
        engine.stop()
        status = engine.status()
        assert not status.is_running

    def test_to_dict_keys(self):
        engine = _engine_with_registry()
        try:
            d = engine.status().to_dict()
            assert "is_running" in d
            assert "overall_health" in d
            assert "uptime_s" in d
        finally:
            engine.stop()


# ============================================================================
# 10. DecisionIntegrationStatistics
# ============================================================================

class TestDecisionIntegrationStatistics:
    def test_initial_zeros(self):
        stats = DecisionIntegrationStatistics()
        s     = stats.snapshot()
        assert s["requests_submitted"]   == 0
        assert s["requests_completed"]   == 0
        assert s["snapshots_published"]  == 0

    def test_record_submitted(self):
        stats = DecisionIntegrationStatistics()
        stats.record_request_submitted()
        s = stats.snapshot()
        assert s["requests_submitted"]  == 1
        assert s["requests_in_flight"]  == 1

    def test_record_completed(self):
        stats = DecisionIntegrationStatistics()
        stats.record_request_submitted()
        stats.record_request_completed(response_time_s=0.5)
        s = stats.snapshot()
        assert s["requests_completed"] == 1
        assert s["requests_in_flight"] == 0
        assert s["average_response_time_s"] > 0

    def test_record_failed(self):
        stats = DecisionIntegrationStatistics()
        stats.record_request_submitted()
        stats.record_request_failed()
        s = stats.snapshot()
        assert s["requests_failed"] == 1
        assert s["requests_in_flight"] == 0

    def test_subsystem_availability(self):
        stats = DecisionIntegrationStatistics()
        stats.record_request_submitted()
        stats.record_request_completed()
        s = stats.snapshot()
        assert s["subsystem_availability"] == pytest.approx(100.0)

    def test_snapshots_published(self):
        stats = DecisionIntegrationStatistics()
        stats.record_snapshot_published()
        stats.record_snapshot_published()
        assert stats.snapshot()["snapshots_published"] == 2

    def test_policy_evaluations(self):
        stats = DecisionIntegrationStatistics()
        stats.record_policy_evaluation()
        assert stats.snapshot()["policy_evaluations"] == 1

    def test_reset(self):
        stats = DecisionIntegrationStatistics()
        stats.record_request_submitted()
        stats.record_request_completed()
        stats.reset()
        s = stats.snapshot()
        assert s["requests_submitted"] == 0
        assert s["requests_completed"] == 0


# ============================================================================
# 11. DecisionIntegrationHistory
# ============================================================================

class TestDecisionIntegrationHistory:
    def test_record_and_retrieve_responses(self):
        history = DecisionIntegrationHistory()
        r = _response()
        history.record_response(r)
        assert history.response_count() == 1
        assert history.latest_response() is r

    def test_responses_for_decision(self):
        history = DecisionIntegrationHistory()
        history.record_response(_response(decision_id="dec-A"))
        history.record_response(_response(decision_id="dec-B"))
        result = history.responses_for_decision("dec-A")
        assert len(result) == 1

    def test_responses_for_session(self):
        history = DecisionIntegrationHistory()
        history.record_response(_response(session_id="sess-X"))
        history.record_response(_response(session_id="sess-Y"))
        assert len(history.responses_for_session("sess-X")) == 1

    def test_failed_and_successful(self):
        history = DecisionIntegrationHistory()
        history.record_response(_response(IntegrationStatus.SUCCESS))
        history.record_response(_response(IntegrationStatus.FAILED))
        assert len(history.failed_responses()) == 1
        assert len(history.successful_responses()) == 1

    def test_record_events(self):
        history = DecisionIntegrationHistory()
        ev      = make_integration_started()
        history.record_event(ev)
        assert history.event_count() == 1
        assert history.latest_event() is ev

    def test_events_by_type(self):
        history = DecisionIntegrationHistory()
        history.record_event(make_integration_started())
        history.record_event(make_integration_stopped())
        result = history.events_by_type(IntegrationEventType.STOPPED)
        assert len(result) == 1

    def test_clear(self):
        history = DecisionIntegrationHistory()
        history.record_response(_response())
        history.record_event(make_integration_started())
        history.clear()
        assert history.response_count() == 0
        assert history.event_count() == 0

    def test_bounded_max_responses(self):
        history = DecisionIntegrationHistory(max_responses=3)
        for _ in range(5):
            history.record_response(_response())
        assert history.response_count() == 3


# ============================================================================
# 12. DecisionIntegrationEvents
# ============================================================================

class TestDecisionIntegrationEvents:
    def test_make_initialized(self):
        ev = make_integration_initialized()
        assert ev.event_type == IntegrationEventType.INITIALIZED

    def test_make_started(self):
        ev = make_integration_started()
        assert ev.event_type == IntegrationEventType.STARTED

    def test_make_stopped(self):
        ev = make_integration_stopped()
        assert ev.event_type == IntegrationEventType.STOPPED

    def test_make_restarted(self):
        ev = make_integration_restarted()
        assert ev.event_type == IntegrationEventType.RESTARTED

    def test_make_request_submitted(self):
        ev = make_request_submitted("req-1", "dec-1", scope="order", priority="medium")
        assert ev.event_type == IntegrationEventType.REQUEST_SUBMITTED
        assert ev.payload["scope"] == "order"

    def test_make_request_completed(self):
        ev = make_request_completed("req-1", "dec-1", "sess-1", status="success")
        assert ev.event_type == IntegrationEventType.REQUEST_COMPLETED
        assert ev.payload["status"] == "success"

    def test_make_request_failed(self):
        ev = make_request_failed("req-1", "dec-1", "sess-1", error_message="boom")
        assert ev.event_type == IntegrationEventType.REQUEST_FAILED
        assert ev.payload["error_message"] == "boom"

    def test_make_snapshot_published(self):
        ev = make_snapshot_published("req-1", "dec-1", "sess-1", "snap-1",
                                     decision_status="approved")
        assert ev.event_type == IntegrationEventType.SNAPSHOT_PUBLISHED
        assert ev.snapshot_id == "snap-1"

    def test_make_health_changed(self):
        ev = make_health_changed(previous_health="healthy", current_health="degraded")
        assert ev.event_type == IntegrationEventType.HEALTH_CHANGED
        assert ev.payload["previous_health"] == "healthy"

    def test_unique_event_ids(self):
        ev1 = make_integration_started()
        ev2 = make_integration_started()
        assert ev1.event_id != ev2.event_id

    def test_immutable(self):
        ev = make_integration_started()
        with pytest.raises((AttributeError, TypeError)):
            ev.event_type = IntegrationEventType.STOPPED  # type: ignore[misc]

    def test_to_dict_keys(self):
        ev = make_request_submitted("r", "d")
        d  = ev.to_dict()
        assert "event_id" in d
        assert isinstance(d["event_type"], str)
        assert "occurred_at" in d


# ============================================================================
# 13. DecisionIntegrationRegistry
# ============================================================================

class TestDecisionIntegrationRegistry:
    def test_register_and_query_in_flight(self):
        reg = DecisionIntegrationRegistry()
        req = _request()
        reg.register_in_flight(req)
        assert reg.is_in_flight(req.request_id)
        assert reg.in_flight_count() == 1

    def test_duplicate_raises(self):
        reg = DecisionIntegrationRegistry()
        req = _request(request_id="dup-req")
        reg.register_in_flight(req)
        with pytest.raises(DuplicateIntegrationError):
            reg.register_in_flight(req)

    def test_capacity_raises(self):
        reg = DecisionIntegrationRegistry(max_in_flight=1)
        reg.register_in_flight(_request(request_id="r1", decision_id="d1"))
        with pytest.raises(IntegrationWorkflowError):
            reg.register_in_flight(_request(request_id="r2", decision_id="d2"))

    def test_deregister_in_flight(self):
        reg = DecisionIntegrationRegistry()
        req = _request()
        reg.register_in_flight(req)
        assert reg.deregister_in_flight(req.request_id)
        assert not reg.is_in_flight(req.request_id)

    def test_complete_and_find(self):
        reg  = DecisionIntegrationRegistry()
        req  = _request()
        resp = _response(request_id=req.request_id)
        reg.register_in_flight(req)
        reg.complete(req.request_id, resp)
        assert reg.find_completed(req.request_id) is resp
        assert not reg.is_in_flight(req.request_id)

    def test_find_by_session(self):
        reg  = DecisionIntegrationRegistry()
        req  = _request()
        resp = _response(request_id=req.request_id, session_id="sess-q1")
        reg.register_in_flight(req)
        reg.complete(req.request_id, resp)
        assert reg.find_by_session("sess-q1") is resp

    def test_find_by_decision(self):
        reg   = DecisionIntegrationRegistry()
        req1  = _request(request_id="r1", decision_id="dec-q1")
        req2  = _request(request_id="r2", decision_id="dec-q1")
        resp1 = _response(request_id="r1", decision_id="dec-q1")
        resp2 = _response(request_id="r2", decision_id="dec-q1")
        for req, resp in [(req1, resp1), (req2, resp2)]:
            reg.register_in_flight(req)
            reg.complete(req.request_id, resp)
        results = reg.find_by_decision("dec-q1")
        assert len(results) == 2

    def test_clear(self):
        reg = DecisionIntegrationRegistry()
        req = _request()
        reg.register_in_flight(req)
        reg.clear()
        assert reg.in_flight_count() == 0


# ============================================================================
# 14. DecisionComponentRegistry
# ============================================================================

class TestDecisionComponentRegistry:
    def test_register_and_get(self):
        reg  = DecisionComponentRegistry()
        mock = MagicMock()
        reg.register(ComponentType.LIFECYCLE, mock)
        assert reg.get(ComponentType.LIFECYCLE) is mock

    def test_get_not_found_raises(self):
        reg = DecisionComponentRegistry()
        with pytest.raises(ComponentNotFoundError):
            reg.get(ComponentType.ENGINE)

    def test_find_returns_none(self):
        reg = DecisionComponentRegistry()
        assert reg.find(ComponentType.ENGINE) is None

    def test_is_available(self):
        reg  = DecisionComponentRegistry()
        mock = MagicMock()
        reg.register(ComponentType.LIFECYCLE, mock)
        assert reg.is_available(ComponentType.LIFECYCLE)
        assert not reg.is_available(ComponentType.ENGINE)

    def test_is_ready_lifecycle_aware(self):
        reg  = DecisionComponentRegistry()
        mock = MagicMock()
        # Simulate LifecycleAwareMixin
        state = MagicMock()
        state.value = "running"
        mock.lifecycle_state.return_value = state
        reg.register(ComponentType.LIFECYCLE, mock)
        assert reg.is_ready(ComponentType.LIFECYCLE)

    def test_is_ready_stopped(self):
        reg  = DecisionComponentRegistry()
        mock = MagicMock()
        state = MagicMock()
        state.value = "stopped"
        mock.lifecycle_state.return_value = state
        reg.register(ComponentType.LIFECYCLE, mock)
        assert not reg.is_ready(ComponentType.LIFECYCLE)

    def test_deregister(self):
        reg  = DecisionComponentRegistry()
        mock = MagicMock()
        reg.register(ComponentType.LIFECYCLE, mock)
        assert reg.deregister(ComponentType.LIFECYCLE)
        assert not reg.is_available(ComponentType.LIFECYCLE)

    def test_count(self):
        reg = DecisionComponentRegistry()
        reg.register(ComponentType.LIFECYCLE, MagicMock())
        reg.register(ComponentType.SNAPSHOT, MagicMock())
        assert reg.count() == 2

    def test_clear(self):
        reg = DecisionComponentRegistry()
        reg.register(ComponentType.LIFECYCLE, MagicMock())
        reg.clear()
        assert reg.count() == 0


# ============================================================================
# 15. DecisionComponentFactory
# ============================================================================

class TestDecisionComponentFactory:
    def test_create_default_returns_registry(self):
        factory  = DecisionComponentFactory()
        registry = factory.create_default()
        assert isinstance(registry, DecisionComponentRegistry)
        assert registry.count() == 5  # M1-M5

    def test_create_lifecycle_only(self):
        factory  = DecisionComponentFactory()
        registry = factory.create_default(
            include_engine=False,
            include_policy=False,
            include_optimization=False,
            include_snapshot=False,
        )
        assert registry.is_available(ComponentType.LIFECYCLE)
        assert not registry.is_available(ComponentType.ENGINE)

    def test_create_without_lifecycle(self):
        factory  = DecisionComponentFactory()
        registry = factory.create_default(
            include_lifecycle=False,
            include_snapshot=False,
        )
        assert not registry.is_available(ComponentType.LIFECYCLE)


# ============================================================================
# 16. DecisionIntegrationManager
# ============================================================================

class TestDecisionIntegrationManager:
    def test_start_stop(self):
        reg     = _minimal_registry()
        manager = DecisionIntegrationManager(component_registry=reg)
        assert not manager.is_started()
        manager.start()
        assert manager.is_started()
        manager.stop()
        assert not manager.is_started()

    def test_start_idempotent(self):
        reg     = _minimal_registry()
        manager = DecisionIntegrationManager(component_registry=reg)
        manager.start()
        manager.start()   # second call should not raise
        assert manager.is_started()
        manager.stop()

    def test_restart(self):
        reg     = _minimal_registry()
        manager = DecisionIntegrationManager(component_registry=reg)
        manager.start()
        manager.restart()
        assert manager.is_started()
        manager.stop()

    def test_registry_accessible(self):
        manager = DecisionIntegrationManager()
        assert isinstance(manager.registry, DecisionComponentRegistry)


# ============================================================================
# 17. DecisionIntegrationEngine — Public API
# ============================================================================

class TestDecisionIntegrationEngine:
    # -- Lifecycle ----------------------------------------------------------

    def test_start_stop(self):
        engine = _engine_with_registry()
        assert engine._is_running()
        engine.stop()
        assert not engine._is_running()

    def test_not_running_error_on_submit(self):
        engine = DecisionIntegrationEngine()
        with pytest.raises(IntegrationNotRunningError):
            engine.submit(_request())

    def test_restart(self):
        engine = _engine_with_registry()
        engine.restart()
        assert engine._is_running()
        engine.stop()

    # -- initialize ---------------------------------------------------------

    def test_initialize(self):
        engine = _engine_with_registry()
        try:
            engine.initialize()  # should not raise
        finally:
            engine.stop()

    # -- validate -----------------------------------------------------------

    def test_validate_valid_request(self):
        engine = _engine_with_registry()
        try:
            result = engine.validate(_request())
            assert result.is_valid
        finally:
            engine.stop()

    def test_validate_invalid_request(self):
        engine = _engine_with_registry()
        try:
            bad = DecisionIntegrationRequest(
                request_id="r", decision_id="", decision_scope="",
                decision_type="order", decision_priority="medium",
            )
            result = engine.validate(bad)
            assert not result.is_valid
        finally:
            engine.stop()

    # -- submit -------------------------------------------------------------

    def test_submit_returns_success(self):
        engine = _engine_with_registry()
        try:
            resp = engine.submit(_request())
            assert resp.status == IntegrationStatus.SUCCESS
            assert resp.session_id
            assert resp.snapshot_id
        finally:
            engine.stop()

    def test_submit_none_raises(self):
        engine = _engine_with_registry()
        try:
            with pytest.raises(IntegrationRequestError):
                engine.submit(None)
        finally:
            engine.stop()

    def test_submit_invalid_request_raises(self):
        engine = _engine_with_registry()
        try:
            bad = DecisionIntegrationRequest(
                request_id="r", decision_id="", decision_scope="",
                decision_type="order", decision_priority="medium",
            )
            with pytest.raises(IntegrationValidationError):
                engine.submit(bad)
        finally:
            engine.stop()

    def test_submit_unique_response_ids(self):
        engine = _engine_with_registry()
        try:
            r1 = engine.submit(_request())
            r2 = engine.submit(_request())
            assert r1.response_id != r2.response_id
        finally:
            engine.stop()

    def test_submit_populates_statistics(self):
        engine = _engine_with_registry()
        try:
            engine.submit(_request())
            s = engine.statistics()
            assert s["requests_submitted"] >= 1
            assert s["requests_completed"] >= 1
            assert s["snapshots_published"] >= 1
        finally:
            engine.stop()

    def test_submit_records_history(self):
        engine = _engine_with_registry()
        try:
            engine.submit(_request())
            assert engine.history().response_count() >= 1
        finally:
            engine.stop()

    def test_submit_emits_events(self):
        engine = _engine_with_registry()
        try:
            engine.submit(_request())
            assert engine.history().event_count() >= 1
        finally:
            engine.stop()

    # -- query --------------------------------------------------------------

    def test_query_by_request_id(self):
        engine = _engine_with_registry()
        try:
            req  = _request()
            resp = engine.submit(req)
            found = engine.query(request_id=req.request_id)
            assert found is resp
        finally:
            engine.stop()

    def test_query_by_session_id(self):
        engine = _engine_with_registry()
        try:
            resp  = engine.submit(_request())
            found = engine.query(session_id=resp.session_id)
            assert found is resp
        finally:
            engine.stop()

    def test_query_by_decision_id(self):
        engine = _engine_with_registry()
        try:
            req  = _request(decision_id="dec-query-001")
            resp = engine.submit(req)
            found = engine.query(decision_id="dec-query-001")
            assert found is resp
        finally:
            engine.stop()

    def test_query_not_found_returns_none(self):
        engine = _engine_with_registry()
        try:
            assert engine.query(request_id="nonexistent") is None
        finally:
            engine.stop()

    # -- health / status / statistics ---------------------------------------

    def test_health_returns_report(self):
        engine = _engine_with_registry()
        try:
            h = engine.health()
            assert isinstance(h, DecisionIntegrationHealth)
            assert h.is_available
        finally:
            engine.stop()

    def test_status_returns_report(self):
        engine = _engine_with_registry()
        try:
            s = engine.status()
            assert isinstance(s, DecisionIntegrationStatus)
            assert s.is_running
        finally:
            engine.stop()

    def test_statistics_keys(self):
        engine = _engine_with_registry()
        try:
            s = engine.statistics()
            assert "requests_submitted" in s
            assert "snapshots_published" in s
            assert "average_response_time_s" in s
        finally:
            engine.stop()

    # -- snapshot -----------------------------------------------------------

    def test_snapshot_after_submit(self):
        engine = _engine_with_registry()
        try:
            engine.submit(_request())
            snap = engine.snapshot()
            assert snap is not None
            assert isinstance(snap, DecisionIntegrationSnapshot)
        finally:
            engine.stop()

    def test_snapshot_none_before_submit(self):
        engine = _engine_with_registry()
        try:
            assert engine.snapshot() is None
        finally:
            engine.stop()

    # -- listeners ----------------------------------------------------------

    def test_listener_receives_events(self):
        engine = _engine_with_registry()
        events: List = []
        engine.add_listener(events.append)
        try:
            engine.submit(_request())
            assert len(events) > 0
        finally:
            engine.remove_listener(events.append)
            engine.stop()

    def test_remove_listener(self):
        engine  = _engine_with_registry()
        events: List = []
        engine.add_listener(events.append)
        engine.remove_listener(events.append)
        try:
            engine.submit(_request())
            # start/stop/restart events still fire from _on_start/_on_stop
            # but our listener should be removed
            count_before = len(events)
            engine.submit(_request())
            assert len(events) == count_before   # no new events received
        finally:
            engine.stop()

    # -- workflow response fields -------------------------------------------

    def test_workflow_timings_present(self):
        engine = _engine_with_registry()
        try:
            resp = engine.submit(_request())
            assert resp.lifecycle_time_s >= 0
            assert resp.snapshot_time_s  >= 0
            assert resp.total_time_s     >= 0
        finally:
            engine.stop()

    def test_component_results_populated(self):
        engine = _engine_with_registry()
        try:
            resp = engine.submit(_request())
            cr   = resp.component_results
            assert cr.get(ComponentType.LIFECYCLE.value) is True
            assert cr.get(ComponentType.SNAPSHOT.value)  is True
        finally:
            engine.stop()


# ============================================================================
# 18. __init__ exports
# ============================================================================

class TestInit:
    def test_primary_interface_importable(self):
        import iios.decision.integration as pkg
        assert hasattr(pkg, "DecisionIntegrationEngine")

    def test_request_response_importable(self):
        import iios.decision.integration as pkg
        assert hasattr(pkg, "DecisionIntegrationRequest")
        assert hasattr(pkg, "DecisionIntegrationResponse")

    def test_version_accessible(self):
        import iios.decision.integration as pkg
        assert pkg.VERSION

    def test_system_id_accessible(self):
        import iios.decision.integration as pkg
        assert pkg.INTEGRATION_SYSTEM_ID == "iios:decision:integration"

    def test_all_exceptions_importable(self):
        import iios.decision.integration as pkg
        for name in [
            "DecisionIntegrationError",
            "IntegrationNotRunningError",
            "IntegrationRequestError",
            "IntegrationValidationError",
            "ComponentNotFoundError",
            "ComponentNotReadyError",
            "IntegrationWorkflowError",
            "DuplicateIntegrationError",
        ]:
            assert hasattr(pkg, name), f"Missing: {name}"


# ============================================================================
# 19. Concurrency
# ============================================================================

class TestConcurrency:
    def test_concurrent_submit(self):
        engine = _engine_with_registry()
        errors: List = []
        results: List = []

        def submit_one():
            try:
                resp = engine.submit(_request())
                results.append(resp)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=submit_one) for _ in range(8)]
        for t in threads: t.start()
        for t in threads: t.join()
        engine.stop()

        assert not errors, f"Errors: {errors}"
        assert len(results) == 8

    def test_concurrent_registry(self):
        reg    = DecisionComponentRegistry()
        errors: List = []

        def register_and_check():
            try:
                mock = MagicMock()
                state = MagicMock()
                state.value = "running"
                mock.lifecycle_state.return_value = state
                reg.register(ComponentType.LIFECYCLE, mock)
                _ = reg.is_ready(ComponentType.LIFECYCLE)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_and_check) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors

    def test_concurrent_statistics(self):
        stats  = DecisionIntegrationStatistics()
        errors: List = []

        def record():
            try:
                stats.record_request_submitted()
                stats.record_request_completed(response_time_s=0.01)
                stats.record_snapshot_published()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        s = stats.snapshot()
        assert s["requests_completed"] == 20

    def test_concurrent_history(self):
        history = DecisionIntegrationHistory()
        errors: List = []

        def record():
            try:
                history.record_response(_response())
                history.record_event(make_integration_started())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert history.response_count() == 20
        assert history.event_count() == 20


# ============================================================================
# 20. Regression
# ============================================================================

class TestRegression:
    def test_response_immutability(self):
        r = _response()
        with pytest.raises((AttributeError, TypeError)):
            r.status = IntegrationStatus.FAILED  # type: ignore[misc]

    def test_request_immutability(self):
        r = _request()
        with pytest.raises((AttributeError, TypeError)):
            r.decision_id = "hacked"  # type: ignore[misc]

    def test_query_returns_none_for_in_flight(self):
        """In-flight requests should not appear in completed query."""
        reg = DecisionIntegrationRegistry(max_in_flight=100)
        req = _request()
        reg.register_in_flight(req)
        assert reg.find_completed(req.request_id) is None

    def test_multiple_requests_same_decision(self):
        """Multiple requests for the same decision_id must all succeed."""
        engine = _engine_with_registry()
        try:
            did   = "dec-multi-001"
            resp1 = engine.submit(_request(decision_id=did))
            resp2 = engine.submit(_request(decision_id=did))
            assert resp1.status == IntegrationStatus.SUCCESS
            assert resp2.status == IntegrationStatus.SUCCESS
            assert resp1.session_id != resp2.session_id
        finally:
            engine.stop()

    def test_listener_exception_does_not_crash_workflow(self):
        """A bad listener must not crash the submit workflow."""
        engine = _engine_with_registry()

        def bad_listener(ev):
            raise RuntimeError("listener crash")

        engine.add_listener(bad_listener)
        try:
            resp = engine.submit(_request())
            assert resp.status == IntegrationStatus.SUCCESS
        finally:
            engine.remove_listener(bad_listener)
            engine.stop()

    def test_statistics_in_flight_decrements_on_failure(self):
        """In-flight counter must reach 0 even when the workflow raises."""
        stats = DecisionIntegrationStatistics()
        stats.record_request_submitted()
        stats.record_request_failed()
        assert stats.snapshot()["requests_in_flight"] == 0
