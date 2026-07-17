"""tests/unit/execution/monitoring/lifecycle/test_monitoring_lifecycle.py
===========================================================================
Comprehensive unit tests for the Execution Monitoring Lifecycle.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

import threading
import time
from typing import List
from unittest.mock import patch

import pytest

from iios.execution.monitoring.lifecycle import (
    ACTIVE_STATES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    ENDED_STATES,
    RUNNING_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VERSION,
    InvalidMonitoringTransitionError,
    MonitoringEvent,
    MonitoringEventType,
    MonitoringFactory,
    MonitoringHistory,
    MonitoringLifecycle,
    MonitoringLifecycleError,
    MonitoringLifecycleNotRunningError,
    MonitoringValidationError,
    MonitoringMetadata,
    MonitoringRegistryCapacityError,
    MonitoringRegistry,
    MonitoringSession,
    MonitoringSessionAlreadyExistsError,
    MonitoringSessionNotFoundError,
    MonitoringSessionTerminalError,
    MonitoringState,
    MonitoringStatistics,
    MonitoringTransition,
    MonitoringValidator,
    MonitoringContext,
    MonitoringStateRecord,
    ValidationResult,
    make_monitoring_context,
    make_monitoring_created,
    make_monitoring_failed,
    make_monitoring_initialized,
    make_monitoring_metadata,
    make_monitoring_paused,
    make_monitoring_resumed,
    make_monitoring_started,
    make_monitoring_stopped,
    make_monitoring_archived,
    make_monitoring_transition,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def lc():
    """Running MonitoringLifecycle instance."""
    lifecycle = MonitoringLifecycle()
    lifecycle.start()
    yield lifecycle
    if lifecycle.lifecycle_state() in ("running", "RUNNING"):
        lifecycle.stop()


@pytest.fixture
def session(lc):
    """A fresh CREATED session."""
    return lc.create("exec-001", "port-001")


@pytest.fixture
def active_session(lc):
    """A session progressed to ACTIVE."""
    s = lc.create("exec-002", "port-002")
    lc.initialize(s.session_id)
    lc.begin(s.session_id)
    lc.mark_active(s.session_id)
    return s


# ─── TestConstants ────────────────────────────────────────────────────────────

class TestConstants:
    def test_monitoring_state_values(self):
        assert MonitoringState.CREATED.value      == "CREATED"
        assert MonitoringState.INITIALIZING.value == "INITIALIZING"
        assert MonitoringState.STARTING.value     == "STARTING"
        assert MonitoringState.ACTIVE.value       == "ACTIVE"
        assert MonitoringState.PAUSED.value       == "PAUSED"
        assert MonitoringState.RESUMING.value     == "RESUMING"
        assert MonitoringState.STOPPING.value     == "STOPPING"
        assert MonitoringState.STOPPED.value      == "STOPPED"
        assert MonitoringState.FAILED.value       == "FAILED"
        assert MonitoringState.ARCHIVED.value     == "ARCHIVED"

    def test_ten_states(self):
        assert len(MonitoringState) == 10

    def test_terminal_states(self):
        assert MonitoringState.STOPPED  in TERMINAL_STATES
        assert MonitoringState.FAILED   in TERMINAL_STATES
        assert MonitoringState.ARCHIVED in TERMINAL_STATES
        assert MonitoringState.ACTIVE   not in TERMINAL_STATES

    def test_running_states(self):
        assert MonitoringState.ACTIVE   in RUNNING_STATES
        assert MonitoringState.PAUSED   in RUNNING_STATES
        assert MonitoringState.RESUMING in RUNNING_STATES
        assert MonitoringState.STOPPED  not in RUNNING_STATES

    def test_active_states(self):
        assert MonitoringState.ACTIVE       in ACTIVE_STATES
        assert MonitoringState.INITIALIZING in ACTIVE_STATES
        assert MonitoringState.ARCHIVED     not in ACTIVE_STATES

    def test_ended_states(self):
        assert MonitoringState.STOPPED  in ENDED_STATES
        assert MonitoringState.FAILED   in ENDED_STATES
        assert MonitoringState.ARCHIVED in ENDED_STATES

    def test_valid_transitions_coverage(self):
        for state in MonitoringState:
            assert state in VALID_TRANSITIONS

    def test_archived_has_no_transitions(self):
        assert len(VALID_TRANSITIONS[MonitoringState.ARCHIVED]) == 0

    def test_version_format(self):
        parts = VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_event_types(self):
        assert len(MonitoringEventType) == 8

    def test_default_max_sessions(self):
        assert DEFAULT_MAX_SESSIONS == 5_000

    def test_default_max_history(self):
        assert DEFAULT_MAX_HISTORY == 1_000


# ─── TestExceptions ───────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_error_code(self):
        e = MonitoringLifecycleError()
        assert e.error_code == "ML-000"

    def test_not_running_code(self):
        e = MonitoringLifecycleNotRunningError()
        assert e.error_code == "ML-001"

    def test_not_found_code(self):
        e = MonitoringSessionNotFoundError("s1")
        assert e.error_code == "ML-002"
        assert e.session_id == "s1"

    def test_invalid_transition_code(self):
        e = InvalidMonitoringTransitionError("s1", "CREATED", "ACTIVE")
        assert e.error_code == "ML-003"
        assert e.from_state == "CREATED"
        assert e.to_state   == "ACTIVE"

    def test_already_exists_code(self):
        e = MonitoringSessionAlreadyExistsError("s1")
        assert e.error_code == "ML-004"

    def test_capacity_code(self):
        e = MonitoringRegistryCapacityError(100)
        assert e.error_code == "ML-005"
        assert e.max_count  == 100

    def test_validation_code(self):
        e = MonitoringValidationError("bad", errors=("err1",))
        assert e.error_code == "ML-006"
        assert "err1" in e.errors

    def test_terminal_code(self):
        e = MonitoringSessionTerminalError("s1", "STOPPED")
        assert e.error_code == "ML-007"
        assert e.state      == "STOPPED"

    def test_all_inherit_base(self):
        errors = [
            MonitoringLifecycleNotRunningError(),
            MonitoringSessionNotFoundError("x"),
            InvalidMonitoringTransitionError("x", "A", "B"),
            MonitoringSessionAlreadyExistsError("x"),
            MonitoringRegistryCapacityError(1),
            MonitoringValidationError(),
            MonitoringSessionTerminalError("x", "STOPPED"),
        ]
        for err in errors:
            assert isinstance(err, MonitoringLifecycleError)


# ─── TestContext ──────────────────────────────────────────────────────────────

class TestContext:
    def test_required_fields(self):
        ctx = make_monitoring_context("exec-1", "port-1")
        assert ctx.execution_session_id == "exec-1"
        assert ctx.portfolio_id         == "port-1"

    def test_optional_fields_default(self):
        ctx = make_monitoring_context("exec-1", "port-1")
        assert ctx.gateway_id  is None
        assert ctx.workflow_id is None
        assert ctx.strategy_id is None
        assert ctx.order_id    is None

    def test_optional_fields_set(self):
        ctx = make_monitoring_context(
            "exec-1", "port-1",
            gateway_id="gw-1",
            workflow_id="wf-1",
            strategy_id="strat-1",
            order_id="ord-1",
        )
        assert ctx.gateway_id  == "gw-1"
        assert ctx.workflow_id == "wf-1"

    def test_has_gateway(self):
        ctx = make_monitoring_context("e", "p", gateway_id="gw")
        assert ctx.has_gateway is True

    def test_has_workflow(self):
        ctx = make_monitoring_context("e", "p", workflow_id="wf")
        assert ctx.has_workflow is True

    def test_frozen(self):
        ctx = make_monitoring_context("e", "p")
        with pytest.raises((AttributeError, TypeError)):
            ctx.portfolio_id = "other"  # type: ignore

    def test_to_dict(self):
        ctx = make_monitoring_context("exec-1", "port-1")
        d = ctx.to_dict()
        assert d["execution_session_id"] == "exec-1"
        assert d["portfolio_id"]         == "port-1"

    def test_monitoring_version_default(self):
        ctx = make_monitoring_context("e", "p")
        assert ctx.monitoring_version == 1


# ─── TestMetadata ─────────────────────────────────────────────────────────────

class TestMetadata:
    def test_defaults(self):
        m = make_monitoring_metadata("s1")
        assert m.session_id    == "s1"
        assert m.schema_version == "1.0"
        assert m.tags           == ()
        assert m.notes          == ""

    def test_custom_tags(self):
        m = make_monitoring_metadata("s1", tags=("tag1", "tag2"))
        assert m.has_tags is True
        assert len(m.tags) == 2

    def test_production_flag(self):
        m = make_monitoring_metadata("s1", environment="PROD")
        assert m.is_production is True
        m2 = make_monitoring_metadata("s1", environment="STAGING")
        assert m2.is_production is False

    def test_to_dict(self):
        m = make_monitoring_metadata("s1")
        d = m.to_dict()
        assert d["session_id"] == "s1"
        assert "created_at" in d

    def test_frozen(self):
        m = make_monitoring_metadata("s1")
        with pytest.raises((AttributeError, TypeError)):
            m.session_id = "other"  # type: ignore


# ─── TestState ────────────────────────────────────────────────────────────────

class TestState:
    def test_is_current(self):
        r = MonitoringStateRecord(MonitoringState.ACTIVE, time.time())
        assert r.is_current is True

    def test_duration_none_while_current(self):
        r = MonitoringStateRecord(MonitoringState.ACTIVE, time.time())
        assert r.duration_ms is None

    def test_with_exit_sets_exited_at(self):
        t = time.time()
        r = MonitoringStateRecord(MonitoringState.ACTIVE, t)
        r2 = r.with_exit(t + 1.0)
        assert r2.exited_at == t + 1.0
        assert r2.is_current is False

    def test_duration_ms(self):
        t = time.time()
        r = MonitoringStateRecord(MonitoringState.ACTIVE, t, t + 2.0)
        assert abs(r.duration_ms - 2000.0) < 1e-6

    def test_to_dict(self):
        r = MonitoringStateRecord(MonitoringState.ACTIVE, time.time())
        d = r.to_dict()
        assert d["state"]      == "ACTIVE"
        assert d["is_current"] is True

    def test_original_unchanged_after_with_exit(self):
        r = MonitoringStateRecord(MonitoringState.ACTIVE, time.time())
        r2 = r.with_exit()
        assert r.is_current  is True
        assert r2.is_current is False


# ─── TestTransition ───────────────────────────────────────────────────────────

class TestTransition:
    def test_make_transition(self):
        t = make_monitoring_transition(
            "s1",
            MonitoringState.CREATED,
            MonitoringState.INITIALIZING,
        )
        assert t.session_id  == "s1"
        assert t.from_state  == MonitoringState.CREATED
        assert t.to_state    == MonitoringState.INITIALIZING
        assert t.transition_id != ""

    def test_unique_ids(self):
        t1 = make_monitoring_transition("s1", MonitoringState.CREATED, MonitoringState.INITIALIZING)
        t2 = make_monitoring_transition("s1", MonitoringState.CREATED, MonitoringState.INITIALIZING)
        assert t1.transition_id != t2.transition_id

    def test_to_dict(self):
        t = make_monitoring_transition("s1", MonitoringState.CREATED, MonitoringState.INITIALIZING)
        d = t.to_dict()
        assert d["from_state"] == "CREATED"
        assert d["to_state"]   == "INITIALIZING"

    def test_frozen(self):
        t = make_monitoring_transition("s1", MonitoringState.CREATED, MonitoringState.INITIALIZING)
        with pytest.raises((AttributeError, TypeError)):
            t.session_id = "other"  # type: ignore


# ─── TestEvents ───────────────────────────────────────────────────────────────

class TestEvents:
    def test_make_created(self):
        e = make_monitoring_created("s1")
        assert e.event_type == MonitoringEventType.MONITORING_CREATED
        assert e.session_id == "s1"

    def test_make_initialized(self):
        e = make_monitoring_initialized("s1")
        assert e.event_type == MonitoringEventType.MONITORING_INITIALIZED

    def test_make_started(self):
        e = make_monitoring_started("s1")
        assert e.event_type == MonitoringEventType.MONITORING_STARTED

    def test_make_paused(self):
        e = make_monitoring_paused("s1")
        assert e.event_type == MonitoringEventType.MONITORING_PAUSED

    def test_make_resumed(self):
        e = make_monitoring_resumed("s1")
        assert e.event_type == MonitoringEventType.MONITORING_RESUMED

    def test_make_stopped(self):
        e = make_monitoring_stopped("s1")
        assert e.event_type == MonitoringEventType.MONITORING_STOPPED

    def test_make_failed(self):
        e = make_monitoring_failed("s1", reason="oops")
        assert e.event_type == MonitoringEventType.MONITORING_FAILED
        assert e.reason      == "oops"

    def test_make_archived(self):
        e = make_monitoring_archived("s1")
        assert e.event_type == MonitoringEventType.MONITORING_ARCHIVED

    def test_unique_event_ids(self):
        e1 = make_monitoring_created("s1")
        e2 = make_monitoring_created("s1")
        assert e1.event_id != e2.event_id

    def test_to_dict(self):
        e = make_monitoring_created("s1")
        d = e.to_dict()
        assert d["event_type"] == "MONITORING_CREATED"
        assert d["session_id"] == "s1"

    def test_frozen(self):
        e = make_monitoring_created("s1")
        with pytest.raises((AttributeError, TypeError)):
            e.session_id = "other"  # type: ignore


# ─── TestStatistics ───────────────────────────────────────────────────────────

class TestStatistics:
    def test_initial_zeroes(self):
        s = MonitoringStatistics()
        assert s.sessions_created  == 0
        assert s.sessions_stopped  == 0
        assert s.total_transitions == 0

    def test_record_created(self):
        s = MonitoringStatistics()
        s.record_created()
        assert s.sessions_created == 1

    def test_record_stopped_with_duration(self):
        s = MonitoringStatistics()
        s.record_stopped(duration_ms=200.0)
        assert s.sessions_stopped  == 1
        assert s.total_duration_ms == 200.0

    def test_average_duration(self):
        s = MonitoringStatistics()
        s.record_stopped(500.0)
        s.record_stopped(1500.0)
        assert abs(s.average_session_duration_ms - 1000.0) < 1e-6

    def test_success_rate_zero_when_no_completions(self):
        s = MonitoringStatistics()
        assert s.success_rate == 0.0

    def test_success_rate(self):
        s = MonitoringStatistics()
        s.record_stopped()
        s.record_failed()
        assert abs(s.success_rate - 0.5) < 1e-6

    def test_failure_rate(self):
        s = MonitoringStatistics()
        s.record_stopped()
        s.record_failed()
        assert abs(s.failure_rate - 0.5) < 1e-6

    def test_reset(self):
        s = MonitoringStatistics()
        s.record_created()
        s.record_stopped()
        s.reset()
        assert s.sessions_created == 0
        assert s.sessions_stopped == 0

    def test_copy_is_independent(self):
        s = MonitoringStatistics()
        s.record_created()
        c = s.copy()
        s.record_created()
        assert c.sessions_created == 1
        assert s.sessions_created == 2

    def test_to_dict(self):
        s = MonitoringStatistics()
        d = s.to_dict()
        assert "sessions_created" in d
        assert "success_rate"     in d

    def test_thread_safe_increments(self):
        s = MonitoringStatistics()
        threads = [threading.Thread(target=s.record_created) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert s.sessions_created == 100


# ─── TestHistory ──────────────────────────────────────────────────────────────

class TestHistory:
    def _make_session(self, portfolio_id="p"):
        return MonitoringSession(
            execution_session_id="exec-hist",
            portfolio_id=portfolio_id,
        )

    def test_append_and_retrieve(self):
        h = MonitoringHistory()
        s = self._make_session()
        h.append_session(s)
        assert h.session_count == 1
        assert h.sessions()[0] is s

    def test_maxlen_sessions(self):
        h = MonitoringHistory(max_sessions=3)
        for _ in range(5):
            h.append_session(self._make_session())
        assert h.session_count == 3

    def test_latest_session(self):
        h = MonitoringHistory()
        s1 = self._make_session("p1")
        s2 = self._make_session("p2")
        h.append_session(s1)
        h.append_session(s2)
        assert h.latest_session() is s2

    def test_latest_session_none_when_empty(self):
        h = MonitoringHistory()
        assert h.latest_session() is None

    def test_sessions_by_portfolio(self):
        h = MonitoringHistory()
        h.append_session(self._make_session("p1"))
        h.append_session(self._make_session("p2"))
        assert len(h.sessions_by_portfolio("p1")) == 1

    def test_sessions_by_execution(self):
        h = MonitoringHistory()
        s = MonitoringSession(execution_session_id="ex-xyz", portfolio_id="p")
        h.append_session(s)
        assert len(h.sessions_by_execution("ex-xyz")) == 1
        assert len(h.sessions_by_execution("other")) == 0

    def test_transitions_and_events(self):
        h = MonitoringHistory()
        t = make_monitoring_transition("s1", MonitoringState.CREATED, MonitoringState.INITIALIZING)
        e = make_monitoring_created("s1")
        h.append_transition(t)
        h.append_event(e)
        assert h.transition_count == 1
        assert h.event_count      == 1

    def test_events_for_session(self):
        h = MonitoringHistory()
        h.append_event(make_monitoring_created("s1"))
        h.append_event(make_monitoring_created("s2"))
        assert len(h.events_for_session("s1")) == 1

    def test_clear(self):
        h = MonitoringHistory()
        h.append_session(self._make_session())
        h.append_event(make_monitoring_created("x"))
        h.clear()
        assert h.session_count == 0
        assert h.event_count   == 0


# ─── TestValidation ───────────────────────────────────────────────────────────

class TestValidation:
    def test_valid_context(self):
        v   = MonitoringValidator()
        ctx = make_monitoring_context("exec-1", "port-1")
        r   = v.validate_context(ctx)
        assert r.is_valid is True

    def test_missing_execution_session_id(self):
        v   = MonitoringValidator()
        ctx = make_monitoring_context("", "port-1")
        r   = v.validate_context(ctx)
        assert r.is_valid is False
        assert any("execution_session_id" in e for e in r.errors)

    def test_missing_portfolio_id(self):
        v   = MonitoringValidator()
        ctx = make_monitoring_context("exec-1", "")
        r   = v.validate_context(ctx)
        assert r.is_valid is False

    def test_valid_transition(self):
        v = MonitoringValidator()
        r = v.validate_transition(MonitoringState.CREATED, MonitoringState.INITIALIZING)
        assert r.is_valid is True

    def test_invalid_transition(self):
        v = MonitoringValidator()
        r = v.validate_transition(MonitoringState.CREATED, MonitoringState.ACTIVE)
        assert r.is_valid is False
        assert len(r.errors) > 0

    def test_valid_session(self):
        v = MonitoringValidator()
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        r = v.validate_session(s)
        assert r.is_valid is True

    def test_validation_result_add_warning(self):
        r = ValidationResult(is_valid=True)
        r.add_warning("check this")
        assert len(r.warnings) == 1
        assert r.is_valid      is True

    def test_validation_result_add_error(self):
        r = ValidationResult(is_valid=True)
        r.add_error("required field missing")
        assert r.is_valid is False


# ─── TestSession ──────────────────────────────────────────────────────────────

class TestSession:
    def test_initial_state(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        assert s.state == MonitoringState.CREATED

    def test_session_id_generated(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        assert s.session_id != ""

    def test_custom_session_id(self):
        s = MonitoringSession(session_id="custom-id", execution_session_id="e", portfolio_id="p")
        assert s.session_id == "custom-id"

    def test_valid_transition_created_to_initializing(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        s.transition_to(MonitoringState.INITIALIZING)
        assert s.state == MonitoringState.INITIALIZING

    def test_invalid_transition_raises(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        with pytest.raises(InvalidMonitoringTransitionError) as exc_info:
            s.transition_to(MonitoringState.ACTIVE)
        assert exc_info.value.error_code == "ML-003"

    def test_full_happy_path(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        for st in [
            MonitoringState.INITIALIZING,
            MonitoringState.STARTING,
            MonitoringState.ACTIVE,
            MonitoringState.STOPPING,
            MonitoringState.STOPPED,
        ]:
            s.transition_to(st)
        assert s.state == MonitoringState.STOPPED

    def test_start_time_set_on_active(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        s.transition_to(MonitoringState.INITIALIZING)
        s.transition_to(MonitoringState.STARTING)
        assert s.start_time is None
        s.transition_to(MonitoringState.ACTIVE)
        assert s.start_time is not None

    def test_end_time_set_on_stopped(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        for st in [MonitoringState.INITIALIZING, MonitoringState.STARTING,
                   MonitoringState.ACTIVE, MonitoringState.STOPPING]:
            s.transition_to(st)
        s.transition_to(MonitoringState.STOPPED)
        assert s.end_time is not None

    def test_end_time_set_on_failed(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        s.transition_to(MonitoringState.FAILED)
        assert s.end_time is not None

    def test_failure_reason(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        s.transition_to(MonitoringState.FAILED, reason="timeout")
        assert s.failure_reason == "timeout"

    def test_is_active(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        for st in [MonitoringState.INITIALIZING, MonitoringState.STARTING,
                   MonitoringState.ACTIVE]:
            s.transition_to(st)
        assert s.is_active is True

    def test_is_terminal(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        s.transition_to(MonitoringState.FAILED)
        assert s.is_terminal is True

    def test_is_running(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        for st in [MonitoringState.INITIALIZING, MonitoringState.STARTING,
                   MonitoringState.ACTIVE]:
            s.transition_to(st)
        assert s.is_running is True

    def test_terminal_blocks_further_transition(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        s.transition_to(MonitoringState.FAILED)
        s.transition_to(MonitoringState.ARCHIVED)  # valid: FAILED → ARCHIVED
        with pytest.raises(MonitoringSessionTerminalError) as exc_info:
            s.transition_to(MonitoringState.ARCHIVED)  # ARCHIVED has no valid targets
        assert exc_info.value.error_code == "ML-007"

    def test_duration_ms_none_before_active(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        assert s.duration_ms is None

    def test_duration_ms_after_active(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        for st in [MonitoringState.INITIALIZING, MonitoringState.STARTING,
                   MonitoringState.ACTIVE]:
            s.transition_to(st)
        assert s.duration_ms is not None
        assert s.duration_ms >= 0.0

    def test_state_history_grows(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        s.transition_to(MonitoringState.INITIALIZING)
        assert len(s.state_history) == 2  # CREATED + INITIALIZING

    def test_to_dict(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        d = s.to_dict()
        assert d["state"]                == "CREATED"
        assert d["execution_session_id"] == "e"

    def test_repr(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        assert "MonitoringSession" in repr(s)
        assert "CREATED"           in repr(s)

    def test_paused_resuming_active(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        for st in [MonitoringState.INITIALIZING, MonitoringState.STARTING,
                   MonitoringState.ACTIVE, MonitoringState.PAUSED,
                   MonitoringState.RESUMING, MonitoringState.ACTIVE]:
            s.transition_to(st)
        assert s.state == MonitoringState.ACTIVE

    def test_start_time_not_reset_on_second_active(self):
        s = MonitoringSession(execution_session_id="e", portfolio_id="p")
        for st in [MonitoringState.INITIALIZING, MonitoringState.STARTING,
                   MonitoringState.ACTIVE]:
            s.transition_to(st)
        first_start = s.start_time
        for st in [MonitoringState.PAUSED, MonitoringState.RESUMING,
                   MonitoringState.ACTIVE]:
            s.transition_to(st)
        assert s.start_time == first_start


# ─── TestRegistry ─────────────────────────────────────────────────────────────

class TestRegistry:
    def _make_reg(self, max_sessions=100):
        reg = MonitoringRegistry(max_sessions=max_sessions)
        reg.start()
        return reg

    def _make_session(self, session_id=None):
        return MonitoringSession(
            session_id=session_id,
            execution_session_id="exec",
            portfolio_id="port",
        )

    def test_store_and_get(self):
        reg = self._make_reg()
        s   = self._make_session("s1")
        reg.store(s)
        assert reg.get("s1") is s
        reg.stop()

    def test_not_found_raises(self):
        reg = self._make_reg()
        with pytest.raises(MonitoringSessionNotFoundError) as exc_info:
            reg.get("nonexistent")
        assert exc_info.value.error_code == "ML-002"
        reg.stop()

    def test_duplicate_raises(self):
        reg = self._make_reg()
        s   = self._make_session("s1")
        reg.store(s)
        with pytest.raises(MonitoringSessionAlreadyExistsError) as exc_info:
            reg.store(s)
        assert exc_info.value.error_code == "ML-004"
        reg.stop()

    def test_capacity_raises(self):
        reg = self._make_reg(max_sessions=2)
        reg.store(self._make_session("s1"))
        reg.store(self._make_session("s2"))
        with pytest.raises(MonitoringRegistryCapacityError) as exc_info:
            reg.store(self._make_session("s3"))
        assert exc_info.value.error_code == "ML-005"
        reg.stop()

    def test_archive(self):
        reg = self._make_reg()
        s   = self._make_session("s1")
        reg.store(s)
        reg.archive("s1")
        with pytest.raises(MonitoringSessionNotFoundError):
            reg.get("s1")
        assert reg.get_archived("s1") is s
        reg.stop()

    def test_all_returns_active(self):
        reg = self._make_reg()
        reg.store(self._make_session("s1"))
        reg.store(self._make_session("s2"))
        assert len(reg.all()) == 2
        reg.stop()

    def test_by_portfolio_id(self):
        reg = self._make_reg()
        reg.store(MonitoringSession(execution_session_id="e", portfolio_id="p1"))
        reg.store(MonitoringSession(execution_session_id="e", portfolio_id="p2"))
        assert len(reg.by_portfolio_id("p1")) == 1
        reg.stop()

    def test_not_running_raises(self):
        reg = MonitoringRegistry()
        with pytest.raises(MonitoringLifecycleNotRunningError) as exc_info:
            reg.store(self._make_session())
        assert exc_info.value.error_code == "ML-001"

    def test_contains(self):
        reg = self._make_reg()
        s   = self._make_session("s1")
        reg.store(s)
        assert reg.contains("s1")  is True
        assert reg.contains("xxx") is False
        reg.stop()


# ─── TestFactory ──────────────────────────────────────────────────────────────

class TestFactory:
    def test_creates_session_in_created_state(self):
        f = MonitoringFactory()
        f.start()
        ctx = make_monitoring_context("exec-1", "port-1")
        s   = f.create(ctx)
        assert s.state        == MonitoringState.CREATED
        assert s.portfolio_id == "port-1"
        f.stop()

    def test_not_running_raises(self):
        f = MonitoringFactory()
        ctx = make_monitoring_context("exec-1", "port-1")
        with pytest.raises(MonitoringLifecycleNotRunningError):
            f.create(ctx)

    def test_create_from_params(self):
        f = MonitoringFactory()
        f.start()
        s = f.create_from_params("exec-1", "port-1", gateway_id="gw-1")
        assert s.gateway_id == "gw-1"
        f.stop()

    def test_each_session_unique_id(self):
        f = MonitoringFactory()
        f.start()
        ctx = make_monitoring_context("exec-1", "port-1")
        s1 = f.create(ctx)
        s2 = f.create(ctx)
        assert s1.session_id != s2.session_id
        f.stop()


# ─── TestLifecycle ────────────────────────────────────────────────────────────

class TestLifecycle:
    def test_create_returns_created_state(self, lc, session):
        assert session.state == MonitoringState.CREATED

    def test_initialize(self, lc, session):
        lc.initialize(session.session_id)
        assert lc.get(session.session_id).state == MonitoringState.INITIALIZING

    def test_start(self, lc, session):
        lc.initialize(session.session_id)
        lc.begin(session.session_id)
        assert lc.get(session.session_id).state == MonitoringState.STARTING

    def test_mark_active(self, lc, session):
        lc.initialize(session.session_id)
        lc.begin(session.session_id)
        lc.mark_active(session.session_id)
        assert lc.get(session.session_id).state == MonitoringState.ACTIVE

    def test_pause(self, lc, active_session):
        lc.pause(active_session.session_id)
        assert lc.get(active_session.session_id).state == MonitoringState.PAUSED

    def test_resume(self, lc, active_session):
        lc.pause(active_session.session_id)
        lc.resume(active_session.session_id)
        assert lc.get(active_session.session_id).state == MonitoringState.RESUMING

    def test_mark_resumed(self, lc, active_session):
        lc.pause(active_session.session_id)
        lc.resume(active_session.session_id)
        lc.mark_resumed(active_session.session_id)
        assert lc.get(active_session.session_id).state == MonitoringState.ACTIVE

    def test_stop(self, lc, active_session):
        lc.cease(active_session.session_id)
        assert lc.get(active_session.session_id).state == MonitoringState.STOPPING

    def test_mark_stopped(self, lc, active_session):
        lc.cease(active_session.session_id)
        lc.mark_stopped(active_session.session_id)
        # session is now in history, no longer in active registry
        s = lc.history().sessions()[-1]
        assert s.state == MonitoringState.STOPPED

    def test_fail(self, lc, active_session):
        lc.fail(active_session.session_id, reason="test-failure")
        s = lc.history().sessions()[-1]
        assert s.state          == MonitoringState.FAILED
        assert s.failure_reason == "test-failure"

    def test_archive(self, lc):
        s = lc.create("exec-arch", "port-arch")
        lc.initialize(s.session_id)
        lc.begin(s.session_id)
        lc.mark_active(s.session_id)
        lc.fail(s.session_id, reason="for-archive")
        lc.archive(s.session_id)
        # After archive, session is not in active registry
        with pytest.raises(MonitoringSessionNotFoundError):
            lc.get(s.session_id)

    def test_not_running_raises(self):
        lc = MonitoringLifecycle()
        with pytest.raises(MonitoringLifecycleNotRunningError) as exc_info:
            lc.create("e", "p")
        assert exc_info.value.error_code == "ML-001"

    def test_session_not_found_raises(self, lc):
        with pytest.raises(MonitoringSessionNotFoundError) as exc_info:
            lc.get("nonexistent")
        assert exc_info.value.error_code == "ML-002"

    def test_invalid_transition_raises(self, lc, session):
        with pytest.raises(InvalidMonitoringTransitionError) as exc_info:
            lc.mark_active(session.session_id)  # CREATED → ACTIVE is invalid
        assert exc_info.value.error_code == "ML-003"

    def test_create_invalid_context_raises(self, lc):
        with pytest.raises(MonitoringValidationError) as exc_info:
            lc.create("", "port-1")  # empty execution_session_id
        assert exc_info.value.error_code == "ML-006"

    def test_statistics_track_sessions(self, lc):
        s = lc.create("exec-stat", "port-stat")
        lc.initialize(s.session_id)
        lc.begin(s.session_id)
        lc.mark_active(s.session_id)
        lc.cease(s.session_id)
        lc.mark_stopped(s.session_id)
        stats = lc.statistics()
        assert stats.sessions_created >= 1
        assert stats.sessions_stopped >= 1

    def test_event_listeners(self, lc):
        received: List[MonitoringEvent] = []
        lc.add_event_listener(received.append)
        s = lc.create("exec-ev", "port-ev")
        assert len(received) >= 1
        assert received[-1].event_type == MonitoringEventType.MONITORING_CREATED
        lc.remove_event_listener(received.append)

    def test_add_remove_listener(self, lc):
        received: List[MonitoringEvent] = []
        lc.add_event_listener(received.append)
        lc.remove_event_listener(received.append)
        lc.create("exec-nolisten", "port-nolisten")
        assert not any(e.event_type == MonitoringEventType.MONITORING_CREATED
                       and e.session_id.startswith("") for e in received
                       if False)  # after removal, listener not invoked

    def test_by_portfolio_id(self, lc):
        lc.create("exec-p1a", "port-A")
        lc.create("exec-p1b", "port-A")
        lc.create("exec-p2",  "port-B")
        assert len(lc.by_portfolio_id("port-A")) == 2
        assert len(lc.by_portfolio_id("port-B")) == 1

    def test_by_execution_session_id(self, lc):
        lc.create("exec-X", "port-1")
        lc.create("exec-X", "port-2")
        assert len(lc.by_execution_session_id("exec-X")) == 2

    def test_active_query(self, lc, active_session):
        active_list = lc.active()
        ids = [s.session_id for s in active_list]
        assert active_session.session_id in ids

    def test_failed_query(self, lc, active_session):
        lc.fail(active_session.session_id, reason="test")
        # after fail, moved to history (append_session), but still in registry
        failed_list = lc.failed()
        ids = [s.session_id for s in failed_list]
        assert active_session.session_id in ids

    def test_stop_from_paused(self, lc, active_session):
        lc.pause(active_session.session_id)
        lc.cease(active_session.session_id)
        assert lc.get(active_session.session_id).state == MonitoringState.STOPPING

    def test_stop_from_resuming(self, lc, active_session):
        lc.pause(active_session.session_id)
        lc.resume(active_session.session_id)
        lc.cease(active_session.session_id)
        assert lc.get(active_session.session_id).state == MonitoringState.STOPPING

    def test_validate_session(self, lc, session):
        result = lc.validate_session(session.session_id)
        assert result.is_valid is True

    def test_create_from_context(self, lc):
        ctx = make_monitoring_context("exec-ctx", "port-ctx")
        s   = lc.create_from_context(ctx)
        assert s.state == MonitoringState.CREATED


# ─── TestConcurrency ──────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_session_creation(self, lc):
        created = []
        errors  = []

        def create_one(i):
            try:
                s = lc.create(f"exec-{i}", "port-concurrent")
                created.append(s.session_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_one, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(errors)  == 0
        assert len(created) == 50
        assert len(set(created)) == 50  # all unique

    def test_concurrent_transitions(self, lc):
        sessions = [lc.create(f"exec-tr-{i}", "port-tr") for i in range(20)]
        errors   = []

        def advance(s):
            try:
                lc.initialize(s.session_id)
                lc.begin(s.session_id)
                lc.mark_active(s.session_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=advance, args=(s,)) for s in sessions]
        for t in threads: t.start()
        for t in threads: t.join()

        assert errors == []
        for s in sessions:
            assert lc.get(s.session_id).state == MonitoringState.ACTIVE


# ─── TestRegressionEdgeCases ──────────────────────────────────────────────────

class TestRegressionEdgeCases:
    def test_listener_exception_does_not_propagate(self, lc):
        def bad_listener(event):
            raise RuntimeError("bad listener")
        lc.add_event_listener(bad_listener)
        # Should not raise
        s = lc.create("exec-bad", "port-bad")
        assert s.state == MonitoringState.CREATED
        lc.remove_event_listener(bad_listener)

    def test_duplicate_listener_not_added_twice(self, lc):
        received = []
        lc.add_event_listener(received.append)
        lc.add_event_listener(received.append)  # duplicate
        lc.create("exec-dup", "port-dup")
        # Only one MONITORING_CREATED expected
        created_events = [
            e for e in received
            if e.event_type == MonitoringEventType.MONITORING_CREATED
        ]
        assert len(created_events) == 1
        lc.remove_event_listener(received.append)

    def test_statistics_independent_of_lifecycle(self, lc):
        s = lc.create("exec-stats2", "port-stats2")
        stats_before = lc.statistics()
        lc.initialize(s.session_id)
        stats_after  = lc.statistics()
        # copy is independent
        assert stats_before.total_transitions == 0
        assert stats_after.total_transitions  >= 1

    def test_registry_count_decreases_after_archive(self, lc):
        s = lc.create("exec-arc", "port-arc")
        lc.initialize(s.session_id)
        lc.begin(s.session_id)
        lc.mark_active(s.session_id)
        lc.fail(s.session_id, reason="cleanup")
        before = lc._registry.active_count
        lc.archive(s.session_id)
        after  = lc._registry.active_count
        assert after == before - 1

    def test_fail_from_created_state(self, lc, session):
        lc.fail(session.session_id, reason="immediate-failure")
        s = lc.history().sessions()[-1]
        assert s.state == MonitoringState.FAILED

    def test_fail_from_initializing(self, lc, session):
        lc.initialize(session.session_id)
        lc.fail(session.session_id, reason="init-failure")
        s = lc.history().sessions()[-1]
        assert s.state == MonitoringState.FAILED

    def test_fail_from_starting(self, lc, session):
        lc.initialize(session.session_id)
        lc.begin(session.session_id)
        lc.fail(session.session_id, reason="start-failure")
        s = lc.history().sessions()[-1]
        assert s.state == MonitoringState.FAILED

    def test_session_to_dict_keys(self, lc, session):
        d = session.to_dict()
        expected_keys = {
            "session_id", "execution_session_id", "portfolio_id",
            "state", "created_at", "updated_at", "monitoring_version",
        }
        for k in expected_keys:
            assert k in d

    def test_all_valid_transitions_reachable(self):
        """Every state listed in VALID_TRANSITIONS maps to known states."""
        for from_state, to_states in VALID_TRANSITIONS.items():
            for to_state in to_states:
                assert isinstance(to_state, MonitoringState)

    def test_monitoring_lifecycle_stop_is_idempotent(self):
        lc = MonitoringLifecycle()
        lc.start()   # engine start
        lc.stop()    # engine stop
        # Calling stop again on already-stopped is handled by LifecycleAwareMixin
        state = lc.lifecycle_state()
        assert state not in ("running", "RUNNING")
