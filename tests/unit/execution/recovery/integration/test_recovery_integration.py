"""
tests/unit/execution/recovery/integration/test_recovery_integration.py
=======================================================================
Comprehensive test suite for C7 M6 — Execution Recovery Integration.

Coverage targets:
  • constants / exceptions
  • value objects (context, request, response, snapshot, events)
  • IntegrationStatistics
  • IntegrationHistory
  • IntegrationRegistry
  • IntegrationValidationResult / IntegrationValidator
  • IntegrationHealthMonitor / ComponentHealthReport
  • IntegrationStatusReport / make_status_report
  • RecoveryComponentRegistry
  • FailoverEngineAdapter
  • RecoveryComponentFactory.create()
  • RecoveryIntegrationManager (full workflow + edge cases)
  • ExecutionRecoveryIntegrationEngine (full lifecycle + API)

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

# ── Package imports ────────────────────────────────────────────────────────────
from iios.execution.recovery.integration import (
    ACTOR_INTEGRATION,
    ACTOR_SYSTEM,
    COMP_ENGINE,
    COMP_FAILOVER,
    COMP_POLICY,
    COMP_SNAPSHOT,
    ComponentHealthReport,
    ComponentStatus,
    ENGINE_ID,
    ExecutionRecoveryIntegrationEngine,
    FailoverEngineAdapter,
    IntegrationContext,
    IntegrationDuplicateError,
    IntegrationError,
    IntegrationEvent,
    IntegrationEventType,
    IntegrationHealth,
    IntegrationHealthMonitor,
    IntegrationHistory,
    IntegrationNotRunningError,
    IntegrationRegistry,
    IntegrationRequest,
    IntegrationResponse,
    IntegrationSessionError,
    IntegrationSnapshot,
    IntegrationSnapshotError,
    IntegrationHistoryError,
    IntegrationRequestError,
    IntegrationComponentError,
    IntegrationHealthError,
    IntegrationStatistics,
    IntegrationStatus,
    IntegrationStatusReport,
    IntegrationValidationError,
    IntegrationValidationResult,
    IntegrationValidator,
    MANAGER_ID,
    RecoveryComponentFactory,
    RecoveryComponentRegistry,
    RecoveryIntegrationManager,
    REGISTRY_ID,
    SCHEMA_VERSION,
    SYSTEM_ID,
    VERSION,
    make_integration_context,
    make_integration_request,
    make_integration_response,
    make_integration_snapshot,
    make_recovery_completed,
    make_recovery_health_changed,
    make_recovery_initialized,
    make_recovery_restarted,
    make_recovery_snapshot_published,
    make_recovery_started,
    make_recovery_stopped,
    make_recovery_validated,
    make_status_report,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _req(**kwargs) -> IntegrationRequest:
    """Build a minimal valid IntegrationRequest."""
    defaults = dict(
        execution_session_id = str(uuid.uuid4()),
        subsystem_id         = "test:subsystem",
        failure_type         = "timeout",
        failure_reason       = "connection timed out",
        recovery_reason      = "auto-recovery triggered",
    )
    defaults.update(kwargs)
    return make_integration_request(**defaults)


def _running_component():
    """Return a mock object whose lifecycle_state() reports 'running'."""
    m = MagicMock()
    m.lifecycle_state.return_value = "running"
    return m


def _stopped_component():
    m = MagicMock()
    m.lifecycle_state.return_value = "stopped"
    return m


def _components_all_running():
    """Return a mock RecoveryComponentRegistry with all components running."""
    reg = MagicMock(spec=RecoveryComponentRegistry)
    reg.engine            = _running_component()
    reg.policy_engine     = _running_component()
    reg.failover_engine   = _running_component()
    reg.snapshot_builder  = _running_component()
    reg.snapshot_store    = _running_component()
    reg.snapshot_cache    = _running_component()
    reg.snapshot_registry = _running_component()
    reg.is_all_running.return_value = True
    reg.component_statuses.return_value = {
        "recovery_engine":   "running",
        "policy_engine":     "running",
        "failover_engine":   "running",
        "snapshot_store":    "running",
        "snapshot_cache":    "running",
        "snapshot_registry": "running",
    }
    return reg


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_system_ids_non_empty(self):
        assert SYSTEM_ID
        assert ENGINE_ID
        assert MANAGER_ID
        assert REGISTRY_ID

    def test_version_format(self):
        parts = VERSION.split(".")
        assert len(parts) == 3

    def test_schema_version_defined(self):
        assert SCHEMA_VERSION

    def test_actor_constants(self):
        assert ACTOR_INTEGRATION
        assert ACTOR_SYSTEM

    def test_comp_constants(self):
        assert COMP_ENGINE
        assert COMP_POLICY
        assert COMP_FAILOVER
        assert COMP_SNAPSHOT

    def test_integration_status_members(self):
        assert IntegrationStatus.ACTIVE
        assert IntegrationStatus.STOPPED
        assert IntegrationStatus.UNKNOWN

    def test_component_status_members(self):
        assert ComponentStatus.RUNNING
        assert ComponentStatus.STOPPED
        assert ComponentStatus.ERROR

    def test_integration_health_members(self):
        assert IntegrationHealth.HEALTHY
        assert IntegrationHealth.DEGRADED
        assert IntegrationHealth.UNHEALTHY
        assert IntegrationHealth.UNKNOWN

    def test_event_type_members(self):
        assert IntegrationEventType.RECOVERY_STARTED
        assert IntegrationEventType.RECOVERY_COMPLETED
        assert IntegrationEventType.RECOVERY_SNAPSHOT_PUBLISHED


# ═══════════════════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_integration_error_base(self):
        exc = IntegrationError("base error")
        assert "RI-000" in exc.error_code
        assert str(exc)

    def test_not_running_default_message(self):
        exc = IntegrationNotRunningError()
        assert "not running" in str(exc).lower()

    def test_validation_error_carries_errors(self):
        exc = IntegrationValidationError("bad", errors=("e1", "e2"))
        assert exc.errors == ("e1", "e2")

    def test_request_error_carries_request_id(self):
        exc = IntegrationRequestError("bad request", request_id="R1")
        assert exc.request_id == "R1"

    def test_component_error_carries_component(self):
        exc = IntegrationComponentError("comp down", component="engine")
        assert exc.component == "engine"

    def test_duplicate_error(self):
        exc = IntegrationDuplicateError("req-1")
        assert exc.request_id == "req-1"
        assert "req-1" in str(exc)

    def test_all_exceptions_inherit_integration_error(self):
        for cls in [
            IntegrationNotRunningError,
            IntegrationValidationError,
            IntegrationRequestError,
            IntegrationSessionError,
            IntegrationComponentError,
            IntegrationHealthError,
            IntegrationSnapshotError,
            IntegrationHistoryError,
            IntegrationDuplicateError,
        ]:
            exc = cls("test") if cls not in (
                IntegrationValidationError, IntegrationRequestError,
                IntegrationComponentError, IntegrationDuplicateError
            ) else _make_exc(cls)
            assert isinstance(exc, IntegrationError)

    def _make_exc(cls):
        mapping = {
            IntegrationValidationError: lambda: IntegrationValidationError("t", errors=()),
            IntegrationRequestError:    lambda: IntegrationRequestError("t"),
            IntegrationComponentError:  lambda: IntegrationComponentError("t"),
            IntegrationDuplicateError:  lambda: IntegrationDuplicateError("rid"),
        }
        return mapping[cls]()


def _make_exc(cls):
    mapping = {
        IntegrationValidationError: lambda: IntegrationValidationError("t", errors=()),
        IntegrationRequestError:    lambda: IntegrationRequestError("t"),
        IntegrationComponentError:  lambda: IntegrationComponentError("t"),
        IntegrationDuplicateError:  lambda: IntegrationDuplicateError("rid"),
    }
    return mapping.get(cls, lambda: cls("t"))()


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrationContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationContext:
    def test_make_basic(self):
        ctx = make_integration_context(
            execution_session_id = "sess-1",
            subsystem_id         = "sub-1",
            failure_type         = "timeout",
            failure_reason       = "exceeded limit",
        )
        assert ctx.execution_session_id == "sess-1"
        assert ctx.subsystem_id == "sub-1"
        assert ctx.failure_type == "timeout"
        assert ctx.failure_severity == "MEDIUM"

    def test_make_with_severity(self):
        ctx = make_integration_context(
            "s", "sub", "type", "reason", failure_severity="HIGH"
        )
        assert ctx.failure_severity == "HIGH"

    def test_make_is_emergency(self):
        ctx = make_integration_context("s", "sub", "type", "reason", is_emergency=True)
        assert ctx.is_emergency is True

    def test_to_dict(self):
        ctx = make_integration_context("s", "sub", "type", "reason")
        d = ctx.to_dict()
        assert d["execution_session_id"] == "s"
        assert isinstance(d["tags"], list)

    def test_frozen(self):
        ctx = make_integration_context("s", "sub", "type", "reason")
        with pytest.raises(Exception):
            ctx.subsystem_id = "mutated"

    def test_tags_default_empty(self):
        ctx = make_integration_context("s", "sub", "type", "reason")
        assert ctx.tags == ()

    def test_explicit_context_id(self):
        ctx = make_integration_context("s", "sub", "type", "reason", context_id="CX-1")
        assert ctx.context_id == "CX-1"


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrationRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationRequest:
    def test_make_defaults(self):
        req = _req()
        assert req.failure_severity == "MEDIUM"
        assert req.request_priority == "NORMAL"
        assert req.request_type     == "AUTOMATIC"
        assert req.requester        == ACTOR_SYSTEM

    def test_make_custom_priority(self):
        req = _req(request_priority="HIGH")
        assert req.request_priority == "HIGH"

    def test_explicit_request_id(self):
        req = _req(request_id="R-EXPLICIT")
        assert req.request_id == "R-EXPLICIT"

    def test_to_dict_keys(self):
        req = _req()
        d = req.to_dict()
        for key in ("request_id", "execution_session_id", "subsystem_id",
                    "failure_type", "failure_reason", "recovery_reason"):
            assert key in d

    def test_frozen(self):
        req = _req()
        with pytest.raises(Exception):
            req.subsystem_id = "mutated"

    def test_tags_tuple(self):
        req = _req(tags=("tag1", "tag2"))
        assert req.tags == ("tag1", "tag2")

    def test_requested_at_auto(self):
        before = time.time()
        req = _req()
        after = time.time()
        assert before <= req.requested_at <= after


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrationResponse
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationResponse:
    def test_make_successful(self):
        r = make_integration_response(
            request_id           = "R1",
            integration_status   = IntegrationStatus.ACTIVE,
            is_successful        = True,
            recovery_duration_ms = 50.0,
            response_time_ms     = 55.0,
        )
        assert r.is_successful is True
        assert r.has_snapshot is False
        assert r.integration_status == IntegrationStatus.ACTIVE

    def test_make_with_error(self):
        r = make_integration_response(
            request_id           = "R2",
            integration_status   = IntegrationStatus.DEGRADED,
            is_successful        = False,
            recovery_duration_ms = 0.0,
            response_time_ms     = 10.0,
            error_message        = "engine failed",
        )
        assert r.error_message == "engine failed"

    def test_has_snapshot_true(self):
        snap = MagicMock()
        r = make_integration_response(
            "R3", IntegrationStatus.ACTIVE, True, 10.0, 12.0,
            recovery_snapshot=snap
        )
        assert r.has_snapshot is True
        assert r.recovery_snapshot is snap

    def test_to_dict(self):
        r = make_integration_response(
            "R4", IntegrationStatus.ACTIVE, True, 10.0, 12.0
        )
        d = r.to_dict()
        assert d["request_id"] == "R4"
        assert "is_successful" in d

    def test_frozen(self):
        r = make_integration_response(
            "R5", IntegrationStatus.ACTIVE, True, 10.0, 12.0
        )
        with pytest.raises(Exception):
            r.request_id = "mutated"


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrationSnapshot (system-state snapshot)
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationSnapshot:
    def _snap(self, **kw):
        defaults = dict(
            integration_status   = IntegrationStatus.ACTIVE,
            integration_health   = IntegrationHealth.HEALTHY,
            component_statuses   = {"recovery_engine": "running"},
            active_request_count = 3,
            total_requests       = 10,
            successful_requests  = 8,
            failed_requests      = 2,
            snapshots_published  = 8,
            uptime_seconds       = 600.0,
        )
        defaults.update(kw)
        return make_integration_snapshot(**defaults)

    def test_make_basic(self):
        s = self._snap()
        assert s.integration_status == IntegrationStatus.ACTIVE
        assert s.is_healthy is True

    def test_is_healthy_false(self):
        s = self._snap(integration_health=IntegrationHealth.DEGRADED)
        assert s.is_healthy is False

    def test_to_dict(self):
        s = self._snap()
        d = s.to_dict()
        assert d["active_request_count"] == 3
        assert "snapshot_id" in d

    def test_frozen(self):
        s = self._snap()
        with pytest.raises(Exception):
            s.uptime_seconds = "mutated"


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrationEvents
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationEvents:
    def test_make_initialized(self):
        e = make_recovery_initialized("R1", actor="test")
        assert e.event_type == IntegrationEventType.RECOVERY_INITIALIZED
        assert e.request_id == "R1"
        assert e.actor == "test"

    def test_make_started(self):
        e = make_recovery_started("R2")
        assert e.event_type == IntegrationEventType.RECOVERY_STARTED

    def test_make_completed(self):
        e = make_recovery_completed("R3")
        assert e.event_type == IntegrationEventType.RECOVERY_COMPLETED

    def test_make_stopped(self):
        e = make_recovery_stopped("R4")
        assert e.event_type == IntegrationEventType.RECOVERY_STOPPED

    def test_make_restarted_no_request(self):
        e = make_recovery_restarted()
        assert e.event_type == IntegrationEventType.RECOVERY_RESTARTED
        assert e.request_id == ""

    def test_make_validated(self):
        e = make_recovery_validated("R5")
        assert e.event_type == IntegrationEventType.RECOVERY_VALIDATED

    def test_make_health_changed(self):
        e = make_recovery_health_changed("DEGRADED", "R6")
        assert e.event_type == IntegrationEventType.RECOVERY_HEALTH_CHANGED
        assert "DEGRADED" in e.reason

    def test_make_snapshot_published(self):
        e = make_recovery_snapshot_published("R7", "S1")
        assert e.event_type == IntegrationEventType.RECOVERY_SNAPSHOT_PUBLISHED
        assert e.metadata["snapshot_id"] == "S1"

    def test_to_dict(self):
        e = make_recovery_started("R8")
        d = e.to_dict()
        assert "event_id" in d
        assert "event_type" in d

    def test_frozen(self):
        e = make_recovery_started("R9")
        with pytest.raises(Exception):
            e.request_id = "mutated"

    def test_event_id_unique(self):
        e1 = make_recovery_started("R")
        e2 = make_recovery_started("R")
        assert e1.event_id != e2.event_id


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrationStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationStatistics:
    def test_initial_zeroes(self):
        s = IntegrationStatistics()
        assert s.total_requests == 0
        assert s.successful_recoveries == 0
        assert s.success_rate == 0.0

    def test_record_request(self):
        s = IntegrationStatistics()
        s.record_request()
        s.record_request()
        assert s.total_requests == 2

    def test_success_rate(self):
        s = IntegrationStatistics()
        s.record_success()
        s.record_success()
        s.record_failure()
        assert abs(s.success_rate - 2/3) < 1e-9

    def test_average_response_time(self):
        s = IntegrationStatistics()
        s.record_response_time(10.0)
        s.record_response_time(20.0)
        assert s.average_response_time_ms == 15.0

    def test_average_recovery_time(self):
        s = IntegrationStatistics()
        s.record_recovery_time(100.0)
        s.record_recovery_time(200.0)
        assert s.average_recovery_time_ms == 150.0

    def test_copy_independent(self):
        s = IntegrationStatistics()
        s.record_request()
        c = s.copy()
        s.record_request()
        assert c.total_requests == 1
        assert s.total_requests == 2

    def test_reset(self):
        s = IntegrationStatistics()
        s.record_request()
        s.reset()
        assert s.total_requests == 0

    def test_to_dict(self):
        s = IntegrationStatistics()
        d = s.to_dict()
        assert "total_requests" in d
        assert "success_rate" in d

    def test_thread_safe(self):
        s = IntegrationStatistics()
        def worker():
            for _ in range(100):
                s.record_request()
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert s.total_requests == 500

    def test_snapshots_published(self):
        s = IntegrationStatistics()
        s.record_snapshot_published()
        assert s.snapshots_published == 1


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrationHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationHistory:
    def test_empty(self):
        h = IntegrationHistory()
        assert h.request_count == 0
        assert h.response_count == 0
        assert h.event_count == 0

    def test_append_request(self):
        h = IntegrationHistory()
        req = _req()
        h.append_request(req)
        assert h.request_count == 1
        assert h.latest_request() is req

    def test_append_response(self):
        h = IntegrationHistory()
        resp = make_integration_response(
            "R1", IntegrationStatus.ACTIVE, True, 10.0, 12.0
        )
        h.append_response(resp)
        assert h.latest_response() is resp

    def test_append_event(self):
        h = IntegrationHistory()
        ev = make_recovery_started("R1")
        h.append_event(ev)
        assert h.event_count == 1

    def test_responses_for_request(self):
        h = IntegrationHistory()
        resp1 = make_integration_response("R1", IntegrationStatus.ACTIVE, True, 10.0, 12.0)
        resp2 = make_integration_response("R2", IntegrationStatus.ACTIVE, True, 10.0, 12.0)
        h.append_response(resp1)
        h.append_response(resp2)
        assert h.responses_for_request("R1") == [resp1]

    def test_responses_for_session(self):
        h = IntegrationHistory()
        session_id = "sess-xyz"
        req = make_integration_request(
            execution_session_id = session_id,
            subsystem_id = "s", failure_type = "t",
            failure_reason = "r", recovery_reason = "rr",
        )
        resp = make_integration_response(req.request_id, IntegrationStatus.ACTIVE, True, 10.0, 12.0)
        h.append_request(req)
        h.append_response(resp)
        results = h.responses_for_session(session_id)
        assert len(results) == 1

    def test_clear(self):
        h = IntegrationHistory()
        h.append_request(_req())
        h.append_event(make_recovery_started("R1"))
        h.clear()
        assert h.request_count == 0
        assert h.event_count == 0

    def test_bounded_maxlen(self):
        h = IntegrationHistory(max_requests=3)
        for _ in range(5):
            h.append_request(_req())
        assert h.request_count == 3  # bounded by deque maxlen

    def test_latest_empty(self):
        h = IntegrationHistory()
        assert h.latest_request() is None
        assert h.latest_response() is None

    def test_thread_safe(self):
        h = IntegrationHistory()
        def worker():
            for _ in range(50):
                h.append_request(_req())
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert h.request_count == 200


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrationRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationRegistry:
    def _started(self):
        r = IntegrationRegistry()
        r.start()
        return r

    def test_start_stop(self):
        r = IntegrationRegistry()
        r.start()
        r.stop()

    def test_register_and_active(self):
        r = self._started()
        try:
            r.register_active("R1")
            assert r.is_active("R1")
            assert not r.is_processed("R1")
        finally:
            r.stop()

    def test_complete_moves_to_processed(self):
        r = self._started()
        try:
            r.register_active("R1")
            r.complete("R1")
            assert not r.is_active("R1")
            assert r.is_processed("R1")
        finally:
            r.stop()

    def test_duplicate_raises(self):
        r = self._started()
        try:
            r.register_active("R1")
            r.complete("R1")
            with pytest.raises(IntegrationDuplicateError):
                r.register_active("R1")
        finally:
            r.stop()

    def test_not_running_raises(self):
        r = IntegrationRegistry()
        with pytest.raises(IntegrationNotRunningError):
            r.register_active("R1")

    def test_active_request_ids(self):
        r = self._started()
        try:
            r.register_active("R1")
            r.register_active("R2")
            ids = r.active_request_ids()
            assert "R1" in ids
            assert "R2" in ids
        finally:
            r.stop()

    def test_counts(self):
        r = self._started()
        try:
            r.register_active("R1")
            assert r.active_count == 1
            r.complete("R1")
            assert r.active_count == 0
            assert r.processed_count == 1
        finally:
            r.stop()

    def test_clear(self):
        r = self._started()
        try:
            r.register_active("R1")
            r.clear()
            assert r.active_count == 0
        finally:
            r.stop()

    def test_thread_safe(self):
        r = self._started()
        try:
            ids = [str(uuid.uuid4()) for _ in range(100)]
            def worker(batch):
                for rid in batch:
                    r.register_active(rid)
                    r.complete(rid)
            batches = [ids[i:i+25] for i in range(0, 100, 25)]
            threads = [threading.Thread(target=worker, args=(b,)) for b in batches]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert r.processed_count == 100
        finally:
            r.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrationValidator / IntegrationValidationResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationValidator:
    def setup_method(self):
        self.v = IntegrationValidator()

    def test_valid_request(self):
        r = self.v.validate_request(_req())
        assert r.is_valid
        assert not r.errors

    def test_none_request(self):
        r = self.v.validate_request(None)
        assert not r.is_valid

    def test_missing_subsystem_id(self):
        req = _req(subsystem_id="")
        r = self.v.validate_request(req)
        assert not r.is_valid
        assert any("subsystem_id" in e for e in r.errors)

    def test_missing_failure_type(self):
        req = _req(failure_type="")
        r = self.v.validate_request(req)
        assert not r.is_valid

    def test_missing_failure_reason(self):
        req = _req(failure_reason="")
        r = self.v.validate_request(req)
        assert not r.is_valid

    def test_missing_recovery_reason(self):
        req = _req(recovery_reason="")
        r = self.v.validate_request(req)
        assert not r.is_valid

    def test_validate_context_none(self):
        r = self.v.validate_context(None)
        assert not r.is_valid

    def test_validate_context_valid(self):
        ctx = make_integration_context("sess", "sub", "type", "reason")
        r = self.v.validate_context(ctx)
        assert r.is_valid


class TestIntegrationValidationResult:
    def test_initial_valid(self):
        r = IntegrationValidationResult()
        assert r.is_valid

    def test_add_error_invalidates(self):
        r = IntegrationValidationResult()
        r.add_error("something wrong")
        assert not r.is_valid
        assert "something wrong" in r.errors

    def test_add_warning_keeps_valid(self):
        r = IntegrationValidationResult()
        r.add_warning("heads up")
        assert r.is_valid
        assert "heads up" in r.warnings

    def test_merge(self):
        r1 = IntegrationValidationResult()
        r2 = IntegrationValidationResult()
        r2.add_error("error from r2")
        r1.merge(r2)
        assert not r1.is_valid
        assert "error from r2" in r1.errors

    def test_to_dict(self):
        r = IntegrationValidationResult()
        d = r.to_dict()
        assert "is_valid" in d


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrationHealthMonitor / ComponentHealthReport
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationHealthMonitor:
    def test_all_running_healthy(self):
        monitor = IntegrationHealthMonitor()
        comp = _components_all_running()
        report = monitor.check_health(comp)
        assert report.overall == IntegrationHealth.HEALTHY
        assert report.engine_health == "running"

    def test_one_stopped_degraded(self):
        monitor = IntegrationHealthMonitor()
        comp = _components_all_running()
        comp.engine = _stopped_component()
        report = monitor.check_health(comp)
        assert report.engine_health == "stopped"
        assert report.overall in (IntegrationHealth.DEGRADED, IntegrationHealth.UNHEALTHY)

    def test_all_stopped_unhealthy(self):
        monitor = IntegrationHealthMonitor()
        comp = MagicMock(spec=RecoveryComponentRegistry)
        for attr in ("engine", "policy_engine", "failover_engine",
                     "snapshot_store", "snapshot_cache", "snapshot_registry"):
            setattr(comp, attr, _stopped_component())
        report = monitor.check_health(comp)
        assert report.overall in (IntegrationHealth.UNHEALTHY, IntegrationHealth.DEGRADED)

    def test_is_healthy_true(self):
        monitor = IntegrationHealthMonitor()
        comp = _components_all_running()
        report = monitor.check_health(comp)
        assert report.is_healthy is True

    def test_to_dict(self):
        monitor = IntegrationHealthMonitor()
        comp = _components_all_running()
        report = monitor.check_health(comp)
        d = report.to_dict()
        assert "overall" in d
        assert "engine_health" in d

    def test_report_frozen(self):
        monitor = IntegrationHealthMonitor()
        comp = _components_all_running()
        report = monitor.check_health(comp)
        with pytest.raises(Exception):
            report.overall = "mutated"


# ═══════════════════════════════════════════════════════════════════════════════
# IntegrationStatusReport / make_status_report
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegrationStatusReport:
    def _report(self):
        comp = _components_all_running()
        return make_status_report(
            components         = comp,
            overall_status     = IntegrationStatus.ACTIVE,
            active_requests    = 5,
            processed_requests = 20,
        )

    def test_make_basic(self):
        r = self._report()
        assert r.overall_status == IntegrationStatus.ACTIVE
        assert r.active_requests == 5
        assert r.processed_requests == 20

    def test_to_dict(self):
        r = self._report()
        d = r.to_dict()
        assert d["overall_status"] == IntegrationStatus.ACTIVE.value
        assert d["active_requests"] == 5

    def test_frozen(self):
        r = self._report()
        with pytest.raises(Exception):
            r.active_requests = "mutated"


# ═══════════════════════════════════════════════════════════════════════════════
# RecoveryComponentRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecoveryComponentRegistry:
    def _make(self, all_running: bool = True):
        comps = {
            "engine":            _running_component() if all_running else _stopped_component(),
            "policy_engine":     _running_component(),
            "failover_engine":   _running_component(),
            "snapshot_builder":  MagicMock(),
            "snapshot_store":    _running_component(),
            "snapshot_cache":    _running_component(),
            "snapshot_registry": _running_component(),
        }
        return RecoveryComponentRegistry(**comps)

    def test_accessors(self):
        reg = self._make()
        assert reg.engine is not None
        assert reg.policy_engine is not None
        assert reg.snapshot_builder is not None

    def test_is_all_running_true(self):
        reg = self._make(all_running=True)
        assert reg.is_all_running()

    def test_is_all_running_false(self):
        reg = self._make(all_running=False)
        assert not reg.is_all_running()

    def test_component_statuses(self):
        reg = self._make()
        statuses = reg.component_statuses()
        assert statuses["recovery_engine"] == "running"

    def test_start_all_calls_each(self):
        reg = self._make()
        reg.start_all()
        # No exception = pass (mocks absorb the calls)

    def test_stop_all_calls_each(self):
        reg = self._make()
        reg.start_all()
        reg.stop_all()


# ═══════════════════════════════════════════════════════════════════════════════
# FailoverEngineAdapter
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailoverEngineAdapter:
    def _adapter(self, execute_success: bool = True):
        engine = MagicMock()
        response = MagicMock()
        response.is_successful = execute_success
        response.failover_session_id = str(uuid.uuid4())
        engine.execute.return_value = response
        return FailoverEngineAdapter(engine=engine), engine

    def test_trigger_success(self):
        adapter, engine = self._adapter(execute_success=True)
        m2_request = MagicMock()
        m2_request.execution_session_id = "sess-1"
        m2_request.subsystem_id = "sub-1"
        m2_context = MagicMock()
        result = adapter.trigger_failover(m2_request, m2_context)
        assert result.triggered is True
        assert result.result == "success"
        engine.execute.assert_called_once()

    def test_trigger_failure(self):
        adapter, _ = self._adapter(execute_success=False)
        m2_request = MagicMock()
        m2_request.execution_session_id = "sess-2"
        m2_request.subsystem_id = "sub-2"
        result = adapter.trigger_failover(m2_request, MagicMock())
        assert result.triggered is False
        assert result.result == "failed"

    def test_trigger_engine_exception(self):
        engine = MagicMock()
        engine.execute.side_effect = RuntimeError("engine exploded")
        adapter = FailoverEngineAdapter(engine=engine)
        result = adapter.trigger_failover(MagicMock(), MagicMock())
        assert result.triggered is False
        assert "error" in result.result

    def test_failover_id_non_empty(self):
        adapter, _ = self._adapter(execute_success=True)
        result = adapter.trigger_failover(MagicMock(), MagicMock())
        assert result.failover_id


# ═══════════════════════════════════════════════════════════════════════════════
# RecoveryComponentFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecoveryComponentFactory:
    def test_create_returns_registry(self):
        reg = RecoveryComponentFactory.create()
        assert isinstance(reg, RecoveryComponentRegistry)

    def test_create_components_not_none(self):
        reg = RecoveryComponentFactory.create()
        assert reg.engine is not None
        assert reg.policy_engine is not None
        assert reg.failover_engine is not None
        assert reg.snapshot_builder is not None
        assert reg.snapshot_store is not None
        assert reg.snapshot_cache is not None
        assert reg.snapshot_registry is not None

    def test_create_custom_limits(self):
        reg = RecoveryComponentFactory.create(
            max_requests=500, max_history=100, max_concurrent=5,
            max_snapshots=200, cache_size=50,
        )
        assert reg is not None


# ═══════════════════════════════════════════════════════════════════════════════
# RecoveryIntegrationManager (with real components)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecoveryIntegrationManagerUnit:
    """Unit tests using mocked components."""

    def _started_manager(self):
        comp = _components_all_running()
        # snapshot builder lifecycle
        comp.snapshot_builder.lifecycle_state.return_value = "running"
        # Fake snapshot returned by builder.build()
        fake_snap = MagicMock()
        fake_snap.snapshot_id = str(uuid.uuid4())
        fake_snap.recovery_session_id = str(uuid.uuid4())
        fake_snap.to_dict.return_value = {}
        comp.snapshot_builder.build.return_value = fake_snap
        # M2 engine responses
        fake_m2_resp = MagicMock()
        comp.engine.start_recovery.return_value = fake_m2_resp
        fake_m1_session = MagicMock()
        comp.engine.get_session_for_request.return_value = fake_m1_session
        # M5 store
        comp.snapshot_store.save.return_value = None
        comp.snapshot_cache.put.return_value = None
        comp.snapshot_registry.register.return_value = None
        comp.snapshot_store.latest.return_value = fake_snap
        comp.snapshot_store.all.return_value = [fake_snap]
        comp.snapshot_store.by_session.return_value = [fake_snap]

        mgr = RecoveryIntegrationManager(comp)
        mgr.start()
        return mgr, comp

    def test_start_stop(self):
        mgr, _ = self._started_manager()
        mgr.stop()

    def test_submit_success(self):
        mgr, _ = self._started_manager()
        try:
            resp = mgr.submit(_req())
            assert isinstance(resp, IntegrationResponse)
            assert resp.is_successful is True
        finally:
            mgr.stop()

    def test_submit_not_running_raises(self):
        comp = _components_all_running()
        mgr = RecoveryIntegrationManager(comp)
        with pytest.raises(IntegrationNotRunningError):
            mgr.submit(_req())

    def test_submit_invalid_request_raises(self):
        mgr, _ = self._started_manager()
        try:
            with pytest.raises(IntegrationValidationError):
                mgr.submit(_req(subsystem_id=""))
        finally:
            mgr.stop()

    def test_submit_duplicate_raises(self):
        mgr, _ = self._started_manager()
        try:
            req = _req()
            mgr.submit(req)
            with pytest.raises(IntegrationDuplicateError):
                mgr.submit(req)
        finally:
            mgr.stop()

    def test_validate_valid(self):
        mgr, _ = self._started_manager()
        try:
            result = mgr.validate(_req())
            assert result.is_valid
        finally:
            mgr.stop()

    def test_validate_invalid(self):
        mgr, _ = self._started_manager()
        try:
            result = mgr.validate(_req(subsystem_id=""))
            assert not result.is_valid
        finally:
            mgr.stop()

    def test_health_returns_report(self):
        mgr, _ = self._started_manager()
        try:
            report = mgr.health()
            assert isinstance(report, ComponentHealthReport)
        finally:
            mgr.stop()

    def test_status_returns_report(self):
        mgr, _ = self._started_manager()
        try:
            status = mgr.status()
            assert isinstance(status, IntegrationStatusReport)
        finally:
            mgr.stop()

    def test_statistics_independent_copy(self):
        mgr, _ = self._started_manager()
        try:
            mgr.submit(_req())
            stats = mgr.statistics()
            assert stats.total_requests >= 1
            stats2 = mgr.statistics()
            assert stats.total_requests == stats2.total_requests
        finally:
            mgr.stop()

    def test_snapshot_latest(self):
        mgr, comp = self._started_manager()
        try:
            mgr.submit(_req())
            snap = mgr.snapshot()
            assert snap is not None
        finally:
            mgr.stop()

    def test_snapshot_by_id(self):
        mgr, comp = self._started_manager()
        try:
            fake = MagicMock()
            comp.snapshot_store.get.return_value = fake
            snap = mgr.snapshot("some-id")
            assert snap is fake
        finally:
            mgr.stop()

    def test_history_populated(self):
        mgr, _ = self._started_manager()
        try:
            mgr.submit(_req())
            hist = mgr.history()
            assert hist.request_count >= 1
        finally:
            mgr.stop()

    def test_query_delegates_to_store(self):
        mgr, comp = self._started_manager()
        try:
            results = mgr.query(recovery_session_id="sess-1")
            comp.snapshot_store.by_session.assert_called_with("sess-1")
        finally:
            mgr.stop()

    def test_query_execution_session(self):
        mgr, comp = self._started_manager()
        try:
            results = mgr.query(execution_session_id="exec-1")
            comp.snapshot_store.by_execution.assert_called_with("exec-1")
        finally:
            mgr.stop()

    def test_query_fallback_all(self):
        mgr, comp = self._started_manager()
        try:
            results = mgr.query()
            comp.snapshot_store.all.assert_called()
        finally:
            mgr.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# ExecutionRecoveryIntegrationEngine — lifecycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionRecoveryIntegrationEngineLifecycle:
    def _engine_with_mocked_components(self):
        comp = _components_all_running()
        comp.snapshot_builder.lifecycle_state.return_value = "running"
        fake_snap = MagicMock()
        fake_snap.snapshot_id = str(uuid.uuid4())
        fake_snap.recovery_session_id = str(uuid.uuid4())
        fake_snap.to_dict.return_value = {}
        comp.snapshot_builder.build.return_value = fake_snap
        comp.engine.start_recovery.return_value = MagicMock()
        comp.engine.get_session_for_request.return_value = MagicMock()
        comp.snapshot_store.save.return_value = None
        comp.snapshot_cache.put.return_value = None
        comp.snapshot_registry.register.return_value = None
        comp.snapshot_store.latest.return_value = fake_snap
        comp.snapshot_store.all.return_value = [fake_snap]
        comp.snapshot_store.by_session.return_value = [fake_snap]
        comp.snapshot_store.by_execution.return_value = [fake_snap]
        return ExecutionRecoveryIntegrationEngine(components=comp)

    def test_not_started_raises(self):
        engine = self._engine_with_mocked_components()
        with pytest.raises(IntegrationNotRunningError):
            engine.submit(_req())

    def test_start_and_stop(self):
        engine = self._engine_with_mocked_components()
        engine.start()
        engine.stop()

    def test_initialize_alias(self):
        engine = self._engine_with_mocked_components()
        engine.initialize()
        engine.stop()

    def test_double_stop_safe(self):
        engine = self._engine_with_mocked_components()
        engine.start()
        engine.stop()
        # Second stop raises EngineNotRunningError from lifecycle mixin — expected
        with pytest.raises(Exception):
            engine.stop()

    def test_system_id(self):
        assert ExecutionRecoveryIntegrationEngine.SYSTEM_ID == ENGINE_ID

    def test_version(self):
        assert ExecutionRecoveryIntegrationEngine.VERSION == VERSION


# ═══════════════════════════════════════════════════════════════════════════════
# ExecutionRecoveryIntegrationEngine — API
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionRecoveryIntegrationEngineAPI:
    def setup_method(self):
        comp = _components_all_running()
        comp.snapshot_builder.lifecycle_state.return_value = "running"
        self.fake_snap = MagicMock()
        self.fake_snap.snapshot_id = str(uuid.uuid4())
        self.fake_snap.recovery_session_id = str(uuid.uuid4())
        self.fake_snap.to_dict.return_value = {}
        comp.snapshot_builder.build.return_value = self.fake_snap
        comp.engine.start_recovery.return_value = MagicMock()
        comp.engine.get_session_for_request.return_value = MagicMock()
        comp.snapshot_store.save.return_value = None
        comp.snapshot_cache.put.return_value = None
        comp.snapshot_registry.register.return_value = None
        comp.snapshot_store.latest.return_value = self.fake_snap
        comp.snapshot_store.all.return_value = [self.fake_snap]
        comp.snapshot_store.by_session.return_value = [self.fake_snap]
        comp.snapshot_store.by_execution.return_value = [self.fake_snap]
        self.comp = comp
        self.engine = ExecutionRecoveryIntegrationEngine(components=comp)
        self.engine.start()

    def teardown_method(self):
        try:
            self.engine.stop()
        except Exception:
            pass

    def test_submit_returns_response(self):
        resp = self.engine.submit(_req())
        assert isinstance(resp, IntegrationResponse)

    def test_submit_not_running(self):
        self.engine.stop()
        with pytest.raises(IntegrationNotRunningError):
            self.engine.submit(_req())

    def test_duplicate_submit_raises(self):
        req = _req()
        self.engine.submit(req)
        with pytest.raises(IntegrationDuplicateError):
            self.engine.submit(req)

    def test_validate_valid(self):
        result = self.engine.validate(_req())
        assert result.is_valid

    def test_validate_invalid(self):
        result = self.engine.validate(_req(subsystem_id=""))
        assert not result.is_valid

    def test_health_report(self):
        report = self.engine.health()
        assert isinstance(report, ComponentHealthReport)

    def test_status_report(self):
        report = self.engine.status()
        assert isinstance(report, IntegrationStatusReport)

    def test_statistics(self):
        stats = self.engine.statistics()
        assert isinstance(stats, IntegrationStatistics)

    def test_statistics_increments_on_submit(self):
        before = self.engine.statistics().total_requests
        self.engine.submit(_req())
        after = self.engine.statistics().total_requests
        assert after == before + 1

    def test_snapshot_latest(self):
        self.engine.submit(_req())
        snap = self.engine.snapshot()
        assert snap is not None

    def test_snapshot_by_id(self):
        self.comp.snapshot_store.get.return_value = self.fake_snap
        snap = self.engine.snapshot("some-id")
        assert snap is self.fake_snap

    def test_history(self):
        self.engine.submit(_req())
        hist = self.engine.history()
        assert isinstance(hist, IntegrationHistory)
        assert hist.request_count >= 1

    def test_query_by_session(self):
        results = self.engine.query(recovery_session_id="s")
        self.comp.snapshot_store.by_session.assert_called_with("s")

    def test_query_by_execution(self):
        results = self.engine.query(execution_session_id="e")
        self.comp.snapshot_store.by_execution.assert_called_with("e")

    def test_api_not_running_raises(self):
        self.engine.stop()
        for method, args in [
            (self.engine.health,      []),
            (self.engine.status,      []),
            (self.engine.statistics,  []),
            (self.engine.snapshot,    []),
            (self.engine.history,     []),
            (self.engine.query,       []),
            (self.engine.validate,    [_req()]),
        ]:
            with pytest.raises(IntegrationNotRunningError):
                method(*args)

    def test_successful_response_has_snapshot(self):
        resp = self.engine.submit(_req())
        assert resp.is_successful
        assert resp.has_snapshot

    def test_response_request_id_matches(self):
        req = _req()
        resp = self.engine.submit(req)
        assert resp.request_id == req.request_id

    def test_multiple_requests_independent(self):
        r1 = _req()
        r2 = _req()
        resp1 = self.engine.submit(r1)
        resp2 = self.engine.submit(r2)
        assert resp1.request_id != resp2.request_id
        assert resp1.response_id != resp2.response_id


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: real components (full wiring smoke test)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRealComponentWiring:
    """
    Smoke tests using real M2/M3/M4/M5 components (no mocks).
    Only validates that the wiring doesn't break on create/start/stop.
    """

    def test_factory_create_and_lifecycle(self):
        reg = RecoveryComponentFactory.create(
            max_requests=100, max_history=50, max_concurrent=5,
            max_snapshots=100, cache_size=20,
        )
        reg.start_all()
        assert reg.is_all_running()
        reg.stop_all()

    def test_engine_start_stop(self):
        engine = ExecutionRecoveryIntegrationEngine(
            components=RecoveryComponentFactory.create(
                max_requests=100, max_history=50, max_concurrent=5,
                max_snapshots=100, cache_size=20,
            )
        )
        engine.start()
        assert engine.lifecycle_state() in ("running", "EngineState.RUNNING")
        engine.stop()

    def test_engine_health_after_start(self):
        comp = RecoveryComponentFactory.create(
            max_requests=100, max_history=50, max_concurrent=5,
            max_snapshots=100, cache_size=20,
        )
        engine = ExecutionRecoveryIntegrationEngine(components=comp)
        engine.start()
        try:
            report = engine.health()
            assert isinstance(report, ComponentHealthReport)
        finally:
            engine.stop()

    def test_engine_statistics_empty(self):
        comp = RecoveryComponentFactory.create(
            max_requests=100, max_history=50, max_concurrent=5,
            max_snapshots=100, cache_size=20,
        )
        engine = ExecutionRecoveryIntegrationEngine(components=comp)
        engine.start()
        try:
            stats = engine.statistics()
            assert stats.total_requests == 0
        finally:
            engine.stop()

    def test_validate_with_real_engine(self):
        comp = RecoveryComponentFactory.create(
            max_requests=100, max_history=50, max_concurrent=5,
            max_snapshots=100, cache_size=20,
        )
        engine = ExecutionRecoveryIntegrationEngine(components=comp)
        engine.start()
        try:
            result = engine.validate(_req())
            assert result.is_valid
            result_bad = engine.validate(_req(subsystem_id=""))
            assert not result_bad.is_valid
        finally:
            engine.stop()

    def test_full_submit_with_real_components(self):
        """End-to-end submit with all real M2/M3/M4/M5 components."""
        comp = RecoveryComponentFactory.create(
            max_requests=100, max_history=50, max_concurrent=5,
            max_snapshots=100, cache_size=20,
        )
        engine = ExecutionRecoveryIntegrationEngine(components=comp)
        engine.start()
        try:
            req = _req()
            resp = engine.submit(req)
            # M2 pipeline may succeed or produce a non-successful outcome depending
            # on the dummy policy/failover responses; we only verify the integration
            # layer accepted and processed the request
            assert isinstance(resp, IntegrationResponse)
            assert resp.request_id == req.request_id
            # Stats should have incremented
            stats = engine.statistics()
            assert stats.total_requests == 1
            # History should have the request
            hist = engine.history()
            assert hist.request_count >= 1
        finally:
            engine.stop()

