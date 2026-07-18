"""tests/unit/execution/recovery/lifecycle/test_recovery_lifecycle.py
==================================================
Comprehensive test suite for C7 Phase 1 M1 — Execution Recovery Lifecycle.

Test classes
------------
TestConstants             — enumerations, state machine maps
TestExceptions            — exception hierarchy
TestRecoveryState         — can_transition helper, StateRecord
TestRecoveryContext       — factory, frozen DTO
TestRecoveryMetadata      — factory, frozen DTO, derived properties
TestRecoverySession       — creation, state machine, milestones
TestRecoveryTransition    — factory, frozen, serialisation
TestRecoveryEvents        — factory functions, immutability
TestRecoveryValidation    — validator, ValidationResult
TestRecoveryStatistics    — accumulation, rates, copy, thread-safety
TestRecoveryHistory       — bounded deques, filtering
TestRecoveryRegistry      — CRUD, lifecycle guard, archive
TestRecoveryFactory       — create from context / params
TestRecoveryLifecycle     — full lifecycle transitions
TestTransitionGates       — all valid/invalid edge cases
TestConcurrency           — thread safety
TestRegressionEdgeCases   — edge cases
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from iios.execution.recovery.lifecycle.constants import (
    ACTIVE_STATES,
    ACTOR_LIFECYCLE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    IMMUTABLE_STATES,
    LIFECYCLE_SYSTEM_ID,
    TERMINAL_STATES,
    SUCCESS_STATES,
    VALID_TRANSITIONS,
    VERSION,
    RecoveryEventType,
    RecoveryState,
    RecoveryTrigger,
)
from iios.execution.recovery.lifecycle.exceptions import (
    RecoveryAlreadyRunningError,
    RecoveryError,
    RecoveryHistoryError,
    RecoveryInvalidTransitionError,
    RecoveryNotRunningError,
    RecoverySessionAlreadyExistsError,
    RecoverySessionNotFoundError,
    RecoverySessionTerminalError,
    RecoveryValidationError,
)
from iios.execution.recovery.lifecycle.recovery_context import (
    RecoveryContext,
    make_recovery_context,
)
from iios.execution.recovery.lifecycle.recovery_metadata import (
    RecoveryMetadata,
    make_recovery_metadata,
)
from iios.execution.recovery.lifecycle.recovery_session import RecoverySession
from iios.execution.recovery.lifecycle.recovery_state import (
    RecoveryStateRecord,
    can_transition,
)
from iios.execution.recovery.lifecycle.recovery_transition import (
    RecoveryTransition,
    make_recovery_transition,
)
from iios.execution.recovery.lifecycle.recovery_events import (
    RecoveryEvent,
    make_recovery_aborted,
    make_recovery_archived,
    make_recovery_assessing,
    make_recovery_completed,
    make_recovery_created,
    make_recovery_detecting,
    make_recovery_failed,
    make_recovery_initialized,
    make_recovery_ready,
    make_recovery_started,
    make_recovery_verifying,
)
from iios.execution.recovery.lifecycle.recovery_validation import (
    RecoveryValidationResult,
    RecoveryValidator,
)
from iios.execution.recovery.lifecycle.recovery_statistics import RecoveryStatistics
from iios.execution.recovery.lifecycle.recovery_history import RecoveryHistory
from iios.execution.recovery.lifecycle.recovery_registry import RecoveryRegistry
from iios.execution.recovery.lifecycle.recovery_factory import RecoveryFactory
from iios.execution.recovery.lifecycle.recovery_lifecycle import RecoveryLifecycle


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sid() -> str:
    return f"exec-{uuid.uuid4().hex[:8]}"

def _sub() -> str:
    return f"sub-{uuid.uuid4().hex[:6]}"

def _ctx(
    exec_id: Optional[str] = None,
    sub_id:  Optional[str] = None,
) -> RecoveryContext:
    return make_recovery_context(
        exec_id or _sid(),
        sub_id  or _sub(),
        RecoveryTrigger.AUTOMATIC,
        "test recovery",
    )

def _session(
    exec_id: Optional[str] = None,
    sub_id:  Optional[str] = None,
) -> RecoverySession:
    return RecoverySession(
        execution_session_id = exec_id or _sid(),
        subsystem_id         = sub_id  or _sub(),
        recovery_trigger     = RecoveryTrigger.AUTOMATIC,
        recovery_reason      = "test",
    )

def _started_lifecycle(**kwargs) -> RecoveryLifecycle:
    lc = RecoveryLifecycle(**kwargs)
    lc.start()
    return lc

def _full_lifecycle(lc: RecoveryLifecycle) -> RecoverySession:
    """Drive a session through CREATED → COMPLETED."""
    s = lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "test")
    lc.initialize(s.session_id)
    lc.detect(s.session_id)
    lc.assess(s.session_id)
    lc.ready(s.session_id)
    lc.begin_recovery(s.session_id)
    lc.verify(s.session_id)
    lc.complete(s.session_id)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# 1  Constants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_version_string(self):
        assert isinstance(VERSION, str) and VERSION

    def test_state_values(self):
        assert RecoveryState.CREATED.value      == "created"
        assert RecoveryState.INITIALIZING.value == "initializing"
        assert RecoveryState.DETECTING.value    == "detecting"
        assert RecoveryState.ASSESSING.value    == "assessing"
        assert RecoveryState.READY.value        == "ready"
        assert RecoveryState.RECOVERING.value   == "recovering"
        assert RecoveryState.VERIFYING.value    == "verifying"
        assert RecoveryState.COMPLETED.value    == "completed"
        assert RecoveryState.FAILED.value       == "failed"
        assert RecoveryState.ABORTED.value      == "aborted"
        assert RecoveryState.ARCHIVED.value     == "archived"

    def test_trigger_values(self):
        assert RecoveryTrigger.MANUAL.value   == "manual"
        assert RecoveryTrigger.AUTOMATIC.value== "automatic"
        assert RecoveryTrigger.POLICY.value   == "policy"

    def test_event_type_values(self):
        assert RecoveryEventType.RECOVERY_CREATED.value    == "recovery_created"
        assert RecoveryEventType.RECOVERY_COMPLETED.value  == "recovery_completed"

    def test_active_states(self):
        assert RecoveryState.RECOVERING in ACTIVE_STATES
        assert RecoveryState.DETECTING  in ACTIVE_STATES
        assert RecoveryState.COMPLETED not in ACTIVE_STATES

    def test_terminal_states(self):
        assert RecoveryState.COMPLETED in TERMINAL_STATES
        assert RecoveryState.FAILED    in TERMINAL_STATES
        assert RecoveryState.ABORTED   in TERMINAL_STATES
        assert RecoveryState.ARCHIVED  in TERMINAL_STATES
        assert RecoveryState.RECOVERING not in TERMINAL_STATES

    def test_immutable_states(self):
        assert RecoveryState.ARCHIVED in IMMUTABLE_STATES
        assert RecoveryState.COMPLETED not in IMMUTABLE_STATES

    def test_success_states(self):
        assert RecoveryState.COMPLETED in SUCCESS_STATES
        assert RecoveryState.FAILED not in SUCCESS_STATES

    def test_valid_transitions_coverage(self):
        """Every state has an entry in VALID_TRANSITIONS."""
        for state in RecoveryState:
            assert state in VALID_TRANSITIONS

    def test_archived_is_terminal(self):
        assert VALID_TRANSITIONS[RecoveryState.ARCHIVED] == frozenset()

    def test_default_limits(self):
        assert DEFAULT_MAX_SESSIONS >= 1
        assert DEFAULT_MAX_HISTORY  >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 2  Exceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_hierarchy(self):
        assert issubclass(RecoveryNotRunningError,         RecoveryError)
        assert issubclass(RecoveryAlreadyRunningError,     RecoveryError)
        assert issubclass(RecoverySessionNotFoundError,    RecoveryError)
        assert issubclass(RecoveryInvalidTransitionError,  RecoveryError)
        assert issubclass(RecoveryValidationError,         RecoveryError)
        assert issubclass(RecoverySessionAlreadyExistsError, RecoveryError)
        assert issubclass(RecoveryHistoryError,            RecoveryError)
        assert issubclass(RecoverySessionTerminalError,    RecoveryError)

    def test_not_running_raises(self):
        with pytest.raises(RecoveryNotRunningError):
            raise RecoveryNotRunningError()

    def test_session_not_found_stores_id(self):
        exc = RecoverySessionNotFoundError("sess-42")
        assert "sess-42" in str(exc)

    def test_invalid_transition_stores_states(self):
        exc = RecoveryInvalidTransitionError("created", "completed", "s1")
        assert "created"   in str(exc)
        assert "completed" in str(exc)

    def test_validation_error_stores_errors(self):
        exc = RecoveryValidationError("bad", errors=("e1", "e2"))
        assert exc.errors == ("e1", "e2")

    def test_terminal_error(self):
        exc = RecoverySessionTerminalError("s1", "archived")
        assert "archived" in str(exc)

    def test_already_exists_stores_id(self):
        exc = RecoverySessionAlreadyExistsError("s-dup")
        assert "s-dup" in str(exc)


# ─────────────────────────────────────────────────────────────────────────────
# 3  RecoveryState helpers
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryState:
    def test_can_transition_valid(self):
        assert can_transition(RecoveryState.CREATED,     RecoveryState.INITIALIZING)
        assert can_transition(RecoveryState.INITIALIZING,RecoveryState.DETECTING)
        assert can_transition(RecoveryState.DETECTING,   RecoveryState.ASSESSING)
        assert can_transition(RecoveryState.ASSESSING,   RecoveryState.READY)
        assert can_transition(RecoveryState.READY,       RecoveryState.RECOVERING)
        assert can_transition(RecoveryState.RECOVERING,  RecoveryState.VERIFYING)
        assert can_transition(RecoveryState.VERIFYING,   RecoveryState.COMPLETED)
        assert can_transition(RecoveryState.VERIFYING,   RecoveryState.RECOVERING)  # retry
        assert can_transition(RecoveryState.COMPLETED,   RecoveryState.ARCHIVED)
        assert can_transition(RecoveryState.FAILED,      RecoveryState.ARCHIVED)
        assert can_transition(RecoveryState.ABORTED,     RecoveryState.ARCHIVED)

    def test_can_transition_invalid(self):
        assert not can_transition(RecoveryState.CREATED,   RecoveryState.COMPLETED)
        assert not can_transition(RecoveryState.ARCHIVED,  RecoveryState.CREATED)
        assert not can_transition(RecoveryState.COMPLETED, RecoveryState.FAILED)
        assert not can_transition(RecoveryState.CREATED,   RecoveryState.RECOVERING)

    def test_fail_from_any_active_state(self):
        for state in ACTIVE_STATES:
            assert can_transition(state, RecoveryState.FAILED), f"{state} should allow FAILED"

    def test_abort_and_fail_from_ready(self):
        """READY allows RECOVERING, FAILED, and ABORTED."""
        assert can_transition(RecoveryState.READY, RecoveryState.ABORTED)
        assert can_transition(RecoveryState.READY, RecoveryState.FAILED)

    def test_state_record_frozen(self):
        rec = RecoveryStateRecord(
            state      = RecoveryState.CREATED,
            entered_at = time.time(),
        )
        with pytest.raises((AttributeError, TypeError)):
            rec.state = RecoveryState.FAILED  # type: ignore

    def test_state_record_to_dict(self):
        rec = RecoveryStateRecord(state=RecoveryState.INITIALIZING, entered_at=time.time())
        d = rec.to_dict()
        assert d["state"] == "initializing"


# ─────────────────────────────────────────────────────────────────────────────
# 4  RecoveryContext
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryContext:
    def test_factory_creates_frozen(self):
        ctx = _ctx()
        with pytest.raises((AttributeError, TypeError)):
            ctx.execution_session_id = "x"  # type: ignore

    def test_required_fields(self):
        ctx = make_recovery_context(
            "exec-1", "sub-1", RecoveryTrigger.MANUAL, "test"
        )
        assert ctx.execution_session_id == "exec-1"
        assert ctx.subsystem_id         == "sub-1"
        assert ctx.recovery_trigger     == RecoveryTrigger.MANUAL
        assert ctx.recovery_reason      == "test"

    def test_optional_fields_default_none(self):
        ctx = _ctx()
        assert ctx.workflow_id       is None
        assert ctx.failure_id        is None
        assert ctx.recovery_plan_id  is None

    def test_has_workflow(self):
        ctx = make_recovery_context(
            "e", "s", RecoveryTrigger.AUTOMATIC, "r", workflow_id="wf-1"
        )
        assert ctx.has_workflow

    def test_has_failure_id(self):
        ctx = make_recovery_context(
            "e", "s", RecoveryTrigger.AUTOMATIC, "r", failure_id="f-1"
        )
        assert ctx.has_failure_id

    def test_has_recovery_plan(self):
        ctx = make_recovery_context(
            "e", "s", RecoveryTrigger.AUTOMATIC, "r", recovery_plan_id="p-1"
        )
        assert ctx.has_recovery_plan

    def test_context_id_auto_assigned(self):
        c1, c2 = _ctx(), _ctx()
        assert c1.context_id != c2.context_id

    def test_tags_and_metadata(self):
        ctx = make_recovery_context(
            "e", "s", RecoveryTrigger.AUTOMATIC, "r",
            tags=("tag1",), metadata={"k": "v"}
        )
        assert ctx.tags == ("tag1",)
        assert ctx.metadata["k"] == "v"

    def test_framework_version(self):
        ctx = _ctx()
        assert ctx.framework_version == VERSION

    def test_to_dict(self):
        ctx = _ctx()
        d = ctx.to_dict()
        assert "context_id"           in d
        assert "execution_session_id" in d
        assert "subsystem_id"         in d
        assert "recovery_trigger"     in d


# ─────────────────────────────────────────────────────────────────────────────
# 5  RecoveryMetadata
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryMetadata:
    def test_factory_creates_frozen(self):
        m = make_recovery_metadata("sess-1")
        with pytest.raises((AttributeError, TypeError)):
            m.attempt_count = 99  # type: ignore

    def test_defaults(self):
        m = make_recovery_metadata("sess-1")
        assert m.attempt_count == 0
        assert m.max_attempts  == 3
        assert not m.is_exhausted

    def test_attempts_remaining(self):
        m = make_recovery_metadata("s", attempt_count=1, max_attempts=3)
        assert m.attempts_remaining == 2

    def test_is_exhausted(self):
        m = make_recovery_metadata("s", attempt_count=3, max_attempts=3)
        assert m.is_exhausted

    def test_assessment_data(self):
        m = make_recovery_metadata("s", assessment_data={"latency_ms": 100.0})
        assert m.assessment_data["latency_ms"] == 100.0

    def test_unique_metadata_ids(self):
        m1 = make_recovery_metadata("s")
        m2 = make_recovery_metadata("s")
        assert m1.metadata_id != m2.metadata_id

    def test_to_dict(self):
        m = make_recovery_metadata("s")
        d = m.to_dict()
        assert "metadata_id"         in d
        assert "recovery_session_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# 6  RecoverySession
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoverySession:
    def test_initial_state(self):
        s = _session()
        assert s.state        == RecoveryState.CREATED
        assert not s.is_active
        assert not s.is_terminal
        assert not s.is_failed
        assert not s.is_completed
        assert not s.is_aborted

    def test_session_id_auto(self):
        s1, s2 = _session(), _session()
        assert s1.session_id != s2.session_id

    def test_transition_to_initializing(self):
        s = _session()
        s.transition_to(RecoveryState.INITIALIZING)
        assert s.state == RecoveryState.INITIALIZING
        assert s.is_active

    def test_full_happy_path(self):
        s = _session()
        for state in (
            RecoveryState.INITIALIZING,
            RecoveryState.DETECTING,
            RecoveryState.ASSESSING,
            RecoveryState.READY,
            RecoveryState.RECOVERING,
            RecoveryState.VERIFYING,
            RecoveryState.COMPLETED,
        ):
            s.transition_to(state)
        assert s.is_completed
        assert s.is_terminal
        assert s.end_time is not None
        assert s.start_time is not None

    def test_start_time_set_on_recovering(self):
        s = _session()
        s.transition_to(RecoveryState.INITIALIZING)
        s.transition_to(RecoveryState.DETECTING)
        s.transition_to(RecoveryState.ASSESSING)
        s.transition_to(RecoveryState.READY)
        assert s.start_time is None
        s.transition_to(RecoveryState.RECOVERING)
        assert s.start_time is not None

    def test_end_time_set_on_completed(self):
        s = _session()
        for st in [
            RecoveryState.INITIALIZING, RecoveryState.DETECTING,
            RecoveryState.ASSESSING, RecoveryState.READY,
            RecoveryState.RECOVERING, RecoveryState.VERIFYING,
            RecoveryState.COMPLETED,
        ]:
            s.transition_to(st)
        assert s.end_time is not None

    def test_failure_reason_set_on_fail(self):
        s = _session()
        s.transition_to(RecoveryState.INITIALIZING, reason="starting")
        s.transition_to(RecoveryState.FAILED, reason="timeout exceeded")
        assert s.failure_reason == "timeout exceeded"
        assert s.is_failed

    def test_abort_reason_set(self):
        s = _session()
        s.transition_to(RecoveryState.INITIALIZING)
        s.transition_to(RecoveryState.ABORTED, reason="operator cancelled")
        assert s.abort_reason == "operator cancelled"
        assert s.is_aborted

    def test_invalid_transition_raises(self):
        s = _session()
        with pytest.raises(RecoveryInvalidTransitionError):
            s.transition_to(RecoveryState.COMPLETED)  # CREATED → COMPLETED is invalid

    def test_archived_is_immutable(self):
        s = _session()
        for st in [
            RecoveryState.INITIALIZING, RecoveryState.DETECTING,
            RecoveryState.ASSESSING, RecoveryState.READY,
            RecoveryState.RECOVERING, RecoveryState.VERIFYING,
            RecoveryState.COMPLETED, RecoveryState.ARCHIVED,
        ]:
            s.transition_to(st)
        with pytest.raises(RecoverySessionTerminalError):
            s.transition_to(RecoveryState.FAILED)

    def test_transition_history_recorded(self):
        s = _session()
        s.transition_to(RecoveryState.INITIALIZING, actor="test", reason="start")
        assert s.transition_count == 1
        t = s.transitions[0]
        assert t.from_state == RecoveryState.CREATED
        assert t.to_state   == RecoveryState.INITIALIZING
        assert t.actor      == "test"
        assert t.reason     == "start"

    def test_state_history_grows(self):
        s = _session()
        initial_len = len(s.state_history)
        s.transition_to(RecoveryState.INITIALIZING)
        assert len(s.state_history) == initial_len + 1

    def test_duration_ms_zero_before_recovering(self):
        s = _session()
        s.transition_to(RecoveryState.INITIALIZING)
        assert s.duration_ms == 0.0

    def test_duration_ms_positive_after_recovering(self):
        s = _session()
        for st in [
            RecoveryState.INITIALIZING, RecoveryState.DETECTING,
            RecoveryState.ASSESSING, RecoveryState.READY,
            RecoveryState.RECOVERING,
        ]:
            s.transition_to(st)
        time.sleep(0.01)
        assert s.duration_ms > 0.0

    def test_to_dict(self):
        s = _session()
        d = s.to_dict()
        assert "session_id"           in d
        assert "execution_session_id" in d
        assert "state"                in d
        assert "recovery_trigger"     in d

    def test_retry_loop(self):
        """VERIFYING → RECOVERING is the retry loop."""
        s = _session()
        for st in [
            RecoveryState.INITIALIZING, RecoveryState.DETECTING,
            RecoveryState.ASSESSING, RecoveryState.READY,
            RecoveryState.RECOVERING, RecoveryState.VERIFYING,
        ]:
            s.transition_to(st)
        # retry
        s.transition_to(RecoveryState.RECOVERING)
        assert s.state == RecoveryState.RECOVERING


# ─────────────────────────────────────────────────────────────────────────────
# 7  RecoveryTransition
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryTransition:
    def test_factory(self):
        t = make_recovery_transition(
            "s1", RecoveryState.CREATED, RecoveryState.INITIALIZING
        )
        assert t.from_state == RecoveryState.CREATED
        assert t.to_state   == RecoveryState.INITIALIZING
        assert t.session_id == "s1"

    def test_immutable(self):
        t = make_recovery_transition(
            "s", RecoveryState.CREATED, RecoveryState.INITIALIZING
        )
        with pytest.raises((AttributeError, TypeError)):
            t.from_state = RecoveryState.FAILED  # type: ignore

    def test_unique_ids(self):
        t1 = make_recovery_transition("s", RecoveryState.CREATED, RecoveryState.INITIALIZING)
        t2 = make_recovery_transition("s", RecoveryState.CREATED, RecoveryState.INITIALIZING)
        assert t1.transition_id != t2.transition_id

    def test_to_dict(self):
        t = make_recovery_transition("s", RecoveryState.CREATED, RecoveryState.INITIALIZING, reason="init")
        d = t.to_dict()
        assert d["from_state"] == "created"
        assert d["to_state"]   == "initializing"
        assert d["reason"]     == "init"

    def test_custom_transition_id(self):
        t = make_recovery_transition("s", RecoveryState.CREATED, RecoveryState.INITIALIZING, transition_id="custom-id")
        assert t.transition_id == "custom-id"


# ─────────────────────────────────────────────────────────────────────────────
# 8  RecoveryEvents
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryEvents:
    def _assert_event(self, ev: RecoveryEvent, etype: RecoveryEventType, sid: str):
        assert ev.event_type  == etype
        assert ev.session_id  == sid
        assert ev.event_id
        assert ev.occurred_at > 0
        assert ev.version     == VERSION

    def test_created(self):
        ev = make_recovery_created("s1")
        self._assert_event(ev, RecoveryEventType.RECOVERY_CREATED, "s1")

    def test_initialized(self):
        ev = make_recovery_initialized("s2")
        self._assert_event(ev, RecoveryEventType.RECOVERY_INITIALIZED, "s2")

    def test_detecting(self):
        ev = make_recovery_detecting("s3")
        self._assert_event(ev, RecoveryEventType.RECOVERY_DETECTING, "s3")

    def test_assessing(self):
        ev = make_recovery_assessing("s4")
        self._assert_event(ev, RecoveryEventType.RECOVERY_ASSESSING, "s4")

    def test_ready(self):
        ev = make_recovery_ready("s5")
        self._assert_event(ev, RecoveryEventType.RECOVERY_READY, "s5")

    def test_started(self):
        ev = make_recovery_started("s6")
        self._assert_event(ev, RecoveryEventType.RECOVERY_STARTED, "s6")

    def test_verifying(self):
        ev = make_recovery_verifying("s7")
        self._assert_event(ev, RecoveryEventType.RECOVERY_VERIFYING, "s7")

    def test_completed(self):
        ev = make_recovery_completed("s8")
        self._assert_event(ev, RecoveryEventType.RECOVERY_COMPLETED, "s8")

    def test_failed(self):
        ev = make_recovery_failed("s9", reason="timeout")
        self._assert_event(ev, RecoveryEventType.RECOVERY_FAILED, "s9")
        assert ev.reason == "timeout"

    def test_aborted(self):
        ev = make_recovery_aborted("s10", reason="cancelled")
        self._assert_event(ev, RecoveryEventType.RECOVERY_ABORTED, "s10")

    def test_archived(self):
        ev = make_recovery_archived("s11")
        self._assert_event(ev, RecoveryEventType.RECOVERY_ARCHIVED, "s11")

    def test_unique_event_ids(self):
        e1 = make_recovery_started("s")
        e2 = make_recovery_started("s")
        assert e1.event_id != e2.event_id

    def test_immutable(self):
        ev = make_recovery_started("s")
        with pytest.raises((AttributeError, TypeError)):
            ev.event_id = "x"  # type: ignore

    def test_to_dict(self):
        ev = make_recovery_started("s")
        d = ev.to_dict()
        assert "event_id"   in d
        assert "event_type" in d
        assert "session_id" in d


# ─────────────────────────────────────────────────────────────────────────────
# 9  Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryValidation:
    def setup_method(self):
        self.v = RecoveryValidator()

    def test_valid_context(self):
        r = self.v.validate_context(_ctx())
        assert r.is_valid

    def test_empty_exec_session_fails(self):
        m = MagicMock()
        m.execution_session_id = ""
        m.subsystem_id         = "sub"
        m.recovery_reason      = "reason"
        m.recovery_trigger     = RecoveryTrigger.AUTOMATIC
        m.recovery_version     = 1
        r = self.v.validate_context(m)
        assert not r.is_valid

    def test_empty_subsystem_fails(self):
        m = MagicMock()
        m.execution_session_id = "exec"
        m.subsystem_id         = ""
        m.recovery_reason      = "reason"
        m.recovery_trigger     = RecoveryTrigger.AUTOMATIC
        m.recovery_version     = 1
        r = self.v.validate_context(m)
        assert not r.is_valid

    def test_empty_reason_yields_warning(self):
        m = MagicMock()
        m.execution_session_id = "exec"
        m.subsystem_id         = "sub"
        m.recovery_reason      = ""
        m.recovery_trigger     = RecoveryTrigger.AUTOMATIC
        m.recovery_version     = 1
        r = self.v.validate_context(m)
        assert r.is_valid   # warning only
        assert r.warnings

    def test_valid_transition(self):
        r = self.v.validate_transition(RecoveryState.CREATED, RecoveryState.INITIALIZING)
        assert r.is_valid

    def test_invalid_transition(self):
        r = self.v.validate_transition(RecoveryState.CREATED, RecoveryState.COMPLETED)
        assert not r.is_valid
        assert r.errors

    def test_validate_session(self):
        s = _session()
        r = self.v.validate_session(s)
        assert r.is_valid

    def test_history_integrity_valid(self):
        s = _session()
        s.transition_to(RecoveryState.INITIALIZING)
        s.transition_to(RecoveryState.DETECTING)
        r = self.v.validate_history_integrity(s.transitions)
        assert r.is_valid

    def test_history_integrity_gap(self):
        t1 = make_recovery_transition("s", RecoveryState.CREATED,      RecoveryState.INITIALIZING)
        t2 = make_recovery_transition("s", RecoveryState.DETECTING,     RecoveryState.ASSESSING)
        # Gap: t1.to_state=INITIALIZING ≠ t2.from_state=DETECTING
        r = self.v.validate_history_integrity([t1, t2])
        assert not r.is_valid

    def test_validation_result_add_error(self):
        vr = RecoveryValidationResult()
        assert vr.is_valid
        vr.add_error("broken")
        assert not vr.is_valid
        assert "broken" in vr.errors

    def test_validation_result_add_warning(self):
        vr = RecoveryValidationResult()
        vr.add_warning("note")
        assert vr.is_valid
        assert "note" in vr.warnings

    def test_validation_result_to_dict(self):
        vr = RecoveryValidationResult()
        vr.add_error("e1")
        d = vr.to_dict()
        assert "is_valid" in d
        assert "errors"   in d
        assert "warnings" in d


# ─────────────────────────────────────────────────────────────────────────────
# 10  Statistics
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryStatistics:
    def test_initial_zeros(self):
        s = RecoveryStatistics()
        assert s.sessions_created   == 0
        assert s.sessions_completed == 0
        assert s.completion_rate    == 0.0

    def test_record_created(self):
        s = RecoveryStatistics()
        s.record_created()
        assert s.sessions_created == 1

    def test_record_completed(self):
        s = RecoveryStatistics()
        s.record_completed(100.0)
        assert s.sessions_completed == 1
        assert s.average_duration_ms == 100.0

    def test_completion_rate(self):
        s = RecoveryStatistics()
        s.record_completed(0.0)
        s.record_completed(0.0)
        s.record_failed()
        assert abs(s.completion_rate - (2/3)) < 1e-9

    def test_failure_rate(self):
        s = RecoveryStatistics()
        s.record_failed()
        assert s.failure_rate == 1.0

    def test_abort_rate(self):
        s = RecoveryStatistics()
        s.record_completed(0.0)
        s.record_aborted()
        assert s.abort_rate == 0.5

    def test_record_transition(self):
        s = RecoveryStatistics()
        s.record_transition()
        assert s.total_transitions == 1

    def test_record_archived(self):
        s = RecoveryStatistics()
        s.record_archived()
        assert s.sessions_archived == 1

    def test_reset(self):
        s = RecoveryStatistics()
        s.record_created()
        s.record_completed(50.0)
        s.reset()
        assert s.sessions_created   == 0
        assert s.sessions_completed == 0

    def test_copy_independent(self):
        s = RecoveryStatistics()
        s.record_created()
        c = s.copy()
        s.record_created()
        assert c.sessions_created == 1
        assert s.sessions_created == 2

    def test_to_dict(self):
        s = RecoveryStatistics()
        d = s.to_dict()
        assert "sessions_created"   in d
        assert "completion_rate"    in d
        assert "average_duration_ms"in d

    def test_thread_safe_increments(self):
        s = RecoveryStatistics()
        threads = [
            threading.Thread(target=lambda: [s.record_created() for _ in range(50)])
            for _ in range(10)
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        assert s.sessions_created == 500


# ─────────────────────────────────────────────────────────────────────────────
# 11  History
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryHistory:
    def test_append_session(self):
        h = RecoveryHistory()
        s = _session()
        h.append_session(s)
        assert h.session_count == 1
        assert h.latest_session() is s

    def test_bounded_sessions(self):
        h = RecoveryHistory(max_sessions=3)
        for _ in range(5):
            h.append_session(_session())
        assert h.session_count == 3

    def test_sessions_for_execution(self):
        h = RecoveryHistory()
        eid = _sid()
        s1 = RecoverySession(execution_session_id=eid, subsystem_id="sub-a",
                             recovery_trigger=RecoveryTrigger.AUTOMATIC, recovery_reason="t")
        s2 = _session()
        h.append_session(s1)
        h.append_session(s2)
        assert len(h.sessions_for_execution(eid)) == 1

    def test_append_transition(self):
        h = RecoveryHistory()
        t = make_recovery_transition("s", RecoveryState.CREATED, RecoveryState.INITIALIZING)
        h.append_transition(t)
        assert h.transition_count == 1

    def test_transitions_for_session(self):
        h = RecoveryHistory()
        t = make_recovery_transition("s1", RecoveryState.CREATED, RecoveryState.INITIALIZING)
        h.append_transition(t)
        h.append_transition(make_recovery_transition("s2", RecoveryState.CREATED, RecoveryState.INITIALIZING))
        assert len(h.transitions_for_session("s1")) == 1

    def test_append_event(self):
        h = RecoveryHistory()
        ev = make_recovery_created("s")
        h.append_event(ev)
        assert h.event_count == 1

    def test_events_for_session(self):
        h = RecoveryHistory()
        h.append_event(make_recovery_created("s1"))
        h.append_event(make_recovery_created("s2"))
        assert len(h.events_for_session("s1")) == 1

    def test_events_matching(self):
        h = RecoveryHistory()
        h.append_event(make_recovery_created("s"))
        h.append_event(make_recovery_started("s"))
        found = h.events_matching(
            lambda e: e.event_type == RecoveryEventType.RECOVERY_CREATED
        )
        assert len(found) == 1

    def test_clear(self):
        h = RecoveryHistory()
        h.append_session(_session())
        h.append_event(make_recovery_created("s"))
        h.clear()
        assert h.session_count == 0
        assert h.event_count   == 0

    def test_latest_none_when_empty(self):
        h = RecoveryHistory()
        assert h.latest_session()    is None
        assert h.latest_event()      is None
        assert h.latest_transition() is None

    def test_completed_sessions_filter(self):
        h = RecoveryHistory()
        s = _session()
        for st in [
            RecoveryState.INITIALIZING, RecoveryState.DETECTING,
            RecoveryState.ASSESSING, RecoveryState.READY,
            RecoveryState.RECOVERING, RecoveryState.VERIFYING,
            RecoveryState.COMPLETED,
        ]:
            s.transition_to(st)
        h.append_session(s)
        h.append_session(_session())  # CREATED — not completed
        assert len(h.completed_sessions()) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 12  Registry
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryRegistry:
    def _started(self) -> RecoveryRegistry:
        r = RecoveryRegistry()
        r.start()
        return r

    def test_store_and_get(self):
        reg = self._started()
        s = _session()
        reg.store(s)
        assert reg.get(s.session_id) is s
        reg.stop()

    def test_get_missing_raises(self):
        reg = self._started()
        with pytest.raises(RecoverySessionNotFoundError):
            reg.get("nonexistent")
        reg.stop()

    def test_find_returns_none(self):
        reg = self._started()
        assert reg.find("x") is None
        reg.stop()

    def test_duplicate_store_raises(self):
        reg = self._started()
        s = _session()
        reg.store(s)
        with pytest.raises(RecoverySessionAlreadyExistsError):
            reg.store(s)
        reg.stop()

    def test_archive_moves_session(self):
        reg = self._started()
        s = _session()
        reg.store(s)
        reg.archive(s.session_id)
        assert reg.find(s.session_id) is None
        assert reg.find_archived(s.session_id) is s
        assert reg.archive_count == 1
        reg.stop()

    def test_for_execution_session(self):
        reg = self._started()
        eid = _sid()
        s1 = RecoverySession(execution_session_id=eid, subsystem_id="sub",
                             recovery_trigger=RecoveryTrigger.AUTOMATIC, recovery_reason="t")
        s2 = _session()
        reg.store(s1)
        reg.store(s2)
        results = reg.for_execution_session(eid)
        assert len(results) == 1
        reg.stop()

    def test_for_state(self):
        reg = self._started()
        s = _session()
        reg.store(s)
        results = reg.for_state(RecoveryState.CREATED)
        assert s in results
        reg.stop()

    def test_active_count(self):
        reg = self._started()
        s = _session()
        s.transition_to(RecoveryState.INITIALIZING)
        reg.store(s)
        assert reg.active_count == 1
        reg.stop()

    def test_contains(self):
        reg = self._started()
        s = _session()
        reg.store(s)
        assert reg.contains(s.session_id)
        assert not reg.contains("unknown")
        reg.stop()

    def test_clear(self):
        reg = self._started()
        reg.store(_session())
        reg.clear()
        assert reg.count == 0
        reg.stop()

    def test_operation_before_start_raises(self):
        reg = RecoveryRegistry()
        with pytest.raises(RecoveryNotRunningError):
            reg.store(_session())

    def test_bounded_eviction(self):
        reg = RecoveryRegistry(max_sessions=2)
        reg.start()
        for _ in range(4):
            reg.store(_session())
        assert reg.count == 2
        reg.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 13  Factory
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryFactory:
    def _started(self) -> RecoveryFactory:
        f = RecoveryFactory()
        f.start()
        return f

    def test_create_from_context(self):
        f = self._started()
        ctx = _ctx()
        s = f.create(ctx)
        assert isinstance(s, RecoverySession)
        assert s.state == RecoveryState.CREATED
        assert s.execution_session_id == ctx.execution_session_id
        f.stop()

    def test_create_from_params(self):
        f = self._started()
        s = f.create_from_params(
            _sid(), _sub(), RecoveryTrigger.MANUAL, "test"
        )
        assert isinstance(s, RecoverySession)
        assert s.state == RecoveryState.CREATED
        f.stop()

    def test_each_create_is_independent(self):
        f = self._started()
        s1 = f.create(_ctx())
        s2 = f.create(_ctx())
        assert s1.session_id != s2.session_id
        f.stop()

    def test_factory_not_started_raises(self):
        f = RecoveryFactory()
        with pytest.raises(RecoveryNotRunningError):
            f.create(_ctx())

    def test_custom_session_id(self):
        f = self._started()
        s = f.create_from_params(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t",
                                  session_id="custom-sid-99")
        assert s.session_id == "custom-sid-99"
        f.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 14  RecoveryLifecycle — full API
# ─────────────────────────────────────────────────────────────────────────────

class TestRecoveryLifecycle:
    def setup_method(self):
        self.lc = _started_lifecycle()

    def teardown_method(self):
        try:
            self.lc.stop()
        except Exception:
            pass

    def test_start_and_stop(self):
        lc = RecoveryLifecycle()
        lc.start()
        assert lc.is_running()
        lc.stop()
        assert not lc.is_running()

    def test_create_returns_session_in_created(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "test")
        assert isinstance(s, RecoverySession)
        assert s.state == RecoveryState.CREATED

    def test_create_before_start_raises(self):
        lc = RecoveryLifecycle()
        with pytest.raises(RecoveryNotRunningError):
            lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")

    def test_create_invalid_context_raises(self):
        with pytest.raises(RecoveryValidationError):
            self.lc.create("", _sub(), RecoveryTrigger.AUTOMATIC, "t")

    def test_full_happy_path(self):
        s = _full_lifecycle(self.lc)
        assert s.is_completed
        assert s.start_time is not None
        assert s.end_time   is not None

    def test_initialize(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        assert s.state == RecoveryState.INITIALIZING

    def test_detect(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        self.lc.detect(s.session_id)
        assert s.state == RecoveryState.DETECTING

    def test_assess(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        self.lc.detect(s.session_id)
        self.lc.assess(s.session_id)
        assert s.state == RecoveryState.ASSESSING

    def test_ready(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        self.lc.detect(s.session_id)
        self.lc.assess(s.session_id)
        self.lc.ready(s.session_id)
        assert s.state == RecoveryState.READY

    def test_begin_recovery(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        self.lc.detect(s.session_id)
        self.lc.assess(s.session_id)
        self.lc.ready(s.session_id)
        self.lc.begin_recovery(s.session_id)
        assert s.state == RecoveryState.RECOVERING

    def test_verify(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        self.lc.detect(s.session_id)
        self.lc.assess(s.session_id)
        self.lc.ready(s.session_id)
        self.lc.begin_recovery(s.session_id)
        self.lc.verify(s.session_id)
        assert s.state == RecoveryState.VERIFYING

    def test_complete(self):
        s = _full_lifecycle(self.lc)
        assert s.state == RecoveryState.COMPLETED

    def test_fail_from_any_active_state(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        self.lc.detect(s.session_id)
        self.lc.fail(s.session_id, "gateway crash")
        assert s.is_failed
        assert s.failure_reason == "gateway crash"

    def test_abort(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        self.lc.abort(s.session_id, "operator cancelled")
        assert s.is_aborted
        assert s.abort_reason == "operator cancelled"

    def test_archive(self):
        s = _full_lifecycle(self.lc)
        self.lc.archive(s.session_id)
        assert s.is_archived
        # Session moved to archive store
        assert self.lc._registry.find(s.session_id) is None
        assert self.lc._registry.find_archived(s.session_id) is s

    def test_retry_recovery(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        self.lc.detect(s.session_id)
        self.lc.assess(s.session_id)
        self.lc.ready(s.session_id)
        self.lc.begin_recovery(s.session_id)
        self.lc.verify(s.session_id)
        self.lc.retry_recovery(s.session_id)
        assert s.state == RecoveryState.RECOVERING

    def test_get_session(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        fetched = self.lc.get_session(s.session_id)
        assert fetched is s

    def test_find_session_none(self):
        assert self.lc.find_session("nonexistent") is None

    def test_sessions_for_execution(self):
        eid = _sid()
        s1 = self.lc.create(eid, _sub(), RecoveryTrigger.AUTOMATIC, "t")
        s2 = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        results = self.lc.sessions_for_execution(eid)
        assert len(results) == 1
        assert results[0] is s1

    def test_active_sessions(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        active = self.lc.active_sessions()
        assert s in active

    def test_sessions_in_state(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        results = self.lc.sessions_in_state(RecoveryState.CREATED)
        assert s in results

    def test_statistics_incremented(self):
        stats_before = self.lc.statistics()
        _full_lifecycle(self.lc)
        stats_after = self.lc.statistics()
        assert stats_after.sessions_created   > stats_before.sessions_created
        assert stats_after.sessions_completed > stats_before.sessions_completed
        assert stats_after.total_transitions  > stats_before.total_transitions

    def test_statistics_fail_incremented(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        self.lc.fail(s.session_id, "test failure")
        stats = self.lc.statistics()
        assert stats.sessions_failed >= 1

    def test_statistics_abort_incremented(self):
        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)
        self.lc.abort(s.session_id, "test abort")
        stats = self.lc.statistics()
        assert stats.sessions_aborted >= 1

    def test_event_listener_called(self):
        received: List[RecoveryEvent] = []
        self.lc.add_event_listener(received.append)

        s = self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        self.lc.initialize(s.session_id)

        assert any(e.event_type == RecoveryEventType.RECOVERY_CREATED   for e in received)
        assert any(e.event_type == RecoveryEventType.RECOVERY_INITIALIZED for e in received)
        self.lc.remove_event_listener(received.append)

    def test_remove_listener_bound_method(self):
        """Bound-method identity regression — must use == not is."""
        received: List[RecoveryEvent] = []

        class _Recv:
            def on_event(self, ev: RecoveryEvent):
                received.append(ev)

        obj = _Recv()
        self.lc.add_event_listener(obj.on_event)
        self.lc.remove_event_listener(obj.on_event)

        self.lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        assert len(received) == 0

    def test_history_records_events(self):
        _full_lifecycle(self.lc)
        h = self.lc.history()
        assert h.event_count >= 1

    def test_history_records_completed_sessions(self):
        _full_lifecycle(self.lc)
        h = self.lc.history()
        assert h.session_count >= 1

    def test_create_from_context(self):
        ctx = _ctx()
        s = self.lc.create_from_context(ctx)
        assert s.state == RecoveryState.CREATED
        assert s.execution_session_id == ctx.execution_session_id


# ─────────────────────────────────────────────────────────────────────────────
# 15  All valid/invalid transition edges
# ─────────────────────────────────────────────────────────────────────────────

class TestTransitionGates:
    """Exhaustive state-machine coverage."""

    def _sess_at(self, *states: RecoveryState) -> RecoverySession:
        s = _session()
        for st in states:
            s.transition_to(st)
        return s

    def test_created_to_initializing(self):
        s = _session()
        s.transition_to(RecoveryState.INITIALIZING)
        assert s.state == RecoveryState.INITIALIZING

    def test_created_to_anything_else_fails(self):
        for to in RecoveryState:
            if to == RecoveryState.INITIALIZING:
                continue
            s = _session()
            with pytest.raises((RecoveryInvalidTransitionError, RecoverySessionTerminalError)):
                s.transition_to(to)

    def test_initializing_to_detecting(self):
        s = self._sess_at(RecoveryState.INITIALIZING)
        s.transition_to(RecoveryState.DETECTING)

    def test_initializing_to_failed(self):
        s = self._sess_at(RecoveryState.INITIALIZING)
        s.transition_to(RecoveryState.FAILED)

    def test_initializing_to_aborted(self):
        s = self._sess_at(RecoveryState.INITIALIZING)
        s.transition_to(RecoveryState.ABORTED)

    def test_detecting_to_assessing(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.DETECTING)
        s.transition_to(RecoveryState.ASSESSING)

    def test_assessing_to_ready(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.DETECTING, RecoveryState.ASSESSING)
        s.transition_to(RecoveryState.READY)

    def test_ready_to_recovering(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.DETECTING,
                          RecoveryState.ASSESSING, RecoveryState.READY)
        s.transition_to(RecoveryState.RECOVERING)

    def test_ready_to_aborted(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.DETECTING,
                          RecoveryState.ASSESSING, RecoveryState.READY)
        s.transition_to(RecoveryState.ABORTED)

    def test_ready_to_failed(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.DETECTING,
                          RecoveryState.ASSESSING, RecoveryState.READY)
        s.transition_to(RecoveryState.FAILED)

    def test_recovering_to_verifying(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.DETECTING,
                          RecoveryState.ASSESSING, RecoveryState.READY,
                          RecoveryState.RECOVERING)
        s.transition_to(RecoveryState.VERIFYING)

    def test_recovering_to_failed(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.DETECTING,
                          RecoveryState.ASSESSING, RecoveryState.READY,
                          RecoveryState.RECOVERING)
        s.transition_to(RecoveryState.FAILED)

    def test_verifying_to_completed(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.DETECTING,
                          RecoveryState.ASSESSING, RecoveryState.READY,
                          RecoveryState.RECOVERING, RecoveryState.VERIFYING)
        s.transition_to(RecoveryState.COMPLETED)

    def test_verifying_retry_loop(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.DETECTING,
                          RecoveryState.ASSESSING, RecoveryState.READY,
                          RecoveryState.RECOVERING, RecoveryState.VERIFYING)
        s.transition_to(RecoveryState.RECOVERING)

    def test_completed_to_archived(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.DETECTING,
                          RecoveryState.ASSESSING, RecoveryState.READY,
                          RecoveryState.RECOVERING, RecoveryState.VERIFYING,
                          RecoveryState.COMPLETED)
        s.transition_to(RecoveryState.ARCHIVED)

    def test_failed_to_archived(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.FAILED)
        s.transition_to(RecoveryState.ARCHIVED)

    def test_aborted_to_archived(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.ABORTED)
        s.transition_to(RecoveryState.ARCHIVED)

    def test_archived_is_completely_blocked(self):
        s = self._sess_at(RecoveryState.INITIALIZING, RecoveryState.FAILED,
                          RecoveryState.ARCHIVED)
        for to in RecoveryState:
            with pytest.raises((RecoverySessionTerminalError, RecoveryInvalidTransitionError)):
                s.transition_to(to)


# ─────────────────────────────────────────────────────────────────────────────
# 16  Concurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_creates(self):
        lc = _started_lifecycle()
        errors: List[Exception] = []

        def _create():
            try:
                lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "concurrency test")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_create) for _ in range(30)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert not errors, f"Errors: {errors}"
        assert lc.statistics().sessions_created == 30
        lc.stop()

    def test_concurrent_statistics_updates(self):
        s = RecoveryStatistics()
        threads = [
            threading.Thread(target=lambda: [s.record_created() for _ in range(100)])
            for _ in range(10)
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        assert s.sessions_created == 1_000

    def test_concurrent_registry_store(self):
        reg = RecoveryRegistry()
        reg.start()
        errors: List[Exception] = []

        def _store():
            try:
                reg.store(_session())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_store) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        reg.stop()

    def test_concurrent_history_appends(self):
        h = RecoveryHistory()
        threads = [
            threading.Thread(target=lambda: h.append_session(_session()))
            for _ in range(30)
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        assert h.session_count == 30

    def test_concurrent_event_listeners(self):
        lc = _started_lifecycle()
        counts: Dict[str, int] = {"n": 0}
        lock = threading.Lock()

        def listener(ev: RecoveryEvent):
            with lock:
                counts["n"] += 1

        lc.add_event_listener(listener)
        threads = [
            threading.Thread(
                target=lambda: lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "c")
            )
            for _ in range(10)
        ]
        for t in threads: t.start()
        for t in threads: t.join()
        lc.remove_event_listener(listener)
        assert counts["n"] >= 10  # at least RECOVERY_CREATED per session
        lc.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 17  Regression / edge cases
# ─────────────────────────────────────────────────────────────────────────────

class TestRegressionEdgeCases:
    def test_duration_ms_zero_without_start(self):
        s = _session()
        assert s.duration_ms == 0.0

    def test_statistics_average_zero_without_completions(self):
        s = RecoveryStatistics()
        assert s.average_duration_ms == 0.0

    def test_history_bounded_at_one(self):
        h = RecoveryHistory(max_sessions=1)
        h.append_session(_session())
        h.append_session(_session())
        assert h.session_count == 1

    def test_registry_archive_missing_raises(self):
        reg = RecoveryRegistry()
        reg.start()
        with pytest.raises(RecoverySessionNotFoundError):
            reg.archive("nonexistent")
        reg.stop()

    def test_context_to_dict_roundtrip(self):
        ctx = _ctx()
        d = ctx.to_dict()
        assert d["execution_session_id"] == ctx.execution_session_id
        assert d["subsystem_id"]         == ctx.subsystem_id

    def test_session_to_dict_has_all_keys(self):
        s = _session()
        d = s.to_dict()
        for key in ("session_id", "execution_session_id", "state", "recovery_trigger",
                    "recovery_reason", "duration_ms", "created_at"):
            assert key in d, f"missing key: {key}"

    def test_lifecycle_statistics_returns_copy(self):
        lc = _started_lifecycle()
        s1 = lc.statistics()
        lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        s2 = lc.statistics()
        # s1 is a snapshot; should not reflect the new create
        assert s1.sessions_created == 0
        assert s2.sessions_created == 1
        lc.stop()

    def test_multiple_retries_allowed(self):
        lc = _started_lifecycle()
        s = lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        lc.initialize(s.session_id)
        lc.detect(s.session_id)
        lc.assess(s.session_id)
        lc.ready(s.session_id)
        lc.begin_recovery(s.session_id)
        # Retry loop: RECOVERING → VERIFYING → RECOVERING (repeated)
        for _ in range(3):
            lc.verify(s.session_id)
            lc.retry_recovery(s.session_id)   # VERIFYING → RECOVERING
        # Should still be in RECOVERING after retries
        assert s.state == RecoveryState.RECOVERING
        lc.stop()

    def test_transition_actor_and_reason_propagated(self):
        lc = _started_lifecycle()
        s = lc.create(_sid(), _sub(), RecoveryTrigger.AUTOMATIC, "t")
        lc.initialize(s.session_id, actor="policy-engine", reason="auto-init")
        t = s.transitions[-1]
        assert t.actor  == "policy-engine"
        assert t.reason == "auto-init"
        lc.stop()

    def test_different_triggers_accepted(self):
        lc = _started_lifecycle()
        for trigger in RecoveryTrigger:
            s = lc.create(_sid(), _sub(), trigger, "trigger test")
            assert s.recovery_trigger == trigger
        lc.stop()
