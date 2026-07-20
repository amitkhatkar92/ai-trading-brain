"""
tests/unit/decision/lifecycle/test_lifecycle.py
================================================
Comprehensive test suite for iios.decision.lifecycle — C9 M1.

Coverage areas
--------------
* Lifecycle management (start/stop)
* Session creation
* All valid state transitions
* Invalid transition rejection
* Pause / resume cycle
* Failure path
* Archive path
* Validation (all five checks)
* Registry (add, find, archive, eviction)
* Factory
* History (events, transitions)
* Statistics (all six counters)
* Events (all eight types)
* Context / Metadata value objects
* Concurrency (parallel creates + transitions)
* Regression (interface surface)
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import List
from unittest.mock import MagicMock

import pytest

from iios.decision.lifecycle import (
    ACTIVE_STATES,
    IMMUTABLE_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    DecisionContext,
    DecisionEvent,
    DecisionEventType,
    DecisionFactory,
    DecisionHistory,
    DecisionInvalidTransitionError,
    DecisionLifecycle,
    DecisionLifecycleError,
    DecisionLifecycleNotRunningError,
    DecisionMetadata,
    DecisionPriority,
    DecisionRegistry,
    DecisionScope,
    DecisionSession,
    DecisionSessionAlreadyExistsError,
    DecisionSessionNotFoundError,
    DecisionSessionTerminatedError,
    DecisionState,
    DecisionStatistics,
    DecisionTransition,
    DecisionTrigger,
    DecisionType,
    DecisionValidationCode,
    DecisionValidationResult,
    DecisionValidator,
    ValidationCheckResult,
    can_transition,
    make_decision_archived,
    make_decision_completed,
    make_decision_created,
    make_decision_failed,
    make_decision_initialized,
    make_decision_paused,
    make_decision_resumed,
    make_decision_started,
    make_transition,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _lc() -> DecisionLifecycle:
    """Return a started DecisionLifecycle."""
    lc = DecisionLifecycle()
    lc.start()
    return lc


def _session(lc: DecisionLifecycle, decision_id: str | None = None) -> DecisionSession:
    return lc.create(decision_id or f"d-{uuid.uuid4()}")


def _full_path(lc: DecisionLifecycle, decision_id: str | None = None) -> DecisionSession:
    """Create a session and run it to COMPLETED."""
    s = _session(lc, decision_id)
    sid = s.session_id
    lc.initialize(sid)
    lc.collect(sid)
    lc.evaluate(sid)
    lc.ready(sid)
    lc.activate(sid)
    lc.complete(sid)
    return lc.find_archived(sid) or lc.find(sid)


# ===========================================================================
# 1. Lifecycle management
# ===========================================================================

class TestLifecycleManagement:
    def test_start(self):
        lc = DecisionLifecycle()
        lc.start()
        assert repr(lc)
        lc.stop()

    def test_stop(self):
        lc = _lc()
        lc.stop()

    def test_not_running_raises(self):
        lc = DecisionLifecycle()
        with pytest.raises(DecisionLifecycleNotRunningError):
            lc.create("d-1")

    def test_repr(self):
        lc = _lc()
        r = repr(lc)
        assert "DecisionLifecycle" in r
        assert "1.0.0" in r
        lc.stop()

    def test_start_stop_multiple_times(self):
        lc = DecisionLifecycle()
        for _ in range(3):
            lc.start()
            lc.stop()


# ===========================================================================
# 2. Session creation
# ===========================================================================

class TestSessionCreation:
    def setup_method(self): self.lc = _lc()
    def teardown_method(self): self.lc.stop()

    def test_create_returns_session(self):
        s = self.lc.create("d-001")
        assert isinstance(s, DecisionSession)

    def test_create_state_is_created(self):
        s = self.lc.create("d-001")
        assert s.state == DecisionState.CREATED

    def test_create_decision_id(self):
        s = self.lc.create("my-decision")
        assert s.decision_id == "my-decision"

    def test_create_session_id_auto(self):
        s1 = self.lc.create("d-1")
        s2 = self.lc.create("d-2")
        assert s1.session_id != s2.session_id

    def test_create_explicit_session_id(self):
        s = self.lc.create("d-1", session_id="sid-explicit")
        assert s.session_id == "sid-explicit"

    def test_create_all_fields(self):
        s = self.lc.create(
            "d-full",
            workflow_id       = "wf-1",
            portfolio_id      = "p-1",
            strategy_id       = "st-1",
            decision_scope    = DecisionScope.PORTFOLIO,
            decision_type     = DecisionType.REBALANCE,
            decision_priority = DecisionPriority.HIGH,
            decision_trigger  = DecisionTrigger.SCHEDULED,
            decision_reason   = "quarterly rebalance",
        )
        assert s.workflow_id   == "wf-1"
        assert s.portfolio_id  == "p-1"
        assert s.strategy_id   == "st-1"
        assert s.decision_scope    == DecisionScope.PORTFOLIO
        assert s.decision_type     == DecisionType.REBALANCE
        assert s.decision_priority == DecisionPriority.HIGH
        assert s.decision_trigger  == DecisionTrigger.SCHEDULED
        assert s.decision_reason   == "quarterly rebalance"

    def test_create_increments_statistics(self):
        self.lc.create("d-1")
        self.lc.create("d-2")
        assert self.lc.statistics().sessions_created == 2

    def test_create_emits_event(self):
        s = self.lc.create("d-ev")
        evts = self.lc.history().events_for_session(s.session_id)
        types = [e.event_type for e in evts]
        assert DecisionEventType.DECISION_CREATED in types

    def test_create_duplicate_session_id_raises(self):
        self.lc.create("d-dup", session_id="dup-sid")
        with pytest.raises(DecisionSessionAlreadyExistsError):
            self.lc.create("d-dup2", session_id="dup-sid")


# ===========================================================================
# 3. Happy-path transitions
# ===========================================================================

class TestHappyPath:
    def setup_method(self): self.lc = _lc()
    def teardown_method(self): self.lc.stop()

    def test_initialize(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        assert self.lc.find(s.session_id).state == DecisionState.INITIALIZING

    def test_collect(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        assert self.lc.find(s.session_id).state == DecisionState.COLLECTING

    def test_evaluate(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        self.lc.evaluate(s.session_id)
        assert self.lc.find(s.session_id).state == DecisionState.EVALUATING

    def test_ready(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        self.lc.evaluate(s.session_id)
        self.lc.ready(s.session_id)
        assert self.lc.find(s.session_id).state == DecisionState.READY

    def test_activate(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        self.lc.evaluate(s.session_id)
        self.lc.ready(s.session_id)
        self.lc.activate(s.session_id)
        result = self.lc.find(s.session_id)
        assert result.state == DecisionState.ACTIVE
        assert result.start_time is not None

    def test_complete(self):
        s = _full_path(self.lc)
        assert s.state == DecisionState.COMPLETED
        assert s.end_time is not None

    def test_archive(self):
        s = _full_path(self.lc)
        sid = s.session_id
        self.lc.archive(sid)
        archived = self.lc.find_archived(sid)
        assert archived is not None
        assert archived.state == DecisionState.ARCHIVED

    def test_full_path_transition_count(self):
        s = _session(self.lc)
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.evaluate(sid)
        self.lc.ready(sid)
        self.lc.activate(sid)
        self.lc.complete(sid)
        s_final = self.lc.find_archived(sid)
        assert s_final.transition_count == 6

    def test_full_path_state_history_length(self):
        s = _session(self.lc)
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.evaluate(sid)
        self.lc.ready(sid)
        self.lc.activate(sid)
        self.lc.complete(sid)
        s_final = self.lc.find_archived(sid)
        # 1 (CREATED) + 6 transitions = 7 records
        assert len(s_final.state_history) == 7


# ===========================================================================
# 4. Invalid transitions
# ===========================================================================

class TestInvalidTransitions:
    def setup_method(self): self.lc = _lc()
    def teardown_method(self): self.lc.stop()

    def test_collect_from_created_raises(self):
        s = _session(self.lc)
        with pytest.raises(DecisionInvalidTransitionError):
            self.lc.collect(s.session_id)

    def test_evaluate_from_created_raises(self):
        s = _session(self.lc)
        with pytest.raises(DecisionInvalidTransitionError):
            self.lc.evaluate(s.session_id)

    def test_complete_from_collecting_raises(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        with pytest.raises(DecisionInvalidTransitionError):
            self.lc.complete(s.session_id)

    def test_activate_from_collecting_raises(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        with pytest.raises(DecisionInvalidTransitionError):
            self.lc.activate(s.session_id)

    def test_archived_session_rejects_transition(self):
        s = _full_path(self.lc)
        sid = s.session_id
        self.lc.archive(sid)
        with pytest.raises(DecisionSessionTerminatedError):
            self.lc.fail(sid)

    def test_invalid_transition_error_fields(self):
        s = _session(self.lc)
        with pytest.raises(DecisionInvalidTransitionError) as exc_info:
            self.lc.collect(s.session_id)
        assert exc_info.value.from_state == DecisionState.CREATED
        assert exc_info.value.to_state   == DecisionState.COLLECTING


# ===========================================================================
# 5. Pause / resume cycle
# ===========================================================================

class TestPauseResume:
    def setup_method(self): self.lc = _lc()
    def teardown_method(self): self.lc.stop()

    def _collecting(self) -> DecisionSession:
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        return self.lc.find(s.session_id)

    def test_pause_from_collecting(self):
        s = self._collecting()
        self.lc.pause(s.session_id)
        assert self.lc.find(s.session_id).state == DecisionState.PAUSED

    def test_pause_from_evaluating(self):
        s = self._collecting()
        self.lc.evaluate(s.session_id)
        self.lc.pause(s.session_id)
        assert self.lc.find(s.session_id).state == DecisionState.PAUSED

    def test_pause_from_ready(self):
        s = self._collecting()
        self.lc.evaluate(s.session_id)
        self.lc.ready(s.session_id)
        self.lc.pause(s.session_id)
        assert self.lc.find(s.session_id).state == DecisionState.PAUSED

    def test_pause_from_active(self):
        s = self._collecting()
        self.lc.evaluate(s.session_id)
        self.lc.ready(s.session_id)
        self.lc.activate(s.session_id)
        self.lc.pause(s.session_id)
        assert self.lc.find(s.session_id).state == DecisionState.PAUSED

    def test_resume_to_resuming(self):
        s = self._collecting()
        self.lc.pause(s.session_id)
        self.lc.resume(s.session_id)
        assert self.lc.find(s.session_id).state == DecisionState.RESUMING

    def test_resume_then_collect(self):
        s = self._collecting()
        self.lc.pause(s.session_id)
        self.lc.resume(s.session_id)
        self.lc.collect(s.session_id)
        assert self.lc.find(s.session_id).state == DecisionState.COLLECTING

    def test_resume_then_evaluate(self):
        s = self._collecting()
        self.lc.evaluate(s.session_id)
        self.lc.pause(s.session_id)
        self.lc.resume(s.session_id)
        self.lc.evaluate(s.session_id)
        assert self.lc.find(s.session_id).state == DecisionState.EVALUATING

    def test_pause_emits_event(self):
        s = self._collecting()
        self.lc.pause(s.session_id)
        evts = self.lc.history().events_for_session(s.session_id)
        types = [e.event_type for e in evts]
        assert DecisionEventType.DECISION_PAUSED in types

    def test_is_paused_true(self):
        s = self._collecting()
        self.lc.pause(s.session_id)
        assert self.lc.find(s.session_id).is_paused

    def test_pause_from_created_raises(self):
        s = _session(self.lc)
        with pytest.raises(DecisionInvalidTransitionError):
            self.lc.pause(s.session_id)


# ===========================================================================
# 6. Failure path
# ===========================================================================

class TestFailurePath:
    def setup_method(self): self.lc = _lc()
    def teardown_method(self): self.lc.stop()

    def test_fail_from_created(self):
        s = _session(self.lc)
        self.lc.fail(s.session_id, reason="rejected")
        r = self.lc.find_archived(s.session_id)
        assert r.state == DecisionState.FAILED

    def test_fail_from_collecting(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        self.lc.fail(s.session_id)
        r = self.lc.find_archived(s.session_id)
        assert r.state == DecisionState.FAILED

    def test_fail_sets_failure_reason(self):
        s = _session(self.lc)
        self.lc.fail(s.session_id, reason="test failure")
        r = self.lc.find_archived(s.session_id)
        assert r.failure_reason == "test failure"

    def test_fail_sets_end_time(self):
        s = _session(self.lc)
        self.lc.fail(s.session_id)
        r = self.lc.find_archived(s.session_id)
        assert r.end_time is not None

    def test_fail_increments_statistics(self):
        s = _session(self.lc)
        self.lc.fail(s.session_id)
        assert self.lc.statistics().sessions_failed == 1

    def test_fail_emits_event(self):
        s = _session(self.lc)
        self.lc.fail(s.session_id, reason="test")
        evts = self.lc.history().events_by_type(DecisionEventType.DECISION_FAILED.value)
        assert len(evts) >= 1
        assert evts[-1].payload.get("reason") == "test"

    def test_archive_failed_session(self):
        s = _session(self.lc)
        self.lc.fail(s.session_id)
        sid = s.session_id
        self.lc.archive(sid)
        r = self.lc.find_archived(sid)
        assert r.state == DecisionState.ARCHIVED

    def test_fail_then_complete_raises(self):
        s = _session(self.lc)
        self.lc.fail(s.session_id)
        with pytest.raises(DecisionInvalidTransitionError):
            self.lc.complete(s.session_id)


# ===========================================================================
# 7. Query methods
# ===========================================================================

class TestQueryMethods:
    def setup_method(self): self.lc = _lc()
    def teardown_method(self): self.lc.stop()

    def test_find_active(self):
        s = _session(self.lc)
        found = self.lc.find(s.session_id)
        assert found is not None
        assert found.session_id == s.session_id

    def test_find_none_for_missing(self):
        assert self.lc.find("nonexistent") is None

    def test_get_raises_for_missing(self):
        with pytest.raises(DecisionSessionNotFoundError):
            self.lc.get("nonexistent")

    def test_all_active(self):
        s1 = _session(self.lc)
        s2 = _session(self.lc)
        active = self.lc.all_active()
        ids = {s.session_id for s in active}
        assert s1.session_id in ids
        assert s2.session_id in ids

    def test_by_state(self):
        s1 = _session(self.lc)
        s2 = _session(self.lc)
        self.lc.initialize(s2.session_id)
        created_list = self.lc.by_state(DecisionState.CREATED)
        ids = {s.session_id for s in created_list}
        assert s1.session_id in ids
        assert s2.session_id not in ids

    def test_by_decision(self):
        s1 = self.lc.create("shared-decision")
        s2 = self.lc.create("shared-decision")
        sessions = self.lc.by_decision("shared-decision")
        ids = {s.session_id for s in sessions}
        assert s1.session_id in ids
        assert s2.session_id in ids

    def test_find_archived(self):
        s = _full_path(self.lc)
        sid = s.session_id
        self.lc.archive(sid)
        found = self.lc.find_archived(sid)
        assert found is not None
        assert found.state == DecisionState.ARCHIVED

    def test_not_running_raises_on_get(self):
        lc = DecisionLifecycle()
        with pytest.raises(DecisionLifecycleNotRunningError):
            lc.get("x")

    def test_not_running_raises_on_find(self):
        lc = DecisionLifecycle()
        with pytest.raises(DecisionLifecycleNotRunningError):
            lc.find("x")


# ===========================================================================
# 8. Validation
# ===========================================================================

class TestValidation:
    def setup_method(self): self.lc = _lc()
    def teardown_method(self): self.lc.stop()

    def test_validate_new_session_passes(self):
        s = _session(self.lc)
        result = self.lc.validate(s.session_id)
        assert result.is_valid

    def test_validate_all_five_checks(self):
        s = _session(self.lc)
        result = self.lc.validate(s.session_id)
        codes = {c.code for c in result.checks}
        for code in DecisionValidationCode:
            assert code in codes

    def test_validate_after_transitions(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        result = self.lc.validate(s.session_id)
        assert result.is_valid

    def test_validate_missing_session_raises(self):
        with pytest.raises(DecisionSessionNotFoundError):
            self.lc.validate("nonexistent")

    def test_validate_passed_count(self):
        s = _session(self.lc)
        result = self.lc.validate(s.session_id)
        assert result.passed_count == 5

    def test_validate_failed_count_zero_on_valid(self):
        s = _session(self.lc)
        result = self.lc.validate(s.session_id)
        assert result.failed_count == 0


class TestValidatorUnit:
    def setup_method(self):
        self.validator = DecisionValidator()
        self.factory   = DecisionFactory()

    def test_valid_new_session(self):
        s = self.factory.create("d-1")
        r = self.validator.validate(s)
        assert r.is_valid

    def test_empty_session_id_fails(self):
        s = self.factory.create("d-1", session_id=" ")
        # Manually corrupt session_id via private attribute for test coverage
        s._session_id = "  "
        r = self.validator.validate(s)
        # identifier consistency should fail
        assert DecisionValidationCode.IDENTIFIER_CONSISTENCY in r.failed_checks

    def test_empty_decision_id_fails(self):
        s = self.factory.create("d-1")
        s._decision_id = "  "
        r = self.validator.validate(s)
        assert DecisionValidationCode.IDENTIFIER_CONSISTENCY in r.failed_checks

    def test_transition_validity_check_passes(self):
        s = self.factory.create("d-1")
        s.transition_to(DecisionState.INITIALIZING)
        s.transition_to(DecisionState.COLLECTING)
        r = self.validator.validate(s)
        assert r.is_valid

    def test_validate_transition_helper_valid(self):
        s = self.factory.create("d-1")
        ok, msg = self.validator.validate_transition(s, DecisionState.INITIALIZING)
        assert ok
        assert msg == ""

    def test_validate_transition_helper_invalid(self):
        s = self.factory.create("d-1")
        ok, msg = self.validator.validate_transition(s, DecisionState.COLLECTING)
        assert not ok
        assert msg

    def test_timestamp_consistency_passes(self):
        s = self.factory.create("d-1")
        s.transition_to(DecisionState.INITIALIZING)
        r = self.validator.validate(s)
        assert DecisionValidationCode.TIMESTAMP_CONSISTENCY not in r.failed_checks

    def test_history_integrity_passes(self):
        s = self.factory.create("d-1")
        r = self.validator.validate(s)
        assert DecisionValidationCode.HISTORY_INTEGRITY not in r.failed_checks


# ===========================================================================
# 9. Registry unit tests
# ===========================================================================

class TestRegistry:
    def setup_method(self):
        self.registry = DecisionRegistry(max_active_sessions=10, max_archived_sessions=5)
        self.factory  = DecisionFactory()

    def _make(self) -> DecisionSession:
        return self.factory.create(f"d-{uuid.uuid4()}")

    def test_add_and_find(self):
        s = self._make()
        self.registry.add(s)
        found = self.registry.find(s.session_id)
        assert found is s

    def test_add_duplicate_raises(self):
        s = self._make()
        self.registry.add(s)
        with pytest.raises(DecisionSessionAlreadyExistsError):
            self.registry.add(s)

    def test_get_raises_when_missing(self):
        with pytest.raises(DecisionSessionNotFoundError):
            self.registry.get("nonexistent")

    def test_find_returns_none_when_missing(self):
        assert self.registry.find("nonexistent") is None

    def test_move_to_archive(self):
        s = self._make()
        self.registry.add(s)
        self.registry.move_to_archive(s.session_id)
        assert self.registry.find(s.session_id) is None
        assert self.registry.find_archived(s.session_id) is s

    def test_by_state(self):
        s1 = self._make()
        s2 = self._make()
        self.registry.add(s1)
        self.registry.add(s2)
        s1.transition_to(DecisionState.INITIALIZING)
        result = self.registry.by_state(DecisionState.INITIALIZING)
        assert s1 in result
        assert s2 not in result

    def test_by_decision(self):
        s1 = self.factory.create("shared")
        s2 = self.factory.create("shared")
        self.registry.add(s1)
        self.registry.add(s2)
        sessions = self.registry.by_decision("shared")
        assert len(sessions) == 2

    def test_active_count(self):
        for _ in range(3):
            s = self._make()
            self.registry.add(s)
        assert self.registry.active_count() == 3

    def test_is_active(self):
        s = self._make()
        self.registry.add(s)
        assert self.registry.is_active(s.session_id)

    def test_clear(self):
        s = self._make()
        self.registry.add(s)
        self.registry.clear()
        assert self.registry.active_count() == 0

    def test_archive_bounded_eviction(self):
        # max_archived = 5, add 7 → only 5 retained
        for _ in range(7):
            s = self._make()
            self.registry.add(s)
            self.registry.move_to_archive(s.session_id)
        assert self.registry.archived_count() <= 5

    def test_cap_raises(self):
        reg = DecisionRegistry(max_active_sessions=2)
        reg.add(self.factory.create("d1"))
        reg.add(self.factory.create("d2"))
        with pytest.raises(RuntimeError):
            reg.add(self.factory.create("d3"))

    def test_find_any(self):
        s = self._make()
        self.registry.add(s)
        self.registry.move_to_archive(s.session_id)
        assert self.registry.find_any(s.session_id) is s


# ===========================================================================
# 10. Factory
# ===========================================================================

class TestFactory:
    def setup_method(self):
        self.factory = DecisionFactory()

    def test_create(self):
        s = self.factory.create("d-1")
        assert isinstance(s, DecisionSession)
        assert s.decision_id == "d-1"
        assert s.state == DecisionState.CREATED

    def test_create_with_id(self):
        s = self.factory.create_with_id(decision_id="d-2", workflow_id="wf-1")
        assert s.workflow_id == "wf-1"

    def test_create_defaults(self):
        s = self.factory.create("d-1")
        assert s.decision_scope    == DecisionScope.ORDER
        assert s.decision_type     == DecisionType.ORDER
        assert s.decision_priority == DecisionPriority.MEDIUM
        assert s.decision_trigger  == DecisionTrigger.AUTOMATIC

    def test_create_custom_scope(self):
        s = self.factory.create("d-1", decision_scope=DecisionScope.PORTFOLIO)
        assert s.decision_scope == DecisionScope.PORTFOLIO

    def test_create_unique_ids(self):
        ids = {self.factory.create("d").session_id for _ in range(100)}
        assert len(ids) == 100


# ===========================================================================
# 11. History
# ===========================================================================

class TestHistory:
    def setup_method(self):
        self.history = DecisionHistory(max_events=10, max_transitions=10)

    def test_record_event(self):
        e = make_decision_created("s1", "d1")
        self.history.record_event(e)
        assert self.history.event_count() == 1

    def test_events_for_session(self):
        e = make_decision_created("s-specific", "d1")
        self.history.record_event(e)
        evts = self.history.events_for_session("s-specific")
        assert len(evts) == 1

    def test_events_for_decision(self):
        e = make_decision_created("s1", "d-specific")
        self.history.record_event(e)
        evts = self.history.events_for_decision("d-specific")
        assert len(evts) == 1

    def test_events_by_type(self):
        self.history.record_event(make_decision_created("s1", "d1"))
        self.history.record_event(make_decision_completed("s1", "d1"))
        created = self.history.events_by_type(DecisionEventType.DECISION_CREATED.value)
        assert len(created) == 1

    def test_record_transition(self):
        t = make_transition("s1", DecisionState.CREATED, DecisionState.INITIALIZING)
        self.history.record_transition(t)
        assert self.history.transition_count() == 1

    def test_transitions_for_session(self):
        t = make_transition("s-mine", DecisionState.CREATED, DecisionState.INITIALIZING)
        self.history.record_transition(t)
        result = self.history.transitions_for_session("s-mine")
        assert len(result) == 1

    def test_bounded_events(self):
        for _ in range(15):
            self.history.record_event(make_decision_created("s", "d"))
        assert self.history.event_count() == 10

    def test_latest_event(self):
        e = make_decision_created("s1", "d1")
        self.history.record_event(e)
        assert self.history.latest_event() is e

    def test_latest_event_none(self):
        assert self.history.latest_event() is None

    def test_clear(self):
        self.history.record_event(make_decision_created("s", "d"))
        self.history.clear()
        assert self.history.event_count() == 0
        assert self.history.transition_count() == 0


# ===========================================================================
# 12. Statistics
# ===========================================================================

class TestStatisticsUnit:
    def setup_method(self):
        self.stats = DecisionStatistics()

    def test_initial_zero(self):
        assert self.stats.sessions_created   == 0
        assert self.stats.sessions_completed == 0
        assert self.stats.sessions_failed    == 0
        assert self.stats.sessions_archived  == 0
        assert self.stats.transition_count   == 0
        assert self.stats.average_session_duration_s == 0.0

    def test_record_created(self):
        self.stats.record_session_created()
        assert self.stats.sessions_created == 1

    def test_record_completed(self):
        self.stats.record_session_completed(2.0)
        assert self.stats.sessions_completed == 1
        assert self.stats.average_session_duration_s == pytest.approx(2.0)

    def test_record_failed(self):
        self.stats.record_session_failed()
        assert self.stats.sessions_failed == 1

    def test_record_archived(self):
        self.stats.record_session_archived()
        assert self.stats.sessions_archived == 1

    def test_record_transition(self):
        self.stats.record_transition()
        self.stats.record_transition()
        assert self.stats.transition_count == 2

    def test_ema_duration(self):
        self.stats.record_session_completed(10.0)
        self.stats.record_session_completed(20.0)
        avg = self.stats.average_session_duration_s
        assert 10.0 < avg < 20.0

    def test_reset(self):
        self.stats.record_session_created()
        self.stats.record_session_completed(1.0)
        self.stats.reset()
        assert self.stats.sessions_created == 0
        assert self.stats.sessions_completed == 0

    def test_snapshot_keys(self):
        d = self.stats.snapshot()
        assert "sessions_created" in d
        assert "sessions_completed" in d
        assert "sessions_failed" in d
        assert "sessions_archived" in d
        assert "average_session_duration_s" in d
        assert "transition_count" in d

    def test_thread_safety(self):
        errors = []
        def inc():
            try:
                for _ in range(100):
                    self.stats.record_session_created()
                    self.stats.record_transition()
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=inc) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert self.stats.sessions_created  == 1000
        assert self.stats.transition_count  == 1000


class TestStatisticsIntegration:
    def setup_method(self): self.lc = _lc()
    def teardown_method(self): self.lc.stop()

    def test_full_path_statistics(self):
        _full_path(self.lc)
        st = self.lc.statistics()
        assert st.sessions_created   == 1
        assert st.sessions_completed == 1
        assert st.sessions_archived  == 0
        assert st.transition_count   >= 6

    def test_failure_path_statistics(self):
        s = _session(self.lc)
        self.lc.fail(s.session_id)
        st = self.lc.statistics()
        assert st.sessions_failed == 1

    def test_archive_statistics(self):
        s = _full_path(self.lc)
        self.lc.archive(s.session_id)
        st = self.lc.statistics()
        assert st.sessions_archived == 1


# ===========================================================================
# 13. Events
# ===========================================================================

class TestEvents:
    def setup_method(self): self.lc = _lc()
    def teardown_method(self): self.lc.stop()

    def _all_event_types(self) -> list:
        # Happy path (create/initialize/start/pause/resume/complete/archive)
        s = _session(self.lc)
        sid = s.session_id
        self.lc.initialize(sid)
        self.lc.collect(sid)
        self.lc.pause(sid)
        self.lc.resume(sid)
        self.lc.collect(sid)
        self.lc.evaluate(sid)
        self.lc.ready(sid)
        self.lc.activate(sid)
        self.lc.complete(sid)
        self.lc.archive(sid)
        # Failure path (provides DECISION_FAILED)
        s2 = _session(self.lc)
        self.lc.fail(s2.session_id)
        # Return events from all sessions
        hist = self.lc.history()
        return list(hist.events_for_session(sid)) + list(hist.events_for_session(s2.session_id))

    def test_decision_created_emitted(self):
        s = _session(self.lc)
        evts = self.lc.history().events_for_session(s.session_id)
        assert any(e.event_type == DecisionEventType.DECISION_CREATED for e in evts)

    def test_decision_initialized_emitted(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        evts = self.lc.history().events_for_session(s.session_id)
        assert any(e.event_type == DecisionEventType.DECISION_INITIALIZED for e in evts)

    def test_decision_started_emitted(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        self.lc.evaluate(s.session_id)
        self.lc.ready(s.session_id)
        self.lc.activate(s.session_id)
        evts = self.lc.history().events_for_session(s.session_id)
        assert any(e.event_type == DecisionEventType.DECISION_STARTED for e in evts)

    def test_decision_paused_emitted(self):
        s = _session(self.lc)
        self.lc.initialize(s.session_id)
        self.lc.collect(s.session_id)
        self.lc.pause(s.session_id)
        evts = self.lc.history().events_for_session(s.session_id)
        assert any(e.event_type == DecisionEventType.DECISION_PAUSED for e in evts)

    def test_decision_completed_emitted(self):
        s = _full_path(self.lc)
        evts = self.lc.history().events_for_session(s.session_id)
        assert any(e.event_type == DecisionEventType.DECISION_COMPLETED for e in evts)

    def test_decision_failed_emitted(self):
        s = _session(self.lc)
        self.lc.fail(s.session_id)
        evts = self.lc.history().events_for_session(s.session_id)
        assert any(e.event_type == DecisionEventType.DECISION_FAILED for e in evts)

    def test_decision_archived_emitted(self):
        s = _full_path(self.lc)
        self.lc.archive(s.session_id)
        evts = self.lc.history().events_for_session(s.session_id)
        assert any(e.event_type == DecisionEventType.DECISION_ARCHIVED for e in evts)

    def test_all_eight_event_types(self):
        evts = self._all_event_types()
        found = {e.event_type for e in evts}
        for et in DecisionEventType:
            assert et in found, f"Missing event type: {et}"

    def test_event_is_frozen(self):
        e = make_decision_created("s", "d")
        with pytest.raises(Exception):
            e.event_id = "mutate"  # type: ignore[misc]


class TestEventFactories:
    def test_make_decision_created(self):
        e = make_decision_created("s1", "d1")
        assert e.event_type == DecisionEventType.DECISION_CREATED
        assert e.session_id == "s1"
        assert e.decision_id == "d1"
        assert e.state == DecisionState.CREATED

    def test_make_decision_initialized(self):
        e = make_decision_initialized("s", "d")
        assert e.event_type == DecisionEventType.DECISION_INITIALIZED
        assert e.state == DecisionState.INITIALIZING

    def test_make_decision_started(self):
        e = make_decision_started("s", "d")
        assert e.event_type == DecisionEventType.DECISION_STARTED
        assert e.state == DecisionState.ACTIVE

    def test_make_decision_paused(self):
        e = make_decision_paused("s", "d", reason="market closed")
        assert e.event_type == DecisionEventType.DECISION_PAUSED
        assert e.payload["reason"] == "market closed"

    def test_make_decision_resumed(self):
        e = make_decision_resumed("s", "d", resumed_to=DecisionState.COLLECTING)
        assert e.event_type == DecisionEventType.DECISION_RESUMED
        assert e.payload["resumed_to"] == "collecting"

    def test_make_decision_completed(self):
        e = make_decision_completed("s", "d", duration_s=5.0)
        assert e.event_type == DecisionEventType.DECISION_COMPLETED
        assert e.payload["duration_s"] == 5.0

    def test_make_decision_failed(self):
        e = make_decision_failed("s", "d", reason="error")
        assert e.event_type == DecisionEventType.DECISION_FAILED
        assert e.payload["reason"] == "error"

    def test_make_decision_archived(self):
        e = make_decision_archived("s", "d")
        assert e.event_type == DecisionEventType.DECISION_ARCHIVED


# ===========================================================================
# 14. Context and Metadata value objects
# ===========================================================================

class TestContextMetadata:
    def setup_method(self):
        self.factory = DecisionFactory()

    def test_context_from_session(self):
        s = self.factory.create("d-1")
        ctx = DecisionContext.from_session(s)
        assert ctx.session_id  == s.session_id
        assert ctx.decision_id == s.decision_id
        assert ctx.context_id  != ""

    def test_context_is_frozen(self):
        s = self.factory.create("d-1")
        ctx = DecisionContext.from_session(s)
        with pytest.raises(Exception):
            ctx.session_id = "mutate"  # type: ignore[misc]

    def test_context_with_extra_metadata(self):
        s = self.factory.create("d-1")
        ctx = DecisionContext.from_session(s, extra_metadata={"key": "val"})
        assert ctx.context_metadata.get("key") == "val"

    def test_metadata_create(self):
        m = DecisionMetadata.create(
            session_id  = "s-1",
            decision_id = "d-1",
            tags        = ("urgent", "order"),
            labels      = {"env": "prod"},
        )
        assert m.has_tag("urgent")
        assert m.get_label("env") == "prod"
        assert m.metadata_id

    def test_metadata_is_frozen(self):
        m = DecisionMetadata.create(session_id="s", decision_id="d")
        with pytest.raises(Exception):
            m.session_id = "mutate"  # type: ignore[misc]

    def test_metadata_to_dict(self):
        m = DecisionMetadata.create(session_id="s", decision_id="d")
        d = m.to_dict()
        assert "metadata_id" in d
        assert "session_id" in d
        assert "decision_id" in d


# ===========================================================================
# 15. State machine unit tests
# ===========================================================================

class TestStateMachine:
    def test_can_transition_valid(self):
        assert can_transition(DecisionState.CREATED, DecisionState.INITIALIZING)

    def test_can_transition_invalid(self):
        assert not can_transition(DecisionState.CREATED, DecisionState.COLLECTING)

    def test_all_states_in_machine(self):
        for state in DecisionState:
            # Every state must appear in VALID_TRANSITIONS (even if value is frozenset())
            assert state in VALID_TRANSITIONS

    def test_archived_has_no_outgoing(self):
        assert len(VALID_TRANSITIONS[DecisionState.ARCHIVED]) == 0

    def test_active_states_not_terminal(self):
        for s in ACTIVE_STATES:
            assert s not in TERMINAL_STATES

    def test_terminal_states_not_active(self):
        for s in TERMINAL_STATES:
            assert s not in ACTIVE_STATES

    def test_immutable_is_archived_only(self):
        assert IMMUTABLE_STATES == frozenset({DecisionState.ARCHIVED})

    def test_all_11_states_defined(self):
        assert len(list(DecisionState)) == 11

    def test_make_transition(self):
        t = make_transition("s1", DecisionState.CREATED, DecisionState.INITIALIZING)
        assert t.session_id  == "s1"
        assert t.from_state  == DecisionState.CREATED
        assert t.to_state    == DecisionState.INITIALIZING
        assert t.transition_id

    def test_transition_is_frozen(self):
        t = make_transition("s", DecisionState.CREATED, DecisionState.INITIALIZING)
        with pytest.raises(Exception):
            t.session_id = "mutate"  # type: ignore[misc]


# ===========================================================================
# 16. Event listeners
# ===========================================================================

class TestListeners:
    def setup_method(self): self.lc = _lc()
    def teardown_method(self): self.lc.stop()

    def test_listener_called_on_create(self):
        received: list[DecisionEvent] = []
        self.lc.add_listener(received.append)
        self.lc.create("d-1")
        assert len(received) >= 1
        assert received[0].event_type == DecisionEventType.DECISION_CREATED

    def test_listener_removed(self):
        received: list[DecisionEvent] = []
        self.lc.add_listener(received.append)
        self.lc.remove_listener(received.append)
        self.lc.create("d-1")
        assert len(received) == 0

    def test_listener_not_added_twice(self):
        received: list[DecisionEvent] = []
        self.lc.add_listener(received.append)
        self.lc.add_listener(received.append)  # duplicate
        self.lc.create("d-1")
        assert len(received) == 1  # only called once

    def test_faulty_listener_does_not_crash(self):
        def bad_listener(e):
            raise RuntimeError("bad listener")
        self.lc.add_listener(bad_listener)
        # Should not raise
        self.lc.create("d-1")


# ===========================================================================
# 17. Concurrency
# ===========================================================================

class TestConcurrency:
    def test_concurrent_creates(self):
        lc = _lc()
        results = []
        errors  = []

        def create_session():
            try:
                s = lc.create(f"d-{uuid.uuid4()}")
                results.append(s)
            except Exception as e:
                errors.append(e)

        try:
            threads = [threading.Thread(target=create_session) for _ in range(50)]
            for t in threads: t.start()
            for t in threads: t.join()
            assert not errors
            assert len(results) == 50
        finally:
            lc.stop()

    def test_concurrent_transitions(self):
        lc = _lc()
        sessions = [lc.create(f"d-{i}") for i in range(20)]
        errors   = []

        def advance(s):
            try:
                lc.initialize(s.session_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=advance, args=(s,)) for s in sessions]
        for t in threads: t.start()
        for t in threads: t.join()
        try:
            assert not errors
        finally:
            lc.stop()

    def test_concurrent_statistics(self):
        stats  = DecisionStatistics()
        errors = []

        def work():
            try:
                for _ in range(100):
                    stats.record_session_created()
                    stats.record_transition()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=work) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
        assert stats.sessions_created == 1000

    def test_concurrent_registry(self):
        reg    = DecisionRegistry()
        fac    = DecisionFactory()
        errors = []

        def ops():
            try:
                s = fac.create(f"d-{uuid.uuid4()}")
                reg.add(s)
                reg.find(s.session_id)
                reg.move_to_archive(s.session_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=ops) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors


# ===========================================================================
# 18. Session domain object
# ===========================================================================

class TestDecisionSession:
    def setup_method(self):
        self.factory = DecisionFactory()

    def test_initial_state_created(self):
        s = self.factory.create("d-1")
        assert s.state == DecisionState.CREATED

    def test_is_active_true(self):
        s = self.factory.create("d-1")
        s.transition_to(DecisionState.INITIALIZING)
        assert s.is_active

    def test_is_terminal_true(self):
        s = self.factory.create("d-1")
        s.transition_to(DecisionState.INITIALIZING)
        s.transition_to(DecisionState.COLLECTING)
        s.transition_to(DecisionState.EVALUATING)
        s.transition_to(DecisionState.READY)
        s.transition_to(DecisionState.ACTIVE)
        s.transition_to(DecisionState.COMPLETED)
        assert s.is_terminal

    def test_is_successful_completed(self):
        s = self.factory.create("d-1")
        s.transition_to(DecisionState.INITIALIZING)
        s.transition_to(DecisionState.COLLECTING)
        s.transition_to(DecisionState.EVALUATING)
        s.transition_to(DecisionState.READY)
        s.transition_to(DecisionState.ACTIVE)
        s.transition_to(DecisionState.COMPLETED)
        assert s.is_successful

    def test_can_transition_to(self):
        s = self.factory.create("d-1")
        assert s.can_transition_to(DecisionState.INITIALIZING)
        assert not s.can_transition_to(DecisionState.COLLECTING)

    def test_start_time_set_on_activate(self):
        s = self.factory.create("d-1")
        assert s.start_time is None
        s.transition_to(DecisionState.INITIALIZING)
        s.transition_to(DecisionState.COLLECTING)
        s.transition_to(DecisionState.EVALUATING)
        s.transition_to(DecisionState.READY)
        s.transition_to(DecisionState.ACTIVE)
        assert s.start_time is not None

    def test_end_time_set_on_complete(self):
        s = self.factory.create("d-1")
        s.transition_to(DecisionState.INITIALIZING)
        s.transition_to(DecisionState.COLLECTING)
        s.transition_to(DecisionState.EVALUATING)
        s.transition_to(DecisionState.READY)
        s.transition_to(DecisionState.ACTIVE)
        s.transition_to(DecisionState.COMPLETED)
        assert s.end_time is not None

    def test_duration_s(self):
        s = self.factory.create("d-1")
        time.sleep(0.01)
        assert s.duration_s >= 0.0

    def test_to_dict(self):
        s = self.factory.create("d-1")
        d = s.to_dict()
        assert d["session_id"] == s.session_id
        assert d["decision_id"] == "d-1"
        assert d["state"] == "created"

    def test_version_increments_on_transition(self):
        s = self.factory.create("d-1")
        initial_version = s.decision_version
        s.transition_to(DecisionState.INITIALIZING)
        assert s.decision_version == initial_version + 1

    def test_repr(self):
        s = self.factory.create("d-1")
        r = repr(s)
        assert "DecisionSession" in r
        assert "d-1" in r


# ===========================================================================
# 19. Regression — interface contracts
# ===========================================================================

class TestRegression:
    def test_lifecycle_has_all_methods(self):
        required = [
            "create", "initialize", "collect", "evaluate", "ready", "activate",
            "pause", "resume", "complete", "fail", "archive",
            "get", "find", "find_archived", "all_active",
            "by_state", "by_decision", "statistics", "history",
            "validate", "add_listener", "remove_listener",
        ]
        for method_name in required:
            assert hasattr(DecisionLifecycle, method_name), f"Missing: {method_name}"

    def test_all_11_states(self):
        states = list(DecisionState)
        assert len(states) == 11
        assert DecisionState.CREATED     in states
        assert DecisionState.INITIALIZING in states
        assert DecisionState.COLLECTING  in states
        assert DecisionState.EVALUATING  in states
        assert DecisionState.READY       in states
        assert DecisionState.ACTIVE      in states
        assert DecisionState.PAUSED      in states
        assert DecisionState.RESUMING    in states
        assert DecisionState.COMPLETED   in states
        assert DecisionState.FAILED      in states
        assert DecisionState.ARCHIVED    in states

    def test_all_8_event_types(self):
        assert len(list(DecisionEventType)) == 8

    def test_all_5_validation_codes(self):
        assert len(list(DecisionValidationCode)) == 5

    def test_session_fields_present(self):
        s = DecisionFactory().create("d-1")
        for attr in [
            "session_id", "decision_id", "workflow_id", "portfolio_id",
            "strategy_id", "decision_scope", "decision_type",
            "decision_priority", "decision_trigger", "decision_reason",
            "decision_version", "state", "created_at", "updated_at",
        ]:
            assert hasattr(s, attr), f"Missing attribute: {attr}"

    def test_statistics_has_six_counters(self):
        st = DecisionStatistics()
        assert hasattr(st, "sessions_created")
        assert hasattr(st, "sessions_completed")
        assert hasattr(st, "sessions_failed")
        assert hasattr(st, "sessions_archived")
        assert hasattr(st, "average_session_duration_s")
        assert hasattr(st, "transition_count")

    def test_exception_hierarchy(self):
        for exc_cls in [
            DecisionSessionNotFoundError,
            DecisionInvalidTransitionError,
            DecisionLifecycleNotRunningError,
            DecisionSessionAlreadyExistsError,
            DecisionSessionTerminatedError,
        ]:
            assert issubclass(exc_cls, DecisionLifecycleError)

    def test_valid_transitions_has_all_states(self):
        for state in DecisionState:
            assert state in VALID_TRANSITIONS

    def test_decision_type_values(self):
        values = {dt.value for dt in DecisionType}
        assert "order" in values
        assert "risk" in values
        assert "rebalance" in values

    def test_decision_priority_ordering(self):
        assert DecisionPriority.CRITICAL < DecisionPriority.HIGH
        assert DecisionPriority.HIGH     < DecisionPriority.MEDIUM
        assert DecisionPriority.MEDIUM   < DecisionPriority.LOW

    def test_decision_scope_values(self):
        scopes = {ds.value for ds in DecisionScope}
        assert "order" in scopes
        assert "portfolio" in scopes
        assert "strategy" in scopes
