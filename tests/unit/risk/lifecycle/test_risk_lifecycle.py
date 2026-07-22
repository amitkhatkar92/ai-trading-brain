"""
test_risk_lifecycle.py — tests/unit/risk/lifecycle
====================================================
Comprehensive test suite for the Risk Lifecycle subsystem (C11 M1).

Sections
--------
1.  Constants
2.  Exceptions
3.  State machine (can_transition)
4.  RiskStateRecord
5.  RiskTransition
6.  RiskContext
7.  RiskMetadata
8.  RiskSession
9.  RiskEvents (11 factory functions)
10. RiskHistory
11. RiskStatistics
12. RiskRegistry
13. RiskFactory
14. RiskValidation (5 checks)
15. RiskLifecycle — public API
16. Full lifecycle happy path
17. Pause / resume path
18. Failure path
19. Re-collect path (VALIDATING → COLLECTING)
20. Re-assess path (MONITORING → ASSESSING)
21. Concurrency safety
22. Regression
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import List, Optional

import pytest

from iios.risk.lifecycle import (
    # constants
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    ACTIVE_STATES,
    TERMINAL_STATES,
    IMMUTABLE_STATES,
    SUCCESS_STATES,
    VALID_TRANSITIONS,
    RiskState,
    RiskType,
    RiskScope,
    RiskPriority,
    RiskEventType,
    RiskValidationCode,
    # exceptions
    RiskLifecycleError,
    RiskSessionNotFoundError,
    RiskInvalidTransitionError,
    RiskSessionTerminatedError,
    RiskLifecycleNotRunningError,
    RiskCapacityExceededError,
    RiskValidationError,
    RiskHistoryError,
    RiskRegistryError,
    RiskConfigurationError,
    # objects
    RiskContext,
    RiskEvent,
    RiskFactory,
    RiskHistory,
    RiskMetadata,
    RiskRegistry,
    RiskSession,
    RiskStateRecord,
    RiskStatistics,
    RiskTransition,
    RiskValidationCheckResult,
    RiskValidationResult,
    RiskValidator,
    # primary interface
    RiskLifecycle,
    # helpers
    can_transition,
    make_transition,
    # event factories
    make_risk_created,
    make_risk_initialized,
    make_risk_collected,
    make_risk_validated,
    make_risk_assessment_started,
    make_risk_monitoring_started,
    make_risk_paused,
    make_risk_resumed,
    make_risk_completed,
    make_risk_failed,
    make_risk_archived,
)


# ===========================================================================
# Fixtures / helpers
# ===========================================================================

def _make_session(
    risk_id:      str = "risk-001",
    portfolio_id: str = "pf-001",
    **kwargs,
) -> RiskSession:
    return RiskFactory().create(risk_id, portfolio_id, **kwargs)


def _advance_to(session: RiskSession, target: RiskState) -> RiskSession:
    """Advance a brand-new session to ``target`` state along the happy path."""
    path = {
        RiskState.INITIALIZING: [RiskState.INITIALIZING],
        RiskState.COLLECTING:   [RiskState.INITIALIZING, RiskState.COLLECTING],
        RiskState.VALIDATING:   [RiskState.INITIALIZING, RiskState.COLLECTING, RiskState.VALIDATING],
        RiskState.READY:        [RiskState.INITIALIZING, RiskState.COLLECTING, RiskState.VALIDATING, RiskState.READY],
        RiskState.ASSESSING:    [RiskState.INITIALIZING, RiskState.COLLECTING, RiskState.VALIDATING, RiskState.READY, RiskState.ASSESSING],
        RiskState.MONITORING:   [RiskState.INITIALIZING, RiskState.COLLECTING, RiskState.VALIDATING, RiskState.READY, RiskState.ASSESSING, RiskState.MONITORING],
        RiskState.COMPLETED:    [RiskState.INITIALIZING, RiskState.COLLECTING, RiskState.VALIDATING, RiskState.READY, RiskState.ASSESSING, RiskState.MONITORING, RiskState.COMPLETED],
        RiskState.FAILED:       [RiskState.INITIALIZING, RiskState.FAILED],
    }
    for s in path.get(target, []):
        session.transition_to(s)
    return session


@pytest.fixture
def lc() -> RiskLifecycle:
    """Started RiskLifecycle; stopped in teardown."""
    lifecycle = RiskLifecycle()
    lifecycle.start()
    yield lifecycle
    if lifecycle.lifecycle_state().value == "running":
        lifecycle.stop()


@pytest.fixture
def session_created() -> RiskSession:
    return _make_session()


@pytest.fixture
def stats() -> RiskStatistics:
    return RiskStatistics()


@pytest.fixture
def history() -> RiskHistory:
    return RiskHistory()


@pytest.fixture
def registry() -> RiskRegistry:
    return RiskRegistry()


@pytest.fixture
def validator() -> RiskValidator:
    return RiskValidator()


@pytest.fixture
def factory() -> RiskFactory:
    return RiskFactory()


# ===========================================================================
# 1. Constants
# ===========================================================================

class TestConstants:
    def test_system_id_starts_with_iios(self):
        assert LIFECYCLE_SYSTEM_ID.startswith("iios:")

    def test_version_format(self):
        parts = VERSION.split(".")
        assert len(parts) == 3

    def test_risk_state_count(self):
        assert len(RiskState) == 12

    def test_risk_type_includes_market(self):
        assert RiskType.MARKET.value == "market"

    def test_risk_scope_includes_portfolio(self):
        assert RiskScope.PORTFOLIO.value == "portfolio"

    def test_risk_priority_values(self):
        vals = {p.value for p in RiskPriority}
        assert {"critical", "high", "medium", "low"} == vals

    def test_event_type_count(self):
        assert len(RiskEventType) == 11

    def test_validation_code_count(self):
        assert len(RiskValidationCode) == 5

    def test_active_states_count(self):
        assert len(ACTIVE_STATES) == 8

    def test_terminal_states_count(self):
        assert len(TERMINAL_STATES) == 3

    def test_immutable_states(self):
        assert IMMUTABLE_STATES == frozenset({RiskState.ARCHIVED})

    def test_success_states(self):
        assert RiskState.COMPLETED in SUCCESS_STATES
        assert RiskState.ARCHIVED in SUCCESS_STATES

    def test_active_terminal_disjoint(self):
        assert ACTIVE_STATES.isdisjoint(TERMINAL_STATES)

    def test_all_12_states_covered_by_transitions(self):
        covered = set(VALID_TRANSITIONS.keys())
        assert covered == set(RiskState)


# ===========================================================================
# 2. Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(RiskLifecycleError, IIOSError)

    def test_all_are_subclasses_of_base(self):
        for cls in (
            RiskSessionNotFoundError, RiskInvalidTransitionError,
            RiskSessionTerminatedError, RiskLifecycleNotRunningError,
            RiskCapacityExceededError, RiskValidationError,
            RiskHistoryError, RiskRegistryError, RiskConfigurationError,
        ):
            assert issubclass(cls, RiskLifecycleError)

    def test_error_codes_unique(self):
        codes = {
            RiskLifecycleError.error_code,
            RiskSessionNotFoundError.error_code,
            RiskInvalidTransitionError.error_code,
            RiskSessionTerminatedError.error_code,
            RiskLifecycleNotRunningError.error_code,
            RiskCapacityExceededError.error_code,
            RiskValidationError.error_code,
            RiskHistoryError.error_code,
            RiskRegistryError.error_code,
            RiskConfigurationError.error_code,
        }
        assert len(codes) == 10

    def test_error_codes_rl_prefix(self):
        for cls in (
            RiskLifecycleError, RiskSessionNotFoundError,
            RiskCapacityExceededError, RiskConfigurationError,
        ):
            assert cls.error_code.startswith("RL-"), cls

    def test_session_not_found_stores_id(self):
        err = RiskSessionNotFoundError("sess-1")
        assert err.session_id == "sess-1"

    def test_invalid_transition_stores_states(self):
        err = RiskInvalidTransitionError(RiskState.CREATED, RiskState.MONITORING, "s-1")
        assert err.from_state == RiskState.CREATED
        assert err.to_state == RiskState.MONITORING

    def test_capacity_error_stores_limit(self):
        err = RiskCapacityExceededError(100)
        assert err.limit == 100

    def test_validation_error_stores_failed_checks(self):
        err = RiskValidationError("fail", failed_checks=("a",))
        assert "a" in err.failed_checks


# ===========================================================================
# 3. State machine (can_transition)
# ===========================================================================

class TestStateMachine:
    def test_created_to_initializing(self):
        assert can_transition(RiskState.CREATED, RiskState.INITIALIZING)

    def test_created_to_failed(self):
        assert can_transition(RiskState.CREATED, RiskState.FAILED)

    def test_created_to_monitoring_invalid(self):
        assert not can_transition(RiskState.CREATED, RiskState.MONITORING)

    def test_initializing_to_collecting(self):
        assert can_transition(RiskState.INITIALIZING, RiskState.COLLECTING)

    def test_collecting_to_validating(self):
        assert can_transition(RiskState.COLLECTING, RiskState.VALIDATING)

    def test_validating_to_ready(self):
        assert can_transition(RiskState.VALIDATING, RiskState.READY)

    def test_validating_to_collecting_retry(self):
        assert can_transition(RiskState.VALIDATING, RiskState.COLLECTING)

    def test_ready_to_assessing(self):
        assert can_transition(RiskState.READY, RiskState.ASSESSING)

    def test_ready_to_paused(self):
        assert can_transition(RiskState.READY, RiskState.PAUSED)

    def test_assessing_to_monitoring(self):
        assert can_transition(RiskState.ASSESSING, RiskState.MONITORING)

    def test_assessing_to_completed(self):
        assert can_transition(RiskState.ASSESSING, RiskState.COMPLETED)

    def test_monitoring_to_assessing_reassess(self):
        assert can_transition(RiskState.MONITORING, RiskState.ASSESSING)

    def test_monitoring_to_completed(self):
        assert can_transition(RiskState.MONITORING, RiskState.COMPLETED)

    def test_paused_to_resuming(self):
        assert can_transition(RiskState.PAUSED, RiskState.RESUMING)

    def test_resuming_to_assessing(self):
        assert can_transition(RiskState.RESUMING, RiskState.ASSESSING)

    def test_resuming_to_monitoring(self):
        assert can_transition(RiskState.RESUMING, RiskState.MONITORING)

    def test_resuming_to_ready(self):
        assert can_transition(RiskState.RESUMING, RiskState.READY)

    def test_completed_to_archived(self):
        assert can_transition(RiskState.COMPLETED, RiskState.ARCHIVED)

    def test_failed_to_archived(self):
        assert can_transition(RiskState.FAILED, RiskState.ARCHIVED)

    def test_archived_has_no_valid_transitions(self):
        for target in RiskState:
            assert not can_transition(RiskState.ARCHIVED, target)

    def test_all_states_in_transition_map(self):
        for s in RiskState:
            assert s in VALID_TRANSITIONS

    def test_every_non_archived_can_reach_archived(self):
        """Every non-ARCHIVED state must have a path to ARCHIVED (via FAILED or COMPLETED)."""
        # Quick check: all states allow FAILED except ARCHIVED itself,
        # and FAILED allows ARCHIVED.
        for s in RiskState:
            if s == RiskState.ARCHIVED:
                continue
            reachable = VALID_TRANSITIONS[s]
            can_fail_or_complete = (
                RiskState.FAILED in reachable
                or RiskState.COMPLETED in reachable
                or RiskState.ARCHIVED in reachable
            )
            assert can_fail_or_complete, f"{s.value} cannot reach a terminal"


# ===========================================================================
# 4. RiskStateRecord
# ===========================================================================

class TestRiskStateRecord:
    def test_is_frozen(self):
        r = RiskStateRecord(RiskState.CREATED, 1000.0)
        with pytest.raises((AttributeError, TypeError)):
            r.state = RiskState.FAILED  # type: ignore

    def test_to_dict(self):
        r = RiskStateRecord(RiskState.ASSESSING, 1000.0, actor="test", reason="r")
        d = r.to_dict()
        assert d["state"] == "assessing"
        assert d["actor"] == "test"
        assert d["reason"] == "r"
        assert d["entered_at"] == 1000.0

    def test_version_included(self):
        r = RiskStateRecord(RiskState.CREATED, 1.0)
        assert r.to_dict()["version"] == VERSION


# ===========================================================================
# 5. RiskTransition
# ===========================================================================

class TestRiskTransition:
    def test_make_transition(self):
        t = make_transition("s-1", RiskState.CREATED, RiskState.INITIALIZING, actor="op")
        assert t.from_state == RiskState.CREATED
        assert t.to_state == RiskState.INITIALIZING
        assert t.session_id == "s-1"
        uuid.UUID(t.transition_id)

    def test_is_frozen(self):
        t = make_transition("s", RiskState.CREATED, RiskState.INITIALIZING)
        with pytest.raises((AttributeError, TypeError)):
            t.from_state = RiskState.FAILED  # type: ignore

    def test_to_dict(self):
        t = make_transition("s", RiskState.CREATED, RiskState.INITIALIZING, reason="init")
        d = t.to_dict()
        assert d["from_state"] == "created"
        assert d["to_state"] == "initializing"
        assert d["reason"] == "init"
        assert "transition_id" in d
        assert "transitioned_at" in d


# ===========================================================================
# 6. RiskContext
# ===========================================================================

class TestRiskContext:
    def test_create(self):
        ctx = RiskContext.create("r-1", "pf-1")
        assert ctx.risk_id == "r-1"
        assert ctx.portfolio_id == "pf-1"
        assert ctx.framework_version == VERSION

    def test_is_frozen(self):
        ctx = RiskContext.create("r-1", "pf-1")
        with pytest.raises((AttributeError, TypeError)):
            ctx.risk_id = "x"  # type: ignore

    def test_metadata_is_copied(self):
        meta = {"k": "v"}
        ctx  = RiskContext.create("r", "p", metadata=meta)
        meta["extra"] = "should not appear"
        assert "extra" not in ctx.metadata

    def test_to_dict(self):
        ctx = RiskContext.create(
            "r-1", "pf-1",
            strategy_id="st-1",
            risk_type=RiskType.MARKET,
            risk_scope=RiskScope.STRATEGY,
            risk_priority=RiskPriority.HIGH,
        )
        d = ctx.to_dict()
        assert d["risk_id"] == "r-1"
        assert d["risk_type"] == "market"
        assert d["risk_scope"] == "strategy"
        assert d["risk_priority"] == "high"


# ===========================================================================
# 7. RiskMetadata
# ===========================================================================

class TestRiskMetadata:
    def test_create(self):
        m = RiskMetadata.create(assessment_id="a-1", source="test", notes="n")
        assert m.assessment_id == "a-1"
        assert m.source == "test"
        assert m.notes == "n"

    def test_is_frozen(self):
        m = RiskMetadata.create()
        with pytest.raises((AttributeError, TypeError)):
            m.notes = "x"  # type: ignore

    def test_tags_copied(self):
        tags = {"k": "v"}
        m    = RiskMetadata.create(tags=tags)
        tags["extra"] = "x"
        assert "extra" not in m.tags

    def test_to_dict(self):
        m = RiskMetadata.create(assessment_id="a", source="s", notes="n", tags={"t": "1"})
        d = m.to_dict()
        assert d["assessment_id"] == "a"
        assert d["tags"]["t"] == "1"


# ===========================================================================
# 8. RiskSession
# ===========================================================================

class TestRiskSession:
    def test_initial_state_is_created(self, session_created):
        assert session_created.state == RiskState.CREATED

    def test_session_id_generated(self, session_created):
        uuid.UUID(session_created.session_id)

    def test_session_id_explicit(self):
        s = _make_session(session_id="explicit-id")
        assert s.session_id == "explicit-id"

    def test_initial_history_has_one_entry(self, session_created):
        assert len(session_created.state_history) == 1
        assert session_created.state_history[0].state == RiskState.CREATED

    def test_initial_transitions_empty(self, session_created):
        assert session_created.transitions == []

    def test_is_active_false_in_created(self, session_created):
        assert not session_created.is_active

    def test_is_active_true_in_assessing(self):
        s = _make_session()
        _advance_to(s, RiskState.ASSESSING)
        assert s.is_active

    def test_is_terminal_true_in_failed(self):
        s = _make_session()
        s.transition_to(RiskState.INITIALIZING)
        s.transition_to(RiskState.FAILED)
        assert s.is_terminal

    def test_is_completed_false_initially(self, session_created):
        assert not session_created.is_completed

    def test_is_completed_true_after_completed(self):
        s = _make_session()
        _advance_to(s, RiskState.COMPLETED)
        assert s.is_completed

    def test_is_failed(self):
        s = _make_session()
        s.transition_to(RiskState.INITIALIZING)
        s.transition_to(RiskState.FAILED, reason="crash")
        assert s.is_failed
        assert s.failure_reason == "crash"

    def test_is_archived(self):
        s = _make_session()
        _advance_to(s, RiskState.COMPLETED)
        s.transition_to(RiskState.ARCHIVED)
        assert s.is_archived

    def test_is_paused(self):
        s = _make_session()
        _advance_to(s, RiskState.ASSESSING)
        s.transition_to(RiskState.PAUSED)
        assert s.is_paused

    def test_is_assessing(self):
        s = _make_session()
        _advance_to(s, RiskState.ASSESSING)
        assert s.is_assessing

    def test_is_monitoring(self):
        s = _make_session()
        _advance_to(s, RiskState.MONITORING)
        assert s.is_monitoring

    def test_updated_at_changes_on_transition(self):
        s = _make_session()
        t0 = s.updated_at
        time.sleep(0.001)
        s.transition_to(RiskState.INITIALIZING)
        assert s.updated_at >= t0

    def test_start_time_set_on_first_assessing(self):
        s = _make_session()
        _advance_to(s, RiskState.ASSESSING)
        assert s.start_time is not None

    def test_end_time_set_on_terminal(self):
        s = _make_session()
        _advance_to(s, RiskState.COMPLETED)
        assert s.end_time is not None

    def test_duration_s_positive(self):
        s = _make_session()
        assert s.duration_s >= 0.0

    def test_transitions_count_grows(self):
        s = _make_session()
        s.transition_to(RiskState.INITIALIZING)
        s.transition_to(RiskState.COLLECTING)
        assert len(s.transitions) == 2

    def test_invalid_transition_raises(self, session_created):
        with pytest.raises(RiskInvalidTransitionError):
            session_created.transition_to(RiskState.MONITORING)

    def test_archived_is_immutable(self):
        s = _make_session()
        _advance_to(s, RiskState.COMPLETED)
        s.transition_to(RiskState.ARCHIVED)
        with pytest.raises(RiskSessionTerminatedError):
            s.transition_to(RiskState.FAILED)

    def test_to_dict_keys(self):
        s   = _make_session()
        d   = s.to_dict()
        for key in (
            "session_id", "risk_id", "portfolio_id", "state",
            "created_at", "updated_at", "risk_scope", "risk_type",
            "risk_priority", "risk_version",
        ):
            assert key in d, key

    def test_to_dict_state_value(self):
        s = _make_session()
        assert s.to_dict()["state"] == "created"

    def test_history_returns_copy(self, session_created):
        h1 = session_created.state_history
        h1.append(object())  # type: ignore
        assert len(session_created.state_history) == 1

    def test_transitions_returns_copy(self, session_created):
        t1 = session_created.transitions
        t1.append(object())  # type: ignore
        assert len(session_created.transitions) == 0

    def test_metadata_returns_copy(self):
        s = _make_session(metadata={"k": "v"})
        m = s.metadata
        m["extra"] = "x"
        assert "extra" not in s.metadata

    def test_fields_from_factory(self):
        s = _make_session(
            risk_id="r-42",
            portfolio_id="pf-42",
            assessment_id="a-1",
            workflow_id="wf-1",
            strategy_id="st-1",
            risk_type=RiskType.CREDIT,
            risk_scope=RiskScope.STRATEGY,
            risk_priority=RiskPriority.HIGH,
            risk_version=3,
        )
        assert s.risk_id       == "r-42"
        assert s.assessment_id == "a-1"
        assert s.workflow_id   == "wf-1"
        assert s.strategy_id   == "st-1"
        assert s.risk_type     == RiskType.CREDIT
        assert s.risk_scope    == RiskScope.STRATEGY
        assert s.risk_priority == RiskPriority.HIGH
        assert s.risk_version  == 3


# ===========================================================================
# 9. Events (11 factory functions)
# ===========================================================================

class TestRiskEvents:
    def _check(self, event: RiskEvent, expected_type: RiskEventType, expected_state: RiskState):
        assert isinstance(event, RiskEvent)
        assert event.event_type == expected_type
        assert event.state == expected_state
        uuid.UUID(event.event_id)
        assert event.occurred_at > 0
        assert event.framework_version == VERSION

    def test_make_risk_created(self):
        e = make_risk_created("s-1", "r-1", "pf-1")
        self._check(e, RiskEventType.RISK_CREATED, RiskState.CREATED)

    def test_make_risk_initialized(self):
        e = make_risk_initialized("s", "r", "p")
        self._check(e, RiskEventType.RISK_INITIALIZED, RiskState.INITIALIZING)

    def test_make_risk_collected(self):
        e = make_risk_collected("s", "r", "p")
        self._check(e, RiskEventType.RISK_COLLECTED, RiskState.COLLECTING)

    def test_make_risk_validated(self):
        e = make_risk_validated("s", "r", "p")
        self._check(e, RiskEventType.RISK_VALIDATED, RiskState.VALIDATING)

    def test_make_risk_assessment_started(self):
        e = make_risk_assessment_started("s", "r", "p")
        self._check(e, RiskEventType.RISK_ASSESSMENT_STARTED, RiskState.ASSESSING)

    def test_make_risk_monitoring_started(self):
        e = make_risk_monitoring_started("s", "r", "p")
        self._check(e, RiskEventType.RISK_MONITORING_STARTED, RiskState.MONITORING)

    def test_make_risk_paused(self):
        e = make_risk_paused("s", "r", "p")
        self._check(e, RiskEventType.RISK_PAUSED, RiskState.PAUSED)

    def test_make_risk_resumed(self):
        e = make_risk_resumed("s", "r", "p")
        self._check(e, RiskEventType.RISK_RESUMED, RiskState.RESUMING)

    def test_make_risk_completed(self):
        e = make_risk_completed("s", "r", "p")
        self._check(e, RiskEventType.RISK_COMPLETED, RiskState.COMPLETED)

    def test_make_risk_failed(self):
        e = make_risk_failed("s", "r", "p")
        self._check(e, RiskEventType.RISK_FAILED, RiskState.FAILED)

    def test_make_risk_archived(self):
        e = make_risk_archived("s", "r", "p")
        self._check(e, RiskEventType.RISK_ARCHIVED, RiskState.ARCHIVED)

    def test_event_is_frozen(self):
        e = make_risk_created("s", "r", "p")
        with pytest.raises((AttributeError, TypeError)):
            e.event_id = "x"  # type: ignore

    def test_each_event_unique_id(self):
        ids = {make_risk_created("s", "r", "p").event_id for _ in range(20)}
        assert len(ids) == 20

    def test_all_11_event_types_covered(self):
        factories = [
            make_risk_created, make_risk_initialized, make_risk_collected,
            make_risk_validated, make_risk_assessment_started,
            make_risk_monitoring_started, make_risk_paused, make_risk_resumed,
            make_risk_completed, make_risk_failed, make_risk_archived,
        ]
        types = {f("s", "r", "p").event_type for f in factories}
        all_types = set(RiskEventType)
        assert types == all_types

    def test_to_dict(self):
        e = make_risk_created("s-1", "r-1", "pf-1")
        d = e.to_dict()
        for key in ("event_id", "event_type", "session_id", "risk_id",
                    "portfolio_id", "state", "occurred_at"):
            assert key in d

    def test_payload_stored(self):
        e = make_risk_completed("s", "r", "p", payload={"duration": 10.0})
        assert e.payload["duration"] == 10.0


# ===========================================================================
# 10. RiskHistory
# ===========================================================================

class TestRiskHistory:
    def test_initial_empty(self, history):
        assert history.event_count() == 0
        assert history.transition_count() == 0

    def test_record_and_get_event(self, history):
        e = make_risk_created("s", "r", "p")
        history.record_event(e)
        assert history.event_count() == 1
        assert history.events()[0] is e

    def test_latest_event(self, history):
        e1 = make_risk_created("s", "r", "p")
        e2 = make_risk_initialized("s", "r", "p")
        history.record_event(e1)
        history.record_event(e2)
        assert history.latest_event() is e2

    def test_latest_event_none_when_empty(self, history):
        assert history.latest_event() is None

    def test_record_and_get_transition(self, history):
        t = make_transition("s", RiskState.CREATED, RiskState.INITIALIZING)
        history.record_transition(t)
        assert history.transition_count() == 1

    def test_events_for_session(self, history):
        e1 = make_risk_created("s-A", "r", "p")
        e2 = make_risk_created("s-B", "r", "p")
        history.record_event(e1)
        history.record_event(e2)
        assert history.events_for_session("s-A") == [e1]

    def test_events_for_portfolio(self, history):
        e1 = make_risk_created("s", "r", "pf-1")
        e2 = make_risk_created("s", "r", "pf-2")
        history.record_event(e1)
        history.record_event(e2)
        assert history.events_for_portfolio("pf-1") == [e1]

    def test_events_by_type(self, history):
        history.record_event(make_risk_created("s", "r", "p"))
        history.record_event(make_risk_initialized("s", "r", "p"))
        created = history.events_by_type(RiskEventType.RISK_CREATED)
        assert len(created) == 1

    def test_transitions_for_session(self, history):
        t1 = make_transition("s-A", RiskState.CREATED, RiskState.INITIALIZING)
        t2 = make_transition("s-B", RiskState.CREATED, RiskState.INITIALIZING)
        history.record_transition(t1)
        history.record_transition(t2)
        assert history.transitions_for_session("s-A") == [t1]

    def test_bounded_maxlen(self):
        h = RiskHistory(max_events=3)
        for i in range(5):
            h.record_event(make_risk_created(f"s-{i}", "r", "p"))
        assert h.event_count() == 3

    def test_clear(self, history):
        history.record_event(make_risk_created("s", "r", "p"))
        history.record_transition(make_transition("s", RiskState.CREATED, RiskState.INITIALIZING))
        history.clear()
        assert history.event_count() == 0
        assert history.transition_count() == 0


# ===========================================================================
# 11. RiskStatistics
# ===========================================================================

class TestRiskStatistics:
    def test_initial_state(self, stats):
        d = stats.snapshot()
        assert d["risk_sessions_created"]   == 0
        assert d["risk_sessions_completed"] == 0
        assert d["risk_sessions_failed"]    == 0
        assert d["risk_sessions_archived"]  == 0
        assert d["transition_count"]        == 0

    def test_record_created(self, stats):
        stats.record_session_created()
        assert stats.snapshot()["risk_sessions_created"] == 1

    def test_record_completed_with_duration(self, stats):
        stats.record_session_completed(duration_s=60.0)
        d = stats.snapshot()
        assert d["risk_sessions_completed"] == 1
        assert d["average_session_duration_s"] == 60.0

    def test_average_duration_two_samples(self, stats):
        stats.record_session_completed(duration_s=10.0)
        stats.record_session_completed(duration_s=20.0)
        d = stats.snapshot()
        assert d["average_session_duration_s"] == 15.0

    def test_record_failed(self, stats):
        stats.record_session_failed()
        assert stats.snapshot()["risk_sessions_failed"] == 1

    def test_record_archived(self, stats):
        stats.record_session_archived()
        assert stats.snapshot()["risk_sessions_archived"] == 1

    def test_record_transition(self, stats):
        stats.record_transition()
        assert stats.snapshot()["transition_count"] == 1

    def test_uptime_positive(self, stats):
        assert stats.snapshot()["uptime_s"] >= 0.0

    def test_ema_duration(self, stats):
        stats.record_session_completed(duration_s=100.0)
        stats.record_session_completed(duration_s=50.0)
        d = stats.snapshot()
        assert d["ema_session_duration_s"] > 0.0

    def test_reset(self, stats):
        stats.record_session_created()
        stats.record_session_completed(duration_s=5.0)
        stats.reset()
        d = stats.snapshot()
        assert d["risk_sessions_created"]  == 0
        assert d["risk_sessions_completed"] == 0

    def test_avg_zero_with_no_samples(self, stats):
        assert stats.snapshot()["average_session_duration_s"] == 0.0


# ===========================================================================
# 12. RiskRegistry
# ===========================================================================

class TestRiskRegistry:
    def test_add_and_get(self, registry):
        s = _make_session()
        registry.add(s)
        assert registry.get(s.session_id) is s

    def test_add_duplicate_raises(self, registry):
        s = _make_session()
        registry.add(s)
        with pytest.raises(RiskRegistryError):
            registry.add(s)

    def test_capacity_exceeded(self):
        reg = RiskRegistry(max_active_sessions=2)
        for _ in range(2):
            reg.add(_make_session())
        with pytest.raises(RiskCapacityExceededError):
            reg.add(_make_session())

    def test_get_missing_raises(self, registry):
        with pytest.raises(RiskSessionNotFoundError):
            registry.get("nonexistent")

    def test_find_returns_none_when_missing(self, registry):
        assert registry.find("x") is None

    def test_get_active(self, registry):
        s = _make_session()
        registry.add(s)
        assert registry.get_active(s.session_id) is s

    def test_archive(self, registry):
        s = _make_session()
        _advance_to(s, RiskState.COMPLETED)
        registry.add(s)
        registry.archive(s.session_id)
        assert not registry.contains_active(s.session_id)
        assert registry.contains(s.session_id)

    def test_archive_missing_raises(self, registry):
        with pytest.raises(RiskSessionNotFoundError):
            registry.archive("nonexistent")

    def test_active_count(self, registry):
        for _ in range(3):
            registry.add(_make_session())
        assert registry.active_count() == 3

    def test_archived_count(self, registry):
        s = _make_session()
        registry.add(s)
        registry.archive(s.session_id)
        assert registry.archived_count() == 1

    def test_active_sessions(self, registry):
        for _ in range(3):
            registry.add(_make_session())
        assert len(registry.active_sessions()) == 3

    def test_archived_sessions_order(self, registry):
        sessions = [_make_session() for _ in range(3)]
        for s in sessions:
            registry.add(s)
        for s in sessions:
            registry.archive(s.session_id)
        archived = registry.archived_sessions()
        assert [s.session_id for s in archived] == [s.session_id for s in sessions]

    def test_sessions_for_portfolio(self, registry):
        s1 = _make_session(portfolio_id="pf-A")
        s2 = _make_session(portfolio_id="pf-B")
        registry.add(s1)
        registry.add(s2)
        assert len(registry.sessions_for_portfolio("pf-A")) == 1

    def test_sessions_for_risk(self, registry):
        s1 = _make_session(risk_id="r-A")
        s2 = _make_session(risk_id="r-B")
        registry.add(s1)
        registry.add(s2)
        assert len(registry.sessions_for_risk("r-A")) == 1

    def test_sessions_by_state(self, registry):
        s1 = _make_session()
        s2 = _make_session()
        _advance_to(s1, RiskState.ASSESSING)
        registry.add(s1)
        registry.add(s2)
        assessing = registry.sessions_by_state(RiskState.ASSESSING)
        assert s1 in assessing
        assert s2 not in assessing

    def test_contains(self, registry):
        s = _make_session()
        registry.add(s)
        assert registry.contains(s.session_id)
        assert not registry.contains("other")

    def test_clear(self, registry):
        for _ in range(3):
            registry.add(_make_session())
        registry.clear()
        assert registry.active_count() == 0

    def test_eviction_when_archive_full(self):
        reg = RiskRegistry(max_active_sessions=10, max_archived_sessions=2)
        sessions = [_make_session() for _ in range(3)]
        for s in sessions:
            reg.add(s)
        for s in sessions:
            reg.archive(s.session_id)
        # oldest should be evicted
        assert reg.archived_count() == 2


# ===========================================================================
# 13. RiskFactory
# ===========================================================================

class TestRiskFactory:
    def test_create_with_defaults(self, factory):
        s = factory.create("r-1", "pf-1")
        assert s.risk_id      == "r-1"
        assert s.portfolio_id == "pf-1"
        assert s.state        == RiskState.CREATED

    def test_create_with_all_fields(self, factory):
        s = factory.create(
            "r-1", "pf-1",
            assessment_id = "a-1",
            workflow_id   = "wf-1",
            strategy_id   = "st-1",
            risk_scope    = RiskScope.ENTERPRISE,
            risk_type     = RiskType.MARKET,
            risk_priority = RiskPriority.CRITICAL,
            risk_version  = 5,
            metadata      = {"env": "prod"},
        )
        assert s.assessment_id == "a-1"
        assert s.workflow_id   == "wf-1"
        assert s.strategy_id   == "st-1"
        assert s.risk_scope    == RiskScope.ENTERPRISE
        assert s.risk_type     == RiskType.MARKET
        assert s.risk_priority == RiskPriority.CRITICAL
        assert s.risk_version  == 5

    def test_create_empty_risk_id_raises(self, factory):
        with pytest.raises(ValueError):
            factory.create("", "pf-1")

    def test_create_empty_portfolio_id_raises(self, factory):
        with pytest.raises(ValueError):
            factory.create("r-1", "")

    def test_session_id_auto_generated(self, factory):
        s = factory.create("r-1", "pf-1")
        uuid.UUID(s.session_id)

    def test_explicit_session_id(self, factory):
        s = factory.create("r-1", "pf-1", session_id="explicit")
        assert s.session_id == "explicit"


# ===========================================================================
# 14. RiskValidation (5 checks)
# ===========================================================================

class TestRiskValidation:
    def test_fresh_session_passes_all(self, validator):
        s      = _make_session()
        result = validator.validate(s)
        assert result.is_valid
        assert result.passed_count == 5
        assert result.failed_count == 0

    def test_advanced_session_passes(self, validator):
        s = _make_session()
        _advance_to(s, RiskState.ASSESSING)
        result = validator.validate(s)
        assert result.is_valid

    def test_check_result_is_frozen(self, validator):
        result = validator.validate(_make_session())
        chk    = result.checks[0]
        with pytest.raises((AttributeError, TypeError)):
            chk.passed = False  # type: ignore

    def test_identifier_consistency_fails_empty_risk_id(self, validator):
        s   = _make_session()
        s._risk_id = ""  # force invalid
        result = validator.validate(s)
        codes  = [c.code for c in result.failed_checks]
        assert RiskValidationCode.IDENTIFIER_CONSISTENCY in codes

    def test_identifier_consistency_fails_empty_portfolio_id(self, validator):
        s  = _make_session()
        s._portfolio_id = ""  # force invalid
        result = validator.validate(s)
        codes  = [c.code for c in result.failed_checks]
        assert RiskValidationCode.IDENTIFIER_CONSISTENCY in codes

    def test_lifecycle_consistency_passes(self, validator):
        s = _make_session()
        result = validator.validate(s)
        lc_check = next(c for c in result.checks
                        if c.code == RiskValidationCode.LIFECYCLE_CONSISTENCY)
        assert lc_check.passed

    def test_transition_validity_created_no_transitions(self, validator):
        s  = _make_session()
        result = validator.validate(s)
        tv = next(c for c in result.checks
                  if c.code == RiskValidationCode.TRANSITION_VALIDITY)
        assert tv.passed

    def test_transition_validity_fails_mismatched_last_target(self, validator):
        s  = _make_session()
        s.transition_to(RiskState.INITIALIZING)
        # Corrupt state to mismatch
        s._state = RiskState.COLLECTING  # type: ignore
        result = validator.validate(s)
        tv = next(c for c in result.checks
                  if c.code == RiskValidationCode.TRANSITION_VALIDITY)
        assert not tv.passed

    def test_timestamp_consistency_passes(self, validator):
        s = _make_session()
        result = validator.validate(s)
        ts = next(c for c in result.checks
                  if c.code == RiskValidationCode.TIMESTAMP_CONSISTENCY)
        assert ts.passed

    def test_timestamp_consistency_fails_if_updated_before_created(self, validator):
        s = _make_session()
        s._updated_at = s._created_at - 1.0  # type: ignore
        result = validator.validate(s)
        ts = next(c for c in result.checks
                  if c.code == RiskValidationCode.TIMESTAMP_CONSISTENCY)
        assert not ts.passed

    def test_history_integrity_passes(self, validator):
        s = _make_session()
        result = validator.validate(s)
        hi = next(c for c in result.checks
                  if c.code == RiskValidationCode.HISTORY_INTEGRITY)
        assert hi.passed

    def test_history_integrity_fails_empty_history(self, validator):
        s = _make_session()
        s._state_history.clear()  # type: ignore
        result = validator.validate(s)
        hi = next(c for c in result.checks
                  if c.code == RiskValidationCode.HISTORY_INTEGRITY)
        assert not hi.passed

    def test_error_messages_populated_on_failure(self, validator):
        s = _make_session()
        s._risk_id = ""  # type: ignore
        result = validator.validate(s)
        assert len(result.error_messages) >= 1


# ===========================================================================
# 15. RiskLifecycle — public API
# ===========================================================================

class TestRiskLifecycle:
    def test_start_and_stop(self):
        lc = RiskLifecycle()
        lc.start()
        assert lc.lifecycle_state().value == "running"
        lc.stop()
        assert lc.lifecycle_state().value == "stopped"

    def test_create_requires_running(self):
        lc = RiskLifecycle()
        with pytest.raises(RiskLifecycleNotRunningError):
            lc.create("r", "pf")

    def test_create_returns_session(self, lc):
        s = lc.create("r-1", "pf-1")
        assert isinstance(s, RiskSession)
        assert s.state == RiskState.CREATED

    def test_create_increments_statistics(self, lc):
        lc.create("r-1", "pf-1")
        assert lc.statistics()["risk_sessions_created"] == 1

    def test_create_emits_created_event(self, lc):
        events: List[RiskEvent] = []
        lc.add_listener(events.append)
        lc.create("r-1", "pf-1")
        types = [e.event_type for e in events]
        assert RiskEventType.RISK_CREATED in types

    def test_initialize(self, lc):
        s = lc.create("r-1", "pf-1")
        lc.initialize(s.session_id)
        assert s.state == RiskState.INITIALIZING

    def test_collect(self, lc):
        s = lc.create("r-1", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        assert s.state == RiskState.COLLECTING

    def test_validate_session(self, lc):
        s = lc.create("r-1", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        assert s.state == RiskState.VALIDATING

    def test_mark_ready(self, lc):
        s = lc.create("r-1", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        assert s.state == RiskState.READY

    def test_start_assessment(self, lc):
        s = lc.create("r-1", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        assert s.state == RiskState.ASSESSING

    def test_start_monitoring(self, lc):
        s = lc.create("r-1", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.start_monitoring(s.session_id)
        assert s.state == RiskState.MONITORING

    def test_complete(self, lc):
        s = lc.create("r-1", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.complete(s.session_id)
        assert s.state == RiskState.COMPLETED
        assert lc.statistics()["risk_sessions_completed"] == 1

    def test_fail(self, lc):
        s = lc.create("r-1", "pf-1")
        lc.fail(s.session_id, reason="test failure")
        assert s.state == RiskState.FAILED
        assert lc.statistics()["risk_sessions_failed"] == 1

    def test_archive(self, lc):
        s = lc.create("r-1", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.complete(s.session_id)
        lc.archive(s.session_id)
        assert s.state == RiskState.ARCHIVED
        assert lc.statistics()["risk_sessions_archived"] == 1

    def test_validate_structure(self, lc):
        s = lc.create("r-1", "pf-1")
        result = lc.validate(s.session_id)
        assert result.is_valid

    def test_get(self, lc):
        s = lc.create("r-1", "pf-1")
        assert lc.get(s.session_id) is s

    def test_find_missing_returns_none(self, lc):
        assert lc.find("nonexistent") is None

    def test_active_sessions(self, lc):
        lc.create("r-1", "pf-1")
        lc.create("r-2", "pf-2")
        assert len(lc.active_sessions()) == 2

    def test_sessions_for_portfolio(self, lc):
        lc.create("r-1", "pf-A")
        lc.create("r-2", "pf-B")
        pf_a = lc.sessions_for_portfolio("pf-A")
        assert len(pf_a) == 1

    def test_sessions_by_state(self, lc):
        s1 = lc.create("r-1", "pf-1")
        s2 = lc.create("r-2", "pf-2")
        lc.initialize(s1.session_id)
        created = lc.sessions_by_state(RiskState.CREATED)
        assert s2 in created
        assert s1 not in created

    def test_add_and_remove_listener(self, lc):
        received: List[RiskEvent] = []
        listener = received.append   # store to preserve identity
        lc.add_listener(listener)
        lc.create("r-1", "pf-1")
        assert len(received) > 0
        lc.remove_listener(listener)
        before = len(received)
        lc.create("r-2", "pf-2")
        assert len(received) == before

    def test_listener_not_duplicated(self, lc):
        received: List[RiskEvent] = []
        listener = received.append   # store to preserve identity
        lc.add_listener(listener)
        lc.add_listener(listener)  # second add — no-op
        lc.create("r-1", "pf-1")
        assert received.count(received[0]) == 1

    def test_history_object_accessible(self, lc):
        assert isinstance(lc.history(), RiskHistory)

    def test_statistics_returns_dict(self, lc):
        d = lc.statistics()
        assert "risk_sessions_created" in d

    def test_create_session_not_found_raises(self, lc):
        with pytest.raises(RiskSessionNotFoundError):
            lc.initialize("nonexistent")

    def test_transition_count_tracked(self, lc):
        s = lc.create("r-1", "pf-1")
        lc.initialize(s.session_id)
        assert lc.statistics()["transition_count"] == 1


# ===========================================================================
# 16. Full lifecycle happy path
# ===========================================================================

class TestFullLifecyclePath:
    def test_complete_happy_path(self, lc):
        s = lc.create("r-happy", "pf-happy")
        assert s.state == RiskState.CREATED

        lc.initialize(s.session_id)
        assert s.state == RiskState.INITIALIZING

        lc.collect(s.session_id)
        assert s.state == RiskState.COLLECTING

        lc.validate_session(s.session_id)
        assert s.state == RiskState.VALIDATING

        lc.mark_ready(s.session_id)
        assert s.state == RiskState.READY

        lc.start_assessment(s.session_id)
        assert s.state == RiskState.ASSESSING
        assert s.start_time is not None

        lc.start_monitoring(s.session_id)
        assert s.state == RiskState.MONITORING

        lc.complete(s.session_id)
        assert s.state == RiskState.COMPLETED
        assert s.end_time is not None

        lc.archive(s.session_id)
        assert s.state == RiskState.ARCHIVED
        assert s.is_archived

    def test_all_transitions_in_history(self, lc):
        s = lc.create("r-hist", "pf-hist")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.complete(s.session_id)
        lc.archive(s.session_id)
        # 6 transitions: INITIALIZING, COLLECTING, VALIDATING, READY, ASSESSING, COMPLETED, ARCHIVED
        assert len(s.transitions) == 7

    def test_statistics_after_full_path(self, lc):
        s = lc.create("r-stat", "pf-stat")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.complete(s.session_id)
        lc.archive(s.session_id)
        d = lc.statistics()
        assert d["risk_sessions_created"]  == 1
        assert d["risk_sessions_completed"] == 1
        assert d["risk_sessions_archived"] == 1
        assert d["transition_count"] == 7

    def test_validation_passes_after_full_path(self, lc):
        s = lc.create("r-val", "pf-val")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        result = lc.validate(s.session_id)
        assert result.is_valid

    def test_event_types_emitted_on_happy_path(self, lc):
        events: List[RiskEvent] = []
        lc.add_listener(events.append)
        s = lc.create("r-ev", "pf-ev")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.start_monitoring(s.session_id)
        lc.complete(s.session_id)
        lc.archive(s.session_id)
        types = {e.event_type for e in events}
        for expected in (
            RiskEventType.RISK_CREATED,
            RiskEventType.RISK_INITIALIZED,
            RiskEventType.RISK_COLLECTED,
            RiskEventType.RISK_VALIDATED,
            RiskEventType.RISK_ASSESSMENT_STARTED,
            RiskEventType.RISK_MONITORING_STARTED,
            RiskEventType.RISK_COMPLETED,
            RiskEventType.RISK_ARCHIVED,
        ):
            assert expected in types, expected


# ===========================================================================
# 17. Pause / resume path
# ===========================================================================

class TestPauseResumePath:
    def _to_assessing(self, lc: RiskLifecycle, risk_id: str = "r-pr") -> RiskSession:
        s = lc.create(risk_id, "pf-pr")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        return s

    def test_pause_from_assessing(self, lc):
        s = self._to_assessing(lc)
        lc.pause(s.session_id)
        assert s.state == RiskState.PAUSED

    def test_resume_from_paused(self, lc):
        s = self._to_assessing(lc)
        lc.pause(s.session_id)
        lc.resume(s.session_id)
        assert s.state == RiskState.RESUMING

    def test_reassess_after_resume(self, lc):
        s = self._to_assessing(lc)
        lc.pause(s.session_id)
        lc.resume(s.session_id)
        lc.start_assessment(s.session_id)
        assert s.state == RiskState.ASSESSING

    def test_monitoring_then_pause_then_monitor(self, lc):
        s = self._to_assessing(lc, "r-mon")
        lc.start_monitoring(s.session_id)
        lc.pause(s.session_id)
        lc.resume(s.session_id)
        lc.start_monitoring(s.session_id)
        assert s.state == RiskState.MONITORING

    def test_pause_event_emitted(self, lc):
        events: List[RiskEvent] = []
        lc.add_listener(events.append)
        s = self._to_assessing(lc, "r-pev")
        lc.pause(s.session_id)
        types = [e.event_type for e in events]
        assert RiskEventType.RISK_PAUSED in types

    def test_resumed_event_emitted(self, lc):
        events: List[RiskEvent] = []
        lc.add_listener(events.append)
        s = self._to_assessing(lc, "r-rev")
        lc.pause(s.session_id)
        lc.resume(s.session_id)
        types = [e.event_type for e in events]
        assert RiskEventType.RISK_RESUMED in types


# ===========================================================================
# 18. Failure path
# ===========================================================================

class TestFailurePath:
    def test_fail_from_created(self, lc):
        s = lc.create("r-fail-cr", "pf-1")
        lc.fail(s.session_id, reason="abort at creation")
        assert s.state == RiskState.FAILED
        assert s.failure_reason == "abort at creation"

    def test_fail_from_collecting(self, lc):
        s = lc.create("r-fail-co", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.fail(s.session_id, reason="bad data")
        assert s.state == RiskState.FAILED

    def test_fail_from_assessing(self, lc):
        s = lc.create("r-fail-as", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.fail(s.session_id, reason="risk engine error")
        assert s.state == RiskState.FAILED

    def test_archive_after_fail(self, lc):
        s = lc.create("r-fail-ar", "pf-1")
        lc.fail(s.session_id)
        lc.archive(s.session_id)
        assert s.state == RiskState.ARCHIVED

    def test_fail_event_emitted(self, lc):
        events: List[RiskEvent] = []
        lc.add_listener(events.append)
        s = lc.create("r-fev", "pf-1")
        lc.fail(s.session_id)
        types = [e.event_type for e in events]
        assert RiskEventType.RISK_FAILED in types

    def test_statistics_track_failure(self, lc):
        s = lc.create("r-fst", "pf-1")
        lc.fail(s.session_id)
        assert lc.statistics()["risk_sessions_failed"] == 1


# ===========================================================================
# 19. Re-collect path (VALIDATING → COLLECTING)
# ===========================================================================

class TestReCollectPath:
    def test_recollect_from_validating(self, lc):
        s = lc.create("r-rc", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        # Insufficient data — re-collect
        lc.collect(s.session_id)
        assert s.state == RiskState.COLLECTING

    def test_full_path_after_recollect(self, lc):
        s = lc.create("r-rc2", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.collect(s.session_id)       # re-collect
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.complete(s.session_id)
        assert s.state == RiskState.COMPLETED


# ===========================================================================
# 20. Re-assess path (MONITORING → ASSESSING)
# ===========================================================================

class TestReAssessPath:
    def test_reassess_from_monitoring(self, lc):
        s = lc.create("r-ra", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.start_monitoring(s.session_id)
        lc.start_assessment(s.session_id)  # re-assess on new data
        assert s.state == RiskState.ASSESSING

    def test_complete_after_reassess(self, lc):
        s = lc.create("r-ra2", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.start_monitoring(s.session_id)
        lc.start_assessment(s.session_id)  # re-assess
        lc.complete(s.session_id)
        assert s.state == RiskState.COMPLETED


# ===========================================================================
# 21. Concurrency safety
# ===========================================================================

class TestConcurrencySafety:
    def test_concurrent_session_creation(self, lc):
        errors  = []
        results = []

        def worker(i: int):
            try:
                s = lc.create(f"r-{i}", f"pf-{i}")
                results.append(s)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"errors: {errors}"
        assert len(results) == 30

    def test_concurrent_registry_operations(self, registry):
        errors = []

        def adder():
            try:
                registry.add(_make_session())
            except RiskCapacityExceededError:
                pass
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=adder) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_concurrent_statistics_increments(self, stats):
        n = 100

        def inc():
            for _ in range(n):
                stats.record_session_created()

        threads = [threading.Thread(target=inc) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.snapshot()["risk_sessions_created"] == 5 * n

    def test_concurrent_history_appends(self, history):
        errors = []

        def recorder():
            try:
                history.record_event(make_risk_created("s", "r", "p"))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=recorder) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert history.event_count() == 100

    def test_concurrent_lifecycle_full_workflows(self, lc):
        errors  = []
        results = []

        def full_workflow(i: int):
            try:
                s = lc.create(f"r-fw-{i}", f"pf-fw-{i}")
                lc.initialize(s.session_id)
                lc.collect(s.session_id)
                lc.validate_session(s.session_id)
                lc.mark_ready(s.session_id)
                lc.start_assessment(s.session_id)
                lc.complete(s.session_id)
                lc.archive(s.session_id)
                results.append(s)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=full_workflow, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"errors: {errors}"
        assert len(results) == 20
        assert all(s.state == RiskState.ARCHIVED for s in results)


# ===========================================================================
# 22. Regression
# ===========================================================================

class TestRegression:
    def test_all_12_risk_states_distinct(self):
        vals = [s.value for s in RiskState]
        assert len(vals) == len(set(vals)) == 12

    def test_all_11_event_types_distinct(self):
        vals = [e.value for e in RiskEventType]
        assert len(vals) == len(set(vals)) == 11

    def test_all_5_validation_codes_distinct(self):
        vals = [c.value for c in RiskValidationCode]
        assert len(vals) == len(set(vals)) == 5

    def test_all_error_codes_rl_prefix(self):
        for cls in (
            RiskLifecycleError, RiskSessionNotFoundError,
            RiskInvalidTransitionError, RiskSessionTerminatedError,
            RiskLifecycleNotRunningError, RiskCapacityExceededError,
            RiskValidationError, RiskHistoryError,
            RiskRegistryError, RiskConfigurationError,
        ):
            assert cls.error_code.startswith("RL-"), cls

    def test_happy_path_end_state_archived(self, lc):
        s = lc.create("r-reg", "pf-reg")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.complete(s.session_id)
        lc.archive(s.session_id)
        assert s.state == RiskState.ARCHIVED
        assert s.end_time is not None
        assert s.duration_s > 0.0

    def test_session_to_dict_stable_keys(self):
        s  = _make_session()
        d1 = s.to_dict()
        d2 = s.to_dict()
        assert d1.keys() == d2.keys()

    def test_lifecycle_stop_cleans_up(self):
        lc = RiskLifecycle()
        lc.start()
        lc.create("r-1", "pf-1")
        lc.stop()
        assert lc.lifecycle_state().value == "stopped"

    def test_archived_session_queryable_via_get(self, lc):
        s = lc.create("r-ar-q", "pf-1")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_assessment(s.session_id)
        lc.complete(s.session_id)
        lc.archive(s.session_id)
        found = lc.get(s.session_id)
        assert found.state == RiskState.ARCHIVED

    def test_session_ids_unique_across_bulk_creation(self, lc):
        sessions = [lc.create(f"r-{i}", "pf-bulk") for i in range(50)]
        ids = {s.session_id for s in sessions}
        assert len(ids) == 50

    def test_validation_5_checks_always_returned(self, validator):
        for state in (RiskState.CREATED, RiskState.COLLECTING, RiskState.ASSESSING):
            s = _make_session()
            if state != RiskState.CREATED:
                _advance_to(s, state)
            result = validator.validate(s)
            assert len(result.checks) == 5

    def test_invalid_transition_never_corrupts_state(self, lc):
        s = lc.create("r-corrupt", "pf-1")
        with pytest.raises(RiskInvalidTransitionError):
            s.transition_to(RiskState.COMPLETED)
        assert s.state == RiskState.CREATED
