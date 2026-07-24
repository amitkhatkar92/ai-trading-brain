"""
tests/unit/workflow/test_workflow_lifecycle_m1.py
--------------------------------------------------
C16 M1 — Workflow Lifecycle test suite.

Tests all 14 source files in iios/workflow/lifecycle/.
Groups:
  A  Constants & enums
  B  Exceptions
  C  WorkflowStateRecord
  D  WorkflowTransition
  E  WorkflowContext
  F  WorkflowMetadata
  G  WorkflowSession
  H  WorkflowEvents
  I  WorkflowHistory
  J  WorkflowStatistics
  K  WorkflowRegistry
  L  WorkflowFactory
  M  WorkflowValidator
  N  WorkflowLifecycle — happy path
  O  WorkflowLifecycle — error paths
  P  WorkflowLifecycle — pause / resume / wait
  Q  WorkflowLifecycle — cancel & retry
  R  WorkflowLifecycle — schedule & queue paths
  S  Concurrency
  T  Regression
"""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest


# ════════════════════════════════════════════════════════════════════════
# A — Constants & enums
# ════════════════════════════════════════════════════════════════════════


class TestConstants:
    def test_state_count(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        assert len(WorkflowLifecycleState) == 14

    def test_event_type_count(self):
        from iios.workflow.lifecycle import WorkflowEventType
        assert len(WorkflowEventType) == 11

    def test_workflow_type_count(self):
        from iios.workflow.lifecycle import WorkflowType
        assert len(WorkflowType) == 10

    def test_workflow_priority_count(self):
        from iios.workflow.lifecycle import WorkflowPriority
        assert len(WorkflowPriority) == 4

    def test_validation_code_count(self):
        from iios.workflow.lifecycle import WorkflowValidationCode
        assert len(WorkflowValidationCode) == 5

    def test_valid_transitions_covers_all_states(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState, VALID_TRANSITIONS
        for state in WorkflowLifecycleState:
            assert state in VALID_TRANSITIONS, f"{state!r} missing from VALID_TRANSITIONS"

    def test_archived_has_no_outgoing_transitions(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState, VALID_TRANSITIONS
        assert VALID_TRANSITIONS[WorkflowLifecycleState.ARCHIVED] == set()

    def test_failed_allows_retry_to_initializing(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState, VALID_TRANSITIONS
        assert (
            WorkflowLifecycleState.INITIALIZING
            in VALID_TRANSITIONS[WorkflowLifecycleState.FAILED]
        )

    def test_failed_allows_archive(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState, VALID_TRANSITIONS
        assert WorkflowLifecycleState.ARCHIVED in VALID_TRANSITIONS[WorkflowLifecycleState.FAILED]

    def test_active_states_does_not_include_archived(self):
        from iios.workflow.lifecycle import ACTIVE_STATES, WorkflowLifecycleState
        assert WorkflowLifecycleState.ARCHIVED not in ACTIVE_STATES

    def test_active_states_includes_running(self):
        from iios.workflow.lifecycle import ACTIVE_STATES, WorkflowLifecycleState
        assert WorkflowLifecycleState.RUNNING in ACTIVE_STATES

    def test_terminal_states_set(self):
        from iios.workflow.lifecycle import TERMINAL_STATES, WorkflowLifecycleState
        assert WorkflowLifecycleState.COMPLETED in TERMINAL_STATES
        assert WorkflowLifecycleState.FAILED in TERMINAL_STATES
        assert WorkflowLifecycleState.CANCELLED in TERMINAL_STATES
        assert WorkflowLifecycleState.ARCHIVED in TERMINAL_STATES

    def test_immutable_states_only_archived(self):
        from iios.workflow.lifecycle import IMMUTABLE_STATES, WorkflowLifecycleState
        assert IMMUTABLE_STATES == {WorkflowLifecycleState.ARCHIVED}

    def test_success_states_only_completed(self):
        from iios.workflow.lifecycle import SUCCESS_STATES, WorkflowLifecycleState
        assert SUCCESS_STATES == {WorkflowLifecycleState.COMPLETED}

    def test_default_constants(self):
        from iios.workflow.lifecycle import (
            DEFAULT_MAX_SESSIONS,
            DEFAULT_MAX_HISTORY,
            DEFAULT_MAX_TRANSITIONS,
            DEFAULT_MAX_ARCHIVED,
        )
        assert DEFAULT_MAX_SESSIONS > 0
        assert DEFAULT_MAX_HISTORY > 0
        assert DEFAULT_MAX_TRANSITIONS > 0
        assert DEFAULT_MAX_ARCHIVED > 0

    def test_actor_constants_non_empty(self):
        from iios.workflow.lifecycle import (
            ACTOR_LIFECYCLE, ACTOR_SYSTEM, ACTOR_OPERATOR
        )
        assert ACTOR_LIFECYCLE
        assert ACTOR_SYSTEM
        assert ACTOR_OPERATOR

    def test_version_constants(self):
        from iios.workflow.lifecycle import VERSION, FRAMEWORK_VERSION, BUILD_VERSION
        assert VERSION
        assert FRAMEWORK_VERSION
        assert BUILD_VERSION

    def test_running_has_multiple_exit_paths(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState, VALID_TRANSITIONS
        exits = VALID_TRANSITIONS[WorkflowLifecycleState.RUNNING]
        assert WorkflowLifecycleState.COMPLETED in exits
        assert WorkflowLifecycleState.FAILED in exits
        assert WorkflowLifecycleState.CANCELLED in exits
        assert WorkflowLifecycleState.PAUSED in exits
        assert WorkflowLifecycleState.WAITING in exits

    def test_state_values_are_strings(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        for state in WorkflowLifecycleState:
            assert isinstance(state.value, str)
            assert state.value == state.value.lower()

    def test_ready_can_go_directly_to_running(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState, VALID_TRANSITIONS
        assert WorkflowLifecycleState.RUNNING in VALID_TRANSITIONS[WorkflowLifecycleState.READY]


# ════════════════════════════════════════════════════════════════════════
# B — Exceptions
# ════════════════════════════════════════════════════════════════════════


class TestExceptions:
    def test_base_exception_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        from iios.workflow.lifecycle import WorkflowLifecycleError
        assert issubclass(WorkflowLifecycleError, IIOSError)

    def test_session_not_found_error(self):
        from iios.workflow.lifecycle import WorkflowSessionNotFoundError
        exc = WorkflowSessionNotFoundError("sid-001")
        assert "sid-001" in str(exc)
        assert exc.session_id == "sid-001"

    def test_invalid_transition_error(self):
        from iios.workflow.lifecycle import WorkflowInvalidTransitionError
        exc = WorkflowInvalidTransitionError("created", "running")
        assert "created" in str(exc)
        assert "running" in str(exc)
        assert exc.from_state == "created"
        assert exc.to_state   == "running"

    def test_session_terminated_error(self):
        from iios.workflow.lifecycle import WorkflowSessionTerminatedError
        exc = WorkflowSessionTerminatedError("ws-999")
        assert "ws-999" in str(exc)
        assert exc.session_id == "ws-999"

    def test_validation_error(self):
        from iios.workflow.lifecycle import WorkflowValidationError
        exc = WorkflowValidationError("check failed")
        assert "check failed" in str(exc)

    def test_capacity_error(self):
        from iios.workflow.lifecycle import WorkflowCapacityError
        exc = WorkflowCapacityError(limit=5000)
        assert exc.limit == 5000
        assert "5000" in str(exc)

    def test_history_error(self):
        from iios.workflow.lifecycle import WorkflowHistoryError
        exc = WorkflowHistoryError("integrity violation")
        assert "integrity violation" in str(exc)

    def test_exception_hierarchy(self):
        from iios.workflow.lifecycle import (
            WorkflowLifecycleError,
            WorkflowSessionNotFoundError,
            WorkflowInvalidTransitionError,
            WorkflowSessionTerminatedError,
        )
        for cls in (
            WorkflowSessionNotFoundError,
            WorkflowInvalidTransitionError,
            WorkflowSessionTerminatedError,
        ):
            assert issubclass(cls, WorkflowLifecycleError)


# ════════════════════════════════════════════════════════════════════════
# C — WorkflowStateRecord
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowStateRecord:
    def test_create_returns_frozen(self):
        from iios.workflow.lifecycle import WorkflowStateRecord, WorkflowLifecycleState
        r = WorkflowStateRecord.create("sid-1", WorkflowLifecycleState.CREATED)
        with pytest.raises((AttributeError, TypeError)):
            r.state = WorkflowLifecycleState.RUNNING  # type: ignore

    def test_record_id_prefix(self):
        from iios.workflow.lifecycle import WorkflowStateRecord, WorkflowLifecycleState
        r = WorkflowStateRecord.create("sid-1", WorkflowLifecycleState.CREATED)
        assert r.record_id.startswith("wsr-")

    def test_to_dict_roundtrip(self):
        from iios.workflow.lifecycle import WorkflowStateRecord, WorkflowLifecycleState
        r = WorkflowStateRecord.create(
            "sid-1", WorkflowLifecycleState.RUNNING, actor="test", reason="started"
        )
        d = r.to_dict()
        r2 = WorkflowStateRecord.from_dict(d)
        assert r == r2

    def test_state_value_in_dict(self):
        from iios.workflow.lifecycle import WorkflowStateRecord, WorkflowLifecycleState
        r = WorkflowStateRecord.create("sid-1", WorkflowLifecycleState.COMPLETED)
        assert r.to_dict()["state"] == "completed"


# ════════════════════════════════════════════════════════════════════════
# D — WorkflowTransition
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowTransition:
    def test_create_returns_frozen(self):
        from iios.workflow.lifecycle import WorkflowTransition, WorkflowLifecycleState
        t = WorkflowTransition.create(
            "sid-1",
            WorkflowLifecycleState.CREATED,
            WorkflowLifecycleState.INITIALIZING,
        )
        with pytest.raises((AttributeError, TypeError)):
            t.from_state = WorkflowLifecycleState.RUNNING  # type: ignore

    def test_transition_id_prefix(self):
        from iios.workflow.lifecycle import WorkflowTransition, WorkflowLifecycleState
        t = WorkflowTransition.create(
            "sid-1",
            WorkflowLifecycleState.CREATED,
            WorkflowLifecycleState.INITIALIZING,
        )
        assert t.transition_id.startswith("wtr-")

    def test_to_dict_roundtrip(self):
        from iios.workflow.lifecycle import WorkflowTransition, WorkflowLifecycleState
        t = WorkflowTransition.create(
            "sid-1",
            WorkflowLifecycleState.RUNNING,
            WorkflowLifecycleState.COMPLETED,
            actor="tester",
            reason="done",
        )
        d = t.to_dict()
        t2 = WorkflowTransition.from_dict(d)
        assert t == t2

    def test_states_in_dict(self):
        from iios.workflow.lifecycle import WorkflowTransition, WorkflowLifecycleState
        t = WorkflowTransition.create(
            "sid-1",
            WorkflowLifecycleState.QUEUED,
            WorkflowLifecycleState.RUNNING,
        )
        d = t.to_dict()
        assert d["from_state"] == "queued"
        assert d["to_state"]   == "running"


# ════════════════════════════════════════════════════════════════════════
# E — WorkflowContext
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowContext:
    def test_create_fills_ids(self):
        from iios.workflow.lifecycle import WorkflowContext
        ctx = WorkflowContext.create("sid-1")
        assert ctx.context_id.startswith("wctx-")
        assert ctx.correlation_id
        assert ctx.trace_id

    def test_custom_correlation(self):
        from iios.workflow.lifecycle import WorkflowContext
        ctx = WorkflowContext.create("sid-1", correlation_id="my-cid")
        assert ctx.correlation_id == "my-cid"

    def test_to_dict_roundtrip(self):
        from iios.workflow.lifecycle import WorkflowContext
        ctx = WorkflowContext.create("sid-1", environment="staging")
        ctx2 = WorkflowContext.from_dict(ctx.to_dict())
        assert ctx == ctx2

    def test_frozen(self):
        from iios.workflow.lifecycle import WorkflowContext
        ctx = WorkflowContext.create("sid-1")
        with pytest.raises((AttributeError, TypeError)):
            ctx.environment = "dev"  # type: ignore

    def test_platform_metadata_stored(self):
        from iios.workflow.lifecycle import WorkflowContext
        ctx = WorkflowContext.create("sid-1", platform_metadata={"key": "val"})
        assert ctx.platform_metadata["key"] == "val"


# ════════════════════════════════════════════════════════════════════════
# F — WorkflowMetadata
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowMetadata:
    def test_default_values(self):
        from iios.workflow.lifecycle import (
            WorkflowMetadata, WorkflowType, WorkflowPriority
        )
        m = WorkflowMetadata.default()
        assert m.workflow_type     == WorkflowType.SEQUENTIAL
        assert m.workflow_priority == WorkflowPriority.NORMAL

    def test_custom_metadata(self):
        from iios.workflow.lifecycle import WorkflowMetadata, WorkflowType, WorkflowPriority
        m = WorkflowMetadata.create(
            WorkflowType.PARALLEL,
            WorkflowPriority.HIGH,
            enterprise_id="ent-001",
            owner_id="user-42",
            tags=["etl", "batch"],
        )
        assert m.enterprise_id == "ent-001"
        assert m.owner_id      == "user-42"
        assert "etl" in m.tags

    def test_to_dict_roundtrip(self):
        from iios.workflow.lifecycle import WorkflowMetadata
        m = WorkflowMetadata.default()
        m2 = WorkflowMetadata.from_dict(m.to_dict())
        assert m == m2

    def test_frozen(self):
        from iios.workflow.lifecycle import WorkflowMetadata
        m = WorkflowMetadata.default()
        with pytest.raises((AttributeError, TypeError)):
            m.enterprise_id = "new"  # type: ignore

    def test_tags_are_tuple(self):
        from iios.workflow.lifecycle import WorkflowMetadata
        m = WorkflowMetadata.create(tags=["a", "b"])
        assert isinstance(m.tags, tuple)


# ════════════════════════════════════════════════════════════════════════
# G — WorkflowSession
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowSession:
    def _make_session(self, sid="sid-001", wid="wf-001"):
        from iios.workflow.lifecycle import (
            WorkflowSession, WorkflowContext, WorkflowMetadata
        )
        ctx = WorkflowContext.create(sid)
        meta = WorkflowMetadata.default()
        return WorkflowSession(
            session_id=sid, workflow_id=wid, context=ctx, metadata=meta
        )

    def test_initial_state_is_created(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        s = self._make_session()
        assert s.state == WorkflowLifecycleState.CREATED

    def test_initial_state_record_exists(self):
        s = self._make_session()
        assert len(s.state_records()) == 1

    def test_valid_transition_succeeds(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        s = self._make_session()
        t = s.transition_to(WorkflowLifecycleState.INITIALIZING)
        assert s.state == WorkflowLifecycleState.INITIALIZING
        assert t.to_state == WorkflowLifecycleState.INITIALIZING

    def test_invalid_transition_raises(self):
        from iios.workflow.lifecycle import (
            WorkflowLifecycleState, WorkflowInvalidTransitionError
        )
        s = self._make_session()
        with pytest.raises(WorkflowInvalidTransitionError):
            s.transition_to(WorkflowLifecycleState.COMPLETED)  # CREATED → COMPLETED invalid

    def test_transition_count_increments(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        s = self._make_session()
        s.transition_to(WorkflowLifecycleState.INITIALIZING)
        assert s.transition_count() == 1
        s.transition_to(WorkflowLifecycleState.VALIDATING)
        assert s.transition_count() == 2

    def test_archived_raises_terminated(self):
        from iios.workflow.lifecycle import (
            WorkflowLifecycleState, WorkflowSessionTerminatedError
        )
        s = self._make_session()
        s.transition_to(WorkflowLifecycleState.INITIALIZING)
        s.transition_to(WorkflowLifecycleState.VALIDATING)
        s.transition_to(WorkflowLifecycleState.READY)
        s.transition_to(WorkflowLifecycleState.RUNNING)
        s.transition_to(WorkflowLifecycleState.COMPLETED)
        s.transition_to(WorkflowLifecycleState.ARCHIVED)
        with pytest.raises(WorkflowSessionTerminatedError):
            s.transition_to(WorkflowLifecycleState.INITIALIZING)

    def test_is_active(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        s = self._make_session()
        s.transition_to(WorkflowLifecycleState.INITIALIZING)
        assert s.is_active

    def test_is_terminal_after_completed(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        s = self._make_session()
        s.transition_to(WorkflowLifecycleState.INITIALIZING)
        s.transition_to(WorkflowLifecycleState.VALIDATING)
        s.transition_to(WorkflowLifecycleState.READY)
        s.transition_to(WorkflowLifecycleState.RUNNING)
        s.transition_to(WorkflowLifecycleState.COMPLETED)
        assert s.is_terminal

    def test_to_dict_keys(self):
        s = self._make_session()
        d = s.to_dict()
        assert "session_id" in d
        assert "workflow_id" in d
        assert "state" in d
        assert "transitions" in d


# ════════════════════════════════════════════════════════════════════════
# H — WorkflowEvents
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowEvents:
    def test_event_id_prefix(self):
        from iios.workflow.lifecycle import (
            WorkflowLifecycleEvent, WorkflowEventType, WorkflowLifecycleState
        )
        e = WorkflowLifecycleEvent.create(
            WorkflowEventType.WORKFLOW_CREATED, "sid-1", WorkflowLifecycleState.CREATED
        )
        assert e.event_id.startswith("wevt-")

    def test_event_is_frozen(self):
        from iios.workflow.lifecycle import (
            WorkflowLifecycleEvent, WorkflowEventType, WorkflowLifecycleState
        )
        e = WorkflowLifecycleEvent.create(
            WorkflowEventType.WORKFLOW_STARTED, "sid-1", WorkflowLifecycleState.RUNNING
        )
        with pytest.raises((AttributeError, TypeError)):
            e.session_id = "other"  # type: ignore

    def test_event_bus_emit_calls_listener(self):
        from iios.workflow.lifecycle import (
            WorkflowLifecycleEventBus, WorkflowEventType, WorkflowLifecycleState
        )
        bus = WorkflowLifecycleEventBus()
        received = []
        bus.add_listener(received.append)
        bus.emit(
            WorkflowEventType.WORKFLOW_COMPLETED,
            "sid-1",
            WorkflowLifecycleState.COMPLETED,
        )
        assert len(received) == 1
        assert received[0].event_type == WorkflowEventType.WORKFLOW_COMPLETED

    def test_event_bus_remove_listener(self):
        from iios.workflow.lifecycle import (
            WorkflowLifecycleEventBus, WorkflowEventType, WorkflowLifecycleState
        )
        bus = WorkflowLifecycleEventBus()
        received = []
        bus.add_listener(received.append)
        bus.remove_listener(received.append)
        bus.emit(
            WorkflowEventType.WORKFLOW_CREATED,
            "sid-1",
            WorkflowLifecycleState.CREATED,
        )
        assert len(received) == 0

    def test_listener_exception_suppressed(self):
        from iios.workflow.lifecycle import (
            WorkflowLifecycleEventBus, WorkflowEventType, WorkflowLifecycleState
        )
        bus = WorkflowLifecycleEventBus()
        bus.add_listener(lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        # Should not raise
        bus.emit(
            WorkflowEventType.WORKFLOW_FAILED,
            "sid-1",
            WorkflowLifecycleState.FAILED,
        )

    def test_event_to_dict(self):
        from iios.workflow.lifecycle import (
            WorkflowLifecycleEvent, WorkflowEventType, WorkflowLifecycleState
        )
        e = WorkflowLifecycleEvent.create(
            WorkflowEventType.WORKFLOW_ARCHIVED, "sid-1", WorkflowLifecycleState.ARCHIVED,
            payload={"reason": "done"}
        )
        d = e.to_dict()
        assert d["event_type"] == "workflow_archived"
        assert d["payload"]["reason"] == "done"

    def test_listener_count(self):
        from iios.workflow.lifecycle import WorkflowLifecycleEventBus
        bus = WorkflowLifecycleEventBus()
        bus.add_listener(lambda e: None)
        bus.add_listener(lambda e: None)
        assert bus.listener_count() == 2


# ════════════════════════════════════════════════════════════════════════
# I — WorkflowHistory
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowHistory:
    def _make_transition(self, sid="sid-1"):
        from iios.workflow.lifecycle import WorkflowTransition, WorkflowLifecycleState
        return WorkflowTransition.create(
            sid, WorkflowLifecycleState.CREATED, WorkflowLifecycleState.INITIALIZING
        )

    def _make_state_record(self, sid="sid-1"):
        from iios.workflow.lifecycle import WorkflowStateRecord, WorkflowLifecycleState
        return WorkflowStateRecord.create(sid, WorkflowLifecycleState.INITIALIZING)

    def test_record_and_retrieve_transition(self):
        from iios.workflow.lifecycle import WorkflowHistory
        h = WorkflowHistory()
        t = self._make_transition()
        h.record_transition(t)
        assert h.get_transition(t.transition_id) == t

    def test_transitions_for_session(self):
        from iios.workflow.lifecycle import WorkflowHistory
        h = WorkflowHistory()
        t = self._make_transition("sid-A")
        h.record_transition(t)
        results = h.transitions_for_session("sid-A")
        assert len(results) == 1
        assert results[0] == t

    def test_state_records_for_session(self):
        from iios.workflow.lifecycle import WorkflowHistory
        h = WorkflowHistory()
        r = self._make_state_record("sid-B")
        h.record_state(r)
        results = h.state_records_for_session("sid-B")
        assert len(results) == 1

    def test_recent_transitions(self):
        from iios.workflow.lifecycle import WorkflowHistory
        h = WorkflowHistory()
        for idx in range(5):
            h.record_transition(self._make_transition(f"sid-{idx}"))
        assert len(h.recent_transitions(3)) == 3

    def test_clear(self):
        from iios.workflow.lifecycle import WorkflowHistory
        h = WorkflowHistory()
        for idx in range(3):
            h.record_transition(self._make_transition(f"sid-{idx}"))
        h.clear()
        assert h.transition_count() == 0

    def test_bounded_capacity(self):
        from iios.workflow.lifecycle import WorkflowHistory
        h = WorkflowHistory(max_transitions=3, max_history=3)
        for idx in range(6):
            h.record_transition(self._make_transition(f"s-{idx}"))
        assert h.transition_count() == 3


# ════════════════════════════════════════════════════════════════════════
# J — WorkflowStatistics
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowStatistics:
    def test_initial_all_zero(self):
        from iios.workflow.lifecycle import WorkflowLifecycleStatistics
        s = WorkflowLifecycleStatistics()
        r = s.report()
        assert r.workflows_created   == 0
        assert r.workflows_completed == 0
        assert r.workflows_failed    == 0
        assert r.workflows_cancelled == 0

    def test_record_created_increments(self):
        from iios.workflow.lifecycle import WorkflowLifecycleStatistics
        s = WorkflowLifecycleStatistics()
        s.record_created()
        s.record_created()
        assert s.report().workflows_created == 2

    def test_record_completed_decrements_running(self):
        from iios.workflow.lifecycle import WorkflowLifecycleStatistics
        s = WorkflowLifecycleStatistics()
        s.record_started()
        s.record_completed(runtime_ms=500.0)
        r = s.report()
        assert r.workflows_running   == 0
        assert r.workflows_completed == 1

    def test_average_runtime_computed(self):
        from iios.workflow.lifecycle import WorkflowLifecycleStatistics
        s = WorkflowLifecycleStatistics()
        s.record_started()
        s.record_completed(runtime_ms=1000.0)
        s.record_started()
        s.record_completed(runtime_ms=2000.0)
        r = s.report()
        assert r.average_runtime_ms == 1500.0

    def test_record_failed(self):
        from iios.workflow.lifecycle import WorkflowLifecycleStatistics
        s = WorkflowLifecycleStatistics()
        s.record_started()
        s.record_failed()
        r = s.report()
        assert r.workflows_failed  == 1
        assert r.workflows_running == 0

    def test_record_cancelled(self):
        from iios.workflow.lifecycle import WorkflowLifecycleStatistics
        s = WorkflowLifecycleStatistics()
        s.record_cancelled()
        assert s.report().workflows_cancelled == 1

    def test_reset_clears_all(self):
        from iios.workflow.lifecycle import WorkflowLifecycleStatistics
        s = WorkflowLifecycleStatistics()
        s.record_created()
        s.record_started()
        s.record_completed(runtime_ms=500.0)
        s.reset()
        r = s.report()
        assert r.workflows_created   == 0
        assert r.workflows_completed == 0

    def test_to_dict_has_all_keys(self):
        from iios.workflow.lifecycle import WorkflowLifecycleStatistics
        s = WorkflowLifecycleStatistics()
        d = s.report().to_dict()
        for key in (
            "workflows_created", "workflows_running", "workflows_completed",
            "workflows_failed", "workflows_cancelled",
            "average_runtime_ms", "average_lifecycle_duration_ms", "captured_at"
        ):
            assert key in d, f"Missing key: {key}"


# ════════════════════════════════════════════════════════════════════════
# K — WorkflowRegistry
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowRegistry:
    def _make_session(self, sid="s1", wid="w1"):
        from iios.workflow.lifecycle import (
            WorkflowSession, WorkflowContext, WorkflowMetadata
        )
        ctx  = WorkflowContext.create(sid)
        meta = WorkflowMetadata.default()
        return WorkflowSession(session_id=sid, workflow_id=wid, context=ctx, metadata=meta)

    def test_register_and_get(self):
        from iios.workflow.lifecycle import WorkflowRegistry
        r = WorkflowRegistry()
        s = self._make_session("s1")
        r.register(s)
        assert r.get("s1") is s

    def test_get_or_raise_unknown(self):
        from iios.workflow.lifecycle import WorkflowRegistry, WorkflowSessionNotFoundError
        r = WorkflowRegistry()
        with pytest.raises(WorkflowSessionNotFoundError):
            r.get_or_raise("unknown")

    def test_deregister(self):
        from iios.workflow.lifecycle import WorkflowRegistry
        r = WorkflowRegistry()
        s = self._make_session("s1")
        r.register(s)
        assert r.deregister("s1") is True
        assert r.get("s1") is None

    def test_by_state(self):
        from iios.workflow.lifecycle import WorkflowRegistry, WorkflowLifecycleState
        r = WorkflowRegistry()
        s = self._make_session("s1")
        r.register(s)
        s.transition_to(WorkflowLifecycleState.INITIALIZING)
        result = r.by_state(WorkflowLifecycleState.INITIALIZING)
        assert s in result

    def test_capacity_error(self):
        from iios.workflow.lifecycle import WorkflowRegistry, WorkflowCapacityError
        r = WorkflowRegistry(max_sessions=2)
        r.register(self._make_session("s1"))
        r.register(self._make_session("s2"))
        with pytest.raises(WorkflowCapacityError):
            r.register(self._make_session("s3"))

    def test_by_workflow(self):
        from iios.workflow.lifecycle import WorkflowRegistry
        r = WorkflowRegistry()
        r.register(self._make_session("s1", "wf-A"))
        r.register(self._make_session("s2", "wf-B"))
        assert len(r.by_workflow("wf-A")) == 1

    def test_count(self):
        from iios.workflow.lifecycle import WorkflowRegistry
        r = WorkflowRegistry()
        r.register(self._make_session("s1"))
        r.register(self._make_session("s2"))
        assert r.count() == 2


# ════════════════════════════════════════════════════════════════════════
# L — WorkflowFactory
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowFactory:
    def test_create_returns_session(self):
        from iios.workflow.lifecycle import WorkflowFactory, WorkflowSession
        f = WorkflowFactory()
        s = f.create("wf-001")
        assert isinstance(s, WorkflowSession)

    def test_session_id_prefix(self):
        from iios.workflow.lifecycle import WorkflowFactory
        f = WorkflowFactory()
        s = f.create("wf-001")
        assert s.session_id.startswith("ws-")

    def test_custom_session_id(self):
        from iios.workflow.lifecycle import WorkflowFactory
        f = WorkflowFactory()
        s = f.create("wf-001", session_id="my-custom-id")
        assert s.session_id == "my-custom-id"

    def test_initial_state_is_created(self):
        from iios.workflow.lifecycle import WorkflowFactory, WorkflowLifecycleState
        f = WorkflowFactory()
        s = f.create("wf-001")
        assert s.state == WorkflowLifecycleState.CREATED

    def test_custom_metadata_applied(self):
        from iios.workflow.lifecycle import (
            WorkflowFactory, WorkflowMetadata, WorkflowType, WorkflowPriority
        )
        f = WorkflowFactory()
        meta = WorkflowMetadata.create(WorkflowType.BATCH, WorkflowPriority.HIGH)
        s = f.create("wf-001", metadata=meta)
        assert s.workflow_type     == WorkflowType.BATCH
        assert s.workflow_priority == WorkflowPriority.HIGH

    def test_create_default(self):
        from iios.workflow.lifecycle import WorkflowFactory
        f = WorkflowFactory()
        s = f.create_default("wf-001")
        assert s.workflow_id == "wf-001"


# ════════════════════════════════════════════════════════════════════════
# M — WorkflowValidator
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowValidator:
    def _make_session(self, sid="sid-1", wid="wf-1"):
        from iios.workflow.lifecycle import (
            WorkflowSession, WorkflowContext, WorkflowMetadata
        )
        ctx  = WorkflowContext.create(sid)
        meta = WorkflowMetadata.default()
        return WorkflowSession(session_id=sid, workflow_id=wid, context=ctx, metadata=meta)

    def test_fresh_session_passes(self):
        from iios.workflow.lifecycle import WorkflowValidator
        v = WorkflowValidator()
        r = v.validate(self._make_session())
        assert r.passed
        assert r.failed_checks == []

    def test_report_has_five_checks(self):
        from iios.workflow.lifecycle import WorkflowValidator
        v = WorkflowValidator()
        r = v.validate(self._make_session())
        assert len(r.results) == 5

    def test_to_dict_has_keys(self):
        from iios.workflow.lifecycle import WorkflowValidator
        v = WorkflowValidator()
        r = v.validate(self._make_session())
        d = r.to_dict()
        assert "session_id" in d
        assert "passed"     in d
        assert "results"    in d

    def test_session_after_transitions_still_passes(self):
        from iios.workflow.lifecycle import WorkflowValidator, WorkflowLifecycleState
        v = WorkflowValidator()
        s = self._make_session()
        s.transition_to(WorkflowLifecycleState.INITIALIZING)
        s.transition_to(WorkflowLifecycleState.VALIDATING)
        r = v.validate(s)
        assert r.passed


# ════════════════════════════════════════════════════════════════════════
# N — WorkflowLifecycle — happy path
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowLifecycleHappyPath:
    def test_create_session(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-001")
        assert s.state == WorkflowLifecycleState.CREATED

    def test_full_success_path(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-001")
        lc.initialize(s.session_id)
        lc.validate_workflow(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start(s.session_id)
        lc.complete(s.session_id)
        lc.archive(s.session_id)
        assert s.state == WorkflowLifecycleState.ARCHIVED

    def test_schedule_queue_path(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-002")
        lc.initialize(s.session_id)
        lc.validate_workflow(s.session_id)
        lc.mark_ready(s.session_id)
        lc.schedule(s.session_id)
        lc.queue(s.session_id)
        lc.start(s.session_id)
        lc.complete(s.session_id)
        assert s.state == WorkflowLifecycleState.COMPLETED

    def test_statistics_after_full_path(self):
        from iios.workflow.lifecycle import WorkflowLifecycle
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-003")
        lc.initialize(s.session_id)
        lc.validate_workflow(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start(s.session_id)
        lc.complete(s.session_id, runtime_ms=500.0, lifecycle_duration_ms=1000.0)
        r = lc.statistics()
        assert r.workflows_created   == 1
        assert r.workflows_completed == 1

    def test_list_sessions(self):
        from iios.workflow.lifecycle import WorkflowLifecycle
        lc = WorkflowLifecycle()
        lc.create_session("wf-001")
        lc.create_session("wf-002")
        assert len(lc.list_sessions()) == 2

    def test_sessions_by_state(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
        lc = WorkflowLifecycle()
        s1 = lc.create_session("wf-001")
        s2 = lc.create_session("wf-002")
        lc.initialize(s1.session_id)
        created = lc.sessions_by_state(WorkflowLifecycleState.CREATED)
        assert s2 in created
        assert s1 not in created

    def test_event_emitted_on_create(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowEventType
        lc = WorkflowLifecycle()
        received = []
        lc.event_bus().add_listener(received.append)
        lc.create_session("wf-001")
        assert any(e.event_type == WorkflowEventType.WORKFLOW_CREATED for e in received)

    def test_transition_recorded_in_history(self):
        from iios.workflow.lifecycle import WorkflowLifecycle
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-001")
        lc.initialize(s.session_id)
        h = lc.history()
        assert h.transition_count() == 1


# ════════════════════════════════════════════════════════════════════════
# O — WorkflowLifecycle — error paths
# ════════════════════════════════════════════════════════════════════════


class TestWorkflowLifecycleErrors:
    def test_unknown_session_raises(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowSessionNotFoundError
        lc = WorkflowLifecycle()
        with pytest.raises(WorkflowSessionNotFoundError):
            lc.initialize("nonexistent")

    def test_invalid_transition_raises(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowInvalidTransitionError
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-001")
        with pytest.raises(WorkflowInvalidTransitionError):
            lc.complete(s.session_id)  # CREATED → COMPLETED invalid

    def test_archived_session_raises_terminated(self):
        from iios.workflow.lifecycle import (
            WorkflowLifecycle, WorkflowSessionTerminatedError
        )
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-001")
        lc.initialize(s.session_id)
        lc.validate_workflow(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start(s.session_id)
        lc.complete(s.session_id)
        lc.archive(s.session_id)
        with pytest.raises(WorkflowSessionTerminatedError):
            lc.initialize(s.session_id)

    def test_get_session_returns_none_for_unknown(self):
        from iios.workflow.lifecycle import WorkflowLifecycle
        lc = WorkflowLifecycle()
        assert lc.get_session("nonexistent") is None

    def test_get_session_or_raise(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowSessionNotFoundError
        lc = WorkflowLifecycle()
        with pytest.raises(WorkflowSessionNotFoundError):
            lc.get_session_or_raise("missing")


# ════════════════════════════════════════════════════════════════════════
# P — WorkflowLifecycle — pause / resume / wait
# ════════════════════════════════════════════════════════════════════════


class TestPauseResumeWait:
    def _running_session(self, lc=None):
        from iios.workflow.lifecycle import WorkflowLifecycle
        lc = lc or WorkflowLifecycle()
        s = lc.create_session("wf-prw")
        lc.initialize(s.session_id)
        lc.validate_workflow(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start(s.session_id)
        return lc, s

    def test_pause_from_running(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        lc, s = self._running_session()
        lc.pause(s.session_id)
        assert s.state == WorkflowLifecycleState.PAUSED

    def test_resume_from_paused(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        lc, s = self._running_session()
        lc.pause(s.session_id)
        lc.resume(s.session_id)
        assert s.state == WorkflowLifecycleState.RESUMING

    def test_resuming_to_running(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        lc, s = self._running_session()
        lc.pause(s.session_id)
        lc.resume(s.session_id)
        lc.resume_from_wait(s.session_id)  # RESUMING → RUNNING
        assert s.state == WorkflowLifecycleState.RUNNING

    def test_wait_from_running(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        lc, s = self._running_session()
        lc.wait(s.session_id)
        assert s.state == WorkflowLifecycleState.WAITING

    def test_resume_from_wait_to_running(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        lc, s = self._running_session()
        lc.wait(s.session_id)
        lc.resume_from_wait(s.session_id)
        assert s.state == WorkflowLifecycleState.RUNNING


# ════════════════════════════════════════════════════════════════════════
# Q — Cancel & retry
# ════════════════════════════════════════════════════════════════════════


class TestCancelRetry:
    def test_cancel_from_created(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-001")
        lc.cancel(s.session_id)
        assert s.state == WorkflowLifecycleState.CANCELLED

    def test_cancel_stats_updated(self):
        from iios.workflow.lifecycle import WorkflowLifecycle
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-001")
        lc.cancel(s.session_id)
        assert lc.statistics().workflows_cancelled == 1

    def test_fail_and_retry(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-001")
        lc.initialize(s.session_id)
        lc.fail(s.session_id)
        assert s.state == WorkflowLifecycleState.FAILED
        lc.retry(s.session_id)
        assert s.state == WorkflowLifecycleState.INITIALIZING

    def test_cancel_then_archive(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-001")
        lc.cancel(s.session_id)
        lc.archive(s.session_id)
        assert s.state == WorkflowLifecycleState.ARCHIVED

    def test_fail_event_emitted(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowEventType
        lc = WorkflowLifecycle()
        received = []
        lc.event_bus().add_listener(received.append)
        s = lc.create_session("wf-001")
        lc.initialize(s.session_id)
        lc.fail(s.session_id)
        types = [e.event_type for e in received]
        assert WorkflowEventType.WORKFLOW_FAILED in types


# ════════════════════════════════════════════════════════════════════════
# R — Schedule & queue paths
# ════════════════════════════════════════════════════════════════════════


class TestScheduleQueue:
    def test_ready_to_scheduled_to_queued_to_running(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-sq")
        lc.initialize(s.session_id)
        lc.validate_workflow(s.session_id)
        lc.mark_ready(s.session_id)
        lc.schedule(s.session_id)
        assert s.state == WorkflowLifecycleState.SCHEDULED
        lc.queue(s.session_id)
        assert s.state == WorkflowLifecycleState.QUEUED
        lc.start(s.session_id)
        assert s.state == WorkflowLifecycleState.RUNNING

    def test_ready_to_queued_directly(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-sq2")
        lc.initialize(s.session_id)
        lc.validate_workflow(s.session_id)
        lc.mark_ready(s.session_id)
        lc.queue(s.session_id)
        assert s.state == WorkflowLifecycleState.QUEUED

    def test_ready_to_running_directly(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowLifecycleState
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-sq3")
        lc.initialize(s.session_id)
        lc.validate_workflow(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start(s.session_id)
        assert s.state == WorkflowLifecycleState.RUNNING

    def test_sessions_by_workflow(self):
        from iios.workflow.lifecycle import WorkflowLifecycle
        lc = WorkflowLifecycle()
        lc.create_session("wf-X")
        lc.create_session("wf-X")
        lc.create_session("wf-Y")
        by_x = lc.sessions_by_workflow("wf-X")
        assert len(by_x) == 2


# ════════════════════════════════════════════════════════════════════════
# S — Concurrency
# ════════════════════════════════════════════════════════════════════════


class TestConcurrency:
    def test_concurrent_create_sessions(self):
        from iios.workflow.lifecycle import WorkflowLifecycle
        lc = WorkflowLifecycle()
        errors = []

        def create():
            try:
                lc.create_session("wf-concurrent")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=create) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert lc.registry().count() == 50

    def test_concurrent_transitions_on_same_session(self):
        """Only one thread can perform the first transition; others should fail gracefully."""
        from iios.workflow.lifecycle import (
            WorkflowLifecycle,
            WorkflowInvalidTransitionError,
            WorkflowSessionTerminatedError,
        )
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-race")
        successes = []
        failures  = []

        def try_init():
            try:
                lc.initialize(s.session_id)
                successes.append(1)
            except (WorkflowInvalidTransitionError, WorkflowSessionTerminatedError):
                failures.append(1)

        threads = [threading.Thread(target=try_init) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one thread wins the CREATED → INITIALIZING race
        assert len(successes) == 1
        assert len(failures)  == 19

    def test_statistics_thread_safe(self):
        from iios.workflow.lifecycle import WorkflowLifecycleStatistics
        stats = WorkflowLifecycleStatistics()
        threads = [
            threading.Thread(target=stats.record_created) for _ in range(100)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert stats.report().workflows_created == 100

    def test_registry_thread_safe(self):
        from iios.workflow.lifecycle import (
            WorkflowRegistry, WorkflowSession, WorkflowContext, WorkflowMetadata
        )
        reg = WorkflowRegistry(max_sessions=200)
        errors = []

        def register(idx):
            try:
                ctx  = WorkflowContext.create(f"s{idx}")
                meta = WorkflowMetadata.default()
                sess = WorkflowSession(
                    session_id=f"s{idx}", workflow_id="wf",
                    context=ctx, metadata=meta
                )
                reg.register(sess)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert reg.count() == 100

    def test_event_bus_thread_safe(self):
        from iios.workflow.lifecycle import (
            WorkflowLifecycleEventBus, WorkflowEventType, WorkflowLifecycleState
        )
        bus = WorkflowLifecycleEventBus()
        received = []
        lock = threading.Lock()

        def listener(e):
            with lock:
                received.append(e)

        bus.add_listener(listener)

        def emit_event(idx):
            bus.emit(
                WorkflowEventType.WORKFLOW_CREATED,
                f"sid-{idx}",
                WorkflowLifecycleState.CREATED,
            )

        threads = [threading.Thread(target=emit_event, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(received) == 50


# ════════════════════════════════════════════════════════════════════════
# T — Regression
# ════════════════════════════════════════════════════════════════════════


class TestRegression:
    def test_exports_complete(self):
        import iios.workflow.lifecycle as mod
        for name in mod.__all__:
            assert hasattr(mod, name), f"Missing export: {name}"

    def test_all_states_have_values(self):
        from iios.workflow.lifecycle import WorkflowLifecycleState
        expected = {
            "created", "initializing", "validating", "ready",
            "scheduled", "queued", "running", "waiting", "paused",
            "resuming", "completed", "failed", "cancelled", "archived"
        }
        actual = {s.value for s in WorkflowLifecycleState}
        assert actual == expected

    def test_all_event_types_have_values(self):
        from iios.workflow.lifecycle import WorkflowEventType
        expected = {
            "workflow_created", "workflow_initialized", "workflow_validated",
            "workflow_scheduled", "workflow_started", "workflow_paused",
            "workflow_resumed", "workflow_completed", "workflow_failed",
            "workflow_cancelled", "workflow_archived"
        }
        actual = {e.value for e in WorkflowEventType}
        assert actual == expected

    def test_no_two_sessions_share_id(self):
        from iios.workflow.lifecycle import WorkflowFactory
        f = WorkflowFactory()
        ids = {f.create("wf-x").session_id for _ in range(100)}
        assert len(ids) == 100

    def test_full_lifecycle_transition_count(self):
        """CREATED→INIT→VAL→READY→RUN→COMPLETED → 5 transitions."""
        from iios.workflow.lifecycle import WorkflowLifecycle
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-tc")
        lc.initialize(s.session_id)
        lc.validate_workflow(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start(s.session_id)
        lc.complete(s.session_id)
        assert s.transition_count() == 5

    def test_validation_passes_after_full_lifecycle(self):
        from iios.workflow.lifecycle import WorkflowLifecycle, WorkflowValidator
        lc = WorkflowLifecycle()
        s = lc.create_session("wf-val")
        lc.initialize(s.session_id)
        lc.validate_workflow(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start(s.session_id)
        lc.complete(s.session_id)
        v = WorkflowValidator()
        report = v.validate(s)
        assert report.passed
