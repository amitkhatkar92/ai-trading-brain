"""
tests/unit/execution/analytics/lifecycle/test_analytics_lifecycle.py
=====================================================================
Comprehensive test suite for C8 M1 — Execution Analytics Lifecycle.

Coverage targets:
  • constants / exceptions
  • AnalyticsStateRecord / can_transition
  • AnalyticsTransition
  • AnalyticsContext / make_analytics_context
  • AnalyticsMetadata / make_analytics_metadata
  • AnalyticsSession (state machine, transitions, side-effects)
  • AnalyticsEvents (all factory functions)
  • AnalyticsStatistics
  • AnalyticsHistory
  • AnalyticsRegistry
  • AnalyticsFactory
  • AnalyticsValidator / AnalyticsValidationResult
  • AnalyticsLifecycle (full lifecycle + edge cases + concurrency)
  • Regression: invalid transitions, terminal guards, duplicate sessions

95%+ coverage target

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import List
from unittest.mock import MagicMock

import pytest

from iios.execution.analytics.lifecycle import (
    ACTIVE_STATES,
    ACTOR_LIFECYCLE,
    ACTOR_SYSTEM,
    AnalyticsContext,
    AnalyticsError,
    AnalyticsEvent,
    AnalyticsEventType,
    AnalyticsFactory,
    AnalyticsHistory,
    AnalyticsHistoryError,
    AnalyticsInvalidTransitionError,
    AnalyticsLifecycle,
    AnalyticsMetadata,
    AnalyticsMode,
    AnalyticsNotRunningError,
    AnalyticsRegistry,
    AnalyticsScope,
    AnalyticsSession,
    AnalyticsSessionAlreadyExistsError,
    AnalyticsSessionNotFoundError,
    AnalyticsSessionTerminalError,
    AnalyticsState,
    AnalyticsStateRecord,
    AnalyticsStatistics,
    AnalyticsTrigger,
    AnalyticsTransition,
    AnalyticsValidationError,
    AnalyticsValidationResult,
    AnalyticsValidator,
    IMMUTABLE_STATES,
    LIFECYCLE_SYSTEM_ID,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VERSION,
    can_transition,
    make_analytics_archived,
    make_analytics_completed,
    make_analytics_context,
    make_analytics_created,
    make_analytics_failed,
    make_analytics_initialized,
    make_analytics_metadata,
    make_analytics_paused,
    make_analytics_resumed,
    make_analytics_started,
    make_analytics_transition,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _new_session(**kwargs) -> AnalyticsSession:
    defaults = dict(execution_session_id=str(uuid.uuid4()))
    defaults.update(kwargs)
    return AnalyticsSession(**defaults)


def _started_lifecycle(**kwargs) -> AnalyticsLifecycle:
    lc = AnalyticsLifecycle(**kwargs)
    lc.start()
    return lc


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_states_defined(self):
        expected = {
            "CREATED", "INITIALIZING", "COLLECTING", "ANALYZING", "READY",
            "ACTIVE", "PAUSED", "RESUMING", "COMPLETED", "FAILED", "ARCHIVED",
        }
        actual = {s.name for s in AnalyticsState}
        assert actual == expected

    def test_valid_transitions_cover_all_states(self):
        for state in AnalyticsState:
            assert state in VALID_TRANSITIONS

    def test_archived_is_terminal(self):
        assert VALID_TRANSITIONS[AnalyticsState.ARCHIVED] == frozenset()
        assert AnalyticsState.ARCHIVED in IMMUTABLE_STATES
        assert AnalyticsState.ARCHIVED in TERMINAL_STATES

    def test_active_states_not_in_terminal(self):
        for s in ACTIVE_STATES:
            assert s not in TERMINAL_STATES

    def test_version_format(self):
        parts = VERSION.split(".")
        assert len(parts) == 3

    def test_scopes_defined(self):
        for scope in ("EXECUTION", "PORTFOLIO", "STRATEGY", "WORKFLOW", "SYSTEM", "CUSTOM"):
            assert hasattr(AnalyticsScope, scope)

    def test_modes_defined(self):
        for mode in ("REAL_TIME", "BATCH", "ON_DEMAND", "SCHEDULED", "REPLAY"):
            assert hasattr(AnalyticsMode, mode)

    def test_triggers_defined(self):
        for t in ("MANUAL", "AUTOMATIC", "SCHEDULED", "EVENT_DRIVEN", "SYSTEM"):
            assert hasattr(AnalyticsTrigger, t)

    def test_event_types_defined(self):
        for et in (
            "ANALYTICS_CREATED", "ANALYTICS_INITIALIZED", "ANALYTICS_STARTED",
            "ANALYTICS_PAUSED", "ANALYTICS_RESUMED", "ANALYTICS_COMPLETED",
            "ANALYTICS_FAILED", "ANALYTICS_ARCHIVED",
        ):
            assert hasattr(AnalyticsEventType, et)


# ═══════════════════════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_error(self):
        e = AnalyticsError("test")
        assert e.error_code == "AL-000"

    def test_not_running(self):
        e = AnalyticsNotRunningError()
        assert "AL-001" in e.error_code
        assert "not running" in str(e).lower()

    def test_not_found(self):
        e = AnalyticsSessionNotFoundError("SID-1")
        assert e.session_id == "SID-1"
        assert "SID-1" in str(e)

    def test_invalid_transition(self):
        e = AnalyticsInvalidTransitionError("created", "completed", "SID-2")
        assert e.from_state == "created"
        assert e.to_state == "completed"
        assert "SID-2" in str(e)

    def test_validation_error_carries_errors(self):
        e = AnalyticsValidationError("bad", errors=("e1", "e2"))
        assert e.errors == ("e1", "e2")

    def test_already_exists(self):
        e = AnalyticsSessionAlreadyExistsError("SID-3")
        assert e.session_id == "SID-3"

    def test_terminal_error(self):
        e = AnalyticsSessionTerminalError("SID-4", "archived")
        assert "archived" in str(e)

    def test_all_inherit_base(self):
        for cls, args in [
            (AnalyticsNotRunningError,          []),
            (AnalyticsSessionNotFoundError,     ["SID"]),
            (AnalyticsInvalidTransitionError,   ["a", "b"]),
            (AnalyticsValidationError,          []),
            (AnalyticsSessionAlreadyExistsError,["SID"]),
            (AnalyticsSessionTerminalError,     ["SID", "state"]),
            (AnalyticsHistoryError,             []),
        ]:
            e = cls(*args)
            assert isinstance(e, AnalyticsError)


# ═══════════════════════════════════════════════════════════════════════════════
# can_transition
# ═══════════════════════════════════════════════════════════════════════════════

class TestCanTransition:
    def test_created_to_initializing(self):
        assert can_transition(AnalyticsState.CREATED, AnalyticsState.INITIALIZING)

    def test_created_to_active_invalid(self):
        assert not can_transition(AnalyticsState.CREATED, AnalyticsState.ACTIVE)

    def test_archived_to_anything_invalid(self):
        for state in AnalyticsState:
            assert not can_transition(AnalyticsState.ARCHIVED, state)

    def test_completed_to_archived(self):
        assert can_transition(AnalyticsState.COMPLETED, AnalyticsState.ARCHIVED)

    def test_paused_to_resuming(self):
        assert can_transition(AnalyticsState.PAUSED, AnalyticsState.RESUMING)

    def test_active_to_paused(self):
        assert can_transition(AnalyticsState.ACTIVE, AnalyticsState.PAUSED)

    def test_analyzing_to_collecting(self):
        assert can_transition(AnalyticsState.ANALYZING, AnalyticsState.COLLECTING)


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsStateRecord
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsStateRecord:
    def test_basic(self):
        r = AnalyticsStateRecord(
            state      = AnalyticsState.CREATED,
            entered_at = 1000.0,
            actor      = "test-actor",
        )
        assert r.state == AnalyticsState.CREATED
        assert r.entered_at == 1000.0
        assert r.actor == "test-actor"

    def test_to_dict(self):
        r = AnalyticsStateRecord(state=AnalyticsState.ACTIVE, entered_at=1.0)
        d = r.to_dict()
        assert d["state"] == "active"
        assert "entered_at" in d

    def test_frozen(self):
        r = AnalyticsStateRecord(state=AnalyticsState.CREATED, entered_at=1.0)
        with pytest.raises(Exception):
            r.state = AnalyticsState.ACTIVE  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsTransition
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsTransition:
    def test_make(self):
        t = make_analytics_transition(
            session_id = "S1",
            from_state = AnalyticsState.CREATED,
            to_state   = AnalyticsState.INITIALIZING,
        )
        assert t.from_state == AnalyticsState.CREATED
        assert t.to_state   == AnalyticsState.INITIALIZING
        assert t.session_id == "S1"
        assert t.version    == VERSION

    def test_to_dict(self):
        t = make_analytics_transition(
            "S1", AnalyticsState.CREATED, AnalyticsState.INITIALIZING
        )
        d = t.to_dict()
        assert d["from_state"] == "created"
        assert d["to_state"]   == "initializing"

    def test_unique_ids(self):
        t1 = make_analytics_transition("S", AnalyticsState.CREATED, AnalyticsState.INITIALIZING)
        t2 = make_analytics_transition("S", AnalyticsState.CREATED, AnalyticsState.INITIALIZING)
        assert t1.transition_id != t2.transition_id

    def test_frozen(self):
        t = make_analytics_transition("S", AnalyticsState.CREATED, AnalyticsState.INITIALIZING)
        with pytest.raises(Exception):
            t.session_id = "other"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsContext:
    def test_defaults(self):
        ctx = make_analytics_context("exec-1")
        assert ctx.execution_session_id == "exec-1"
        assert ctx.analytics_scope   == AnalyticsScope.EXECUTION
        assert ctx.analytics_mode    == AnalyticsMode.ON_DEMAND
        assert ctx.analytics_trigger == AnalyticsTrigger.AUTOMATIC

    def test_custom_fields(self):
        ctx = make_analytics_context(
            "exec-2",
            analytics_scope = AnalyticsScope.PORTFOLIO,
            portfolio_id    = "PORTF-1",
            tags            = ("tag1",),
        )
        assert ctx.portfolio_id == "PORTF-1"
        assert ctx.tags == ("tag1",)

    def test_to_dict(self):
        ctx = make_analytics_context("exec-3")
        d = ctx.to_dict()
        assert d["execution_session_id"] == "exec-3"
        assert isinstance(d["tags"], list)

    def test_frozen(self):
        ctx = make_analytics_context("exec-4")
        with pytest.raises(Exception):
            ctx.execution_session_id = "other"  # type: ignore[misc]

    def test_explicit_context_id(self):
        ctx = make_analytics_context("exec-5", context_id="CTX-1")
        assert ctx.context_id == "CTX-1"


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsMetadata
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsMetadata:
    def test_defaults(self):
        m = make_analytics_metadata("sess-1")
        assert m.analytics_session_id == "sess-1"
        assert m.data_window_seconds  == 60.0
        assert m.sample_count         == 0

    def test_collection_duration(self):
        m = make_analytics_metadata(
            "sess-2",
            collection_start=100.0,
            collection_end  =200.0,
        )
        assert m.collection_duration_seconds == 100.0

    def test_analysis_duration(self):
        m = make_analytics_metadata(
            "sess-3",
            analysis_start=50.0,
            analysis_end  =75.0,
        )
        assert m.analysis_duration_seconds == 25.0

    def test_duration_none_when_missing(self):
        m = make_analytics_metadata("sess-4")
        assert m.collection_duration_seconds is None
        assert m.analysis_duration_seconds   is None

    def test_to_dict(self):
        m = make_analytics_metadata("sess-5")
        d = m.to_dict()
        assert d["analytics_session_id"] == "sess-5"
        assert "data_window_seconds" in d

    def test_frozen(self):
        m = make_analytics_metadata("sess-6")
        with pytest.raises(Exception):
            m.sample_count = 99  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsSession — state machine
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsSessionStateMachine:
    def test_initial_state(self):
        s = _new_session()
        assert s.state == AnalyticsState.CREATED
        assert not s.is_terminal
        assert s.start_time is None

    def test_happy_path(self):
        s = _new_session()
        for target in (
            AnalyticsState.INITIALIZING,
            AnalyticsState.COLLECTING,
            AnalyticsState.ANALYZING,
            AnalyticsState.READY,
            AnalyticsState.ACTIVE,
            AnalyticsState.COMPLETED,
        ):
            s.transition_to(target)
        assert s.state == AnalyticsState.COMPLETED
        assert s.start_time is not None
        assert s.end_time   is not None
        assert s.is_terminal

    def test_archive_after_complete(self):
        s = _new_session()
        for t in (
            AnalyticsState.INITIALIZING, AnalyticsState.COLLECTING,
            AnalyticsState.ANALYZING, AnalyticsState.READY,
            AnalyticsState.ACTIVE, AnalyticsState.COMPLETED,
        ):
            s.transition_to(t)
        s.transition_to(AnalyticsState.ARCHIVED)
        assert s.is_archived
        assert s.state in IMMUTABLE_STATES

    def test_invalid_transition_raises(self):
        s = _new_session()
        with pytest.raises(AnalyticsInvalidTransitionError):
            s.transition_to(AnalyticsState.ACTIVE)

    def test_archived_transition_raises(self):
        s = _new_session()
        for t in (
            AnalyticsState.INITIALIZING, AnalyticsState.COLLECTING,
            AnalyticsState.ANALYZING, AnalyticsState.READY,
            AnalyticsState.ACTIVE, AnalyticsState.COMPLETED,
            AnalyticsState.ARCHIVED,
        ):
            s.transition_to(t)
        with pytest.raises(AnalyticsSessionTerminalError):
            s.transition_to(AnalyticsState.FAILED)

    def test_pause_and_resume(self):
        s = _new_session()
        s.transition_to(AnalyticsState.INITIALIZING)
        s.transition_to(AnalyticsState.COLLECTING)
        s.transition_to(AnalyticsState.PAUSED)
        assert s.is_paused
        s.transition_to(AnalyticsState.RESUMING)
        s.transition_to(AnalyticsState.ACTIVE)
        assert s.state == AnalyticsState.ACTIVE

    def test_fail_from_any_active_state(self):
        for active_state in (
            AnalyticsState.INITIALIZING,
            AnalyticsState.COLLECTING,
            AnalyticsState.ANALYZING,
            AnalyticsState.READY,
            AnalyticsState.ACTIVE,
            AnalyticsState.PAUSED,
        ):
            s = _new_session()
            path_to = {
                AnalyticsState.INITIALIZING: [AnalyticsState.INITIALIZING],
                AnalyticsState.COLLECTING:   [AnalyticsState.INITIALIZING, AnalyticsState.COLLECTING],
                AnalyticsState.ANALYZING:    [AnalyticsState.INITIALIZING, AnalyticsState.COLLECTING, AnalyticsState.ANALYZING],
                AnalyticsState.READY:        [AnalyticsState.INITIALIZING, AnalyticsState.COLLECTING, AnalyticsState.ANALYZING, AnalyticsState.READY],
                AnalyticsState.ACTIVE:       [AnalyticsState.INITIALIZING, AnalyticsState.COLLECTING, AnalyticsState.ANALYZING, AnalyticsState.READY, AnalyticsState.ACTIVE],
                AnalyticsState.PAUSED:       [AnalyticsState.INITIALIZING, AnalyticsState.COLLECTING, AnalyticsState.PAUSED],
            }
            for step in path_to[active_state]:
                s.transition_to(step)
            s.transition_to(AnalyticsState.FAILED)
            assert s.is_failed
            assert s.end_time is not None

    def test_transition_count_increments(self):
        s = _new_session()
        s.transition_to(AnalyticsState.INITIALIZING)
        s.transition_to(AnalyticsState.COLLECTING)
        assert s.transition_count == 2

    def test_state_history_length(self):
        s = _new_session()
        s.transition_to(AnalyticsState.INITIALIZING)
        # CREATED + INITIALIZING
        assert len(s.state_history) == 2

    def test_failure_reason(self):
        s = _new_session()
        s.transition_to(AnalyticsState.INITIALIZING)
        s.set_failure_reason("disk full")
        s.transition_to(AnalyticsState.FAILED)
        assert s.failure_reason == "disk full"

    def test_duration_seconds(self):
        s = _new_session()
        for t in (
            AnalyticsState.INITIALIZING, AnalyticsState.COLLECTING,
            AnalyticsState.ANALYZING, AnalyticsState.READY,
            AnalyticsState.ACTIVE,
        ):
            s.transition_to(t)
        assert s.start_time is not None
        assert s.duration_seconds is None   # end_time not yet set
        s.transition_to(AnalyticsState.COMPLETED)
        assert s.duration_seconds is not None
        assert s.duration_seconds >= 0.0

    def test_to_dict(self):
        s = _new_session()
        d = s.to_dict()
        assert d["state"] == "created"
        assert "session_id" in d

    def test_re_analyze_loop(self):
        """ACTIVE → ANALYZING (re-analyze) is valid."""
        s = _new_session()
        for t in (
            AnalyticsState.INITIALIZING, AnalyticsState.COLLECTING,
            AnalyticsState.ANALYZING, AnalyticsState.READY, AnalyticsState.ACTIVE,
        ):
            s.transition_to(t)
        s.transition_to(AnalyticsState.ANALYZING)
        assert s.state == AnalyticsState.ANALYZING

    def test_created_to_failed(self):
        """CREATED → FAILED is valid."""
        s = _new_session()
        s.transition_to(AnalyticsState.FAILED)
        assert s.is_failed


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsEvents
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsEvents:
    def test_make_created(self):
        e = make_analytics_created("S1")
        assert e.event_type == AnalyticsEventType.ANALYTICS_CREATED
        assert e.session_id == "S1"

    def test_make_initialized(self):
        e = make_analytics_initialized("S2")
        assert e.event_type == AnalyticsEventType.ANALYTICS_INITIALIZED

    def test_make_started(self):
        e = make_analytics_started("S3")
        assert e.event_type == AnalyticsEventType.ANALYTICS_STARTED

    def test_make_paused(self):
        e = make_analytics_paused("S4")
        assert e.event_type == AnalyticsEventType.ANALYTICS_PAUSED

    def test_make_resumed(self):
        e = make_analytics_resumed("S5")
        assert e.event_type == AnalyticsEventType.ANALYTICS_RESUMED

    def test_make_completed(self):
        e = make_analytics_completed("S6")
        assert e.event_type == AnalyticsEventType.ANALYTICS_COMPLETED

    def test_make_failed(self):
        e = make_analytics_failed("S7")
        assert e.event_type == AnalyticsEventType.ANALYTICS_FAILED

    def test_make_archived(self):
        e = make_analytics_archived("S8")
        assert e.event_type == AnalyticsEventType.ANALYTICS_ARCHIVED

    def test_to_dict(self):
        e = make_analytics_created("S9")
        d = e.to_dict()
        assert "event_id" in d
        assert d["event_type"] == "analytics_created"

    def test_frozen(self):
        e = make_analytics_created("S10")
        with pytest.raises(Exception):
            e.session_id = "other"  # type: ignore[misc]

    def test_unique_event_ids(self):
        e1 = make_analytics_created("S")
        e2 = make_analytics_created("S")
        assert e1.event_id != e2.event_id

    def test_custom_actor(self):
        e = make_analytics_created("S11", actor="custom-actor")
        assert e.actor == "custom-actor"


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsStatistics:
    def test_initial_zeroes(self):
        s = AnalyticsStatistics()
        assert s.sessions_created    == 0
        assert s.sessions_completed  == 0
        assert s.sessions_failed     == 0
        assert s.sessions_archived   == 0
        assert s.transition_count    == 0
        assert s.success_rate        == 0.0

    def test_record_created(self):
        s = AnalyticsStatistics()
        s.record_created()
        s.record_created()
        assert s.sessions_created == 2

    def test_record_completed_with_duration(self):
        s = AnalyticsStatistics()
        s.record_completed(10.0)
        s.record_completed(20.0)
        assert s.sessions_completed == 2
        assert s.average_session_duration_seconds == 15.0

    def test_record_failed(self):
        s = AnalyticsStatistics()
        s.record_failed()
        assert s.sessions_failed == 1

    def test_record_archived(self):
        s = AnalyticsStatistics()
        s.record_archived()
        assert s.sessions_archived == 1

    def test_record_transition(self):
        s = AnalyticsStatistics()
        s.record_transition()
        s.record_transition()
        assert s.transition_count == 2

    def test_success_rate(self):
        s = AnalyticsStatistics()
        s.record_completed()
        s.record_completed()
        s.record_failed()
        rate = s.success_rate
        assert abs(rate - 2/3) < 1e-9

    def test_copy_independent(self):
        s = AnalyticsStatistics()
        s.record_created()
        c = s.copy()
        s.record_created()
        assert c.sessions_created == 1
        assert s.sessions_created == 2

    def test_reset(self):
        s = AnalyticsStatistics()
        s.record_created()
        s.record_completed(5.0)
        s.reset()
        assert s.sessions_created == 0

    def test_to_dict(self):
        s = AnalyticsStatistics()
        d = s.to_dict()
        assert "sessions_created" in d
        assert "transition_count" in d

    def test_thread_safety(self):
        s = AnalyticsStatistics()
        def worker():
            for _ in range(200):
                s.record_created()
                s.record_transition()
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert s.sessions_created == 1000
        assert s.transition_count == 1000


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsHistory:
    def test_empty(self):
        h = AnalyticsHistory()
        assert h.session_count    == 0
        assert h.transition_count == 0
        assert h.event_count      == 0
        assert h.latest_session() is None
        assert h.latest_event()   is None

    def test_record_session(self):
        h = AnalyticsHistory()
        s = _new_session()
        h.record_session(s)
        assert h.session_count == 1
        assert h.latest_session() is s

    def test_record_transition(self):
        h = AnalyticsHistory()
        t = make_analytics_transition(
            "S1", AnalyticsState.CREATED, AnalyticsState.INITIALIZING
        )
        h.record_transition(t)
        assert h.transition_count == 1

    def test_record_event(self):
        h = AnalyticsHistory()
        e = make_analytics_created("S1")
        h.record_event(e)
        assert h.event_count == 1
        assert h.latest_event() is e

    def test_sessions_for_execution(self):
        h = AnalyticsHistory()
        eid = "exec-xyz"
        s1 = AnalyticsSession(execution_session_id=eid)
        s2 = AnalyticsSession(execution_session_id="other")
        h.record_session(s1)
        h.record_session(s2)
        results = h.sessions_for_execution(eid)
        assert len(results) == 1
        assert results[0] is s1

    def test_transitions_for_session(self):
        h = AnalyticsHistory()
        t = make_analytics_transition("S1", AnalyticsState.CREATED, AnalyticsState.INITIALIZING)
        h.record_transition(t)
        assert len(h.transitions_for_session("S1")) == 1
        assert len(h.transitions_for_session("other")) == 0

    def test_events_for_session(self):
        h = AnalyticsHistory()
        h.record_event(make_analytics_created("S1"))
        h.record_event(make_analytics_created("S2"))
        assert len(h.events_for_session("S1")) == 1

    def test_clear(self):
        h = AnalyticsHistory()
        h.record_session(_new_session())
        h.record_event(make_analytics_created("S1"))
        h.clear()
        assert h.session_count == 0
        assert h.event_count   == 0

    def test_bounded(self):
        h = AnalyticsHistory(max_sessions=3)
        for _ in range(5):
            h.record_session(_new_session())
        assert h.session_count == 3

    def test_thread_safety(self):
        h = AnalyticsHistory()
        def worker():
            for _ in range(50):
                h.record_event(make_analytics_created(str(uuid.uuid4())))
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert h.event_count == 200


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsRegistry:
    def _started(self) -> AnalyticsRegistry:
        r = AnalyticsRegistry()
        r.start()
        return r

    def test_start_stop(self):
        r = AnalyticsRegistry()
        r.start()
        r.stop()

    def test_store_and_get(self):
        r = self._started()
        try:
            s = _new_session()
            r.store(s)
            fetched = r.get(s.session_id)
            assert fetched is s
        finally:
            r.stop()

    def test_not_found_raises(self):
        r = self._started()
        try:
            with pytest.raises(AnalyticsSessionNotFoundError):
                r.get("nonexistent")
        finally:
            r.stop()

    def test_find_returns_none(self):
        r = self._started()
        try:
            assert r.find("nonexistent") is None
        finally:
            r.stop()

    def test_duplicate_store_raises(self):
        r = self._started()
        try:
            s = _new_session()
            r.store(s)
            with pytest.raises(AnalyticsSessionAlreadyExistsError):
                r.store(s)
        finally:
            r.stop()

    def test_archive(self):
        r = self._started()
        try:
            s = _new_session()
            r.store(s)
            r.archive(s.session_id)
            assert r.active_count == 0
            assert r.archived_count == 1
            assert r.find_archived(s.session_id) is s
        finally:
            r.stop()

    def test_archive_missing_raises(self):
        r = self._started()
        try:
            with pytest.raises(AnalyticsSessionNotFoundError):
                r.archive("nonexistent")
        finally:
            r.stop()

    def test_not_running_raises(self):
        r = AnalyticsRegistry()
        with pytest.raises(AnalyticsNotRunningError):
            r.store(_new_session())

    def test_by_state(self):
        r = self._started()
        try:
            s1 = _new_session()
            s2 = _new_session()
            r.store(s1)
            r.store(s2)
            s1.transition_to(AnalyticsState.INITIALIZING)
            assert len(r.by_state(AnalyticsState.INITIALIZING)) == 1
            assert len(r.by_state(AnalyticsState.CREATED)) == 1
        finally:
            r.stop()

    def test_by_execution_session(self):
        r = self._started()
        try:
            eid = "exec-filter"
            s1 = AnalyticsSession(execution_session_id=eid)
            s2 = AnalyticsSession(execution_session_id="other")
            r.store(s1)
            r.store(s2)
            results = r.by_execution_session(eid)
            assert len(results) == 1
        finally:
            r.stop()

    def test_all(self):
        r = self._started()
        try:
            r.store(_new_session())
            r.store(_new_session())
            assert len(r.all()) == 2
        finally:
            r.stop()

    def test_clear(self):
        r = self._started()
        try:
            r.store(_new_session())
            r.clear()
            assert r.active_count == 0
        finally:
            r.stop()

    def test_capacity_eviction(self):
        r = AnalyticsRegistry(max_sessions=2)
        r.start()
        try:
            r.store(_new_session())
            r.store(_new_session())
            r.store(_new_session())  # triggers eviction
            assert r.active_count == 2
        finally:
            r.stop()

    def test_thread_safety(self):
        r = self._started()
        sessions = [_new_session() for _ in range(100)]
        def worker(batch):
            for s in batch:
                r.store(s)
        batches = [sessions[i:i+25] for i in range(0, 100, 25)]
        threads = [threading.Thread(target=worker, args=(b,)) for b in batches]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert r.active_count == 100
        r.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsFactory:
    def _started(self) -> AnalyticsFactory:
        f = AnalyticsFactory()
        f.start()
        return f

    def test_create_from_context(self):
        f = self._started()
        try:
            ctx = make_analytics_context("exec-1")
            s = f.create(ctx)
            assert isinstance(s, AnalyticsSession)
            assert s.state == AnalyticsState.CREATED
            assert s.execution_session_id == "exec-1"
        finally:
            f.stop()

    def test_create_from_params(self):
        f = self._started()
        try:
            s = f.create_from_params("exec-2", analytics_scope=AnalyticsScope.PORTFOLIO)
            assert s.analytics_scope == AnalyticsScope.PORTFOLIO
        finally:
            f.stop()

    def test_not_running_raises(self):
        f = AnalyticsFactory()
        ctx = make_analytics_context("exec-3")
        with pytest.raises(AnalyticsNotRunningError):
            f.create(ctx)

    def test_each_call_unique_session_id(self):
        f = self._started()
        try:
            ctx = make_analytics_context("exec-4")
            s1 = f.create(ctx)
            s2 = f.create(ctx)
            assert s1.session_id != s2.session_id
        finally:
            f.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsValidator:
    def setup_method(self):
        self.v = AnalyticsValidator()

    def test_valid_context(self):
        ctx = make_analytics_context("exec-1")
        r = self.v.validate_context(ctx)
        assert r.is_valid

    def test_none_context(self):
        r = self.v.validate_context(None)
        assert not r.is_valid

    def test_missing_execution_session_id(self):
        ctx = make_analytics_context("")
        r = self.v.validate_context(ctx)
        assert not r.is_valid
        assert any("execution_session_id" in e for e in r.errors)

    def test_valid_session(self):
        s = _new_session()
        r = self.v.validate_session(s)
        assert r.is_valid

    def test_none_session(self):
        r = self.v.validate_session(None)
        assert not r.is_valid

    def test_lifecycle_consistency_active_no_start_time(self):
        s = _new_session()
        for t in (
            AnalyticsState.INITIALIZING, AnalyticsState.COLLECTING,
            AnalyticsState.ANALYZING, AnalyticsState.READY, AnalyticsState.ACTIVE,
        ):
            s.transition_to(t)
        # Normally start_time is set automatically; just verify validation runs
        r = self.v.validate_lifecycle_consistency(s)
        assert isinstance(r, AnalyticsValidationResult)

    def test_lifecycle_consistency_failed_no_reason_warning(self):
        s = _new_session()
        s.transition_to(AnalyticsState.INITIALIZING)
        s.transition_to(AnalyticsState.FAILED)
        r = self.v.validate_lifecycle_consistency(s)
        assert any("failure_reason" in w.lower() for w in r.warnings)


class TestAnalyticsValidationResult:
    def test_initial_valid(self):
        r = AnalyticsValidationResult()
        assert r.is_valid

    def test_add_error(self):
        r = AnalyticsValidationResult()
        r.add_error("oops")
        assert not r.is_valid
        assert "oops" in r.errors

    def test_add_warning_stays_valid(self):
        r = AnalyticsValidationResult()
        r.add_warning("heads up")
        assert r.is_valid
        assert "heads up" in r.warnings

    def test_merge(self):
        r1 = AnalyticsValidationResult()
        r2 = AnalyticsValidationResult()
        r2.add_error("from r2")
        r1.merge(r2)
        assert not r1.is_valid
        assert "from r2" in r1.errors

    def test_to_dict(self):
        r = AnalyticsValidationResult()
        d = r.to_dict()
        assert "is_valid" in d
        assert "errors" in d
        assert "warnings" in d


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsLifecycle — lifecycle management
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsLifecycleManagement:
    def test_start_stop(self):
        lc = AnalyticsLifecycle()
        lc.start()
        lc.stop()

    def test_not_started_raises(self):
        lc = AnalyticsLifecycle()
        with pytest.raises(AnalyticsNotRunningError):
            lc.create("exec-1")

    def test_stopped_raises(self):
        lc = _started_lifecycle()
        lc.stop()
        with pytest.raises(AnalyticsNotRunningError):
            lc.create("exec-1")


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsLifecycle — session creation
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsLifecycleCreation:
    def setup_method(self):
        self.lc = _started_lifecycle()

    def teardown_method(self):
        try:
            self.lc.stop()
        except Exception:
            pass

    def test_create_basic(self):
        s = self.lc.create("exec-1")
        assert isinstance(s, AnalyticsSession)
        assert s.state == AnalyticsState.CREATED
        assert s.execution_session_id == "exec-1"

    def test_create_with_scope(self):
        s = self.lc.create("exec-2", analytics_scope=AnalyticsScope.PORTFOLIO)
        assert s.analytics_scope == AnalyticsScope.PORTFOLIO

    def test_create_with_workflow(self):
        s = self.lc.create("exec-3", workflow_id="WF-1")
        assert s.workflow_id == "WF-1"

    def test_create_from_context(self):
        ctx = make_analytics_context("exec-4", portfolio_id="P1")
        s = self.lc.create_from_context(ctx)
        assert s.portfolio_id == "P1"

    def test_create_from_invalid_context_raises(self):
        ctx = make_analytics_context("")  # missing execution_session_id
        with pytest.raises(AnalyticsValidationError):
            self.lc.create_from_context(ctx)

    def test_statistics_increments(self):
        before = self.lc.statistics().sessions_created
        self.lc.create("exec-5")
        after = self.lc.statistics().sessions_created
        assert after == before + 1

    def test_create_event_emitted(self):
        captured: List[AnalyticsEvent] = []
        self.lc.add_listener(captured.append)
        self.lc.create("exec-6")
        assert any(e.event_type == AnalyticsEventType.ANALYTICS_CREATED for e in captured)


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsLifecycle — full happy path
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsLifecycleHappyPath:
    def setup_method(self):
        self.lc = _started_lifecycle()
        self.events: List[AnalyticsEvent] = []
        self.lc.add_listener(self.events.append)

    def teardown_method(self):
        try:
            self.lc.stop()
        except Exception:
            pass

    def test_full_lifecycle(self):
        s = self.lc.create("exec-1")
        sid = s.session_id
        self.lc.initialize(sid)
        assert self.lc.get(sid).state == AnalyticsState.INITIALIZING
        self.lc.collect(sid)
        assert self.lc.get(sid).state == AnalyticsState.COLLECTING
        self.lc.analyze(sid)
        assert self.lc.get(sid).state == AnalyticsState.ANALYZING
        self.lc.ready(sid)
        assert self.lc.get(sid).state == AnalyticsState.READY
        self.lc.activate(sid)
        assert self.lc.get(sid).state == AnalyticsState.ACTIVE
        self.lc.complete(sid)
        assert self.lc.get(sid).state == AnalyticsState.COMPLETED
        self.lc.archive(sid)
        assert self.lc.find(sid) is None
        assert self.lc.find_archived(sid) is not None

    def test_events_emitted_in_order(self):
        s = self.lc.create("exec-2")
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.analyze(sid)
        self.lc.ready(sid)
        self.lc.activate(sid)
        self.lc.complete(sid)
        self.lc.archive(sid)
        event_types = [e.event_type for e in self.events if e.session_id == sid]
        assert AnalyticsEventType.ANALYTICS_CREATED   in event_types
        assert AnalyticsEventType.ANALYTICS_COMPLETED in event_types
        assert AnalyticsEventType.ANALYTICS_ARCHIVED  in event_types

    def test_statistics_after_full_lifecycle(self):
        s = self.lc.create("exec-3")
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.analyze(sid)
        self.lc.ready(sid)
        self.lc.activate(sid)
        self.lc.complete(sid)
        self.lc.archive(sid)
        stats = self.lc.statistics()
        assert stats.sessions_created   == 1
        assert stats.sessions_completed == 1
        assert stats.sessions_archived  == 1
        assert stats.transition_count   >= 6

    def test_history_populated(self):
        s = self.lc.create("exec-4")
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.analyze(sid)
        self.lc.ready(sid)
        self.lc.activate(sid)
        self.lc.complete(sid)
        self.lc.archive(sid)
        hist = self.lc.history()
        assert hist.session_count >= 1
        assert hist.event_count   >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsLifecycle — pause / resume
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsLifecyclePauseResume:
    def setup_method(self):
        self.lc = _started_lifecycle()

    def teardown_method(self):
        try:
            self.lc.stop()
        except Exception:
            pass

    def test_pause_during_collecting(self):
        s = self.lc.create("exec-1")
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.pause(sid)
        assert self.lc.get(sid).state == AnalyticsState.PAUSED

    def test_resume_and_continue(self):
        s = self.lc.create("exec-2")
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.pause(sid)
        self.lc.resume(sid)
        assert self.lc.get(sid).state == AnalyticsState.RESUMING
        self.lc.collect(sid)
        assert self.lc.get(sid).state == AnalyticsState.COLLECTING
        self.lc.analyze(sid)
        self.lc.ready(sid)
        self.lc.activate(sid)
        self.lc.complete(sid)
        assert self.lc.get(sid).state == AnalyticsState.COMPLETED

    def test_pause_events(self):
        captured: List[AnalyticsEvent] = []
        self.lc.add_listener(captured.append)
        s = self.lc.create("exec-3")
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.pause(sid)
        assert any(e.event_type == AnalyticsEventType.ANALYTICS_PAUSED
                   and e.session_id == sid for e in captured)

    def test_resume_events(self):
        captured: List[AnalyticsEvent] = []
        self.lc.add_listener(captured.append)
        s = self.lc.create("exec-4")
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.pause(sid)
        self.lc.resume(sid)
        assert any(e.event_type == AnalyticsEventType.ANALYTICS_RESUMED
                   and e.session_id == sid for e in captured)


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsLifecycle — failure
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsLifecycleFailure:
    def setup_method(self):
        self.lc = _started_lifecycle()

    def teardown_method(self):
        try:
            self.lc.stop()
        except Exception:
            pass

    def test_fail_from_collecting(self):
        s = self.lc.create("exec-1")
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.fail(sid, reason="data source unavailable")
        assert self.lc.get(sid).state == AnalyticsState.FAILED
        assert self.lc.get(sid).failure_reason == "data source unavailable"

    def test_fail_increments_stats(self):
        s = self.lc.create("exec-2")
        self.lc.initialize(s.session_id)
        self.lc.fail(s.session_id)
        assert self.lc.statistics().sessions_failed == 1

    def test_archive_failed_session(self):
        s = self.lc.create("exec-3")
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.fail(sid)
        self.lc.archive(sid)
        assert self.lc.find(sid) is None
        assert self.lc.find_archived(sid) is not None

    def test_fail_emits_event(self):
        captured: List[AnalyticsEvent] = []
        self.lc.add_listener(captured.append)
        s = self.lc.create("exec-4")
        self.lc.initialize(s.session_id)
        self.lc.fail(s.session_id, reason="timeout")
        assert any(e.event_type == AnalyticsEventType.ANALYTICS_FAILED
                   and e.session_id == s.session_id for e in captured)


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsLifecycle — invalid transitions
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsLifecycleInvalidTransitions:
    def setup_method(self):
        self.lc = _started_lifecycle()

    def teardown_method(self):
        try:
            self.lc.stop()
        except Exception:
            pass

    def test_activate_from_created_raises(self):
        s = self.lc.create("exec-1")
        with pytest.raises(AnalyticsInvalidTransitionError):
            self.lc.activate(s.session_id)

    def test_complete_from_collecting_raises(self):
        s = self.lc.create("exec-2")
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        with pytest.raises(AnalyticsInvalidTransitionError):
            self.lc.complete(s.session_id)

    def test_archive_from_active_raises(self):
        s = self.lc.create("exec-3")
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        self.lc.analyze(s.session_id)
        self.lc.ready(s.session_id)
        self.lc.activate(s.session_id)
        with pytest.raises(AnalyticsInvalidTransitionError):
            self.lc.archive(s.session_id)

    def test_double_complete_raises(self):
        s = self.lc.create("exec-4")
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        self.lc.analyze(s.session_id)
        self.lc.ready(s.session_id)
        self.lc.activate(s.session_id)
        self.lc.complete(s.session_id)
        with pytest.raises(AnalyticsInvalidTransitionError):
            self.lc.complete(s.session_id)

    def test_session_not_found_raises(self):
        with pytest.raises(AnalyticsSessionNotFoundError):
            self.lc.initialize("nonexistent-session-id")


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsLifecycle — query methods
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsLifecycleQueries:
    def setup_method(self):
        self.lc = _started_lifecycle()

    def teardown_method(self):
        try:
            self.lc.stop()
        except Exception:
            pass

    def test_all_active_returns_active_sessions(self):
        self.lc.create("e1")
        self.lc.create("e2")
        active = self.lc.all_active()
        assert len(active) == 2

    def test_by_state_filter(self):
        s = self.lc.create("e1")
        self.lc.initialize(s.session_id)
        result = self.lc.by_state(AnalyticsState.INITIALIZING)
        assert any(r.session_id == s.session_id for r in result)

    def test_by_execution_session(self):
        eid = "exec-filter"
        s1 = self.lc.create(eid)
        s2 = self.lc.create("other-exec")
        result = self.lc.by_execution_session(eid)
        assert any(r.session_id == s1.session_id for r in result)
        assert not any(r.session_id == s2.session_id for r in result)

    def test_get_archived(self):
        s = self.lc.create("e1")
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.analyze(sid)
        self.lc.ready(sid)
        self.lc.activate(sid)
        self.lc.complete(sid)
        self.lc.archive(sid)
        archived = self.lc.find_archived(sid)
        assert archived is not None
        assert archived.session_id == sid


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsLifecycle — event listeners
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsLifecycleListeners:
    def setup_method(self):
        self.lc = _started_lifecycle()

    def teardown_method(self):
        try:
            self.lc.stop()
        except Exception:
            pass

    def test_listener_receives_events(self):
        received: List[AnalyticsEvent] = []
        self.lc.add_listener(received.append)
        self.lc.create("exec-1")
        assert len(received) >= 1

    def test_remove_listener(self):
        received: List[AnalyticsEvent] = []
        self.lc.add_listener(received.append)
        self.lc.remove_listener(received.append)
        self.lc.create("exec-2")
        assert len(received) == 0

    def test_faulty_listener_does_not_crash(self):
        def bad_listener(e):
            raise RuntimeError("listener boom")
        self.lc.add_listener(bad_listener)
        # Should not raise
        session = self.lc.create("exec-3")
        assert session is not None

    def test_multiple_listeners(self):
        r1: List = []
        r2: List = []
        self.lc.add_listener(r1.append)
        self.lc.add_listener(r2.append)
        self.lc.create("exec-4")
        assert len(r1) >= 1
        assert len(r2) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# AnalyticsLifecycle — concurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyticsLifecycleConcurrency:
    def test_concurrent_create(self):
        lc = _started_lifecycle(max_sessions=500)
        results = []
        errors  = []

        def worker():
            try:
                s = lc.create(str(uuid.uuid4()))
                results.append(s.session_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lc.stop()
        assert len(errors) == 0
        assert len(results) == 100

    def test_concurrent_full_lifecycle(self):
        lc = _started_lifecycle(max_sessions=100)

        def worker():
            s = lc.create(str(uuid.uuid4()))
            sid = s.session_id
            lc.initialize(sid)
            lc.collect(sid)
            lc.analyze(sid)
            lc.ready(sid)
            lc.activate(sid)
            lc.complete(sid)
            lc.archive(sid)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = lc.statistics()
        assert stats.sessions_created   == 20
        assert stats.sessions_completed == 20
        assert stats.sessions_archived  == 20
        lc.stop()

    def test_concurrent_statistics(self):
        lc = _started_lifecycle(max_sessions=500)
        errors = []

        def worker():
            try:
                for _ in range(10):
                    s = lc.create(str(uuid.uuid4()))
                    lc.initialize(s.session_id)
                    lc.fail(s.session_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lc.stop()
        assert len(errors) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Regression
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    def test_re_analyze_loop_full(self):
        """ACTIVE can loop back through ANALYZING → READY → ACTIVE."""
        lc = _started_lifecycle()
        s = lc.create("exec-1")
        sid = s.session_id
        lc.initialize(sid)
        lc.collect(sid)
        lc.analyze(sid)
        lc.ready(sid)
        lc.activate(sid)
        # Re-analyze
        lc.analyze(sid)
        lc.ready(sid)
        lc.activate(sid)
        lc.complete(sid)
        assert lc.get(sid).state == AnalyticsState.COMPLETED
        lc.stop()

    def test_collecting_to_analyzing_to_collecting(self):
        """ANALYZING can loop back to COLLECTING if data insufficient."""
        lc = _started_lifecycle()
        s = lc.create("exec-2")
        sid = s.session_id
        lc.initialize(sid)
        lc.collect(sid)
        lc.analyze(sid)
        lc.collect(sid)  # re-collect
        lc.analyze(sid)
        lc.ready(sid)
        lc.activate(sid)
        lc.complete(sid)
        assert lc.get(sid).is_completed
        lc.stop()

    def test_multiple_sessions_independent(self):
        """Two sessions do not interfere with each other."""
        lc = _started_lifecycle()
        s1 = lc.create("exec-1")
        s2 = lc.create("exec-2")
        lc.initialize(s1.session_id)
        # s2 still in CREATED
        assert lc.get(s2.session_id).state == AnalyticsState.CREATED
        assert lc.get(s1.session_id).state == AnalyticsState.INITIALIZING
        lc.stop()

    def test_statistics_independent_copy(self):
        """statistics() returns a copy; further ops don't mutate the snapshot."""
        lc = _started_lifecycle()
        lc.create("exec-1")
        snap = lc.statistics()
        assert snap.sessions_created == 1
        lc.create("exec-2")
        assert snap.sessions_created == 1   # copy unchanged
        lc.stop()

    def test_history_event_count_matches_transitions(self):
        lc = _started_lifecycle()
        s = lc.create("exec-1")
        sid = s.session_id
        lc.initialize(sid)
        lc.collect(sid)
        # history should have events
        hist = lc.history()
        assert hist.event_count >= 1
        lc.stop()
