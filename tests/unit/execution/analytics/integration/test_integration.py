"""
tests/unit/execution/analytics/integration/test_integration.py
================================================================
Comprehensive test suite for iios.execution.analytics.integration — C8 M6.

Coverage areas
--------------
* Integration lifecycle (init, start, stop, restart)
* Public API (submit, health, status, statistics, validate, query, snapshot, history)
* Workflow correctness (M1-M5 pipeline steps)
* Graceful degradation (M2/M3/M4 failures do not abort the pipeline)
* Validation (all seven checks)
* Health assessment (component health, overall health)
* Status (running/stopped/degraded)
* Statistics (all seven counters)
* History (responses, snapshots, events)
* Events (all eight types)
* Registry (register, mark_in_progress, mark_completed, mark_failed, eviction)
* Concurrency (parallel submit calls)
* Regression (interface contracts)
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from iios.execution.analytics.integration import (
    AnalyticsComponentFactory,
    AnalyticsComponentRegistry,
    AnalyticsIntegrationEvent,
    AnalyticsIntegrationHealth,
    AnalyticsIntegrationHistory,
    AnalyticsIntegrationRegistry,
    AnalyticsIntegrationRequest,
    AnalyticsIntegrationResponse,
    AnalyticsIntegrationStatistics,
    AnalyticsIntegrationStatus,
    AnalyticsIntegrationValidator,
    ComponentType,
    ExecutionAnalyticsIntegration,
    IntegrationAlreadyRunningError,
    IntegrationError,
    IntegrationEventType,
    IntegrationHealthLevel,
    IntegrationNotReadyError,
    IntegrationNotRunningError,
    IntegrationResponseStatus,
    IntegrationSnapshotRecord,
    IntegrationValidationCode,
    IntegrationValidationResult,
    IntegrationStatus,
    RegistryEntry,
    RegistryEntryState,
    ValidationCheckResult,
    assess_integration_health,
    build_integration_status,
    make_analytics_completed,
    make_analytics_health_changed,
    make_analytics_initialized,
    make_analytics_restarted,
    make_analytics_snapshot_published,
    make_analytics_started,
    make_analytics_stopped,
    make_analytics_validated,
)
from iios.execution.analytics.lifecycle import AnalyticsScope, AnalyticsMode
from iios.execution.analytics.snapshot import ExecutionAnalyticsSnapshot


# ===========================================================================
# Helpers
# ===========================================================================

def _make_integration() -> ExecutionAnalyticsIntegration:
    """Create, initialize, and start a fresh integration instance."""
    itg = ExecutionAnalyticsIntegration()
    itg.initialize()
    itg.start()
    return itg


def _make_request(*, session_id: str | None = None) -> AnalyticsIntegrationRequest:
    return AnalyticsIntegrationRequest(
        execution_session_id=session_id or f"exec-{uuid.uuid4()}",
        reason="test",
    )


# ===========================================================================
# 1. Integration lifecycle
# ===========================================================================

class TestIntegrationLifecycle:
    def test_create(self):
        itg = ExecutionAnalyticsIntegration()
        assert itg is not None
        assert "ExecutionAnalyticsIntegration" in repr(itg)

    def test_initialize_then_start(self):
        itg = ExecutionAnalyticsIntegration()
        itg.initialize()
        itg.start()
        h = itg.health()
        assert h.is_operational
        itg.stop()

    def test_start_without_initialize_raises(self):
        itg = ExecutionAnalyticsIntegration()
        with pytest.raises(IntegrationNotReadyError):
            itg.start()

    def test_initialize_is_idempotent(self):
        itg = ExecutionAnalyticsIntegration()
        itg.initialize()
        itg.initialize()  # second call is a no-op
        itg.start()
        itg.stop()

    def test_initialize_while_running_raises(self):
        itg = _make_integration()
        try:
            with pytest.raises(IntegrationAlreadyRunningError):
                itg.initialize()
        finally:
            itg.stop()

    def test_stop(self):
        itg = _make_integration()
        itg.stop()
        h = itg.health()
        assert not h.is_operational

    def test_restart(self):
        itg = _make_integration()
        try:
            itg.restart()
            h = itg.health()
            assert h.is_operational
        finally:
            itg.stop()

    def test_restart_records_event(self):
        itg = _make_integration()
        try:
            itg.restart()
            evts = itg.events()
            types = [e.event_type.value for e in evts]
            assert IntegrationEventType.ANALYTICS_RESTARTED.value in types
        finally:
            itg.stop()

    def test_repr(self):
        itg = ExecutionAnalyticsIntegration()
        r = repr(itg)
        assert "ExecutionAnalyticsIntegration" in r
        assert "1.0.0" in r


# ===========================================================================
# 2. Public API — submit
# ===========================================================================

class TestSubmit:
    def setup_method(self):
        self.itg = _make_integration()

    def teardown_method(self):
        self.itg.stop()

    def test_submit_returns_response(self):
        req = _make_request()
        resp = self.itg.submit(req)
        assert isinstance(resp, AnalyticsIntegrationResponse)

    def test_submit_success_status(self):
        req = _make_request()
        resp = self.itg.submit(req)
        assert resp.status == IntegrationResponseStatus.SUCCESS

    def test_submit_has_snapshot(self):
        req = _make_request()
        resp = self.itg.submit(req)
        assert resp.has_snapshot
        assert isinstance(resp.snapshot, ExecutionAnalyticsSnapshot)

    def test_submit_has_performance(self):
        req = _make_request()
        resp = self.itg.submit(req)
        assert resp.has_performance

    def test_submit_has_predictions(self):
        req = _make_request()
        resp = self.itg.submit(req)
        assert resp.has_predictions

    def test_submit_request_id_propagated(self):
        req = _make_request()
        resp = self.itg.submit(req)
        assert resp.request_id == req.request_id

    def test_submit_execution_session_id_propagated(self):
        req = _make_request(session_id="exec-xyz-999")
        resp = self.itg.submit(req)
        assert resp.execution_session_id == "exec-xyz-999"

    def test_submit_processing_ms_positive(self):
        req = _make_request()
        resp = self.itg.submit(req)
        assert resp.processing_ms >= 0.0

    def test_submit_invalid_request_rejected(self):
        # empty execution_session_id
        req = AnalyticsIntegrationRequest(execution_session_id="  ")
        resp = self.itg.submit(req)
        assert resp.status == IntegrationResponseStatus.REJECTED
        assert resp.snapshot is None

    def test_submit_bad_priority_rejected(self):
        req = AnalyticsIntegrationRequest(
            execution_session_id="exec-001", priority=0
        )
        resp = self.itg.submit(req)
        assert resp.status == IntegrationResponseStatus.REJECTED

    def test_submit_without_performance(self):
        req = AnalyticsIntegrationRequest(
            execution_session_id="exec-noperf",
            include_performance=False,
        )
        resp = self.itg.submit(req)
        assert resp.status in (
            IntegrationResponseStatus.SUCCESS,
            IntegrationResponseStatus.PARTIAL,
        )

    def test_submit_without_predictions(self):
        req = AnalyticsIntegrationRequest(
            execution_session_id="exec-nopred",
            include_predictions=False,
        )
        resp = self.itg.submit(req)
        assert resp.status in (
            IntegrationResponseStatus.SUCCESS,
            IntegrationResponseStatus.PARTIAL,
        )

    def test_submit_without_snapshot(self):
        req = AnalyticsIntegrationRequest(
            execution_session_id="exec-nosnap",
            include_snapshot=False,
        )
        resp = self.itg.submit(req)
        # No snapshot requested → PARTIAL
        assert resp.status == IntegrationResponseStatus.PARTIAL
        assert resp.snapshot is None

    def test_submit_raises_when_not_running(self):
        itg = ExecutionAnalyticsIntegration()
        itg.initialize()
        with pytest.raises(IntegrationNotRunningError):
            itg.submit(_make_request())

    def test_is_success_true_on_success(self):
        req = _make_request()
        resp = self.itg.submit(req)
        assert resp.is_success

    def test_submit_multiple_requests(self):
        resps = [self.itg.submit(_make_request()) for _ in range(5)]
        assert all(r.is_success for r in resps)


# ===========================================================================
# 3. Public API — health
# ===========================================================================

class TestHealth:
    def test_health_while_running(self):
        itg = _make_integration()
        try:
            h = itg.health()
            assert isinstance(h, AnalyticsIntegrationHealth)
            assert h.is_operational
        finally:
            itg.stop()

    def test_health_all_components_healthy(self):
        itg = _make_integration()
        try:
            h = itg.health()
            assert h.lifecycle_health.is_running
            assert h.engine_health.is_running
            assert h.performance_health.is_running
            assert h.predictive_health.is_running
            assert h.snapshot_health.is_running
        finally:
            itg.stop()

    def test_health_not_running_not_operational(self):
        itg = ExecutionAnalyticsIntegration()
        h = itg.health()
        assert not h.is_operational
        assert h.overall_health == IntegrationHealthLevel.CRITICAL

    def test_health_stopped_not_operational(self):
        itg = _make_integration()
        itg.stop()
        h = itg.health()
        assert not h.is_operational

    def test_health_emits_change_event(self):
        itg = _make_integration()
        try:
            # Force a health change by reading health, stopping, and re-reading
            itg.health()  # seed last_health
            itg.stop()
            itg.health()  # should detect change
            evts = itg.events()
            change_evts = [
                e for e in evts
                if e.event_type == IntegrationEventType.ANALYTICS_HEALTH_CHANGED
            ]
            assert len(change_evts) >= 1
        finally:
            pass  # already stopped

    def test_component_health_records(self):
        itg = _make_integration()
        try:
            h = itg.health()
            cr = h.component_healths
            assert ComponentType.LIFECYCLE in cr
            assert ComponentType.ENGINE in cr
            assert ComponentType.PERFORMANCE in cr
            assert ComponentType.PREDICTIVE in cr
            assert ComponentType.SNAPSHOT in cr
        finally:
            itg.stop()


# ===========================================================================
# 4. Public API — status
# ===========================================================================

class TestStatus:
    def test_status_while_running(self):
        itg = _make_integration()
        try:
            s = itg.status()
            assert isinstance(s, AnalyticsIntegrationStatus)
            assert s.is_running
            assert s.is_operational
        finally:
            itg.stop()

    def test_status_not_running(self):
        itg = ExecutionAnalyticsIntegration()
        s = itg.status()
        assert not s.is_running
        assert not s.is_operational

    def test_status_after_stop(self):
        itg = _make_integration()
        itg.stop()
        s = itg.status()
        assert not s.is_running
        assert s.status == IntegrationStatus.STOPPED

    def test_status_running_state(self):
        itg = _make_integration()
        try:
            s = itg.status()
            assert s.status == IntegrationStatus.RUNNING
        finally:
            itg.stop()

    def test_status_has_component_states(self):
        itg = _make_integration()
        try:
            s = itg.status()
            assert len(s.component_states) == 5
        finally:
            itg.stop()

    def test_status_uptime_increases(self):
        itg = _make_integration()
        try:
            s1 = itg.status()
            time.sleep(0.05)
            s2 = itg.status()
            assert s2.uptime_seconds >= s1.uptime_seconds
        finally:
            itg.stop()

    def test_status_active_requests_zero_at_rest(self):
        itg = _make_integration()
        try:
            s = itg.status()
            assert s.active_requests == 0
        finally:
            itg.stop()


# ===========================================================================
# 5. Public API — statistics
# ===========================================================================

class TestStatistics:
    def test_statistics_type(self):
        itg = _make_integration()
        try:
            st = itg.statistics()
            assert isinstance(st, AnalyticsIntegrationStatistics)
        finally:
            itg.stop()

    def test_statistics_requests_count(self):
        itg = _make_integration()
        try:
            itg.submit(_make_request())
            itg.submit(_make_request())
            st = itg.statistics()
            assert st.analytics_requests == 2
        finally:
            itg.stop()

    def test_statistics_sessions_count(self):
        itg = _make_integration()
        try:
            itg.submit(_make_request())
            st = itg.statistics()
            assert st.analytics_sessions >= 1
        finally:
            itg.stop()

    def test_statistics_snapshots_published(self):
        itg = _make_integration()
        try:
            itg.submit(_make_request())
            st = itg.statistics()
            assert st.analytics_snapshots_published >= 1
        finally:
            itg.stop()

    def test_statistics_performance_reports(self):
        itg = _make_integration()
        try:
            itg.submit(_make_request())
            st = itg.statistics()
            assert st.performance_reports_generated >= 1
        finally:
            itg.stop()

    def test_statistics_forecasts_generated(self):
        itg = _make_integration()
        try:
            itg.submit(_make_request())
            st = itg.statistics()
            assert st.forecasts_generated >= 1
        finally:
            itg.stop()

    def test_statistics_availability_default_one(self):
        itg = _make_integration()
        try:
            st = itg.statistics()
            assert st.subsystem_availability == 1.0
        finally:
            itg.stop()

    def test_statistics_avg_response_time(self):
        itg = _make_integration()
        try:
            itg.submit(_make_request())
            st = itg.statistics()
            assert st.average_response_time_ms >= 0.0
        finally:
            itg.stop()

    def test_statistics_snapshot_dict(self):
        itg = _make_integration()
        try:
            st = itg.statistics()
            d = st.snapshot()
            assert "analytics_requests" in d
            assert "analytics_sessions" in d
            assert "analytics_snapshots_published" in d
            assert "performance_reports_generated" in d
            assert "forecasts_generated" in d
            assert "subsystem_availability" in d
            assert "average_response_time_ms" in d
        finally:
            itg.stop()

    def test_statistics_reset(self):
        itg = _make_integration()
        try:
            itg.submit(_make_request())
            itg.statistics().reset()
            st = itg.statistics()
            assert st.analytics_requests == 0
        finally:
            itg.stop()


# ===========================================================================
# 6. Public API — validate
# ===========================================================================

class TestValidate:
    def test_validate_passes_when_running(self):
        itg = _make_integration()
        try:
            result = itg.validate()
            assert isinstance(result, IntegrationValidationResult)
            assert result.is_valid
            assert result.passed_count == 7
        finally:
            itg.stop()

    def test_validate_fails_when_not_running(self):
        itg = ExecutionAnalyticsIntegration()
        result = itg.validate()
        assert not result.is_valid
        assert result.failed_count > 0

    def test_validate_checks_tuple(self):
        itg = _make_integration()
        try:
            result = itg.validate()
            assert len(result.checks) == 7
            for check in result.checks:
                assert isinstance(check, ValidationCheckResult)
        finally:
            itg.stop()

    def test_validate_all_check_codes_present(self):
        itg = _make_integration()
        try:
            result = itg.validate()
            codes = {c.code for c in result.checks}
            for code in IntegrationValidationCode:
                assert code in codes
        finally:
            itg.stop()

    def test_validate_records_event(self):
        itg = _make_integration()
        try:
            itg.validate()
            evts = itg.events()
            types = [e.event_type.value for e in evts]
            assert IntegrationEventType.ANALYTICS_VALIDATED.value in types
        finally:
            itg.stop()

    def test_validate_no_perf_check_passes_when_disabled(self):
        itg = _make_integration()
        try:
            result = itg.validate(include_performance=False, include_predictions=False)
            assert result.is_valid
        finally:
            itg.stop()


# ===========================================================================
# 7. Public API — query / snapshot / history / events
# ===========================================================================

class TestQueryAndHistory:
    def setup_method(self):
        self.itg = _make_integration()

    def teardown_method(self):
        self.itg.stop()

    def test_snapshot_none_before_submit(self):
        assert self.itg.snapshot() is None

    def test_snapshot_after_submit(self):
        self.itg.submit(_make_request())
        snap = self.itg.snapshot()
        assert snap is not None
        assert isinstance(snap, ExecutionAnalyticsSnapshot)

    def test_snapshot_none_when_not_running(self):
        itg = ExecutionAnalyticsIntegration()
        assert itg.snapshot() is None

    def test_history_empty_initially(self):
        h = self.itg.history()
        assert isinstance(h, list)

    def test_history_grows_with_submits(self):
        self.itg.submit(_make_request())
        self.itg.submit(_make_request())
        h = self.itg.history()
        assert len(h) == 2

    def test_history_returns_responses(self):
        self.itg.submit(_make_request())
        h = self.itg.history()
        assert all(isinstance(r, AnalyticsIntegrationResponse) for r in h)

    def test_events_initially_non_empty(self):
        # initialized + started events were already emitted
        evts = self.itg.events()
        assert len(evts) >= 2

    def test_events_after_submit_grows(self):
        initial = len(self.itg.events())
        self.itg.submit(_make_request())
        after = len(self.itg.events())
        assert after > initial

    def test_snapshot_records(self):
        self.itg.submit(_make_request())
        records = self.itg.snapshot_records()
        assert len(records) >= 1
        assert all(isinstance(r, IntegrationSnapshotRecord) for r in records)

    def test_query_by_execution_session(self):
        sid = f"exec-query-{uuid.uuid4()}"
        req = AnalyticsIntegrationRequest(execution_session_id=sid)
        self.itg.submit(req)
        results = self.itg.query(execution_session_id=sid)
        assert isinstance(results, list)

    def test_query_by_request_id(self):
        req = _make_request()
        self.itg.submit(req)
        results = self.itg.query(request_id=req.request_id)
        assert isinstance(results, list)

    def test_query_returns_list_when_not_found(self):
        results = self.itg.query(execution_session_id="exec-no-such")
        assert results == []

    def test_query_raises_when_not_running(self):
        itg = ExecutionAnalyticsIntegration()
        itg.initialize()
        with pytest.raises(IntegrationNotRunningError):
            itg.query(execution_session_id="x")


# ===========================================================================
# 8. Events
# ===========================================================================

class TestEvents:
    def test_initialized_event_emitted(self):
        itg = ExecutionAnalyticsIntegration()
        itg.initialize()
        evts = itg.events()
        types = [e.event_type.value for e in evts]
        assert IntegrationEventType.ANALYTICS_INITIALIZED.value in types
        itg.start()
        itg.stop()

    def test_started_event_emitted(self):
        itg = _make_integration()
        evts = itg.events()
        types = [e.event_type.value for e in evts]
        assert IntegrationEventType.ANALYTICS_STARTED.value in types
        itg.stop()

    def test_stopped_event_emitted(self):
        itg = _make_integration()
        itg.stop()
        evts = itg.events()
        types = [e.event_type.value for e in evts]
        assert IntegrationEventType.ANALYTICS_STOPPED.value in types

    def test_completed_event_on_submit(self):
        itg = _make_integration()
        try:
            itg.submit(_make_request())
            evts = itg.events()
            types = [e.event_type.value for e in evts]
            assert IntegrationEventType.ANALYTICS_COMPLETED.value in types
        finally:
            itg.stop()

    def test_snapshot_published_event_on_submit(self):
        itg = _make_integration()
        try:
            itg.submit(_make_request())
            evts = itg.events()
            types = [e.event_type.value for e in evts]
            assert IntegrationEventType.ANALYTICS_SNAPSHOT_PUBLISHED.value in types
        finally:
            itg.stop()

    def test_validated_event_on_validate(self):
        itg = _make_integration()
        try:
            itg.validate()
            evts = itg.events()
            types = [e.event_type.value for e in evts]
            assert IntegrationEventType.ANALYTICS_VALIDATED.value in types
        finally:
            itg.stop()

    def test_restarted_event_on_restart(self):
        itg = _make_integration()
        try:
            itg.restart()
            evts = itg.events()
            types = [e.event_type.value for e in evts]
            assert IntegrationEventType.ANALYTICS_RESTARTED.value in types
        finally:
            itg.stop()

    def test_make_analytics_initialized(self):
        e = make_analytics_initialized()
        assert e.event_type == IntegrationEventType.ANALYTICS_INITIALIZED
        assert e.event_id

    def test_make_analytics_started(self):
        e = make_analytics_started()
        assert e.event_type == IntegrationEventType.ANALYTICS_STARTED

    def test_make_analytics_completed(self):
        e = make_analytics_completed(request_id="req-1", processing_ms=5.0)
        assert e.event_type == IntegrationEventType.ANALYTICS_COMPLETED
        assert e.payload["processing_ms"] == 5.0
        assert e.request_id == "req-1"

    def test_make_analytics_stopped(self):
        e = make_analytics_stopped(reason="test")
        assert e.event_type == IntegrationEventType.ANALYTICS_STOPPED
        assert e.payload["reason"] == "test"

    def test_make_analytics_restarted(self):
        e = make_analytics_restarted()
        assert e.event_type == IntegrationEventType.ANALYTICS_RESTARTED

    def test_make_analytics_validated(self):
        e = make_analytics_validated(passed=False, failed_checks=("lc",))
        assert e.event_type == IntegrationEventType.ANALYTICS_VALIDATED
        assert not e.payload["passed"]
        assert "lc" in e.payload["failed_checks"]

    def test_make_analytics_health_changed(self):
        e = make_analytics_health_changed(previous_health="healthy", current_health="degraded")
        assert e.event_type == IntegrationEventType.ANALYTICS_HEALTH_CHANGED
        assert e.payload["previous_health"] == "healthy"

    def test_make_analytics_snapshot_published(self):
        e = make_analytics_snapshot_published(request_id="req-2", snapshot_id="snap-1")
        assert e.event_type == IntegrationEventType.ANALYTICS_SNAPSHOT_PUBLISHED
        assert e.payload["snapshot_id"] == "snap-1"


# ===========================================================================
# 9. Validation unit tests
# ===========================================================================

class TestValidationUnit:
    def setup_method(self):
        self.validator = AnalyticsIntegrationValidator()

    def test_all_running_is_valid(self):
        result = self.validator.validate(
            lifecycle_running   = True,
            engine_running      = True,
            performance_running = True,
            predictive_running  = True,
            snapshot_running    = True,
            integration_running = True,
            request_valid       = True,
        )
        assert result.is_valid
        assert result.passed_count == 7

    def test_lifecycle_not_running_fails(self):
        result = self.validator.validate(
            lifecycle_running   = False,
            engine_running      = True,
            performance_running = True,
            predictive_running  = True,
            snapshot_running    = True,
            integration_running = True,
        )
        assert not result.is_valid
        assert IntegrationValidationCode.LIFECYCLE_CONSISTENCY in result.failed_checks

    def test_engine_not_running_fails(self):
        result = self.validator.validate(
            lifecycle_running   = True,
            engine_running      = False,
            performance_running = True,
            predictive_running  = True,
            snapshot_running    = True,
            integration_running = True,
        )
        assert IntegrationValidationCode.ENGINE_CONSISTENCY in result.failed_checks

    def test_perf_not_required_when_disabled(self):
        result = self.validator.validate(
            lifecycle_running   = True,
            engine_running      = True,
            performance_running = False,
            predictive_running  = True,
            snapshot_running    = True,
            integration_running = True,
            include_performance = False,
        )
        assert result.is_valid

    def test_pred_not_required_when_disabled(self):
        result = self.validator.validate(
            lifecycle_running   = True,
            engine_running      = True,
            performance_running = True,
            predictive_running  = False,
            snapshot_running    = True,
            integration_running = True,
            include_predictions = False,
        )
        assert result.is_valid

    def test_perf_required_by_default(self):
        result = self.validator.validate(
            lifecycle_running   = True,
            engine_running      = True,
            performance_running = False,
            predictive_running  = True,
            snapshot_running    = True,
            integration_running = True,
        )
        assert IntegrationValidationCode.PERFORMANCE_CONSISTENCY in result.failed_checks

    def test_snapshot_not_running_fails(self):
        result = self.validator.validate(
            lifecycle_running   = True,
            engine_running      = True,
            performance_running = True,
            predictive_running  = True,
            snapshot_running    = False,
            integration_running = True,
        )
        assert IntegrationValidationCode.SNAPSHOT_CONSISTENCY in result.failed_checks

    def test_integration_not_running_fails(self):
        result = self.validator.validate(
            lifecycle_running   = True,
            engine_running      = True,
            performance_running = True,
            predictive_running  = True,
            snapshot_running    = True,
            integration_running = False,
        )
        assert IntegrationValidationCode.INTEGRATION_CONSISTENCY in result.failed_checks

    def test_invalid_request_fails(self):
        result = self.validator.validate(
            lifecycle_running   = True,
            engine_running      = True,
            performance_running = True,
            predictive_running  = True,
            snapshot_running    = True,
            integration_running = True,
            request_valid       = False,
            request_error       = "bad request",
        )
        assert IntegrationValidationCode.SUBSYSTEM_READINESS in result.failed_checks

    def test_multiple_failures(self):
        result = self.validator.validate(
            lifecycle_running   = False,
            engine_running      = False,
            performance_running = False,
            predictive_running  = False,
            snapshot_running    = False,
            integration_running = False,
        )
        assert result.failed_count >= 5

    def test_validate_request_only_valid(self):
        ok, msg = self.validator.validate_request_only(
            execution_session_id="exec-001", priority=5
        )
        assert ok
        assert msg == ""

    def test_validate_request_only_empty_session(self):
        ok, msg = self.validator.validate_request_only(
            execution_session_id="  ", priority=5
        )
        assert not ok

    def test_validate_request_only_bad_priority(self):
        ok, msg = self.validator.validate_request_only(
            execution_session_id="exec-001", priority=0
        )
        assert not ok


# ===========================================================================
# 10. Health unit tests (assess_integration_health)
# ===========================================================================

class TestHealthUnit:
    def test_all_healthy(self):
        h = assess_integration_health(
            lifecycle_running=True, engine_running=True,
            performance_running=True, predictive_running=True,
            snapshot_running=True,
        )
        assert h.overall_health == IntegrationHealthLevel.HEALTHY
        assert h.is_operational

    def test_lifecycle_not_running_not_operational(self):
        h = assess_integration_health(
            lifecycle_running=False, engine_running=True,
            performance_running=True, predictive_running=True,
            snapshot_running=True,
        )
        assert not h.is_operational

    def test_engine_not_running_not_operational(self):
        h = assess_integration_health(
            lifecycle_running=True, engine_running=False,
            performance_running=True, predictive_running=True,
            snapshot_running=True,
        )
        assert not h.is_operational

    def test_snapshot_not_running_not_operational(self):
        h = assess_integration_health(
            lifecycle_running=True, engine_running=True,
            performance_running=True, predictive_running=True,
            snapshot_running=False,
        )
        assert not h.is_operational

    def test_perf_not_running_still_operational(self):
        # M3 is non-blocking for operational status
        h = assess_integration_health(
            lifecycle_running=True, engine_running=True,
            performance_running=False, predictive_running=True,
            snapshot_running=True,
        )
        assert h.is_operational

    def test_predictive_not_running_still_operational(self):
        h = assess_integration_health(
            lifecycle_running=True, engine_running=True,
            performance_running=True, predictive_running=False,
            snapshot_running=True,
        )
        assert h.is_operational

    def test_all_not_running_critical(self):
        h = assess_integration_health(
            lifecycle_running=False, engine_running=False,
            performance_running=False, predictive_running=False,
            snapshot_running=False,
        )
        assert h.is_critical

    def test_component_health_records(self):
        h = assess_integration_health(
            lifecycle_running=True, engine_running=True,
            performance_running=True, predictive_running=True,
            snapshot_running=True,
        )
        assert h.lifecycle_health.component == ComponentType.LIFECYCLE
        assert h.lifecycle_health.is_healthy
        assert h.lifecycle_health.is_running


# ===========================================================================
# 11. Registry unit tests
# ===========================================================================

class TestRegistry:
    def setup_method(self):
        self.registry = AnalyticsIntegrationRegistry()

    def _req(self) -> AnalyticsIntegrationRequest:
        return _make_request()

    def test_register(self):
        req = self._req()
        entry = self.registry.register(req)
        assert isinstance(entry, RegistryEntry)
        assert entry.state == RegistryEntryState.REGISTERED

    def test_register_duplicate_in_flight_raises(self):
        req = self._req()
        self.registry.register(req)
        with pytest.raises(ValueError):
            self.registry.register(req)

    def test_mark_in_progress(self):
        req = self._req()
        self.registry.register(req)
        self.registry.mark_in_progress(req.request_id, "sess-001")
        entry = self.registry.get(req.request_id)
        assert entry.state == RegistryEntryState.IN_PROGRESS
        assert entry.analytics_session_id == "sess-001"

    def test_mark_completed(self):
        req = self._req()
        self.registry.register(req)
        self.registry.mark_completed(req.request_id)
        entry = self.registry.get(req.request_id)
        assert entry.state == RegistryEntryState.COMPLETED

    def test_mark_failed(self):
        req = self._req()
        self.registry.register(req)
        self.registry.mark_failed(req.request_id, "oops")
        entry = self.registry.get(req.request_id)
        assert entry.state == RegistryEntryState.FAILED
        assert entry.error_message == "oops"

    def test_mark_rejected(self):
        req = self._req()
        self.registry.register(req)
        self.registry.mark_rejected(req.request_id, "bad request")
        entry = self.registry.get(req.request_id)
        assert entry.state == RegistryEntryState.REJECTED

    def test_active_count(self):
        r1, r2 = self._req(), self._req()
        self.registry.register(r1)
        self.registry.register(r2)
        assert self.registry.active_count() == 2
        self.registry.mark_completed(r1.request_id)
        assert self.registry.active_count() == 1

    def test_all_active(self):
        r1, r2 = self._req(), self._req()
        self.registry.register(r1)
        self.registry.register(r2)
        active = self.registry.all_active()
        assert len(active) == 2

    def test_get_nonexistent(self):
        assert self.registry.get("nonexistent") is None

    def test_clear(self):
        req = self._req()
        self.registry.register(req)
        self.registry.clear()
        assert self.registry.total_count() == 0

    def test_clear_completed(self):
        r1, r2 = self._req(), self._req()
        self.registry.register(r1)
        self.registry.register(r2)
        self.registry.mark_completed(r1.request_id)
        removed = self.registry.clear_completed()
        assert removed == 1
        assert self.registry.total_count() == 1

    def test_eviction(self):
        # Fill registry beyond max with completed entries
        reg = AnalyticsIntegrationRegistry(max_entries=3)
        requests = [self._req() for _ in range(4)]
        for req in requests:
            try:
                reg.register(req)
                reg.mark_completed(req.request_id)
            except Exception:
                pass
        # Should have evicted to stay at max
        assert reg.total_count() <= 3


# ===========================================================================
# 12. History unit tests
# ===========================================================================

class TestHistory:
    def setup_method(self):
        self.history = AnalyticsIntegrationHistory(max_responses=5, max_snapshots=5, max_events=5)

    def _resp(self) -> AnalyticsIntegrationResponse:
        return AnalyticsIntegrationResponse.rejected(
            request_id="r1", execution_session_id="s1", reason="test"
        )

    def test_record_response(self):
        self.history.record_response(self._resp())
        assert self.history.response_count() == 1

    def test_latest_response(self):
        r = self._resp()
        self.history.record_response(r)
        assert self.history.latest_response() is r

    def test_bounded_responses(self):
        for _ in range(10):
            self.history.record_response(self._resp())
        assert self.history.response_count() == 5

    def test_responses_for_request(self):
        req_id = "req-specific"
        resp = AnalyticsIntegrationResponse.rejected(
            request_id=req_id, execution_session_id="s", reason="x"
        )
        self.history.record_response(resp)
        results = self.history.responses_for_request(req_id)
        assert len(results) == 1

    def test_record_event(self):
        e = make_analytics_initialized()
        self.history.record_event(e)
        assert self.history.event_count() == 1

    def test_events_by_type(self):
        self.history.record_event(make_analytics_started())
        self.history.record_event(make_analytics_stopped(reason="x"))
        evts = self.history.events_by_type(IntegrationEventType.ANALYTICS_STARTED.value)
        assert len(evts) == 1

    def test_clear(self):
        self.history.record_event(make_analytics_initialized())
        self.history.record_response(self._resp())
        self.history.clear()
        assert self.history.response_count() == 0
        assert self.history.event_count() == 0

    def test_latest_event_none(self):
        assert self.history.latest_event() is None

    def test_latest_snapshot_none(self):
        assert self.history.latest_snapshot() is None


# ===========================================================================
# 13. Statistics unit tests
# ===========================================================================

class TestStatisticsUnit:
    def setup_method(self):
        self.stats = AnalyticsIntegrationStatistics()

    def test_initial_zero(self):
        assert self.stats.analytics_requests == 0
        assert self.stats.analytics_sessions == 0
        assert self.stats.analytics_snapshots_published == 0
        assert self.stats.performance_reports_generated == 0
        assert self.stats.forecasts_generated == 0
        assert self.stats.failed_requests == 0
        assert self.stats.rejected_requests == 0

    def test_record_request_received(self):
        self.stats.record_request_received()
        assert self.stats.analytics_requests == 1

    def test_record_session_created(self):
        self.stats.record_session_created()
        assert self.stats.analytics_sessions == 1

    def test_record_snapshot_published(self):
        self.stats.record_snapshot_published()
        assert self.stats.analytics_snapshots_published == 1

    def test_record_performance_report(self):
        self.stats.record_performance_report()
        assert self.stats.performance_reports_generated == 1

    def test_record_forecast(self):
        self.stats.record_forecast_generated()
        assert self.stats.forecasts_generated == 1

    def test_record_completed_sets_latency(self):
        self.stats.record_request_completed(100.0)
        assert self.stats.average_response_time_ms == pytest.approx(100.0)

    def test_ema_latency(self):
        self.stats.record_request_completed(100.0)
        self.stats.record_request_completed(200.0)
        # EMA should be between 100 and 200
        assert 100.0 < self.stats.average_response_time_ms < 200.0

    def test_availability_ticks(self):
        self.stats.record_availability_tick(is_up=True)
        self.stats.record_availability_tick(is_up=False)
        assert self.stats.subsystem_availability == pytest.approx(0.5)

    def test_reset(self):
        self.stats.record_request_received()
        self.stats.record_session_created()
        self.stats.reset()
        assert self.stats.analytics_requests == 0
        assert self.stats.analytics_sessions == 0

    def test_thread_safety(self):
        errors = []
        def increment():
            try:
                for _ in range(100):
                    self.stats.record_request_received()
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert self.stats.analytics_requests == 1000


# ===========================================================================
# 14. Request / Response / Context value objects
# ===========================================================================

class TestValueObjects:
    def test_request_is_frozen(self):
        req = _make_request()
        with pytest.raises(Exception):
            req.execution_session_id = "mutate"  # type: ignore[misc]

    def test_request_default_request_id(self):
        r1 = _make_request()
        r2 = _make_request()
        assert r1.request_id != r2.request_id

    def test_request_valid(self):
        req = AnalyticsIntegrationRequest(execution_session_id="exec-001")
        assert req.is_valid()

    def test_request_invalid_empty_session(self):
        req = AnalyticsIntegrationRequest(execution_session_id="  ")
        assert not req.is_valid()

    def test_request_invalid_priority(self):
        req = AnalyticsIntegrationRequest(execution_session_id="x", priority=11)
        assert not req.is_valid()

    def test_request_has_session_context(self):
        req = AnalyticsIntegrationRequest(
            execution_session_id="x", workflow_id="wf-1"
        )
        assert req.has_session_context

    def test_response_is_frozen(self):
        resp = AnalyticsIntegrationResponse.rejected(
            request_id="r", execution_session_id="s", reason="x"
        )
        with pytest.raises(Exception):
            resp.status = IntegrationResponseStatus.SUCCESS  # type: ignore[misc]

    def test_response_success_has_snapshot(self):
        snap = MagicMock(spec=ExecutionAnalyticsSnapshot)
        snap.has_performance = True
        snap.has_predictions = True
        resp = AnalyticsIntegrationResponse.success(
            request_id="r", analytics_session_id="a",
            execution_session_id="e", snapshot=snap, processing_ms=1.0,
        )
        assert resp.is_success
        assert resp.has_snapshot
        assert resp.status == IntegrationResponseStatus.SUCCESS

    def test_response_success_no_snapshot_is_partial(self):
        resp = AnalyticsIntegrationResponse.success(
            request_id="r", analytics_session_id="a",
            execution_session_id="e", snapshot=None, processing_ms=1.0,
        )
        assert resp.status == IntegrationResponseStatus.PARTIAL
        assert resp.is_success  # PARTIAL is still is_success

    def test_response_failed(self):
        resp = AnalyticsIntegrationResponse.failed(
            request_id="r", analytics_session_id="a",
            execution_session_id="e", error_message="oops", processing_ms=1.0,
        )
        assert not resp.is_success
        assert resp.status == IntegrationResponseStatus.FAILED

    def test_response_rejected(self):
        resp = AnalyticsIntegrationResponse.rejected(
            request_id="r", execution_session_id="e", reason="bad"
        )
        assert resp.status == IntegrationResponseStatus.REJECTED
        assert not resp.is_success


# ===========================================================================
# 15. IntegrationSnapshotRecord
# ===========================================================================

class TestSnapshotRecord:
    def test_create(self):
        snap = MagicMock(spec=ExecutionAnalyticsSnapshot)
        snap.snapshot_id = "snap-001"
        snap.has_performance = True
        snap.has_predictions = False
        snap.has_risk = False
        snap.has_capacity = False
        record = IntegrationSnapshotRecord.create(
            request_id="req-1",
            analytics_session_id="sess-1",
            execution_session_id="exec-1",
            snapshot=snap,
        )
        assert record.snapshot_id == "snap-001"
        assert record.request_id == "req-1"
        assert record.has_performance

    def test_frozen(self):
        snap = MagicMock(spec=ExecutionAnalyticsSnapshot)
        snap.snapshot_id = "s"
        snap.has_performance = False
        snap.has_predictions = False
        snap.has_risk = False
        snap.has_capacity = False
        record = IntegrationSnapshotRecord.create(
            request_id="r", analytics_session_id="a",
            execution_session_id="e", snapshot=snap,
        )
        with pytest.raises(Exception):
            record.request_id = "mutate"  # type: ignore[misc]


# ===========================================================================
# 16. Concurrency tests
# ===========================================================================

class TestConcurrency:
    def test_concurrent_submits(self):
        itg = _make_integration()
        results = []
        errors = []

        def submit_one():
            try:
                req = _make_request()
                resp = itg.submit(req)
                results.append(resp)
            except Exception as e:
                errors.append(e)

        try:
            threads = [threading.Thread(target=submit_one) for _ in range(10)]
            for t in threads: t.start()
            for t in threads: t.join()

            assert not errors, f"Concurrent submit errors: {errors}"
            assert len(results) == 10
            assert all(r.is_success for r in results)
        finally:
            itg.stop()

    def test_concurrent_health_status_calls(self):
        itg = _make_integration()
        errors = []

        def check():
            try:
                itg.health()
                itg.status()
            except Exception as e:
                errors.append(e)

        try:
            threads = [threading.Thread(target=check) for _ in range(10)]
            for t in threads: t.start()
            for t in threads: t.join()
            assert not errors
        finally:
            itg.stop()

    def test_concurrent_registry_operations(self):
        registry = AnalyticsIntegrationRegistry()
        errors = []

        def ops():
            try:
                req = _make_request()
                registry.register(req)
                registry.mark_in_progress(req.request_id, "sess")
                registry.mark_completed(req.request_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=ops) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors


# ===========================================================================
# 17. Regression — interface contracts
# ===========================================================================

class TestRegression:
    """Ensure public API surface has not changed shape."""

    def test_integration_has_all_public_methods(self):
        for method_name in (
            "initialize", "start", "stop", "restart",
            "health", "status", "statistics", "snapshot",
            "history", "validate", "submit", "query",
        ):
            assert hasattr(ExecutionAnalyticsIntegration, method_name)

    def test_request_required_field(self):
        with pytest.raises(TypeError):
            AnalyticsIntegrationRequest()  # type: ignore[call-arg]

    def test_response_frozen(self):
        resp = AnalyticsIntegrationResponse.rejected(
            request_id="x", execution_session_id="y", reason="z"
        )
        assert hasattr(resp, "snapshot")
        assert hasattr(resp, "status")
        assert hasattr(resp, "processing_ms")
        assert hasattr(resp, "is_success")

    def test_health_has_all_component_fields(self):
        h = assess_integration_health(
            lifecycle_running=True, engine_running=True,
            performance_running=True, predictive_running=True,
            snapshot_running=True,
        )
        assert hasattr(h, "lifecycle_health")
        assert hasattr(h, "engine_health")
        assert hasattr(h, "performance_health")
        assert hasattr(h, "predictive_health")
        assert hasattr(h, "snapshot_health")
        assert hasattr(h, "overall_health")
        assert hasattr(h, "is_operational")

    def test_statistics_has_all_seven_counters(self):
        st = AnalyticsIntegrationStatistics()
        assert hasattr(st, "analytics_requests")
        assert hasattr(st, "analytics_sessions")
        assert hasattr(st, "analytics_snapshots_published")
        assert hasattr(st, "performance_reports_generated")
        assert hasattr(st, "forecasts_generated")
        assert hasattr(st, "subsystem_availability")
        assert hasattr(st, "average_response_time_ms")

    def test_validation_result_fields(self):
        validator = AnalyticsIntegrationValidator()
        result = validator.validate(
            lifecycle_running=True, engine_running=True,
            performance_running=True, predictive_running=True,
            snapshot_running=True, integration_running=True,
        )
        assert hasattr(result, "is_valid")
        assert hasattr(result, "checks")
        assert hasattr(result, "failed_checks")
        assert hasattr(result, "error_messages")
        assert hasattr(result, "passed_count")
        assert hasattr(result, "failed_count")

    def test_all_event_types_creatable(self):
        for et in IntegrationEventType:
            assert et.value  # non-empty string

    def test_all_validation_codes_present(self):
        assert len(list(IntegrationValidationCode)) == 7

    def test_all_component_types_present(self):
        assert len(list(ComponentType)) == 5
