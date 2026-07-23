"""
test_supervisor_lifecycle.py
=============================
Unit tests for C13 M1 — AI Supervisor Lifecycle.

Coverage:
  Constants, Exceptions, Session, State, Transition,
  Context, Metadata, Events, Factory, History,
  Statistics, Registry, Validation, Lifecycle,
  Concurrency, Regression

Target: 95%+ coverage.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List

import pytest

from iios.supervisor.lifecycle import (
    # Primary interface
    SupervisorLifecycle,
    # Session
    SupervisorSession,
    # Value objects
    SupervisorContext,
    SupervisorMetadata,
    SupervisorStateRecord,
    SupervisorTransition,
    # Events
    SupervisorEvent,
    SupervisorEventType,
    make_supervisor_archived,
    make_supervisor_completed,
    make_supervisor_created,
    make_supervisor_failed,
    make_supervisor_initialized,
    make_supervisor_monitoring_started,
    make_supervisor_paused,
    make_supervisor_resumed,
    make_supervisor_started,
    make_supervisor_validated,
    # Factory / Registry
    SupervisorFactory,
    SupervisorHistory,
    SupervisorRegistry,
    SupervisorStatistics,
    # Validation
    SupervisorValidationCheckResult,
    SupervisorValidationResult,
    SupervisorValidator,
    SupervisorValidationCode,
    # State helpers
    can_transition,
    make_transition,
    # Enums
    SupervisorPriority,
    SupervisorScope,
    SupervisorState,
    SupervisorType,
    # Constants
    ACTIVE_STATES,
    TERMINAL_STATES,
    IMMUTABLE_STATES,
    SUCCESS_STATES,
    VALID_TRANSITIONS,
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    # Exceptions
    SupervisorCapacityExceededError,
    SupervisorHistoryError,
    SupervisorInvalidTransitionError,
    SupervisorLifecycleError,
    SupervisorLifecycleNotRunningError,
    SupervisorRegistryError,
    SupervisorSessionNotFoundError,
    SupervisorSessionTerminatedError,
    SupervisorValidationError,
    SupervisorConfigurationError,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_session(
    supervisor_id: str = "SUP-001",
    workflow_id:   str = "WF-001",
    **kwargs,
) -> SupervisorSession:
    f = SupervisorFactory()
    return f.create(supervisor_id, workflow_id=workflow_id, **kwargs)


def _full_lc() -> SupervisorLifecycle:
    lc = SupervisorLifecycle()
    lc.start()
    return lc


def _advance_to_supervising(lc: SupervisorLifecycle, sid: str) -> None:
    lc.initialize(sid)
    lc.discover(sid)
    lc.validate_session(sid)
    lc.mark_ready(sid)
    lc.start_supervising(sid)


def _advance_to_monitoring(lc: SupervisorLifecycle, sid: str) -> None:
    _advance_to_supervising(lc, sid)
    lc.start_monitoring(sid)


# ============================================================================
# 1. Constants
# ============================================================================

class TestConstants:
    def test_state_values(self):
        assert SupervisorState.CREATED.value      == "created"
        assert SupervisorState.INITIALIZING.value == "initializing"
        assert SupervisorState.DISCOVERING.value  == "discovering"
        assert SupervisorState.VALIDATING.value   == "validating"
        assert SupervisorState.READY.value        == "ready"
        assert SupervisorState.SUPERVISING.value  == "supervising"
        assert SupervisorState.MONITORING.value   == "monitoring"
        assert SupervisorState.PAUSED.value       == "paused"
        assert SupervisorState.RESUMING.value     == "resuming"
        assert SupervisorState.COMPLETED.value    == "completed"
        assert SupervisorState.FAILED.value       == "failed"
        assert SupervisorState.ARCHIVED.value     == "archived"

    def test_exactly_twelve_states(self):
        assert len(SupervisorState) == 12

    def test_active_states_count(self):
        assert len(ACTIVE_STATES) == 8

    def test_terminal_states(self):
        assert TERMINAL_STATES == frozenset({
            SupervisorState.COMPLETED,
            SupervisorState.FAILED,
            SupervisorState.ARCHIVED,
        })

    def test_immutable_states(self):
        assert IMMUTABLE_STATES == frozenset({SupervisorState.ARCHIVED})

    def test_success_states(self):
        assert SupervisorState.COMPLETED in SUCCESS_STATES
        assert SupervisorState.ARCHIVED in SUCCESS_STATES

    def test_valid_transitions_coverage(self):
        # Every state must appear as a key
        for state in SupervisorState:
            assert state in VALID_TRANSITIONS

    def test_archived_is_terminal(self):
        assert VALID_TRANSITIONS[SupervisorState.ARCHIVED] == frozenset()

    def test_supervisor_type_values(self):
        assert SupervisorType.PROCESS.value    == "process"
        assert SupervisorType.RISK.value       == "risk"
        assert SupervisorType.GOVERNANCE.value == "governance"

    def test_supervisor_scope_values(self):
        assert SupervisorScope.ENTERPRISE.value == "enterprise"
        assert SupervisorScope.SYSTEM.value     == "system"

    def test_priority_values(self):
        assert SupervisorPriority.CRITICAL.value == "critical"
        assert SupervisorPriority.LOW.value      == "low"

    def test_event_types_count(self):
        assert len(SupervisorEventType) == 10

    def test_validation_codes_count(self):
        assert len(SupervisorValidationCode) == 5

    def test_lifecycle_system_id(self):
        assert LIFECYCLE_SYSTEM_ID == "iios:supervisor:lifecycle"

    def test_version(self):
        assert VERSION == "1.0.0"


# ============================================================================
# 2. Exceptions
# ============================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        err = SupervisorLifecycleError("test")
        assert isinstance(err, IIOSError)

    def test_base_error_code(self):
        err = SupervisorLifecycleError("msg")
        assert "SL-000" in str(err.code)

    def test_not_found_stores_session_id(self):
        err = SupervisorSessionNotFoundError("ses-123")
        assert err.session_id == "ses-123"
        assert "SL-001" in str(err.code)

    def test_invalid_transition_stores_states(self):
        err = SupervisorInvalidTransitionError(
            from_state = SupervisorState.CREATED,
            to_state   = SupervisorState.COMPLETED,
            session_id = "ses-x",
        )
        assert err.from_state == SupervisorState.CREATED
        assert err.to_state   == SupervisorState.COMPLETED
        assert "SL-002" in str(err.code)

    def test_terminated_error(self):
        err = SupervisorSessionTerminatedError("s1", "archived")
        assert "SL-003" in str(err.code)

    def test_not_running_default_message(self):
        err = SupervisorLifecycleNotRunningError()
        assert "not running" in str(err).lower()
        assert "SL-004" in str(err.code)

    def test_capacity_stores_limit(self):
        err = SupervisorCapacityExceededError(100)
        assert err.limit == 100
        assert "SL-005" in str(err.code)

    def test_validation_error_code(self):
        assert "SL-006" in str(SupervisorValidationError().code)

    def test_history_error_code(self):
        assert "SL-007" in str(SupervisorHistoryError().code)

    def test_registry_error_code(self):
        assert "SL-008" in str(SupervisorRegistryError().code)

    def test_configuration_error_code(self):
        assert "SL-009" in str(SupervisorConfigurationError().code)

    def test_hierarchy(self):
        for cls in [
            SupervisorSessionNotFoundError,
            SupervisorInvalidTransitionError,
            SupervisorSessionTerminatedError,
            SupervisorLifecycleNotRunningError,
            SupervisorCapacityExceededError,
            SupervisorValidationError,
            SupervisorHistoryError,
            SupervisorRegistryError,
            SupervisorConfigurationError,
        ]:
            assert issubclass(cls, SupervisorLifecycleError)


# ============================================================================
# 3. SupervisorState / can_transition
# ============================================================================

class TestSupervisorState:
    def test_can_transition_valid(self):
        assert can_transition(SupervisorState.CREATED, SupervisorState.INITIALIZING)
        assert can_transition(SupervisorState.INITIALIZING, SupervisorState.DISCOVERING)
        assert can_transition(SupervisorState.DISCOVERING, SupervisorState.VALIDATING)
        assert can_transition(SupervisorState.VALIDATING, SupervisorState.READY)
        assert can_transition(SupervisorState.READY, SupervisorState.SUPERVISING)
        assert can_transition(SupervisorState.SUPERVISING, SupervisorState.MONITORING)
        assert can_transition(SupervisorState.MONITORING, SupervisorState.COMPLETED)
        assert can_transition(SupervisorState.COMPLETED, SupervisorState.ARCHIVED)

    def test_can_transition_invalid(self):
        assert not can_transition(SupervisorState.CREATED, SupervisorState.COMPLETED)
        assert not can_transition(SupervisorState.ARCHIVED, SupervisorState.CREATED)
        assert not can_transition(SupervisorState.COMPLETED, SupervisorState.SUPERVISING)

    def test_can_transition_fail_paths(self):
        for state in SupervisorState:
            if state not in IMMUTABLE_STATES and state not in TERMINAL_STATES:
                assert can_transition(state, SupervisorState.FAILED)

    def test_state_record_to_dict(self):
        rec = SupervisorStateRecord(
            state      = SupervisorState.READY,
            entered_at = 1000.0,
            actor      = "test",
            reason     = "r",
        )
        d = rec.to_dict()
        assert d["state"] == "ready"
        assert d["entered_at"] == 1000.0
        assert d["actor"] == "test"


# ============================================================================
# 4. SupervisorTransition
# ============================================================================

class TestSupervisorTransition:
    def test_make_transition(self):
        t = make_transition(
            "ses-1",
            SupervisorState.CREATED,
            SupervisorState.INITIALIZING,
        )
        assert t.session_id  == "ses-1"
        assert t.from_state  == SupervisorState.CREATED
        assert t.to_state    == SupervisorState.INITIALIZING
        assert len(t.transition_id) > 0

    def test_transition_is_frozen(self):
        t = make_transition("s", SupervisorState.CREATED, SupervisorState.INITIALIZING)
        with pytest.raises((AttributeError, TypeError)):
            t.session_id = "other"  # type: ignore

    def test_to_dict(self):
        t = make_transition("s", SupervisorState.READY, SupervisorState.SUPERVISING)
        d = t.to_dict()
        assert d["from_state"] == "ready"
        assert d["to_state"]   == "supervising"


# ============================================================================
# 5. SupervisorContext
# ============================================================================

class TestSupervisorContext:
    def test_create_default(self):
        ctx = SupervisorContext.create("sup-001")
        assert ctx.supervisor_id       == "sup-001"
        assert ctx.supervisor_type     == SupervisorType.CUSTOM
        assert ctx.supervisor_scope    == SupervisorScope.SYSTEM
        assert ctx.supervisor_priority == SupervisorPriority.MEDIUM
        assert ctx.context_id != ""

    def test_create_custom(self):
        ctx = SupervisorContext.create(
            "sup-002",
            supervisor_type     = SupervisorType.RISK,
            supervisor_scope    = SupervisorScope.ENTERPRISE,
            supervisor_priority = SupervisorPriority.CRITICAL,
            tags                = {"env": "prod"},
        )
        assert ctx.supervisor_type     == SupervisorType.RISK
        assert ctx.supervisor_scope    == SupervisorScope.ENTERPRISE
        assert ctx.supervisor_priority == SupervisorPriority.CRITICAL
        assert ctx.tags["env"]         == "prod"

    def test_is_frozen(self):
        ctx = SupervisorContext.create("sup-003")
        with pytest.raises((AttributeError, TypeError)):
            ctx.supervisor_id = "other"  # type: ignore

    def test_to_dict(self):
        ctx = SupervisorContext.create("sup-004")
        d = ctx.to_dict()
        assert d["supervisor_id"] == "sup-004"
        assert "supervisor_type" in d
        assert "supervisor_scope" in d


# ============================================================================
# 6. SupervisorMetadata
# ============================================================================

class TestSupervisorMetadata:
    def test_create_default(self):
        m = SupervisorMetadata.create(supervisor_id="sup-x")
        assert m.supervisor_id == "sup-x"
        assert m.source        == ""
        assert isinstance(m.tags, dict)

    def test_to_dict(self):
        m = SupervisorMetadata.create(supervisor_id="sup-y", notes="n")
        d = m.to_dict()
        assert d["supervisor_id"] == "sup-y"
        assert d["notes"]         == "n"

    def test_is_frozen(self):
        m = SupervisorMetadata.create()
        with pytest.raises((AttributeError, TypeError)):
            m.supervisor_id = "x"  # type: ignore


# ============================================================================
# 7. SupervisorSession
# ============================================================================

class TestSupervisorSession:
    def test_created_state_on_init(self):
        s = _make_session()
        assert s.state == SupervisorState.CREATED

    def test_is_active_in_created(self):
        s = _make_session()
        assert not s.is_active   # CREATED is not in ACTIVE_STATES
        assert not s.is_terminal

    def test_initial_properties(self):
        s = _make_session(supervisor_id="SUP-XYZ", workflow_id="WF-ABC")
        assert s.supervisor_id == "SUP-XYZ"
        assert s.workflow_id   == "WF-ABC"
        assert s.supervisor_version == 1

    def test_transition_to_initializing(self):
        s = _make_session()
        t = s.transition_to(SupervisorState.INITIALIZING)
        assert s.state == SupervisorState.INITIALIZING
        assert t.from_state == SupervisorState.CREATED
        assert t.to_state   == SupervisorState.INITIALIZING
        assert s.supervisor_version == 2

    def test_invalid_transition_raises(self):
        s = _make_session()
        with pytest.raises(SupervisorInvalidTransitionError):
            s.transition_to(SupervisorState.SUPERVISING)

    def test_archived_is_immutable(self):
        s = _make_session()
        for state in [
            SupervisorState.INITIALIZING,
            SupervisorState.DISCOVERING,
            SupervisorState.VALIDATING,
            SupervisorState.READY,
            SupervisorState.SUPERVISING,
            SupervisorState.COMPLETED,
            SupervisorState.ARCHIVED,
        ]:
            s.transition_to(state)
        with pytest.raises(SupervisorSessionTerminatedError):
            s.transition_to(SupervisorState.FAILED)

    def test_mark_failed(self):
        s = _make_session()
        s.transition_to(SupervisorState.INITIALIZING)
        s.mark_failed(reason="test failure")
        assert s.state          == SupervisorState.FAILED
        assert s.failure_reason == "test failure"

    def test_duration_none_before_completion(self):
        s = _make_session()
        assert s.duration_s is None

    def test_start_time_set_on_supervising(self):
        s = _make_session()
        for state in [
            SupervisorState.INITIALIZING,
            SupervisorState.DISCOVERING,
            SupervisorState.VALIDATING,
            SupervisorState.READY,
            SupervisorState.SUPERVISING,
        ]:
            s.transition_to(state)
        assert s.start_time is not None

    def test_end_time_set_on_completed(self):
        s = _make_session()
        for state in [
            SupervisorState.INITIALIZING,
            SupervisorState.DISCOVERING,
            SupervisorState.VALIDATING,
            SupervisorState.READY,
            SupervisorState.SUPERVISING,
            SupervisorState.COMPLETED,
        ]:
            s.transition_to(state)
        assert s.end_time is not None
        assert s.duration_s is not None
        assert s.duration_s >= 0.0

    def test_state_history_immutability(self):
        s = _make_session()
        history = s.state_history
        history.append(None)  # type: ignore
        assert len(s.state_history) == 1  # original unchanged

    def test_transitions_list_is_copy(self):
        s = _make_session()
        s.transition_to(SupervisorState.INITIALIZING)
        txns = s.transitions
        txns.clear()
        assert len(s.transitions) == 1

    def test_to_dict(self):
        s = _make_session()
        d = s.to_dict()
        assert d["state"]        == "created"
        assert d["supervisor_id"] == "SUP-001"
        assert "created_at" in d
        assert "updated_at" in d

    def test_metadata_copy_on_read(self):
        s = _make_session(metadata={"k": "v"})
        m = s.metadata
        m["k"] = "changed"
        assert s.metadata["k"] == "v"


# ============================================================================
# 8. SupervisorEvents
# ============================================================================

class TestSupervisorEvents:
    def _check_event(self, ev, expected_type, expected_state):
        assert isinstance(ev, SupervisorEvent)
        assert ev.event_type  == expected_type
        assert ev.state       == expected_state
        assert ev.session_id  == "ses-1"
        assert len(ev.event_id) > 0

    def test_make_supervisor_created(self):
        ev = make_supervisor_created("ses-1", "sup-1")
        self._check_event(ev, SupervisorEventType.SUPERVISOR_CREATED, SupervisorState.CREATED)

    def test_make_supervisor_initialized(self):
        ev = make_supervisor_initialized("ses-1", "sup-1")
        self._check_event(ev, SupervisorEventType.SUPERVISOR_INITIALIZED, SupervisorState.INITIALIZING)

    def test_make_supervisor_validated(self):
        ev = make_supervisor_validated("ses-1", "sup-1")
        self._check_event(ev, SupervisorEventType.SUPERVISOR_VALIDATED, SupervisorState.VALIDATING)

    def test_make_supervisor_started(self):
        ev = make_supervisor_started("ses-1", "sup-1")
        self._check_event(ev, SupervisorEventType.SUPERVISOR_STARTED, SupervisorState.SUPERVISING)

    def test_make_supervisor_monitoring_started(self):
        ev = make_supervisor_monitoring_started("ses-1", "sup-1")
        self._check_event(ev, SupervisorEventType.SUPERVISOR_MONITORING_STARTED, SupervisorState.MONITORING)

    def test_make_supervisor_paused(self):
        ev = make_supervisor_paused("ses-1", "sup-1")
        self._check_event(ev, SupervisorEventType.SUPERVISOR_PAUSED, SupervisorState.PAUSED)

    def test_make_supervisor_resumed(self):
        ev = make_supervisor_resumed("ses-1", "sup-1")
        self._check_event(ev, SupervisorEventType.SUPERVISOR_RESUMED, SupervisorState.RESUMING)

    def test_make_supervisor_completed(self):
        ev = make_supervisor_completed("ses-1", "sup-1")
        self._check_event(ev, SupervisorEventType.SUPERVISOR_COMPLETED, SupervisorState.COMPLETED)

    def test_make_supervisor_failed(self):
        ev = make_supervisor_failed("ses-1", "sup-1")
        self._check_event(ev, SupervisorEventType.SUPERVISOR_FAILED, SupervisorState.FAILED)

    def test_make_supervisor_archived(self):
        ev = make_supervisor_archived("ses-1", "sup-1")
        self._check_event(ev, SupervisorEventType.SUPERVISOR_ARCHIVED, SupervisorState.ARCHIVED)

    def test_event_is_frozen(self):
        ev = make_supervisor_created("ses-1", "sup-1")
        with pytest.raises((AttributeError, TypeError)):
            ev.event_id = "new"  # type: ignore

    def test_event_to_dict(self):
        ev = make_supervisor_started("ses-2", "sup-2", "wf-2", payload={"k": "v"})
        d = ev.to_dict()
        assert d["session_id"]    == "ses-2"
        assert d["supervisor_id"] == "sup-2"
        assert d["workflow_id"]   == "wf-2"
        assert d["payload"]["k"]  == "v"

    def test_event_unique_ids(self):
        ids = {make_supervisor_created("s", "x").event_id for _ in range(20)}
        assert len(ids) == 20


# ============================================================================
# 9. SupervisorFactory
# ============================================================================

class TestSupervisorFactory:
    def test_create_basic(self):
        f = SupervisorFactory()
        s = f.create("sup-001")
        assert s.supervisor_id == "sup-001"
        assert s.state         == SupervisorState.CREATED

    def test_create_rejects_empty_id(self):
        with pytest.raises(ValueError):
            SupervisorFactory().create("")

    def test_create_custom_fields(self):
        s = SupervisorFactory().create(
            "sup-002",
            supervisor_type     = SupervisorType.RISK,
            supervisor_scope    = SupervisorScope.ENTERPRISE,
            supervisor_priority = SupervisorPriority.CRITICAL,
        )
        assert s.supervisor_type     == SupervisorType.RISK
        assert s.supervisor_scope    == SupervisorScope.ENTERPRISE
        assert s.supervisor_priority == SupervisorPriority.CRITICAL

    def test_create_explicit_session_id(self):
        sid = "explicit-ses-id"
        s   = SupervisorFactory().create("sup-x", session_id=sid)
        assert s.session_id == sid

    def test_create_auto_session_id(self):
        s = SupervisorFactory().create("sup-y")
        assert len(s.session_id) > 0

    def test_consecutive_ids_are_unique(self):
        f = SupervisorFactory()
        ids = {f.create("sup-z").session_id for _ in range(10)}
        assert len(ids) == 10


# ============================================================================
# 10. SupervisorHistory
# ============================================================================

class TestSupervisorHistory:
    def test_record_and_retrieve_events(self):
        h  = SupervisorHistory()
        ev = make_supervisor_created("s1", "sup1")
        h.record_event(ev)
        assert h.event_count() == 1
        assert h.events()[0] is ev

    def test_latest_event_none_when_empty(self):
        assert SupervisorHistory().latest_event() is None

    def test_events_for_session(self):
        h  = SupervisorHistory()
        e1 = make_supervisor_created("s1", "sup1")
        e2 = make_supervisor_created("s2", "sup2")
        h.record_event(e1)
        h.record_event(e2)
        assert len(h.events_for_session("s1")) == 1
        assert len(h.events_for_session("s2")) == 1

    def test_events_for_supervisor(self):
        h  = SupervisorHistory()
        e1 = make_supervisor_created("s1", "sup-A")
        e2 = make_supervisor_initialized("s2", "sup-A")
        e3 = make_supervisor_created("s3", "sup-B")
        h.record_event(e1)
        h.record_event(e2)
        h.record_event(e3)
        assert len(h.events_for_supervisor("sup-A")) == 2

    def test_events_by_type(self):
        h = SupervisorHistory()
        h.record_event(make_supervisor_created("s1", "x"))
        h.record_event(make_supervisor_created("s2", "x"))
        h.record_event(make_supervisor_initialized("s3", "x"))
        results = h.events_by_type(SupervisorEventType.SUPERVISOR_CREATED)
        assert len(results) == 2

    def test_transitions_record_and_retrieve(self):
        h = SupervisorHistory()
        t = make_transition("s1", SupervisorState.CREATED, SupervisorState.INITIALIZING)
        h.record_transition(t)
        assert h.transition_count() == 1
        assert h.transitions_for_session("s1")[0] is t

    def test_bounded_by_maxlen(self):
        h = SupervisorHistory(max_events=3)
        for i in range(5):
            h.record_event(make_supervisor_created(f"s{i}", "x"))
        assert h.event_count() == 3

    def test_clear(self):
        h = SupervisorHistory()
        h.record_event(make_supervisor_created("s", "x"))
        h.record_transition(
            make_transition("s", SupervisorState.CREATED, SupervisorState.INITIALIZING)
        )
        h.clear()
        assert h.event_count()      == 0
        assert h.transition_count() == 0


# ============================================================================
# 11. SupervisorStatistics
# ============================================================================

class TestSupervisorStatistics:
    def test_initial_zeros(self):
        s = SupervisorStatistics().snapshot()
        assert s["supervisor_sessions_created"]   == 0
        assert s["supervisor_sessions_completed"] == 0
        assert s["supervisor_sessions_failed"]    == 0
        assert s["supervisor_sessions_archived"]  == 0
        assert s["transition_count"]              == 0

    def test_record_created(self):
        st = SupervisorStatistics()
        st.record_session_created()
        st.record_session_created()
        assert st.snapshot()["supervisor_sessions_created"] == 2

    def test_record_completed_with_duration(self):
        st = SupervisorStatistics()
        st.record_session_completed(duration_s=1.0)
        st.record_session_completed(duration_s=3.0)
        snap = st.snapshot()
        assert snap["supervisor_sessions_completed"] == 2
        assert snap["average_session_duration_s"] == pytest.approx(2.0, abs=0.01)

    def test_record_failed(self):
        st = SupervisorStatistics()
        st.record_session_failed()
        assert st.snapshot()["supervisor_sessions_failed"] == 1

    def test_record_archived(self):
        st = SupervisorStatistics()
        st.record_session_archived()
        assert st.snapshot()["supervisor_sessions_archived"] == 1

    def test_transition_count(self):
        st = SupervisorStatistics()
        for _ in range(5):
            st.record_transition()
        assert st.snapshot()["transition_count"] == 5

    def test_uptime_positive(self):
        st = SupervisorStatistics()
        time.sleep(0.01)
        assert st.snapshot()["uptime_s"] > 0

    def test_ema_duration(self):
        st = SupervisorStatistics()
        st.record_session_completed(duration_s=10.0)
        snap = st.snapshot()
        assert snap["ema_session_duration_s"] == pytest.approx(10.0, abs=0.01)

    def test_reset(self):
        st = SupervisorStatistics()
        st.record_session_created()
        st.record_session_failed()
        st.reset()
        snap = st.snapshot()
        assert snap["supervisor_sessions_created"] == 0
        assert snap["supervisor_sessions_failed"]  == 0


# ============================================================================
# 12. SupervisorRegistry
# ============================================================================

class TestSupervisorRegistry:
    def test_add_and_get(self):
        reg = SupervisorRegistry()
        s   = _make_session()
        reg.add(s)
        assert reg.get(s.session_id) is s

    def test_get_not_found_raises(self):
        with pytest.raises(SupervisorSessionNotFoundError):
            SupervisorRegistry().get("missing")

    def test_find_returns_none(self):
        assert SupervisorRegistry().find("missing") is None

    def test_duplicate_raises(self):
        reg = SupervisorRegistry()
        s   = _make_session()
        reg.add(s)
        with pytest.raises(SupervisorRegistryError):
            reg.add(s)

    def test_capacity_exceeded(self):
        reg = SupervisorRegistry(max_active_sessions=2)
        reg.add(_make_session(supervisor_id="a", session_id="a1"))
        reg.add(_make_session(supervisor_id="b", session_id="b1"))
        with pytest.raises(SupervisorCapacityExceededError):
            reg.add(_make_session(supervisor_id="c", session_id="c1"))

    def test_archive(self):
        reg = SupervisorRegistry()
        s   = _make_session()
        reg.add(s)
        reg.archive(s.session_id)
        assert reg.active_count   == 0
        assert reg.archived_count == 1
        # still retrievable
        assert reg.get(s.session_id) is s

    def test_archive_missing_raises(self):
        with pytest.raises(SupervisorSessionNotFoundError):
            SupervisorRegistry().archive("missing")

    def test_get_active_raises_for_archived(self):
        reg = SupervisorRegistry()
        s   = _make_session()
        reg.add(s)
        reg.archive(s.session_id)
        with pytest.raises(SupervisorSessionNotFoundError):
            reg.get_active(s.session_id)

    def test_sessions_by_state(self):
        reg = SupervisorRegistry()
        s1  = _make_session(supervisor_id="a", session_id="a1")
        s2  = _make_session(supervisor_id="b", session_id="b1")
        reg.add(s1)
        reg.add(s2)
        s1.transition_to(SupervisorState.INITIALIZING)
        assert len(reg.sessions_by_state(SupervisorState.INITIALIZING)) == 1
        assert len(reg.sessions_by_state(SupervisorState.CREATED))      == 1

    def test_sessions_by_type(self):
        reg = SupervisorRegistry()
        s   = SupervisorFactory().create("sup-001", supervisor_type=SupervisorType.RISK)
        reg.add(s)
        assert len(reg.sessions_by_type(SupervisorType.RISK))   == 1
        assert len(reg.sessions_by_type(SupervisorType.CUSTOM)) == 0

    def test_sessions_by_scope(self):
        reg = SupervisorRegistry()
        s   = SupervisorFactory().create("sup-001", supervisor_scope=SupervisorScope.ENTERPRISE)
        reg.add(s)
        assert len(reg.sessions_by_scope(SupervisorScope.ENTERPRISE)) == 1

    def test_sessions_by_workflow(self):
        reg = SupervisorRegistry()
        s   = SupervisorFactory().create("sup-001", workflow_id="wf-x")
        reg.add(s)
        assert len(reg.sessions_by_workflow("wf-x"))   == 1
        assert len(reg.sessions_by_workflow("wf-other")) == 0

    def test_clear(self):
        reg = SupervisorRegistry()
        reg.add(_make_session(supervisor_id="a", session_id="a1"))
        reg.clear()
        assert reg.active_count == 0

    def test_fifo_archive_eviction(self):
        reg = SupervisorRegistry(max_archived_sessions=2)
        for i in range(4):
            s = _make_session(supervisor_id=f"x{i}", session_id=f"s{i}")
            reg.add(s)
            reg.archive(s.session_id)
        assert reg.archived_count == 2


# ============================================================================
# 13. SupervisorValidation
# ============================================================================

class TestSupervisorValidation:
    def test_fresh_session_is_valid(self):
        s = _make_session()
        r = SupervisorValidator().validate(s)
        assert r.is_valid
        assert r.failed_count == 0
        assert r.passed_count == 5

    def test_validation_result_structure(self):
        s = _make_session()
        r = SupervisorValidator().validate(s)
        assert len(r.checks) == 5
        assert r.error_messages == []

    def test_empty_supervisor_id_fails_identifier(self):
        s = _make_session(supervisor_id="SUP-001")
        # Patch to simulate empty id
        s._supervisor_id = ""  # type: ignore
        r = SupervisorValidator().validate(s)
        assert not r.is_valid
        codes = [c.code for c in r.failed_checks]
        assert SupervisorValidationCode.IDENTIFIER_CONSISTENCY in codes

    def test_non_created_without_transitions_fails(self):
        s = _make_session()
        s._state        = SupervisorState.READY  # type: ignore
        s._transitions  = []  # type: ignore
        r = SupervisorValidator().validate(s)
        assert not r.is_valid

    def test_timestamp_inversion_fails(self):
        s = _make_session()
        s._updated_at = s._created_at - 1.0  # type: ignore
        r = SupervisorValidator().validate(s)
        assert not r.is_valid

    def test_history_mismatch_fails(self):
        s = _make_session()
        # Force state mismatch
        s._state = SupervisorState.SUPERVISING  # type: ignore
        r = SupervisorValidator().validate(s)
        assert not r.is_valid

    def test_error_messages_populated(self):
        s = _make_session()
        s._supervisor_id = ""  # type: ignore
        r = SupervisorValidator().validate(s)
        assert len(r.error_messages) >= 1


# ============================================================================
# 14. SupervisorLifecycle — start/stop/guard
# ============================================================================

class TestSupervisorLifecycleGuard:
    def test_create_before_start_raises(self):
        lc = SupervisorLifecycle()
        with pytest.raises(SupervisorLifecycleNotRunningError):
            lc.create("sup-001")

    def test_start_and_stop(self):
        lc = SupervisorLifecycle()
        lc.start()
        assert lc.lifecycle_state().value == "running"
        lc.stop()
        assert lc.lifecycle_state().value != "running"

    def test_create_after_stop_raises(self):
        lc = SupervisorLifecycle()
        lc.start()
        lc.stop()
        with pytest.raises(SupervisorLifecycleNotRunningError):
            lc.create("sup-001")


# ============================================================================
# 15. SupervisorLifecycle — happy path
# ============================================================================

class TestSupervisorLifecycleHappyPath:
    def setup_method(self):
        self.lc = _full_lc()

    def teardown_method(self):
        self.lc.stop()

    def test_full_happy_path(self):
        s = self.lc.create("sup-001", workflow_id="wf-001")
        assert s.state == SupervisorState.CREATED

        self.lc.initialize(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.INITIALIZING

        self.lc.discover(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.DISCOVERING

        self.lc.validate_session(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.VALIDATING

        self.lc.mark_ready(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.READY

        self.lc.start_supervising(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.SUPERVISING

        self.lc.start_monitoring(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.MONITORING

        self.lc.complete(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.COMPLETED

        self.lc.archive(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.ARCHIVED

    def test_fail_path(self):
        s = self.lc.create("sup-fail")
        self.lc.initialize(s.session_id)
        self.lc.fail(s.session_id, reason="test error")
        sess = self.lc.get_session(s.session_id)
        assert sess.state          == SupervisorState.FAILED
        assert sess.failure_reason == "test error"

    def test_pause_resume_path(self):
        s = self.lc.create("sup-pause")
        _advance_to_supervising(self.lc, s.session_id)
        self.lc.pause(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.PAUSED
        self.lc.resume(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.RESUMING
        self.lc.start_supervising(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.SUPERVISING

    def test_rediscover_path(self):
        """VALIDATING → DISCOVERING re-discover path."""
        s = self.lc.create("sup-redis")
        self.lc.initialize(s.session_id)
        self.lc.discover(s.session_id)
        self.lc.validate_session(s.session_id)
        # Re-discover from VALIDATING
        self.lc.discover(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.DISCOVERING

    def test_monitoring_back_to_supervising(self):
        """MONITORING → SUPERVISING re-supervise path."""
        s = self.lc.create("sup-resup")
        _advance_to_monitoring(self.lc, s.session_id)
        self.lc.start_supervising(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.SUPERVISING

    def test_resume_to_monitoring(self):
        """PAUSED → RESUMING → MONITORING path."""
        s = self.lc.create("sup-resmon")
        _advance_to_monitoring(self.lc, s.session_id)
        self.lc.pause(s.session_id)
        self.lc.resume(s.session_id)
        self.lc.start_monitoring(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.MONITORING

    def test_resume_to_ready(self):
        """PAUSED → RESUMING → READY path."""
        s = self.lc.create("sup-resready")
        self.lc.initialize(s.session_id)
        self.lc.discover(s.session_id)
        self.lc.validate_session(s.session_id)
        self.lc.mark_ready(s.session_id)
        self.lc.pause(s.session_id)
        self.lc.resume(s.session_id)
        self.lc.mark_ready(s.session_id)
        assert self.lc.get_session(s.session_id).state == SupervisorState.READY


# ============================================================================
# 16. SupervisorLifecycle — queries
# ============================================================================

class TestSupervisorLifecycleQuery:
    def setup_method(self):
        self.lc = _full_lc()

    def teardown_method(self):
        self.lc.stop()

    def test_active_sessions(self):
        s1 = self.lc.create("sup-q1")
        s2 = self.lc.create("sup-q2")
        active = self.lc.active_sessions()
        assert len(active) == 2

    def test_sessions_by_state(self):
        s1 = self.lc.create("sup-a")
        s2 = self.lc.create("sup-b")
        self.lc.initialize(s1.session_id)
        result = self.lc.sessions_by_state(SupervisorState.INITIALIZING)
        assert len(result) == 1

    def test_sessions_by_type(self):
        self.lc.create("sup-risk", supervisor_type=SupervisorType.RISK)
        self.lc.create("sup-custom")
        assert len(self.lc.sessions_by_type(SupervisorType.RISK)) == 1

    def test_sessions_by_scope(self):
        self.lc.create("sup-ent", supervisor_scope=SupervisorScope.ENTERPRISE)
        self.lc.create("sup-sys")
        assert len(self.lc.sessions_by_scope(SupervisorScope.ENTERPRISE)) == 1

    def test_sessions_by_workflow(self):
        self.lc.create("sup-wf1", workflow_id="wf-x")
        self.lc.create("sup-wf2", workflow_id="wf-y")
        assert len(self.lc.sessions_by_workflow("wf-x")) == 1

    def test_find_session_returns_none(self):
        assert self.lc.find_session("missing") is None

    def test_get_session_raises_not_found(self):
        with pytest.raises(SupervisorSessionNotFoundError):
            self.lc.get_session("missing")


# ============================================================================
# 17. SupervisorLifecycle — events & listeners
# ============================================================================

class TestSupervisorLifecycleEvents:
    def setup_method(self):
        self.lc = _full_lc()

    def teardown_method(self):
        self.lc.stop()

    def test_create_emits_created_event(self):
        received = []
        self.lc.add_listener(received.append)
        s = self.lc.create("sup-ev")
        assert any(e.event_type == SupervisorEventType.SUPERVISOR_CREATED for e in received)

    def test_initialize_emits_initialized_event(self):
        received = []
        s = self.lc.create("sup-init")
        self.lc.add_listener(received.append)
        self.lc.initialize(s.session_id)
        assert any(e.event_type == SupervisorEventType.SUPERVISOR_INITIALIZED for e in received)

    def test_validate_session_emits_validated(self):
        received = []
        s = self.lc.create("sup-val")
        self.lc.initialize(s.session_id)
        self.lc.discover(s.session_id)
        self.lc.add_listener(received.append)
        self.lc.validate_session(s.session_id)
        assert any(e.event_type == SupervisorEventType.SUPERVISOR_VALIDATED for e in received)

    def test_start_supervising_emits_started(self):
        received = []
        s = self.lc.create("sup-start")
        _advance_to_supervising(self.lc, s.session_id)
        # Already advanced; check history
        evts = self.lc.events()
        assert any(e.event_type == SupervisorEventType.SUPERVISOR_STARTED for e in evts)

    def test_complete_emits_completed(self):
        received = []
        s = self.lc.create("sup-comp")
        _advance_to_supervising(self.lc, s.session_id)
        self.lc.add_listener(received.append)
        self.lc.complete(s.session_id)
        assert any(e.event_type == SupervisorEventType.SUPERVISOR_COMPLETED for e in received)

    def test_fail_emits_failed(self):
        received = []
        s = self.lc.create("sup-fail-ev")
        self.lc.initialize(s.session_id)
        self.lc.add_listener(received.append)
        self.lc.fail(s.session_id, reason="r")
        assert any(e.event_type == SupervisorEventType.SUPERVISOR_FAILED for e in received)

    def test_archive_emits_archived(self):
        received = []
        s = self.lc.create("sup-arch")
        _advance_to_supervising(self.lc, s.session_id)
        self.lc.complete(s.session_id)
        self.lc.add_listener(received.append)
        self.lc.archive(s.session_id)
        assert any(e.event_type == SupervisorEventType.SUPERVISOR_ARCHIVED for e in received)

    def test_remove_listener(self):
        received = []
        self.lc.add_listener(received.append)
        self.lc.remove_listener(received.append)
        prev = len(received)
        self.lc.create("sup-no-ev")
        assert len(received) == prev

    def test_listener_exception_does_not_propagate(self):
        def bad(e):
            raise RuntimeError("boom")
        self.lc.add_listener(bad)
        # should not raise
        self.lc.create("sup-bad-listener")

    def test_recent_events(self):
        for i in range(5):
            self.lc.create(f"sup-rec-{i}")
        recent = self.lc.recent_events(3)
        assert len(recent) <= 3

    def test_transitions_history(self):
        s = self.lc.create("sup-txn")
        self.lc.initialize(s.session_id)
        txns = self.lc.transitions()
        assert len(txns) >= 1


# ============================================================================
# 18. SupervisorLifecycle — statistics
# ============================================================================

class TestSupervisorLifecycleStatistics:
    def setup_method(self):
        self.lc = _full_lc()

    def teardown_method(self):
        self.lc.stop()

    def test_session_created_increments(self):
        self.lc.create("sup-stat")
        snap = self.lc.statistics()
        assert snap["supervisor_sessions_created"] >= 1

    def test_session_failed_increments(self):
        s = self.lc.create("sup-sf")
        self.lc.fail(s.session_id, reason="x")
        snap = self.lc.statistics()
        assert snap["supervisor_sessions_failed"] >= 1

    def test_session_archived_increments(self):
        s = self.lc.create("sup-sa")
        _advance_to_supervising(self.lc, s.session_id)
        self.lc.complete(s.session_id)
        self.lc.archive(s.session_id)
        snap = self.lc.statistics()
        assert snap["supervisor_sessions_archived"] >= 1

    def test_transition_count(self):
        s = self.lc.create("sup-tc")
        self.lc.initialize(s.session_id)
        snap = self.lc.statistics()
        assert snap["transition_count"] >= 1

    def test_completed_with_duration(self):
        s = self.lc.create("sup-dur")
        _advance_to_supervising(self.lc, s.session_id)
        self.lc.complete(s.session_id)
        snap = self.lc.statistics()
        assert snap["supervisor_sessions_completed"] >= 1


# ============================================================================
# 19. SupervisorLifecycle — validate
# ============================================================================

class TestSupervisorLifecycleValidate:
    def setup_method(self):
        self.lc = _full_lc()

    def teardown_method(self):
        self.lc.stop()

    def test_validate_fresh_session(self):
        s = self.lc.create("sup-v")
        r = self.lc.validate(s.session_id)
        assert r.is_valid

    def test_validate_after_transitions(self):
        s = self.lc.create("sup-v2")
        self.lc.initialize(s.session_id)
        self.lc.discover(s.session_id)
        r = self.lc.validate(s.session_id)
        assert r.is_valid

    def test_validate_not_found_raises(self):
        with pytest.raises(SupervisorSessionNotFoundError):
            self.lc.validate("missing")


# ============================================================================
# 20. Concurrency
# ============================================================================

class TestConcurrency:
    def test_concurrent_creates(self):
        lc     = _full_lc()
        errors = []
        ids    = []
        lock   = threading.Lock()

        def create_one(n):
            try:
                s = lc.create(f"sup-con-{n}")
                with lock:
                    ids.append(s.session_id)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=create_one, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lc.stop()
        assert len(errors) == 0
        assert len(set(ids)) == 20

    def test_concurrent_transitions(self):
        lc    = _full_lc()
        s     = lc.create("sup-ctr")
        lc.initialize(s.session_id)

        # Two threads try to discover: only one should succeed
        results = []
        lock    = threading.Lock()

        def try_discover():
            try:
                lc.discover(s.session_id)
                with lock:
                    results.append("ok")
            except Exception:
                with lock:
                    results.append("err")

        threads = [threading.Thread(target=try_discover) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lc.stop()
        assert results.count("ok") == 1
        assert results.count("err") == 1

    def test_concurrent_statistics(self):
        lc = _full_lc()

        def create_and_complete(n):
            s = lc.create(f"sup-stat-{n}")
            lc.initialize(s.session_id)
            lc.fail(s.session_id, reason="concurrent")

        threads = [threading.Thread(target=create_and_complete, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        snap = lc.statistics()
        lc.stop()
        assert snap["supervisor_sessions_created"] == 10
        assert snap["supervisor_sessions_failed"]  == 10

    def test_concurrent_listeners(self):
        lc       = _full_lc()
        received = []
        lock     = threading.Lock()

        def listener(ev):
            with lock:
                received.append(ev)

        lc.add_listener(listener)

        def create_one(n):
            lc.create(f"sup-lst-{n}")

        threads = [threading.Thread(target=create_one, args=(i,)) for i in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lc.stop()
        assert len(received) == 15


# ============================================================================
# 21. Public surface (regression)
# ============================================================================

class TestPublicSurface:
    def test_all_exports_importable(self):
        from iios.supervisor.lifecycle import __all__ as all_names
        import iios.supervisor.lifecycle as mod
        for name in all_names:
            assert hasattr(mod, name), f"Missing: {name}"

    def test_primary_interface_is_supervisor_lifecycle(self):
        lc = SupervisorLifecycle()
        assert hasattr(lc, "create")
        assert hasattr(lc, "initialize")
        assert hasattr(lc, "discover")
        assert hasattr(lc, "validate_session")
        assert hasattr(lc, "mark_ready")
        assert hasattr(lc, "start_supervising")
        assert hasattr(lc, "start_monitoring")
        assert hasattr(lc, "pause")
        assert hasattr(lc, "resume")
        assert hasattr(lc, "complete")
        assert hasattr(lc, "fail")
        assert hasattr(lc, "archive")
        assert hasattr(lc, "statistics")
        assert hasattr(lc, "validate")
        assert hasattr(lc, "add_listener")
        assert hasattr(lc, "remove_listener")


# ============================================================================
# 22. Regression
# ============================================================================

class TestRegression:
    def test_invalid_transition_message_contains_states(self):
        err = SupervisorInvalidTransitionError(
            SupervisorState.CREATED, SupervisorState.MONITORING
        )
        msg = str(err)
        assert "created" in msg.lower()
        assert "monitoring" in msg.lower()

    def test_session_version_increments_monotonically(self):
        s = _make_session()
        v0 = s.supervisor_version
        s.transition_to(SupervisorState.INITIALIZING)
        assert s.supervisor_version == v0 + 1
        s.transition_to(SupervisorState.DISCOVERING)
        assert s.supervisor_version == v0 + 2

    def test_event_occurred_at_is_float(self):
        ev = make_supervisor_created("s", "x")
        assert isinstance(ev.occurred_at, float)

    def test_transition_to_dict_has_all_keys(self):
        t = make_transition("s", SupervisorState.READY, SupervisorState.SUPERVISING)
        d = t.to_dict()
        for key in ("transition_id", "session_id", "from_state", "to_state",
                    "actor", "reason", "transitioned_at", "version"):
            assert key in d

    def test_session_to_dict_has_all_keys(self):
        s = _make_session()
        d = s.to_dict()
        for key in ("session_id", "supervisor_id", "workflow_id",
                    "supervisor_scope", "supervisor_type", "supervisor_priority",
                    "supervisor_version", "state", "created_at", "updated_at"):
            assert key in d

    def test_lifecycle_not_running_error_is_supervisor_error(self):
        assert issubclass(SupervisorLifecycleNotRunningError, SupervisorLifecycleError)

    def test_created_state_not_in_active_states(self):
        assert SupervisorState.CREATED not in ACTIVE_STATES

    def test_all_terminal_states_not_in_active(self):
        for s in TERMINAL_STATES:
            assert s not in ACTIVE_STATES

    def test_completed_succeeds_statistics(self):
        lc = _full_lc()
        s = lc.create("sup-reg-c")
        _advance_to_supervising(lc, s.session_id)
        lc.complete(s.session_id)
        snap = lc.statistics()
        lc.stop()
        assert snap["supervisor_sessions_completed"] == 1

    def test_fail_then_archive(self):
        lc = _full_lc()
        s = lc.create("sup-fa")
        lc.initialize(s.session_id)
        lc.fail(s.session_id, reason="boom")
        lc.archive(s.session_id)
        sess = lc.get_session(s.session_id)
        lc.stop()
        assert sess.state == SupervisorState.ARCHIVED

    def test_multiple_sessions_independent(self):
        lc = _full_lc()
        s1 = lc.create("sup-ind1")
        s2 = lc.create("sup-ind2")
        lc.initialize(s1.session_id)
        # s2 still CREATED
        assert lc.get_session(s2.session_id).state == SupervisorState.CREATED
        assert lc.get_session(s1.session_id).state == SupervisorState.INITIALIZING
        lc.stop()
