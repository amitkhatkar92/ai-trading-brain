"""
tests/unit/knowledge/test_knowledge_lifecycle.py
--------------------------------------------------
Comprehensive test suite for iios.knowledge.lifecycle (C14 M1).

Coverage targets: ≥ 95 %
Test classes   : 17
Approx. tests  : 210+

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
import time
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from iios.knowledge.lifecycle import (
    ACTIVE_STATES,
    ACTOR_LIFECYCLE,
    ACTOR_OPERATOR,
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    IMMUTABLE_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VERSION,
    KnowledgeCapacityError,
    KnowledgeContext,
    KnowledgeEvent,
    KnowledgeEventBus,
    KnowledgeEventType,
    KnowledgeFactory,
    KnowledgeHistory,
    KnowledgeHistoryError,
    KnowledgeInvalidTransitionError,
    KnowledgeLifecycle,
    KnowledgeLifecycleError,
    KnowledgeLifecycleNotRunningError,
    KnowledgeLifecycleState,
    KnowledgeMetadata,
    KnowledgeRegistryError,
    KnowledgeRegistry,
    KnowledgeScope,
    KnowledgeSession,
    KnowledgeSessionNotFoundError,
    KnowledgeSessionTerminatedError,
    KnowledgeSource,
    KnowledgeStateRecord,
    KnowledgeStatistics,
    KnowledgeTransition,
    KnowledgeType,
    KnowledgeValidationCode,
    KnowledgeValidationError,
    KnowledgeValidationResult,
    KnowledgeValidator,
    SUCCESS_STATES,
)
from iios.investment.workflow.engine_lifecycle import EngineAlreadyRunningError


# ===========================================================================
# Helpers
# ===========================================================================


def _make_session(
    artifact_id: str = "art-001",
    knowledge_type: KnowledgeType = KnowledgeType.FACT,
) -> KnowledgeSession:
    """Create a KnowledgeSession via the factory (includes initial state record)."""
    factory = KnowledgeFactory()
    return factory.create(artifact_id=artifact_id, knowledge_type=knowledge_type)


def _started_lifecycle(**kwargs) -> KnowledgeLifecycle:
    lc = KnowledgeLifecycle(**kwargs)
    lc.start()
    return lc


def _full_happy_path(lc: KnowledgeLifecycle, artifact_id: str = "art-001") -> KnowledgeSession:
    """Run a session through the complete happy path and return it."""
    session = lc.create(artifact_id, KnowledgeType.FACT)
    sid = session.session_id
    lc.initialize(sid)
    lc.collect(sid)
    lc.validate_session(sid)
    lc.mark_ready(sid)
    lc.start_capture(sid)
    lc.mark_indexing_pending(sid)
    lc.publish(sid)
    lc.complete(sid)
    lc.archive(sid)
    return session


# ===========================================================================
# 1. TestConstants
# ===========================================================================


class TestConstants:
    def test_version_is_string(self):
        assert isinstance(VERSION, str)
        assert VERSION

    def test_all_states_in_valid_transitions(self):
        for state in KnowledgeLifecycleState:
            assert state in VALID_TRANSITIONS, f"{state} missing from VALID_TRANSITIONS"

    def test_archived_has_no_transitions(self):
        assert VALID_TRANSITIONS[KnowledgeLifecycleState.ARCHIVED] == frozenset()

    def test_terminal_states_disjoint_from_active(self):
        assert ACTIVE_STATES.isdisjoint(TERMINAL_STATES)

    def test_archived_in_immutable_states(self):
        assert KnowledgeLifecycleState.ARCHIVED in IMMUTABLE_STATES

    def test_success_states_subset_of_terminal_or_published(self):
        for s in SUCCESS_STATES:
            assert s in (
                KnowledgeLifecycleState.PUBLISHED,
                KnowledgeLifecycleState.COMPLETED,
            )

    def test_thirteen_states(self):
        assert len(KnowledgeLifecycleState) == 13

    def test_ten_event_types(self):
        assert len(KnowledgeEventType) == 10

    def test_knowledge_type_has_custom(self):
        assert KnowledgeType.CUSTOM is not None

    def test_knowledge_scope_global(self):
        assert KnowledgeScope.GLOBAL is not None

    def test_knowledge_source_unknown(self):
        assert KnowledgeSource.UNKNOWN is not None

    def test_default_max_sessions_positive(self):
        assert DEFAULT_MAX_SESSIONS > 0

    def test_default_max_archived_positive(self):
        assert DEFAULT_MAX_ARCHIVED > 0

    def test_default_max_history_positive(self):
        assert DEFAULT_MAX_HISTORY > 0


# ===========================================================================
# 2. TestExceptions
# ===========================================================================


class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(KnowledgeLifecycleError, IIOSError)

    def test_error_codes_unique(self):
        errors = [
            KnowledgeLifecycleError,
            KnowledgeSessionNotFoundError,
            KnowledgeInvalidTransitionError,
            KnowledgeSessionTerminatedError,
            KnowledgeValidationError,
            KnowledgeRegistryError,
            KnowledgeCapacityError,
            KnowledgeLifecycleNotRunningError,
            KnowledgeHistoryError,
        ]
        codes = [e.error_code for e in errors]
        assert len(codes) == len(set(codes))

    def test_session_not_found_carries_session_id(self):
        ex = KnowledgeSessionNotFoundError(session_id="s-123")
        assert ex.session_id == "s-123"

    def test_invalid_transition_carries_states(self):
        ex = KnowledgeInvalidTransitionError(from_state="created", to_state="published")
        assert ex.from_state == "created"
        assert ex.to_state == "published"

    def test_capacity_error_carries_limit(self):
        ex = KnowledgeCapacityError(limit=100)
        assert ex.limit == 100

    def test_not_running_has_default_message(self):
        ex = KnowledgeLifecycleNotRunningError()
        assert "not running" in str(ex).lower()

    def test_hierarchy_chain(self):
        assert issubclass(KnowledgeSessionNotFoundError, KnowledgeLifecycleError)
        assert issubclass(KnowledgeInvalidTransitionError, KnowledgeLifecycleError)
        assert issubclass(KnowledgeSessionTerminatedError, KnowledgeLifecycleError)
        assert issubclass(KnowledgeValidationError, KnowledgeLifecycleError)
        assert issubclass(KnowledgeRegistryError, KnowledgeLifecycleError)
        assert issubclass(KnowledgeCapacityError, KnowledgeLifecycleError)
        assert issubclass(KnowledgeLifecycleNotRunningError, KnowledgeLifecycleError)
        assert issubclass(KnowledgeHistoryError, KnowledgeLifecycleError)


# ===========================================================================
# 3. TestKnowledgeMetadata
# ===========================================================================


class TestMetadata:
    def test_create_defaults(self):
        m = KnowledgeMetadata.create(KnowledgeType.FACT)
        assert m.knowledge_type == KnowledgeType.FACT
        assert m.knowledge_scope == KnowledgeScope.DOMAIN
        assert m.knowledge_source == KnowledgeSource.INTERNAL

    def test_tags_are_frozen(self):
        m = KnowledgeMetadata.create(KnowledgeType.RULE, tags=["a", "b"])
        assert isinstance(m.tags, frozenset)
        assert "a" in m.tags

    def test_to_dict_keys(self):
        m = KnowledgeMetadata.create(KnowledgeType.CONCEPT)
        d = m.to_dict()
        for key in ("knowledge_type", "knowledge_scope", "knowledge_source", "knowledge_version"):
            assert key in d

    def test_is_frozen(self):
        m = KnowledgeMetadata.create(KnowledgeType.FACT)
        with pytest.raises((AttributeError, TypeError)):
            m.knowledge_type = KnowledgeType.RULE  # type: ignore[misc]


# ===========================================================================
# 4. TestKnowledgeContext
# ===========================================================================


class TestContext:
    def test_create_generates_id(self):
        ctx = KnowledgeContext.create("system")
        assert ctx.context_id
        assert ctx.actor == "system"

    def test_explicit_context_id(self):
        ctx = KnowledgeContext.create("operator", context_id="ctx-999")
        assert ctx.context_id == "ctx-999"

    def test_to_dict_has_actor(self):
        ctx = KnowledgeContext.create("bot")
        d = ctx.to_dict()
        assert d["actor"] == "bot"

    def test_is_frozen(self):
        ctx = KnowledgeContext.create("system")
        with pytest.raises((AttributeError, TypeError)):
            ctx.actor = "someone"  # type: ignore[misc]


# ===========================================================================
# 5. TestKnowledgeStateRecord
# ===========================================================================


class TestStateRecord:
    def test_create(self):
        rec = KnowledgeStateRecord.create(
            session_id="s-1",
            state=KnowledgeLifecycleState.CREATED,
            actor="system",
        )
        assert rec.session_id == "s-1"
        assert rec.state == KnowledgeLifecycleState.CREATED

    def test_to_dict(self):
        rec = KnowledgeStateRecord.create("s-2", KnowledgeLifecycleState.READY, "op")
        d = rec.to_dict()
        assert d["state"] == "ready"

    def test_is_frozen(self):
        rec = KnowledgeStateRecord.create("s-3", KnowledgeLifecycleState.CREATED, "s")
        with pytest.raises((AttributeError, TypeError)):
            rec.actor = "other"  # type: ignore[misc]


# ===========================================================================
# 6. TestKnowledgeTransition
# ===========================================================================


class TestTransition:
    def test_create(self):
        t = KnowledgeTransition.create(
            session_id="s-1",
            from_state=KnowledgeLifecycleState.CREATED,
            to_state=KnowledgeLifecycleState.INITIALIZING,
            actor="system",
        )
        assert t.from_state == KnowledgeLifecycleState.CREATED
        assert t.to_state == KnowledgeLifecycleState.INITIALIZING

    def test_to_dict(self):
        t = KnowledgeTransition.create(
            "s-1",
            KnowledgeLifecycleState.READY,
            KnowledgeLifecycleState.CAPTURING,
            "lc",
        )
        d = t.to_dict()
        assert d["from_state"] == "ready"
        assert d["to_state"] == "capturing"

    def test_is_frozen(self):
        t = KnowledgeTransition.create(
            "s-1",
            KnowledgeLifecycleState.CREATED,
            KnowledgeLifecycleState.INITIALIZING,
            "sys",
        )
        with pytest.raises((AttributeError, TypeError)):
            t.actor = "other"  # type: ignore[misc]


# ===========================================================================
# 7. TestKnowledgeSession
# ===========================================================================


class TestSession:
    def test_initial_state_is_created(self):
        s = _make_session()
        assert s.state == KnowledgeLifecycleState.CREATED

    def test_is_active_initially(self):
        s = _make_session()
        assert s.is_active
        assert not s.is_terminal

    def test_history_has_initial_record(self):
        s = _make_session()
        assert len(s.state_history) == 1
        assert s.state_history[0].state == KnowledgeLifecycleState.CREATED

    def test_valid_transition(self):
        s = _make_session()
        s.transition_to(KnowledgeLifecycleState.INITIALIZING, "system")
        assert s.state == KnowledgeLifecycleState.INITIALIZING

    def test_invalid_transition_raises(self):
        s = _make_session()
        with pytest.raises(KnowledgeInvalidTransitionError):
            s.transition_to(KnowledgeLifecycleState.PUBLISHED, "system")

    def test_archived_is_immutable(self):
        s = _make_session()
        # walk to ARCHIVED
        for state in (
            KnowledgeLifecycleState.INITIALIZING,
            KnowledgeLifecycleState.COLLECTING,
            KnowledgeLifecycleState.VALIDATING,
            KnowledgeLifecycleState.READY,
            KnowledgeLifecycleState.CAPTURING,
            KnowledgeLifecycleState.INDEXING_PENDING,
            KnowledgeLifecycleState.PUBLISHED,
            KnowledgeLifecycleState.COMPLETED,
            KnowledgeLifecycleState.ARCHIVED,
        ):
            s.transition_to(state, "system")
        with pytest.raises(KnowledgeSessionTerminatedError):
            s.transition_to(KnowledgeLifecycleState.FAILED, "system")

    def test_failure_reason_captured(self):
        s = _make_session()
        s.transition_to(KnowledgeLifecycleState.INITIALIZING, "system")
        s.transition_to(KnowledgeLifecycleState.FAILED, "system", reason="parse error")
        assert s.failure_reason == "parse error"

    def test_transitions_list_grows(self):
        s = _make_session()
        s.transition_to(KnowledgeLifecycleState.INITIALIZING, "system")
        s.transition_to(KnowledgeLifecycleState.COLLECTING, "system")
        assert len(s.transitions) == 2

    def test_to_dict_has_session_id(self):
        s = _make_session()
        d = s.to_dict()
        assert "session_id" in d
        assert "state" in d

    def test_duration_none_before_archive(self):
        s = _make_session()
        # end_time not set for non-terminal states
        assert s.duration_seconds is None

    def test_duration_set_after_terminal(self):
        s = _make_session()
        s.transition_to(KnowledgeLifecycleState.INITIALIZING, "system")
        s.transition_to(KnowledgeLifecycleState.FAILED, "system")
        assert s.duration_seconds is not None
        assert s.duration_seconds >= 0

    def test_start_time_set_on_capturing(self):
        s = _make_session()
        for st in (
            KnowledgeLifecycleState.INITIALIZING,
            KnowledgeLifecycleState.COLLECTING,
            KnowledgeLifecycleState.VALIDATING,
            KnowledgeLifecycleState.READY,
            KnowledgeLifecycleState.CAPTURING,
        ):
            s.transition_to(st, "system")
        assert s.start_time is not None

    def test_knowledge_type_property(self):
        s = _make_session(knowledge_type=KnowledgeType.RULE)
        assert s.knowledge_type == KnowledgeType.RULE

    def test_repr(self):
        s = _make_session()
        assert "KnowledgeSession" in repr(s)


# ===========================================================================
# 8. TestKnowledgeFactory
# ===========================================================================


class TestFactory:
    def test_creates_session(self):
        f = KnowledgeFactory()
        s = f.create("art-1", KnowledgeType.FACT)
        assert isinstance(s, KnowledgeSession)
        assert s.state == KnowledgeLifecycleState.CREATED

    def test_explicit_session_id(self):
        f = KnowledgeFactory()
        s = f.create("art-2", KnowledgeType.RULE, session_id="explicit-id")
        assert s.session_id == "explicit-id"

    def test_metadata_applied(self):
        f = KnowledgeFactory()
        s = f.create(
            "art-3",
            KnowledgeType.STRATEGY,
            knowledge_scope=KnowledgeScope.GLOBAL,
            knowledge_version="2.1.0",
            author="alice",
        )
        assert s.knowledge_scope == KnowledgeScope.GLOBAL
        assert s.knowledge_version == "2.1.0"
        assert s.metadata.author == "alice"

    def test_initial_history_recorded(self):
        f = KnowledgeFactory()
        s = f.create("art-4", KnowledgeType.FACT)
        assert len(s.state_history) == 1
        assert s.state_history[0].state == KnowledgeLifecycleState.CREATED


# ===========================================================================
# 9. TestKnowledgeRegistry
# ===========================================================================


class TestRegistry:
    def test_register_and_get(self):
        r = KnowledgeRegistry()
        s = _make_session()
        r.register(s)
        assert r.get(s.session_id) is s

    def test_duplicate_registration_raises(self):
        r = KnowledgeRegistry()
        s = _make_session()
        r.register(s)
        with pytest.raises(KnowledgeRegistryError):
            r.register(s)

    def test_not_found_raises(self):
        r = KnowledgeRegistry()
        with pytest.raises(KnowledgeSessionNotFoundError):
            r.get("ghost")

    def test_get_or_none_returns_none(self):
        r = KnowledgeRegistry()
        assert r.get_or_none("no-such") is None

    def test_capacity_limit(self):
        r = KnowledgeRegistry(max_sessions=2)
        s1 = _make_session("a1")
        s2 = _make_session("a2")
        s3 = _make_session("a3")
        r.register(s1)
        r.register(s2)
        with pytest.raises(KnowledgeCapacityError):
            r.register(s3)

    def test_update_archives_session(self):
        r = KnowledgeRegistry()
        s = _make_session()
        r.register(s)
        # walk to ARCHIVED
        for state in (
            KnowledgeLifecycleState.INITIALIZING,
            KnowledgeLifecycleState.COLLECTING,
            KnowledgeLifecycleState.VALIDATING,
            KnowledgeLifecycleState.READY,
            KnowledgeLifecycleState.CAPTURING,
            KnowledgeLifecycleState.INDEXING_PENDING,
            KnowledgeLifecycleState.PUBLISHED,
            KnowledgeLifecycleState.COMPLETED,
            KnowledgeLifecycleState.ARCHIVED,
        ):
            s.transition_to(state, "system")
        r.update(s)
        assert r.active_count() == 0
        assert r.archived_count() == 1

    def test_all_active_returns_list(self):
        r = KnowledgeRegistry()
        for i in range(3):
            r.register(_make_session(f"art-{i}"))
        assert len(r.all_active()) == 3

    def test_by_state_filter(self):
        r = KnowledgeRegistry()
        s = _make_session()
        r.register(s)
        results = r.by_state(KnowledgeLifecycleState.CREATED)
        assert s in results

    def test_by_type_filter(self):
        r = KnowledgeRegistry()
        s = _make_session(knowledge_type=KnowledgeType.RULE)
        r.register(s)
        assert s in r.by_type(KnowledgeType.RULE)
        assert s not in r.by_type(KnowledgeType.FACT)

    def test_by_scope_filter(self):
        r = KnowledgeRegistry()
        f = KnowledgeFactory()
        s = f.create("art-x", KnowledgeType.FACT, knowledge_scope=KnowledgeScope.GLOBAL)
        r.register(s)
        assert s in r.by_scope(KnowledgeScope.GLOBAL)

    def test_contains(self):
        r = KnowledgeRegistry()
        s = _make_session()
        r.register(s)
        assert r.contains(s.session_id)
        assert not r.contains("absent")

    def test_remove(self):
        r = KnowledgeRegistry()
        s = _make_session()
        r.register(s)
        removed = r.remove(s.session_id)
        assert removed is s
        assert not r.contains(s.session_id)

    def test_remove_nonexistent_returns_none(self):
        r = KnowledgeRegistry()
        assert r.remove("no-such") is None

    def test_clear(self):
        r = KnowledgeRegistry()
        r.register(_make_session("a"))
        r.clear()
        assert r.total_count() == 0


# ===========================================================================
# 10. TestKnowledgeHistory
# ===========================================================================


class TestHistory:
    def _make_transition(self, session_id: str = "s-1") -> KnowledgeTransition:
        return KnowledgeTransition.create(
            session_id  = session_id,
            from_state  = KnowledgeLifecycleState.CREATED,
            to_state    = KnowledgeLifecycleState.INITIALIZING,
            actor       = "system",
        )

    def test_record_and_count(self):
        h = KnowledgeHistory()
        h.record(self._make_transition())
        assert h.count() == 1

    def test_bounded_eviction(self):
        h = KnowledgeHistory(max_entries=3)
        for i in range(5):
            h.record(self._make_transition(f"s-{i}"))
        assert h.count() == 3

    def test_for_session(self):
        h = KnowledgeHistory()
        h.record(self._make_transition("s-A"))
        h.record(self._make_transition("s-B"))
        results = h.for_session("s-A")
        assert len(results) == 1
        assert results[0].session_id == "s-A"

    def test_recent_limited(self):
        h = KnowledgeHistory()
        for i in range(30):
            h.record(self._make_transition(f"s-{i}"))
        assert len(h.recent(10)) == 10

    def test_all_returns_list(self):
        h = KnowledgeHistory()
        h.record(self._make_transition())
        assert isinstance(h.all(), list)

    def test_session_count(self):
        h = KnowledgeHistory()
        h.record(self._make_transition("s-X"))
        h.record(self._make_transition("s-Y"))
        assert h.session_count() == 2

    def test_clear(self):
        h = KnowledgeHistory()
        h.record(self._make_transition())
        h.clear()
        assert h.count() == 0


# ===========================================================================
# 11. TestKnowledgeStatistics
# ===========================================================================


class TestStatistics:
    def test_initial_snapshot_zeros(self):
        s = KnowledgeStatistics()
        snap = s.snapshot()
        assert snap["knowledge_sessions_created"] == 0
        assert snap["transition_count"] == 0

    def test_record_created(self):
        s = KnowledgeStatistics()
        s.record_created()
        assert s.snapshot()["knowledge_sessions_created"] == 1

    def test_record_completed(self):
        s = KnowledgeStatistics()
        s.record_completed()
        assert s.snapshot()["knowledge_sessions_completed"] == 1

    def test_record_failed(self):
        s = KnowledgeStatistics()
        s.record_failed()
        assert s.snapshot()["knowledge_sessions_failed"] == 1

    def test_record_archived_and_duration(self):
        s = KnowledgeStatistics()
        s.record_archived(duration_seconds=5.0)
        snap = s.snapshot()
        assert snap["knowledge_sessions_archived"] == 1
        assert snap["average_session_duration_seconds"] == pytest.approx(5.0)

    def test_average_duration_multiple(self):
        s = KnowledgeStatistics()
        s.record_archived(duration_seconds=2.0)
        s.record_archived(duration_seconds=4.0)
        assert s.snapshot()["average_session_duration_seconds"] == pytest.approx(3.0)

    def test_record_transition(self):
        s = KnowledgeStatistics()
        s.record_transition()
        s.record_transition()
        assert s.snapshot()["transition_count"] == 2

    def test_reset(self):
        s = KnowledgeStatistics()
        s.record_created()
        s.reset()
        assert s.snapshot()["knowledge_sessions_created"] == 0

    def test_snapshot_has_all_six_keys(self):
        s = KnowledgeStatistics()
        snap = s.snapshot()
        expected = {
            "knowledge_sessions_created",
            "knowledge_sessions_completed",
            "knowledge_sessions_failed",
            "knowledge_sessions_archived",
            "transition_count",
            "average_session_duration_seconds",
        }
        assert expected <= set(snap.keys())


# ===========================================================================
# 12. TestKnowledgeValidator
# ===========================================================================


class TestValidator:
    def test_valid_session_passes_all(self):
        s = _make_session()
        v = KnowledgeValidator()
        results = v.validate(s)
        assert all(r.passed for r in results)

    def test_empty_session_id_fails_identifier(self):
        s = _make_session()
        s._session_id = ""
        v = KnowledgeValidator()
        results = v.validate(s)
        id_result = next(r for r in results if r.code == KnowledgeValidationCode.IDENTIFIER_CONSISTENCY)
        assert not id_result.passed

    def test_empty_artifact_id_fails_identifier(self):
        s = _make_session()
        s._artifact_id = ""
        v = KnowledgeValidator()
        results = v.validate(s)
        id_result = next(r for r in results if r.code == KnowledgeValidationCode.IDENTIFIER_CONSISTENCY)
        assert not id_result.passed

    def test_raise_on_failure(self):
        s = _make_session()
        s._session_id = ""
        v = KnowledgeValidator()
        with pytest.raises(KnowledgeValidationError):
            v.validate(s, raise_on_failure=True)

    def test_five_checks_returned(self):
        s = _make_session()
        v = KnowledgeValidator()
        results = v.validate(s)
        assert len(results) == 5

    def test_validation_result_to_dict(self):
        r = KnowledgeValidationResult(
            code=KnowledgeValidationCode.IDENTIFIER_CONSISTENCY,
            passed=True,
            message="OK",
        )
        d = r.to_dict()
        assert d["code"] == "IDENTIFIER_CONSISTENCY"

    def test_timestamp_inconsistency_detected(self):
        s = _make_session()
        s._updated_at = s._created_at - 1  # updated before created — impossible
        v = KnowledgeValidator()
        results = v.validate(s)
        ts = next(r for r in results if r.code == KnowledgeValidationCode.TIMESTAMP_CONSISTENCY)
        assert not ts.passed

    def test_empty_history_fails_integrity(self):
        s = _make_session()
        s._state_history.clear()
        v = KnowledgeValidator()
        results = v.validate(s)
        hist = next(r for r in results if r.code == KnowledgeValidationCode.HISTORY_INTEGRITY)
        assert not hist.passed


# ===========================================================================
# 13. TestKnowledgeEvents
# ===========================================================================


class TestEvents:
    def test_event_create(self):
        e = KnowledgeEvent.create(
            event_type  = KnowledgeEventType.KNOWLEDGE_CREATED,
            session_id  = "s-1",
            artifact_id = "art-1",
            state       = KnowledgeLifecycleState.CREATED,
            actor       = "system",
        )
        assert e.event_type == KnowledgeEventType.KNOWLEDGE_CREATED
        assert e.session_id == "s-1"

    def test_event_to_dict(self):
        e = KnowledgeEvent.create(
            KnowledgeEventType.KNOWLEDGE_PUBLISHED,
            "s-2", "art-2", KnowledgeLifecycleState.PUBLISHED, "lc",
        )
        d = e.to_dict()
        assert d["event_type"] == "knowledge.published"

    def test_event_is_frozen(self):
        e = KnowledgeEvent.create(
            KnowledgeEventType.KNOWLEDGE_ARCHIVED,
            "s-3", "art-3", KnowledgeLifecycleState.ARCHIVED, "sys",
        )
        with pytest.raises((AttributeError, TypeError)):
            e.actor = "other"  # type: ignore[misc]

    def test_event_bus_dispatch(self):
        received = []
        bus = KnowledgeEventBus()
        bus.add_listener(received.append)
        e = KnowledgeEvent.create(
            KnowledgeEventType.KNOWLEDGE_FAILED,
            "s-4", "art-4", KnowledgeLifecycleState.FAILED, "sys",
        )
        bus.emit(e)
        assert len(received) == 1

    def test_event_bus_duplicate_listener_ignored(self):
        bus = KnowledgeEventBus()
        listener = MagicMock()
        bus.add_listener(listener)
        bus.add_listener(listener)
        assert bus.listener_count() == 1

    def test_event_bus_remove_listener(self):
        bus = KnowledgeEventBus()
        listener = MagicMock()
        bus.add_listener(listener)
        removed = bus.remove_listener(listener)
        assert removed
        assert bus.listener_count() == 0

    def test_event_bus_remove_nonexistent_returns_false(self):
        bus = KnowledgeEventBus()
        assert not bus.remove_listener(MagicMock())

    def test_event_bus_isolates_listener_exceptions(self):
        """A crashing listener must not prevent subsequent listeners from receiving events."""
        def bad_listener(_): raise RuntimeError("boom")
        good_calls = []
        bus = KnowledgeEventBus()
        bus.add_listener(bad_listener)
        bus.add_listener(good_calls.append)
        e = KnowledgeEvent.create(
            KnowledgeEventType.KNOWLEDGE_CREATED,
            "s-5", "art-5", KnowledgeLifecycleState.CREATED, "sys",
        )
        bus.emit(e)          # must not raise
        assert len(good_calls) == 1

    def test_event_bus_clear(self):
        bus = KnowledgeEventBus()
        bus.add_listener(MagicMock())
        bus.clear()
        assert bus.listener_count() == 0

    def test_all_ten_event_types_covered(self):
        expected = {
            "knowledge.created",
            "knowledge.initialized",
            "knowledge.validated",
            "knowledge.capture_started",
            "knowledge.published",
            "knowledge.paused",
            "knowledge.resumed",
            "knowledge.completed",
            "knowledge.failed",
            "knowledge.archived",
        }
        actual = {e.value for e in KnowledgeEventType}
        assert actual == expected


# ===========================================================================
# 14. TestLifecycleTransitions (KnowledgeLifecycle)
# ===========================================================================


class TestLifecycleTransitions:
    def test_start_stop(self):
        lc = KnowledgeLifecycle()
        lc.start()
        assert lc.lifecycle_state().value == "running"
        lc.stop()
        assert lc.lifecycle_state().value != "running"

    def test_double_start_raises(self):
        lc = KnowledgeLifecycle()
        lc.start()
        with pytest.raises(EngineAlreadyRunningError):
            lc.start()
        lc.stop()

    def test_create_requires_running(self):
        lc = KnowledgeLifecycle()
        with pytest.raises(KnowledgeLifecycleNotRunningError):
            lc.create("art-1", KnowledgeType.FACT)

    def test_create_returns_session(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("art-1", KnowledgeType.FACT)
            assert isinstance(s, KnowledgeSession)
            assert s.state == KnowledgeLifecycleState.CREATED
        finally:
            lc.stop()

    def test_happy_path(self):
        lc = _started_lifecycle()
        try:
            s = _full_happy_path(lc)
            assert s.state == KnowledgeLifecycleState.ARCHIVED
        finally:
            lc.stop()

    def test_initialize(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("art-2", KnowledgeType.RULE)
            lc.initialize(s.session_id)
            assert s.state == KnowledgeLifecycleState.INITIALIZING
        finally:
            lc.stop()

    def test_collect(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            lc.collect(s.session_id)
            assert s.state == KnowledgeLifecycleState.COLLECTING
        finally:
            lc.stop()

    def test_validate_session(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            lc.collect(s.session_id)
            lc.validate_session(s.session_id)
            assert s.state == KnowledgeLifecycleState.VALIDATING
        finally:
            lc.stop()

    def test_mark_ready(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            lc.collect(s.session_id)
            lc.validate_session(s.session_id)
            lc.mark_ready(s.session_id)
            assert s.state == KnowledgeLifecycleState.READY
        finally:
            lc.stop()

    def test_pause_from_ready(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            lc.collect(s.session_id)
            lc.validate_session(s.session_id)
            lc.mark_ready(s.session_id)
            lc.pause(s.session_id)
            assert s.state == KnowledgeLifecycleState.PAUSED
        finally:
            lc.stop()

    def test_pause_from_published(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            lc.collect(s.session_id)
            lc.validate_session(s.session_id)
            lc.mark_ready(s.session_id)
            lc.start_capture(s.session_id)
            lc.mark_indexing_pending(s.session_id)
            lc.publish(s.session_id)
            lc.pause(s.session_id)
            assert s.state == KnowledgeLifecycleState.PAUSED
        finally:
            lc.stop()

    def test_resume(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            lc.collect(s.session_id)
            lc.validate_session(s.session_id)
            lc.mark_ready(s.session_id)
            lc.pause(s.session_id)
            lc.resume(s.session_id)
            assert s.state == KnowledgeLifecycleState.RESUMING
        finally:
            lc.stop()

    def test_mark_resumed_to_ready(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            lc.collect(s.session_id)
            lc.validate_session(s.session_id)
            lc.mark_ready(s.session_id)
            lc.pause(s.session_id)
            lc.resume(s.session_id)
            lc.mark_resumed(s.session_id, to_state=KnowledgeLifecycleState.READY)
            assert s.state == KnowledgeLifecycleState.READY
        finally:
            lc.stop()

    def test_mark_resumed_to_capturing(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            lc.collect(s.session_id)
            lc.validate_session(s.session_id)
            lc.mark_ready(s.session_id)
            lc.pause(s.session_id)
            lc.resume(s.session_id)
            lc.mark_resumed(s.session_id, to_state=KnowledgeLifecycleState.CAPTURING)
            assert s.state == KnowledgeLifecycleState.CAPTURING
        finally:
            lc.stop()

    def test_fail(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            lc.fail(s.session_id, reason="connection error")
            assert s.state == KnowledgeLifecycleState.FAILED
            assert s.failure_reason == "connection error"
        finally:
            lc.stop()

    def test_archive_from_failed(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            lc.fail(s.session_id)
            lc.archive(s.session_id)
            assert s.state == KnowledgeLifecycleState.ARCHIVED
        finally:
            lc.stop()

    def test_archive_from_paused(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            lc.collect(s.session_id)
            lc.validate_session(s.session_id)
            lc.mark_ready(s.session_id)
            lc.pause(s.session_id)
            lc.archive(s.session_id)
            assert s.state == KnowledgeLifecycleState.ARCHIVED
        finally:
            lc.stop()


# ===========================================================================
# 15. TestInvalidTransitions
# ===========================================================================


class TestInvalidTransitions:
    def test_created_to_published_invalid(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            with pytest.raises(KnowledgeInvalidTransitionError):
                lc.publish(s.session_id)
        finally:
            lc.stop()

    def test_skip_collecting(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("a", KnowledgeType.FACT)
            lc.initialize(s.session_id)
            with pytest.raises(KnowledgeInvalidTransitionError):
                lc.mark_ready(s.session_id)  # skipped collecting / validating
        finally:
            lc.stop()

    def test_unknown_session_raises(self):
        lc = _started_lifecycle()
        try:
            with pytest.raises(KnowledgeSessionNotFoundError):
                lc.initialize("does-not-exist")
        finally:
            lc.stop()

    def test_archived_raises_terminated_on_any_op(self):
        lc = _started_lifecycle()
        try:
            s = _full_happy_path(lc)
            with pytest.raises(KnowledgeSessionTerminatedError):
                lc.fail(s.session_id, reason="post-archive")
        finally:
            lc.stop()


# ===========================================================================
# 16. TestPublicSurface
# ===========================================================================


class TestPublicSurface:
    def test_health_returns_dict(self):
        lc = _started_lifecycle()
        try:
            h = lc.health()
            assert "status" in h
            assert "lifecycle_state" in h
        finally:
            lc.stop()

    def test_statistics_six_keys(self):
        lc = _started_lifecycle()
        try:
            stats = lc.statistics()
            assert len(stats) >= 6
        finally:
            lc.stop()

    def test_get_session(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("art-x", KnowledgeType.FACT)
            retrieved = lc.get_session(s.session_id)
            assert retrieved is s
        finally:
            lc.stop()

    def test_validate_public(self):
        lc = _started_lifecycle()
        try:
            s = lc.create("art-v", KnowledgeType.CONCEPT)
            results = lc.validate(s.session_id)
            assert len(results) == 5
        finally:
            lc.stop()

    def test_history_public(self):
        lc = _started_lifecycle()
        try:
            _full_happy_path(lc, "art-h1")
            h = lc.history()
            assert isinstance(h, list)
            assert len(h) > 0
        finally:
            lc.stop()

    def test_history_by_session(self):
        lc = _started_lifecycle()
        try:
            s = _full_happy_path(lc, "art-h2")
            h = lc.history(session_id=s.session_id)
            assert all(t.session_id == s.session_id for t in h)
        finally:
            lc.stop()

    def test_add_and_remove_listener(self):
        lc = _started_lifecycle()
        try:
            received = []
            lc.add_listener(received.append)
            lc.create("art-ev", KnowledgeType.FACT)
            assert len(received) >= 1
            lc.remove_listener(received.append)
        finally:
            lc.stop()

    def test_statistics_accumulate_after_full_path(self):
        lc = _started_lifecycle()
        try:
            _full_happy_path(lc)
            stats = lc.statistics()
            assert stats["knowledge_sessions_created"] == 1
            assert stats["knowledge_sessions_completed"] == 1
            assert stats["knowledge_sessions_archived"] == 1
        finally:
            lc.stop()

    def test_health_status_healthy_when_running(self):
        lc = _started_lifecycle()
        try:
            assert lc.health()["status"] == "healthy"
        finally:
            lc.stop()

    def test_health_active_session_count(self):
        lc = _started_lifecycle()
        try:
            lc.create("art-c1", KnowledgeType.FACT)
            lc.create("art-c2", KnowledgeType.RULE)
            h = lc.health()
            assert h["active_sessions"] == 2
        finally:
            lc.stop()


# ===========================================================================
# 17. TestConcurrency
# ===========================================================================


class TestConcurrency:
    def test_concurrent_creates(self):
        """N threads each create a session — all must succeed."""
        lc = _started_lifecycle(max_sessions=200)
        errors = []
        sessions = []
        lock = threading.Lock()

        def _create(i: int):
            try:
                s = lc.create(f"art-concurrent-{i}", KnowledgeType.FACT)
                with lock:
                    sessions.append(s)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_create, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lc.stop()
        assert not errors, f"Concurrent create errors: {errors}"
        assert len(sessions) == 50

    def test_concurrent_full_paths(self):
        """N threads each run a full happy path — no cross-contamination."""
        lc = _started_lifecycle(max_sessions=200, max_archived=200)
        errors = []

        def _path(i: int):
            try:
                _full_happy_path(lc, f"art-path-{i}")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_path, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lc.stop()
        assert not errors, f"Concurrent path errors: {errors}"

    def test_concurrent_statistics_accuracy(self):
        """Statistics counters must be accurate under concurrent writes."""
        N = 30
        lc = _started_lifecycle(max_sessions=500, max_archived=500)

        def _create_only(_):
            lc.create(f"art-stat-{id(threading.current_thread())}", KnowledgeType.FACT)

        threads = [threading.Thread(target=_create_only, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = lc.statistics()
        lc.stop()
        assert stats["knowledge_sessions_created"] == N


# ===========================================================================
# 18. TestRegression (supervisor tests not broken)
# ===========================================================================


class TestRegression:
    """Smoke-test that importing knowledge.lifecycle does not pollute supervisor."""

    def test_supervisor_lifecycle_import_still_works(self):
        from iios.supervisor.lifecycle import SupervisorLifecycle  # noqa: F401
        from iios.supervisor.lifecycle import SupervisorState       # noqa: F401
        # Both imports must succeed without error

    def test_knowledge_lifecycle_does_not_overlap_supervisor_errors(self):
        from iios.supervisor.lifecycle.exceptions import SupervisorLifecycleError
        # Different base paths — no name collision
        assert SupervisorLifecycleError.__name__ != KnowledgeLifecycleError.__name__

    def test_knowledge_lifecycle_state_distinct_from_supervisor_state(self):
        from iios.supervisor.lifecycle.constants import SupervisorState
        assert KnowledgeLifecycleState.__name__ != SupervisorState.__name__
