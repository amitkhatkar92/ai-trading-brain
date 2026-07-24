"""
tests/unit/integration/test_integration_lifecycle_m1.py
--------------------------------------------------------
C15 M1 — Integration Lifecycle test suite.

Tests all 14 source files in iios/integration/lifecycle/.
"""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

import pytest

# ════════════════════════════════════════════════════════════════════════
# 1. Constants
# ════════════════════════════════════════════════════════════════════════


class TestConstants:
    def test_state_count(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        assert len(IntegrationLifecycleState) == 13

    def test_event_type_count(self):
        from iios.integration.lifecycle import IntegrationEventType
        assert len(IntegrationEventType) == 11

    def test_integration_type_count(self):
        from iios.integration.lifecycle import IntegrationType
        assert len(IntegrationType) == 8

    def test_integration_scope_count(self):
        from iios.integration.lifecycle import IntegrationScope
        assert len(IntegrationScope) == 5

    def test_validation_code_count(self):
        from iios.integration.lifecycle import IntegrationValidationCode
        assert len(IntegrationValidationCode) == 5

    def test_valid_transitions_covers_all_states(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            VALID_TRANSITIONS,
        )
        for state in IntegrationLifecycleState:
            assert state in VALID_TRANSITIONS, f"{state!r} missing from VALID_TRANSITIONS"

    def test_archived_has_no_outgoing_transitions(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            VALID_TRANSITIONS,
        )
        assert VALID_TRANSITIONS[IntegrationLifecycleState.ARCHIVED] == set()

    def test_failed_allows_retry(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            VALID_TRANSITIONS,
        )
        assert (
            IntegrationLifecycleState.INITIALIZING
            in VALID_TRANSITIONS[IntegrationLifecycleState.FAILED]
        )

    def test_active_states_set(self):
        from iios.integration.lifecycle import ACTIVE_STATES, IntegrationLifecycleState
        assert IntegrationLifecycleState.ACTIVE in ACTIVE_STATES
        assert IntegrationLifecycleState.ARCHIVED not in ACTIVE_STATES

    def test_immutable_states_only_archived(self):
        from iios.integration.lifecycle import IMMUTABLE_STATES, IntegrationLifecycleState
        assert IMMUTABLE_STATES == {IntegrationLifecycleState.ARCHIVED}

    def test_default_constants(self):
        from iios.integration.lifecycle import (
            DEFAULT_MAX_SESSIONS,
            DEFAULT_MAX_HISTORY,
            DEFAULT_MAX_TRANSITIONS,
        )
        assert DEFAULT_MAX_SESSIONS    == 10_000
        assert DEFAULT_MAX_HISTORY     == 5_000
        assert DEFAULT_MAX_TRANSITIONS == 100_000

    def test_actors(self):
        from iios.integration.lifecycle import (
            ACTOR_LIFECYCLE,
            ACTOR_OPERATOR,
            ACTOR_SYSTEM,
        )
        assert "lifecycle" in ACTOR_LIFECYCLE
        assert "operator"  in ACTOR_OPERATOR
        assert "system"    in ACTOR_SYSTEM


# ════════════════════════════════════════════════════════════════════════
# 2. Exceptions
# ════════════════════════════════════════════════════════════════════════


class TestExceptions:
    def test_base_exception_ilc_000(self):
        from iios.integration.lifecycle import IntegrationLifecycleError
        exc = IntegrationLifecycleError("test error")
        assert "ILC-000" in str(exc.error_code)

    def test_session_not_found_ilc_001(self):
        from iios.integration.lifecycle import IntegrationSessionNotFoundError
        exc = IntegrationSessionNotFoundError("abc-123")
        assert exc.session_id == "abc-123"
        assert "ILC-001" in exc.error_code

    def test_invalid_transition_ilc_002(self):
        from iios.integration.lifecycle import IntegrationInvalidTransitionError
        exc = IntegrationInvalidTransitionError("created", "archived")
        assert exc.from_state == "created"
        assert exc.to_state   == "archived"
        assert "ILC-002" in exc.error_code

    def test_session_terminated_ilc_003(self):
        from iios.integration.lifecycle import IntegrationSessionTerminatedError
        exc = IntegrationSessionTerminatedError("s-001")
        assert exc.session_id == "s-001"
        assert "ILC-003" in exc.error_code

    def test_validation_error_ilc_004(self):
        from iios.integration.lifecycle import IntegrationValidationError
        exc = IntegrationValidationError("bad", failed_checks=["identifier_consistency"])
        assert "identifier_consistency" in exc.failed_checks

    def test_capacity_error_ilc_005(self):
        from iios.integration.lifecycle import IntegrationCapacityError
        exc = IntegrationCapacityError(limit=100)
        assert exc.limit == 100

    def test_history_error_ilc_006(self):
        from iios.integration.lifecycle import IntegrationHistoryError
        exc = IntegrationHistoryError("history broken")
        assert "ILC-006" in exc.error_code

    def test_hierarchy(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycleError,
            IntegrationSessionNotFoundError,
        )
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(IntegrationSessionNotFoundError, IntegrationLifecycleError)
        assert issubclass(IntegrationLifecycleError, IIOSError)


# ════════════════════════════════════════════════════════════════════════
# 3. IntegrationContext
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationContext:
    def test_create(self):
        from iios.integration.lifecycle import IntegrationContext
        ctx = IntegrationContext.create("s-001")
        assert ctx.session_id == "s-001"
        assert ctx.context_id.startswith("ictx-")
        assert ctx.correlation_id
        assert ctx.trace_id

    def test_frozen(self):
        from iios.integration.lifecycle import IntegrationContext
        ctx = IntegrationContext.create("s-001")
        with pytest.raises((AttributeError, TypeError)):
            ctx.session_id = "other"  # type: ignore

    def test_to_dict(self):
        from iios.integration.lifecycle import IntegrationContext
        ctx = IntegrationContext.create("s-001")
        d   = ctx.to_dict()
        assert d["session_id"] == "s-001"
        assert "context_id" in d

    def test_from_dict_round_trip(self):
        from iios.integration.lifecycle import IntegrationContext
        ctx  = IntegrationContext.create("s-001", environment="staging")
        ctx2 = IntegrationContext.from_dict(ctx.to_dict())
        assert ctx2.session_id   == ctx.session_id
        assert ctx2.environment  == "staging"


# ════════════════════════════════════════════════════════════════════════
# 4. IntegrationMetadata
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationMetadata:
    def test_default(self):
        from iios.integration.lifecycle import IntegrationMetadata, IntegrationType
        meta = IntegrationMetadata.default()
        assert meta.integration_type == IntegrationType.INTERNAL

    def test_create(self):
        from iios.integration.lifecycle import (
            IntegrationMetadata,
            IntegrationType,
            IntegrationScope,
        )
        meta = IntegrationMetadata.create(
            IntegrationType.REST_API,
            IntegrationScope.EXTERNAL,
            provider="acme",
            protocol="https",
        )
        assert meta.provider  == "acme"
        assert meta.protocol  == "https"
        assert meta.integration_type  == IntegrationType.REST_API
        assert meta.integration_scope == IntegrationScope.EXTERNAL

    def test_frozen(self):
        from iios.integration.lifecycle import IntegrationMetadata
        meta = IntegrationMetadata.default()
        with pytest.raises((AttributeError, TypeError)):
            meta.provider = "other"  # type: ignore

    def test_to_dict_from_dict(self):
        from iios.integration.lifecycle import IntegrationMetadata, IntegrationType
        meta  = IntegrationMetadata.create(IntegrationType.WEBSOCKET, provider="ws-svc")
        meta2 = IntegrationMetadata.from_dict(meta.to_dict())
        assert meta2.integration_type == IntegrationType.WEBSOCKET
        assert meta2.provider         == "ws-svc"

    def test_tags_are_tuple(self):
        from iios.integration.lifecycle import IntegrationMetadata
        meta = IntegrationMetadata.create(tags=["a", "b"])
        assert isinstance(meta.tags, tuple)
        assert "a" in meta.tags


# ════════════════════════════════════════════════════════════════════════
# 5. IntegrationStateRecord
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationStateRecord:
    def test_create(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        from iios.integration.lifecycle.integration_state import IntegrationStateRecord
        rec = IntegrationStateRecord.create("s-001", IntegrationLifecycleState.ACTIVE)
        assert rec.session_id   == "s-001"
        assert rec.state        == IntegrationLifecycleState.ACTIVE
        assert rec.record_id.startswith("sr-")

    def test_frozen(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        from iios.integration.lifecycle.integration_state import IntegrationStateRecord
        rec = IntegrationStateRecord.create("s-001", IntegrationLifecycleState.ACTIVE)
        with pytest.raises((AttributeError, TypeError)):
            rec.session_id = "x"  # type: ignore

    def test_to_dict_from_dict(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        from iios.integration.lifecycle.integration_state import IntegrationStateRecord
        rec  = IntegrationStateRecord.create("s-001", IntegrationLifecycleState.READY)
        rec2 = IntegrationStateRecord.from_dict(rec.to_dict())
        assert rec2.state == IntegrationLifecycleState.READY


# ════════════════════════════════════════════════════════════════════════
# 6. IntegrationTransition
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationTransition:
    def test_create(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            IntegrationTransition,
        )
        tr = IntegrationTransition.create(
            "s-001",
            IntegrationLifecycleState.CREATED,
            IntegrationLifecycleState.INITIALIZING,
        )
        assert tr.session_id   == "s-001"
        assert tr.from_state   == IntegrationLifecycleState.CREATED
        assert tr.to_state     == IntegrationLifecycleState.INITIALIZING
        assert tr.transition_id.startswith("tr-")

    def test_frozen(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            IntegrationTransition,
        )
        tr = IntegrationTransition.create(
            "s-001",
            IntegrationLifecycleState.CREATED,
            IntegrationLifecycleState.INITIALIZING,
        )
        with pytest.raises((AttributeError, TypeError)):
            tr.session_id = "other"  # type: ignore

    def test_to_dict_from_dict(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            IntegrationTransition,
        )
        tr  = IntegrationTransition.create(
            "s-001",
            IntegrationLifecycleState.CREATED,
            IntegrationLifecycleState.INITIALIZING,
            reason="unit test",
        )
        tr2 = IntegrationTransition.from_dict(tr.to_dict())
        assert tr2.reason    == "unit test"
        assert tr2.to_state  == IntegrationLifecycleState.INITIALIZING


# ════════════════════════════════════════════════════════════════════════
# 7. IntegrationSession
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationSession:
    def _make(self, workflow_id: str = "wf-test") -> object:
        from iios.integration.lifecycle import (
            IntegrationContext,
            IntegrationMetadata,
            IntegrationSession,
        )
        sid  = "s-test-001"
        ctx  = IntegrationContext.create(sid)
        meta = IntegrationMetadata.default()
        return IntegrationSession(sid, workflow_id, ctx, meta)

    def test_initial_state_is_created(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        s = self._make()
        assert s.state == IntegrationLifecycleState.CREATED

    def test_can_transition_to_valid(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        s = self._make()
        assert s.can_transition_to(IntegrationLifecycleState.INITIALIZING)

    def test_can_transition_to_invalid(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        s = self._make()
        assert not s.can_transition_to(IntegrationLifecycleState.ACTIVE)

    def test_transition_to(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        s  = self._make()
        tr = s.transition_to(IntegrationLifecycleState.INITIALIZING)
        assert s.state    == IntegrationLifecycleState.INITIALIZING
        assert tr.to_state == IntegrationLifecycleState.INITIALIZING

    def test_invalid_transition_raises(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            IntegrationInvalidTransitionError,
        )
        s = self._make()
        with pytest.raises(IntegrationInvalidTransitionError):
            s.transition_to(IntegrationLifecycleState.ACTIVE)

    def test_is_active(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        s = self._make()
        s.transition_to(IntegrationLifecycleState.INITIALIZING)
        assert s.is_active

    def test_is_terminal_archived(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            IntegrationSessionTerminatedError,
        )
        s = self._make()
        # Walk to ARCHIVED through a valid path: CREATED→INIT→DISC→CONF→VALID→READY→ARCHIVED
        s.transition_to(IntegrationLifecycleState.INITIALIZING)
        s.transition_to(IntegrationLifecycleState.DISCOVERING)
        s.transition_to(IntegrationLifecycleState.CONFIGURING)
        s.transition_to(IntegrationLifecycleState.VALIDATING)
        s.transition_to(IntegrationLifecycleState.READY)
        s.transition_to(IntegrationLifecycleState.ARCHIVED)
        assert s.is_terminal
        with pytest.raises(IntegrationSessionTerminatedError):
            s.transition_to(IntegrationLifecycleState.ACTIVE)

    def test_to_dict(self):
        s = self._make()
        d = s.to_dict()
        assert d["session_id"]  == "s-test-001"
        assert d["workflow_id"] == "wf-test"

    def test_transition_count_increments(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        s = self._make()
        s.transition_to(IntegrationLifecycleState.INITIALIZING)
        assert s.transition_count() == 1

    def test_state_records_initial_plus_one_per_transition(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        s = self._make()
        # Initial CREATED record + one after transition
        s.transition_to(IntegrationLifecycleState.INITIALIZING)
        assert len(s.state_records()) == 2


# ════════════════════════════════════════════════════════════════════════
# 8. Valid Transitions (parametrized)
# ════════════════════════════════════════════════════════════════════════


class TestValidTransitions:
    VALID_PAIRS = [
        ("created",      "initializing"),
        ("initializing", "discovering"),
        ("discovering",  "configuring"),
        ("configuring",  "validating"),
        ("validating",   "ready"),
        ("ready",        "connecting"),
        ("connecting",   "active"),
        ("active",       "paused"),
        ("active",       "completed"),
        ("paused",       "resuming"),
        ("resuming",     "active"),
        ("completed",    "archived"),
        ("failed",       "archived"),
        ("failed",       "initializing"),
    ]

    INVALID_PAIRS = [
        ("created",   "active"),
        ("archived",  "created"),
        ("archived",  "initializing"),
        ("completed", "active"),
        ("active",    "created"),
    ]

    @pytest.mark.parametrize("from_s,to_s", VALID_PAIRS)
    def test_valid(self, from_s: str, to_s: str):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            VALID_TRANSITIONS,
        )
        f = IntegrationLifecycleState(from_s)
        t = IntegrationLifecycleState(to_s)
        assert t in VALID_TRANSITIONS[f]

    @pytest.mark.parametrize("from_s,to_s", INVALID_PAIRS)
    def test_invalid(self, from_s: str, to_s: str):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            VALID_TRANSITIONS,
        )
        f = IntegrationLifecycleState(from_s)
        t = IntegrationLifecycleState(to_s)
        assert t not in VALID_TRANSITIONS[f]


# ════════════════════════════════════════════════════════════════════════
# 9. IntegrationLifecycle — full happy path
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationLifecycle:
    def _lc(self):
        from iios.integration.lifecycle import IntegrationLifecycle
        return IntegrationLifecycle()

    def test_create_session(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        lc      = self._lc()
        session = lc.create_session("wf-001")
        assert session.state == IntegrationLifecycleState.CREATED
        assert lc.get_session(session.session_id) is session

    def test_full_happy_path(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        lc  = self._lc()
        s   = lc.create_session("wf-happy")
        sid = s.session_id

        lc.initialize(sid)
        lc.discover(sid)
        lc.configure(sid)
        lc.validate_session(sid)
        lc.mark_ready(sid)
        lc.connect(sid)
        lc.activate(sid)
        lc.complete(sid)
        lc.archive(sid)

        assert lc.get_session(sid).state == IntegrationLifecycleState.ARCHIVED

    def test_stats_increment(self):
        lc  = self._lc()
        s   = lc.create_session("wf-stats")
        sid = s.session_id

        lc.initialize(sid)
        lc.discover(sid)
        lc.configure(sid)
        lc.validate_session(sid)
        lc.mark_ready(sid)
        lc.connect(sid)
        lc.activate(sid)
        lc.complete(sid)
        lc.archive(sid)

        report = lc.stats.report()
        assert report.integration_sessions_created   >= 1
        assert report.integration_sessions_completed >= 1
        assert report.integration_sessions_archived  >= 1
        assert report.transition_count               >= 8

    def test_health(self):
        lc = self._lc()
        h  = lc.health()
        assert h["status"] == "healthy"
        assert "active_sessions" in h

    def test_session_not_found_raises(self):
        from iios.integration.lifecycle import IntegrationSessionNotFoundError
        lc = self._lc()
        with pytest.raises(IntegrationSessionNotFoundError):
            lc.initialize("nonexistent-session-id")


# ════════════════════════════════════════════════════════════════════════
# 10. Pause / Resume
# ════════════════════════════════════════════════════════════════════════


class TestLifecyclePauseResume:
    def _active_session(self):
        from iios.integration.lifecycle import IntegrationLifecycle
        lc  = IntegrationLifecycle()
        s   = lc.create_session("wf-pause")
        sid = s.session_id
        lc.initialize(sid)
        lc.discover(sid)
        lc.configure(sid)
        lc.validate_session(sid)
        lc.mark_ready(sid)
        lc.connect(sid)
        lc.activate(sid)
        return lc, sid

    def test_pause_resume_cycle(self):
        from iios.integration.lifecycle import IntegrationLifecycleState
        lc, sid = self._active_session()
        lc.pause(sid)
        assert lc.get_session(sid).state == IntegrationLifecycleState.PAUSED
        lc.resume(sid)
        assert lc.get_session(sid).state == IntegrationLifecycleState.RESUMING
        lc.mark_resumed(sid)
        assert lc.get_session(sid).state == IntegrationLifecycleState.ACTIVE


# ════════════════════════════════════════════════════════════════════════
# 11. Fail and Retry
# ════════════════════════════════════════════════════════════════════════


class TestLifecycleFail:
    def test_fail_from_active(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycle,
            IntegrationLifecycleState,
        )
        lc  = IntegrationLifecycle()
        s   = lc.create_session("wf-fail")
        sid = s.session_id
        lc.initialize(sid)
        lc.discover(sid)
        lc.configure(sid)
        lc.validate_session(sid)
        lc.mark_ready(sid)
        lc.connect(sid)
        lc.activate(sid)
        lc.fail(sid, reason="simulated error")
        assert lc.get_session(sid).state == IntegrationLifecycleState.FAILED
        assert lc.stats.report().integration_sessions_failed >= 1

    def test_fail_then_archive(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycle,
            IntegrationLifecycleState,
        )
        lc  = IntegrationLifecycle()
        s   = lc.create_session("wf-fail-arch")
        sid = s.session_id
        lc.initialize(sid)
        lc.fail(sid)
        lc.archive(sid)
        assert lc.get_session(sid).state == IntegrationLifecycleState.ARCHIVED

    def test_fail_then_retry(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycle,
            IntegrationLifecycleState,
        )
        lc  = IntegrationLifecycle()
        s   = lc.create_session("wf-retry")
        sid = s.session_id
        lc.initialize(sid)
        lc.fail(sid)
        lc.retry(sid)
        assert lc.get_session(sid).state == IntegrationLifecycleState.INITIALIZING


# ════════════════════════════════════════════════════════════════════════
# 12. IntegrationHistory
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationHistory:
    def test_record_and_retrieve(self):
        from iios.integration.lifecycle import (
            IntegrationHistory,
            IntegrationLifecycleState,
            IntegrationTransition,
        )
        h  = IntegrationHistory()
        tr = IntegrationTransition.create(
            "s-001",
            IntegrationLifecycleState.CREATED,
            IntegrationLifecycleState.INITIALIZING,
        )
        h.record_transition(tr)
        assert h.transition_count() == 1
        assert h.get_transition(tr.transition_id) is tr

    def test_by_session(self):
        from iios.integration.lifecycle import (
            IntegrationHistory,
            IntegrationLifecycleState,
            IntegrationTransition,
        )
        h  = IntegrationHistory()
        t1 = IntegrationTransition.create(
            "s-A", IntegrationLifecycleState.CREATED, IntegrationLifecycleState.INITIALIZING
        )
        t2 = IntegrationTransition.create(
            "s-B", IntegrationLifecycleState.CREATED, IntegrationLifecycleState.INITIALIZING
        )
        h.record_transition(t1)
        h.record_transition(t2)
        assert len(h.transitions_for_session("s-A")) == 1
        assert len(h.transitions_for_session("s-B")) == 1

    def test_bounded(self):
        from iios.integration.lifecycle import (
            IntegrationHistory,
            IntegrationLifecycleState,
            IntegrationTransition,
        )
        h = IntegrationHistory(max_transitions=3)
        for i in range(5):
            tr = IntegrationTransition.create(
                f"s-{i}",
                IntegrationLifecycleState.CREATED,
                IntegrationLifecycleState.INITIALIZING,
            )
            h.record_transition(tr)
        assert h.transition_count() == 3

    def test_recent(self):
        from iios.integration.lifecycle import (
            IntegrationHistory,
            IntegrationLifecycleState,
            IntegrationTransition,
        )
        h = IntegrationHistory()
        for i in range(30):
            tr = IntegrationTransition.create(
                f"s-{i}",
                IntegrationLifecycleState.CREATED,
                IntegrationLifecycleState.INITIALIZING,
            )
            h.record_transition(tr)
        assert len(h.recent_transitions(10)) == 10

    def test_clear(self):
        from iios.integration.lifecycle import (
            IntegrationHistory,
            IntegrationLifecycleState,
            IntegrationTransition,
        )
        h  = IntegrationHistory()
        tr = IntegrationTransition.create(
            "s-001",
            IntegrationLifecycleState.CREATED,
            IntegrationLifecycleState.INITIALIZING,
        )
        h.record_transition(tr)
        h.clear()
        assert h.transition_count() == 0


# ════════════════════════════════════════════════════════════════════════
# 13. IntegrationLifecycleStatistics
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationStatistics:
    def test_all_counters(self):
        from iios.integration.lifecycle import IntegrationLifecycleStatistics
        stats = IntegrationLifecycleStatistics()
        stats.record_created()
        stats.record_completed(duration_ms=100.0)
        stats.record_failed()
        stats.record_archived()
        stats.record_transition()
        stats.record_transition()

        r = stats.report()
        assert r.integration_sessions_created   == 1
        assert r.integration_sessions_completed == 1
        assert r.integration_sessions_failed    == 1
        assert r.integration_sessions_archived  == 1
        assert r.transition_count               == 2
        assert r.average_session_duration_ms    == 100.0

    def test_reset(self):
        from iios.integration.lifecycle import IntegrationLifecycleStatistics
        stats = IntegrationLifecycleStatistics()
        stats.record_created()
        stats.reset()
        r = stats.report()
        assert r.integration_sessions_created == 0

    def test_average_no_completed(self):
        from iios.integration.lifecycle import IntegrationLifecycleStatistics
        stats = IntegrationLifecycleStatistics()
        r = stats.report()
        assert r.average_session_duration_ms == 0.0

    def test_report_to_dict(self):
        from iios.integration.lifecycle import IntegrationLifecycleStatistics
        stats = IntegrationLifecycleStatistics()
        d = stats.report().to_dict()
        assert "integration_sessions_created" in d
        assert "captured_at" in d


# ════════════════════════════════════════════════════════════════════════
# 14. IntegrationRegistry
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationRegistry:
    def _session(self, sid: str = "s-reg-001", wf: str = "wf-x"):
        from iios.integration.lifecycle import (
            IntegrationContext,
            IntegrationMetadata,
            IntegrationSession,
        )
        ctx  = IntegrationContext.create(sid)
        meta = IntegrationMetadata.default()
        return IntegrationSession(sid, wf, ctx, meta)

    def test_register_and_get(self):
        from iios.integration.lifecycle import IntegrationRegistry
        reg = IntegrationRegistry()
        s   = self._session()
        reg.register(s)
        assert reg.get(s.session_id) is s

    def test_get_or_raise_not_found(self):
        from iios.integration.lifecycle import (
            IntegrationRegistry,
            IntegrationSessionNotFoundError,
        )
        reg = IntegrationRegistry()
        with pytest.raises(IntegrationSessionNotFoundError):
            reg.get_or_raise("nonexistent")

    def test_deregister(self):
        from iios.integration.lifecycle import IntegrationRegistry
        reg = IntegrationRegistry()
        s   = self._session()
        reg.register(s)
        assert reg.deregister(s.session_id)
        assert reg.get(s.session_id) is None

    def test_by_workflow(self):
        from iios.integration.lifecycle import IntegrationRegistry
        reg = IntegrationRegistry()
        s1  = self._session("s-1", "wf-alpha")
        s2  = self._session("s-2", "wf-alpha")
        s3  = self._session("s-3", "wf-beta")
        reg.register(s1)
        reg.register(s2)
        reg.register(s3)
        by_alpha = reg.by_workflow("wf-alpha")
        assert len(by_alpha) == 2

    def test_by_state(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            IntegrationRegistry,
        )
        reg = IntegrationRegistry()
        s   = self._session()
        s.transition_to(IntegrationLifecycleState.INITIALIZING)
        reg.register(s)
        by_init = reg.by_state(IntegrationLifecycleState.INITIALIZING)
        assert s in by_init

    def test_capacity_error(self):
        from iios.integration.lifecycle import (
            IntegrationCapacityError,
            IntegrationRegistry,
        )
        reg = IntegrationRegistry(max_sessions=2)
        reg.register(self._session("s-1"))
        reg.register(self._session("s-2"))
        with pytest.raises(IntegrationCapacityError):
            reg.register(self._session("s-3"))

    def test_count(self):
        from iios.integration.lifecycle import IntegrationRegistry
        reg = IntegrationRegistry()
        assert reg.count() == 0
        reg.register(self._session("s-001"))
        assert reg.count() == 1


# ════════════════════════════════════════════════════════════════════════
# 15. IntegrationFactory
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationFactory:
    def test_create(self):
        from iios.integration.lifecycle import (
            IntegrationFactory,
            IntegrationLifecycleState,
        )
        factory = IntegrationFactory()
        session = factory.create("wf-factory")
        assert session.workflow_id == "wf-factory"
        assert session.state       == IntegrationLifecycleState.CREATED

    def test_create_default(self):
        from iios.integration.lifecycle import (
            IntegrationFactory,
            IntegrationLifecycleState,
        )
        factory = IntegrationFactory()
        session = factory.create_default("wf-default")
        assert session.state == IntegrationLifecycleState.CREATED

    def test_custom_session_id(self):
        from iios.integration.lifecycle import IntegrationFactory
        factory = IntegrationFactory()
        session = factory.create("wf-x", session_id="custom-sid-001")
        assert session.session_id == "custom-sid-001"


# ════════════════════════════════════════════════════════════════════════
# 16. IntegrationValidation
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationValidation:
    def _valid_session(self):
        from iios.integration.lifecycle import (
            IntegrationContext,
            IntegrationMetadata,
            IntegrationSession,
        )
        sid  = "s-valid-001"
        ctx  = IntegrationContext.create(sid)
        meta = IntegrationMetadata.default()
        return IntegrationSession(sid, "wf-valid", ctx, meta)

    def test_all_checks_pass(self):
        from iios.integration.lifecycle import IntegrationValidator
        v   = IntegrationValidator()
        s   = self._valid_session()
        rpt = v.validate(s)
        assert rpt.passed
        assert rpt.failed_checks == []

    def test_identifier_consistency_fails(self):
        from iios.integration.lifecycle import (
            IntegrationContext,
            IntegrationMetadata,
            IntegrationSession,
            IntegrationValidator,
            IntegrationValidationCode,
        )
        ctx  = IntegrationContext.create("s-bad")
        meta = IntegrationMetadata.default()
        # Manually construct with empty session_id using __new__
        s = object.__new__(IntegrationSession)
        s._session_id    = ""          # empty — should fail check
        s._workflow_id   = "wf-x"
        s._state         = __import__(
            "iios.integration.lifecycle.constants",
            fromlist=["IntegrationLifecycleState"]
        ).IntegrationLifecycleState.CREATED
        s._context       = ctx
        s._metadata      = meta
        s._created_at    = "2024-01-01T00:00:00+00:00"
        s._updated_at    = "2024-01-01T00:00:00+00:00"
        s._transitions   = []
        s._state_records = [1]  # fake 1 record to satisfy count
        import threading
        s._lock = threading.Lock()

        v   = IntegrationValidator()
        rpt = v.validate(s)
        assert not rpt.passed
        assert IntegrationValidationCode.IDENTIFIER_CONSISTENCY.value in rpt.failed_checks

    def test_validate_transition(self):
        from iios.integration.lifecycle import (
            IntegrationLifecycleState,
            IntegrationValidator,
        )
        v = IntegrationValidator()
        s = self._valid_session()
        assert v.validate_transition(s, IntegrationLifecycleState.INITIALIZING)
        assert not v.validate_transition(s, IntegrationLifecycleState.ACTIVE)


# ════════════════════════════════════════════════════════════════════════
# 17. IntegrationEvents
# ════════════════════════════════════════════════════════════════════════


class TestIntegrationEvents:
    def test_event_create(self):
        from iios.integration.lifecycle import (
            IntegrationEventType,
            IntegrationLifecycleState,
        )
        from iios.integration.lifecycle.integration_events import IntegrationLifecycleEvent
        evt = IntegrationLifecycleEvent.create(
            IntegrationEventType.INTEGRATION_CREATED,
            "s-001",
            IntegrationLifecycleState.CREATED,
        )
        assert evt.event_id.startswith("levt-")
        assert evt.session_id == "s-001"

    def test_event_to_dict(self):
        from iios.integration.lifecycle import (
            IntegrationEventType,
            IntegrationLifecycleState,
        )
        from iios.integration.lifecycle.integration_events import IntegrationLifecycleEvent
        evt = IntegrationLifecycleEvent.create(
            IntegrationEventType.INTEGRATION_ACTIVATED,
            "s-001",
            IntegrationLifecycleState.ACTIVE,
        )
        d = evt.to_dict()
        assert "event_id"   in d
        assert "event_type" in d

    def test_bus_listener(self):
        from iios.integration.lifecycle import (
            IntegrationEventType,
            IntegrationLifecycleState,
        )
        from iios.integration.lifecycle.integration_events import (
            IntegrationLifecycleEvent,
            IntegrationLifecycleEventBus,
        )
        received = []
        bus = IntegrationLifecycleEventBus()
        bus.add_listener(received.append)
        bus.emit(
            IntegrationEventType.INTEGRATION_CREATED,
            "s-001",
            IntegrationLifecycleState.CREATED,
        )
        assert len(received) == 1
        assert isinstance(received[0], IntegrationLifecycleEvent)

    def test_bus_listener_exception_suppressed(self):
        from iios.integration.lifecycle import (
            IntegrationEventType,
            IntegrationLifecycleState,
        )
        from iios.integration.lifecycle.integration_events import IntegrationLifecycleEventBus

        def bad_listener(evt):
            raise RuntimeError("simulated bad listener")

        bus = IntegrationLifecycleEventBus()
        bus.add_listener(bad_listener)
        # Should not raise
        bus.emit(
            IntegrationEventType.INTEGRATION_FAILED,
            "s-001",
            IntegrationLifecycleState.FAILED,
        )

    def test_remove_listener(self):
        from iios.integration.lifecycle import (
            IntegrationEventType,
            IntegrationLifecycleState,
        )
        from iios.integration.lifecycle.integration_events import IntegrationLifecycleEventBus
        received = []
        bus = IntegrationLifecycleEventBus()
        listener = received.append
        bus.add_listener(listener)
        bus.remove_listener(listener)
        bus.emit(
            IntegrationEventType.INTEGRATION_ACTIVATED,
            "s-001",
            IntegrationLifecycleState.ACTIVE,
        )
        assert len(received) == 0

    def test_listener_count(self):
        from iios.integration.lifecycle.integration_events import IntegrationLifecycleEventBus
        bus = IntegrationLifecycleEventBus()
        assert bus.listener_count() == 0
        bus.add_listener(lambda e: None)
        assert bus.listener_count() == 1


# ════════════════════════════════════════════════════════════════════════
# 18. Concurrency
# ════════════════════════════════════════════════════════════════════════


class TestConcurrency:
    def test_concurrent_registry_register(self):
        from iios.integration.lifecycle import (
            IntegrationContext,
            IntegrationMetadata,
            IntegrationRegistry,
            IntegrationSession,
        )
        reg    = IntegrationRegistry(max_sessions=1000)
        errors = []

        def register(i: int):
            try:
                sid  = f"s-conc-{i:04d}"
                ctx  = IntegrationContext.create(sid)
                meta = IntegrationMetadata.default()
                s    = IntegrationSession(sid, "wf-conc", ctx, meta)
                reg.register(s)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert reg.count() == 50

    def test_concurrent_statistics(self):
        from iios.integration.lifecycle import IntegrationLifecycleStatistics
        stats = IntegrationLifecycleStatistics()

        def increment():
            for _ in range(100):
                stats.record_created()

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.report().integration_sessions_created == 1000

    def test_concurrent_transitions_on_session(self):
        from iios.integration.lifecycle import (
            IntegrationContext,
            IntegrationInvalidTransitionError,
            IntegrationMetadata,
            IntegrationLifecycleState,
            IntegrationSession,
            IntegrationSessionTerminatedError,
        )
        sid  = "s-conc-trans"
        ctx  = IntegrationContext.create(sid)
        meta = IntegrationMetadata.default()
        s    = IntegrationSession(sid, "wf-conc", ctx, meta)

        succeeded = []
        errors    = []

        def try_transition():
            try:
                s.transition_to(IntegrationLifecycleState.INITIALIZING)
                succeeded.append(True)
            except (IntegrationInvalidTransitionError, IntegrationSessionTerminatedError):
                pass
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=try_transition) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one thread should have succeeded
        assert len(succeeded) == 1
        assert errors == []


# ════════════════════════════════════════════════════════════════════════
# 19. Regression — prior modules still importable
# ════════════════════════════════════════════════════════════════════════


class TestRegression:
    def test_c15_m1_importable(self):
        import iios.integration.lifecycle as m
        assert hasattr(m, "IntegrationLifecycle")
        assert hasattr(m, "IntegrationSession")
        assert hasattr(m, "IntegrationLifecycleState")

    def test_prior_integration_importable(self):
        import iios.integration
        assert iios.integration is not None

    def test_knowledge_modules_importable(self):
        """C14 M1-M6 knowledge modules must still import cleanly."""
        import iios.knowledge
        assert iios.knowledge is not None

    def test_supervisor_importable(self):
        """Supervisor modules must still import cleanly."""
        import iios.supervisor
        assert iios.supervisor is not None

    def test_all_lifecycle_exports_present(self):
        from iios.integration.lifecycle import __all__
        import iios.integration.lifecycle as m
        for name in __all__:
            assert hasattr(m, name), f"Missing export: {name!r}"
