"""
tests/unit/portfolio/lifecycle/test_lifecycle.py
=================================================
Comprehensive unit tests for the Portfolio Lifecycle subsystem.

Coverage targets:
- constants and state-set membership
- exceptions (all 10 subclasses)
- PortfolioStateRecord
- can_transition()
- PortfolioTransition / make_transition()
- PortfolioContext.create() / to_dict()
- PortfolioMetadata.create() / to_dict()
- PortfolioSession creation, state queries, transition_to(), fail()
- PortfolioFactory.create()
- PortfolioEvent / 11 factory functions
- PortfolioRegistry (add, get, find, archive, capacity, duplicate)
- PortfolioHistory (events, transitions, queries)
- PortfolioStatistics (all counters, EMA, reset)
- PortfolioValidator (all 5 checks, valid/invalid cases)
- PortfolioLifecycle — full happy path, transitions, fail, archive,
  listeners, statistics, history, validation, guard
"""
from __future__ import annotations

import time
import threading
from typing import List
from unittest.mock import MagicMock

import pytest

from iios.portfolio.lifecycle import (
    # Primary interface
    PortfolioLifecycle,
    # Domain objects
    PortfolioSession,
    PortfolioContext,
    PortfolioMetadata,
    PortfolioEvent,
    PortfolioFactory,
    PortfolioHistory,
    PortfolioRegistry,
    PortfolioStateRecord,
    PortfolioStatistics,
    PortfolioTransition,
    PortfolioValidationCheckResult,
    PortfolioValidationResult,
    PortfolioValidator,
    # Enums
    PortfolioEventType,
    PortfolioObjective,
    PortfolioScope,
    PortfolioState,
    PortfolioStatus,
    PortfolioType,
    PortfolioValidationCode,
    # Exceptions
    PortfolioLifecycleError,
    PortfolioSessionNotFoundError,
    PortfolioInvalidTransitionError,
    PortfolioSessionTerminatedError,
    PortfolioLifecycleNotRunningError,
    PortfolioCapacityExceededError,
    PortfolioValidationError,
    PortfolioHistoryError,
    PortfolioRegistryError,
    PortfolioConfigurationError,
    # State sets
    ACTIVE_STATES,
    TERMINAL_STATES,
    SUCCESS_STATES,
    IMMUTABLE_STATES,
    VALID_TRANSITIONS,
    # Helpers
    can_transition,
    make_transition,
    # Event factories
    make_portfolio_created,
    make_portfolio_initialized,
    make_portfolio_loaded,
    make_portfolio_validated,
    make_portfolio_activated,
    make_portfolio_paused,
    make_portfolio_resumed,
    make_portfolio_rebalancing,
    make_portfolio_completed,
    make_portfolio_failed,
    make_portfolio_archived,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _started_lc(**kw) -> PortfolioLifecycle:
    lc = PortfolioLifecycle(**kw)
    lc.start()
    return lc


def _full_lifecycle_session(lc: PortfolioLifecycle, portfolio_id: str = "pf-001") -> PortfolioSession:
    """Drive a session through the full happy path to COMPLETED."""
    s = lc.create(portfolio_id, portfolio_name="Test Fund")
    lc.initialize(s.session_id)
    lc.load(s.session_id)
    lc.validate_session(s.session_id)
    lc.ready(s.session_id)
    lc.activate(s.session_id)
    lc.complete(s.session_id)
    return lc.get_session(s.session_id)


# ===========================================================================
# Constants
# ===========================================================================

class TestConstants:
    def test_active_states_contains_expected(self):
        for state in [
            PortfolioState.INITIALIZING,
            PortfolioState.LOADING,
            PortfolioState.VALIDATING,
            PortfolioState.READY,
            PortfolioState.ACTIVE,
            PortfolioState.PAUSED,
            PortfolioState.RESUMING,
            PortfolioState.REBALANCING,
        ]:
            assert state in ACTIVE_STATES

    def test_terminal_states(self):
        assert PortfolioState.COMPLETED in TERMINAL_STATES
        assert PortfolioState.FAILED    in TERMINAL_STATES
        assert PortfolioState.ARCHIVED  in TERMINAL_STATES

    def test_success_states(self):
        assert PortfolioState.COMPLETED in SUCCESS_STATES

    def test_immutable_states(self):
        assert PortfolioState.ARCHIVED in IMMUTABLE_STATES

    def test_valid_transitions_created(self):
        allowed = VALID_TRANSITIONS[PortfolioState.CREATED]
        assert PortfolioState.INITIALIZING in allowed
        assert PortfolioState.FAILED       in allowed

    def test_valid_transitions_archived_is_empty(self):
        assert not VALID_TRANSITIONS[PortfolioState.ARCHIVED]


# ===========================================================================
# Exceptions
# ===========================================================================

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        ex = PortfolioLifecycleError("boom")
        assert isinstance(ex, IIOSError)
        assert ex.error_code == "PL-000"

    def test_not_found(self):
        ex = PortfolioSessionNotFoundError("s1")
        assert ex.session_id == "s1"
        assert ex.error_code == "PL-001"

    def test_invalid_transition(self):
        ex = PortfolioInvalidTransitionError(
            PortfolioState.CREATED, PortfolioState.COMPLETED, "s1"
        )
        assert ex.error_code == "PL-002"
        assert ex.session_id == "s1"

    def test_terminated(self):
        ex = PortfolioSessionTerminatedError("s1", state="ARCHIVED")
        assert ex.session_id == "s1"
        assert ex.error_code == "PL-003"

    def test_not_running(self):
        ex = PortfolioLifecycleNotRunningError()
        assert ex.error_code == "PL-004"

    def test_capacity_exceeded(self):
        ex = PortfolioCapacityExceededError(100)
        assert ex.limit == 100
        assert ex.error_code == "PL-005"

    def test_validation_error(self):
        ex = PortfolioValidationError("bad", failed_checks=("c1",))
        assert ex.failed_checks == ("c1",)
        assert ex.error_code == "PL-006"

    def test_history_error(self):
        ex = PortfolioHistoryError("hist err")
        assert ex.error_code == "PL-007"

    def test_registry_error(self):
        ex = PortfolioRegistryError("reg err")
        assert ex.error_code == "PL-008"

    def test_configuration_error(self):
        ex = PortfolioConfigurationError("cfg err")
        assert ex.error_code == "PL-009"


# ===========================================================================
# PortfolioStateRecord
# ===========================================================================

class TestPortfolioStateRecord:
    def test_create_defaults(self):
        r = PortfolioStateRecord(
            state      = PortfolioState.CREATED,
            entered_at = 0.0,
            actor      = "test",
            reason     = "unit",
        )
        assert r.state == PortfolioState.CREATED
        assert r.actor == "test"

    def test_to_dict_keys(self):
        r = PortfolioStateRecord(
            state=PortfolioState.ACTIVE, entered_at=1.0, actor="a", reason="r"
        )
        d = r.to_dict()
        assert d["state"] == "active"
        assert d["actor"] == "a"

    def test_frozen(self):
        r = PortfolioStateRecord(
            state=PortfolioState.CREATED, entered_at=0.0, actor="a", reason=""
        )
        with pytest.raises((AttributeError, TypeError)):
            r.actor = "mutated"  # type: ignore[misc]


# ===========================================================================
# can_transition
# ===========================================================================

class TestCanTransition:
    def test_allowed(self):
        assert can_transition(PortfolioState.CREATED, PortfolioState.INITIALIZING)

    def test_not_allowed(self):
        assert not can_transition(PortfolioState.CREATED, PortfolioState.COMPLETED)

    def test_archived_to_anything_false(self):
        for target in PortfolioState:
            assert not can_transition(PortfolioState.ARCHIVED, target)


# ===========================================================================
# PortfolioTransition / make_transition
# ===========================================================================

class TestPortfolioTransition:
    def test_make_transition_fields(self):
        t = make_transition(
            "s1",
            PortfolioState.CREATED,
            PortfolioState.INITIALIZING,
            actor="actor",
            reason="test",
        )
        assert t.session_id == "s1"
        assert t.from_state == PortfolioState.CREATED
        assert t.to_state   == PortfolioState.INITIALIZING
        assert t.actor      == "actor"
        assert t.reason     == "test"
        assert t.transition_id  # non-empty UUID
        assert t.transitioned_at > 0

    def test_to_dict(self):
        t = make_transition(
            "s2", PortfolioState.LOADING, PortfolioState.VALIDATING,
            actor="a", reason="r"
        )
        d = t.to_dict()
        assert d["from_state"] == "loading"
        assert d["to_state"]   == "validating"

    def test_frozen(self):
        t = make_transition(
            "s3", PortfolioState.CREATED, PortfolioState.FAILED,
            actor="a", reason=""
        )
        with pytest.raises((AttributeError, TypeError)):
            t.actor = "mutated"  # type: ignore[misc]


# ===========================================================================
# PortfolioContext
# ===========================================================================

class TestPortfolioContext:
    def test_create_defaults(self):
        ctx = PortfolioContext.create("pf-100")
        assert ctx.portfolio_id    == "pf-100"
        assert ctx.portfolio_currency == "INR"
        assert ctx.context_id          # non-empty

    def test_create_custom(self):
        ctx = PortfolioContext.create(
            "pf-200",
            portfolio_name      = "Growth",
            portfolio_type      = PortfolioType.EQUITY,
            portfolio_currency  = "USD",
        )
        assert ctx.portfolio_name     == "Growth"
        assert ctx.portfolio_type     == PortfolioType.EQUITY
        assert ctx.portfolio_currency == "USD"

    def test_to_dict(self):
        ctx = PortfolioContext.create("pf-300")
        d = ctx.to_dict()
        assert "context_id"     in d
        assert "portfolio_id"   in d
        assert d["portfolio_id"] == "pf-300"


# ===========================================================================
# PortfolioMetadata
# ===========================================================================

class TestPortfolioMetadata:
    def test_create_defaults(self):
        m = PortfolioMetadata.create("s1", "pf-001")
        assert m.session_id     == "s1"
        assert m.portfolio_id   == "pf-001"
        assert m.metadata_id         # non-empty UUID

    def test_create_with_tags(self):
        m = PortfolioMetadata.create(
            "s2", "pf-002",
            tags  = ("equity", "long"),
            labels= {"env": "prod"},
        )
        assert "equity" in m.tags
        assert m.labels["env"] == "prod"

    def test_to_dict(self):
        m = PortfolioMetadata.create("s3", "pf-003", tags=("x",))
        d = m.to_dict()
        assert "x" in d["tags"]

    def test_frozen(self):
        m = PortfolioMetadata.create("s4", "pf-004")
        with pytest.raises((AttributeError, TypeError)):
            m.session_id = "mutated"  # type: ignore[misc]


# ===========================================================================
# PortfolioSession
# ===========================================================================

class TestPortfolioSession:
    def test_initial_state(self):
        s = PortfolioSession(portfolio_id="pf-001")
        assert s.state             == PortfolioState.CREATED
        assert s.portfolio_id      == "pf-001"
        assert s.is_active         is False  # CREATED is not in ACTIVE_STATES
        assert s.is_terminal       is False
        assert s.is_archived       is False
        assert s.failure_reason    == ""
        assert len(s.state_history) == 1
        assert len(s.transitions)   == 0
        assert s.session_id         # auto-generated UUID
        assert s.session_id != ""

    def test_explicit_session_id(self):
        s = PortfolioSession(session_id="explicit-id", portfolio_id="pf")
        assert s.session_id == "explicit-id"

    def test_transition_valid(self):
        s = PortfolioSession(portfolio_id="pf")
        s.transition_to(PortfolioState.INITIALIZING, actor="test", reason="go")
        assert s.state == PortfolioState.INITIALIZING
        assert len(s.transitions) == 1
        assert len(s.state_history) == 2

    def test_transition_invalid_raises(self):
        s = PortfolioSession(portfolio_id="pf")
        with pytest.raises(PortfolioInvalidTransitionError):
            s.transition_to(PortfolioState.COMPLETED)

    def test_transition_to_archived_then_immutable(self):
        s = PortfolioSession(portfolio_id="pf")
        # Drive to COMPLETED → ARCHIVED
        s.transition_to(PortfolioState.INITIALIZING)
        s.transition_to(PortfolioState.LOADING)
        s.transition_to(PortfolioState.VALIDATING)
        s.transition_to(PortfolioState.READY)
        s.transition_to(PortfolioState.ACTIVE)
        s.transition_to(PortfolioState.COMPLETED)
        s.transition_to(PortfolioState.ARCHIVED)
        with pytest.raises(PortfolioSessionTerminatedError):
            s.transition_to(PortfolioState.FAILED)

    def test_fail_shortcut(self):
        s = PortfolioSession(portfolio_id="pf")
        s.fail(reason="network error")
        assert s.state          == PortfolioState.FAILED
        assert s.failure_reason == "network error"
        assert s.is_terminal

    def test_is_active_after_active(self):
        s = PortfolioSession(portfolio_id="pf")
        s.transition_to(PortfolioState.INITIALIZING)
        s.transition_to(PortfolioState.LOADING)
        s.transition_to(PortfolioState.VALIDATING)
        s.transition_to(PortfolioState.READY)
        s.transition_to(PortfolioState.ACTIVE)
        assert s.is_active

    def test_is_paused(self):
        s = PortfolioSession(portfolio_id="pf")
        s.transition_to(PortfolioState.INITIALIZING)
        s.transition_to(PortfolioState.LOADING)
        s.transition_to(PortfolioState.VALIDATING)
        s.transition_to(PortfolioState.READY)
        s.transition_to(PortfolioState.PAUSED)
        assert s.is_paused

    def test_is_rebalancing(self):
        s = PortfolioSession(portfolio_id="pf")
        for state in [
            PortfolioState.INITIALIZING,
            PortfolioState.LOADING,
            PortfolioState.VALIDATING,
            PortfolioState.READY,
            PortfolioState.ACTIVE,
            PortfolioState.REBALANCING,
        ]:
            s.transition_to(state)
        assert s.is_rebalancing

    def test_start_time_set_on_active(self):
        s = PortfolioSession(portfolio_id="pf")
        s.transition_to(PortfolioState.INITIALIZING)
        s.transition_to(PortfolioState.LOADING)
        s.transition_to(PortfolioState.VALIDATING)
        s.transition_to(PortfolioState.READY)
        assert s.start_time is None
        s.transition_to(PortfolioState.ACTIVE)
        assert s.start_time is not None

    def test_end_time_set_on_completed(self):
        s = PortfolioSession(portfolio_id="pf")
        for state in [PortfolioState.INITIALIZING, PortfolioState.LOADING,
                      PortfolioState.VALIDATING, PortfolioState.READY,
                      PortfolioState.ACTIVE, PortfolioState.COMPLETED]:
            s.transition_to(state)
        assert s.end_time is not None

    def test_duration_s_positive(self):
        s = PortfolioSession(portfolio_id="pf")
        time.sleep(0.01)
        dur = s.duration_s()
        assert dur is not None and dur >= 0.0

    def test_to_dict_keys(self):
        s = PortfolioSession(portfolio_id="pf-x")
        d = s.to_dict()
        assert d["portfolio_id"] == "pf-x"
        assert d["state"]        == "created"

    def test_version_increments_on_transition(self):
        s = PortfolioSession(portfolio_id="pf")
        v0 = s.portfolio_version
        s.transition_to(PortfolioState.INITIALIZING)
        assert s.portfolio_version == v0 + 1


# ===========================================================================
# PortfolioFactory
# ===========================================================================

class TestPortfolioFactory:
    def test_create_returns_session_in_created_state(self):
        f = PortfolioFactory()
        s = f.create("pf-001")
        assert isinstance(s, PortfolioSession)
        assert s.state == PortfolioState.CREATED

    def test_create_with_options(self):
        f = PortfolioFactory()
        s = f.create(
            "pf-002",
            portfolio_name      = "Custom",
            portfolio_type      = PortfolioType.BALANCED,
            portfolio_currency  = "USD",
        )
        assert s.portfolio_name     == "Custom"
        assert s.portfolio_type     == PortfolioType.BALANCED
        assert s.portfolio_currency == "USD"

    def test_create_explicit_session_id(self):
        f = PortfolioFactory()
        s = f.create("pf-003", session_id="explicit")
        assert s.session_id == "explicit"


# ===========================================================================
# PortfolioEvent / factories
# ===========================================================================

class TestPortfolioEvents:
    def _check_event(self, event: PortfolioEvent, expected_type: PortfolioEventType):
        assert event.event_type   == expected_type
        assert event.event_id          # non-empty UUID
        assert event.session_id   == "s1"
        assert event.portfolio_id == "pf-001"
        assert event.occurred_at  > 0

    def test_make_portfolio_created(self):
        self._check_event(
            make_portfolio_created("s1", "pf-001"),
            PortfolioEventType.PORTFOLIO_CREATED,
        )

    def test_make_portfolio_initialized(self):
        self._check_event(
            make_portfolio_initialized("s1", "pf-001"),
            PortfolioEventType.PORTFOLIO_INITIALIZED,
        )

    def test_make_portfolio_loaded(self):
        self._check_event(
            make_portfolio_loaded("s1", "pf-001"),
            PortfolioEventType.PORTFOLIO_LOADED,
        )

    def test_make_portfolio_validated(self):
        self._check_event(
            make_portfolio_validated("s1", "pf-001"),
            PortfolioEventType.PORTFOLIO_VALIDATED,
        )

    def test_make_portfolio_activated(self):
        self._check_event(
            make_portfolio_activated("s1", "pf-001"),
            PortfolioEventType.PORTFOLIO_ACTIVATED,
        )

    def test_make_portfolio_paused(self):
        self._check_event(
            make_portfolio_paused("s1", "pf-001"),
            PortfolioEventType.PORTFOLIO_PAUSED,
        )

    def test_make_portfolio_resumed(self):
        self._check_event(
            make_portfolio_resumed("s1", "pf-001"),
            PortfolioEventType.PORTFOLIO_RESUMED,
        )

    def test_make_portfolio_rebalancing(self):
        self._check_event(
            make_portfolio_rebalancing("s1", "pf-001"),
            PortfolioEventType.PORTFOLIO_REBALANCING,
        )

    def test_make_portfolio_completed(self):
        self._check_event(
            make_portfolio_completed("s1", "pf-001"),
            PortfolioEventType.PORTFOLIO_COMPLETED,
        )

    def test_make_portfolio_failed(self):
        event = make_portfolio_failed("s1", "pf-001", reason="network")
        assert event.event_type == PortfolioEventType.PORTFOLIO_FAILED
        assert event.payload.get("reason") == "network"

    def test_make_portfolio_archived(self):
        self._check_event(
            make_portfolio_archived("s1", "pf-001"),
            PortfolioEventType.PORTFOLIO_ARCHIVED,
        )

    def test_event_to_dict(self):
        e = make_portfolio_created("s1", "pf-001")
        d = e.to_dict()
        assert d["event_type"] == "portfolio_created"
        assert d["session_id"] == "s1"


# ===========================================================================
# PortfolioRegistry
# ===========================================================================

class TestPortfolioRegistry:
    def _session(self, portfolio_id: str = "pf") -> PortfolioSession:
        return PortfolioSession(portfolio_id=portfolio_id)

    def test_add_and_get(self):
        reg = PortfolioRegistry()
        s   = self._session()
        reg.add(s)
        assert reg.get(s.session_id) is s

    def test_find_returns_none_for_missing(self):
        reg = PortfolioRegistry()
        assert reg.find("nope") is None

    def test_duplicate_raises_registry_error(self):
        reg = PortfolioRegistry()
        s   = self._session()
        reg.add(s)
        with pytest.raises(PortfolioRegistryError):
            reg.add(s)

    def test_capacity_exceeded(self):
        reg = PortfolioRegistry(max_active_sessions=2)
        reg.add(self._session("pf1"))
        reg.add(self._session("pf2"))
        with pytest.raises(PortfolioCapacityExceededError):
            reg.add(self._session("pf3"))

    def test_archive_moves_to_archived(self):
        reg = PortfolioRegistry()
        s   = self._session()
        reg.add(s)
        reg.archive(s.session_id)
        assert not reg.contains_active(s.session_id)
        assert reg.find(s.session_id) is s

    def test_archive_missing_raises_not_found(self):
        reg = PortfolioRegistry()
        with pytest.raises(PortfolioSessionNotFoundError):
            reg.archive("ghost")

    def test_get_missing_raises_not_found(self):
        reg = PortfolioRegistry()
        with pytest.raises(PortfolioSessionNotFoundError):
            reg.get("ghost")

    def test_sessions_for_portfolio(self):
        reg = PortfolioRegistry()
        s1  = PortfolioSession(portfolio_id="pf-A")
        s2  = PortfolioSession(portfolio_id="pf-A")
        s3  = PortfolioSession(portfolio_id="pf-B")
        reg.add(s1); reg.add(s2); reg.add(s3)
        result = reg.sessions_for_portfolio("pf-A")
        assert len(result) == 2

    def test_archived_eviction_on_overflow(self):
        reg = PortfolioRegistry(max_archived_sessions=2)
        sessions = [PortfolioSession(portfolio_id="pf") for _ in range(3)]
        for s in sessions:
            reg.add(s)
        for s in sessions:
            reg.archive(s.session_id)
        # only 2 retained
        assert reg.archived_count() == 2

    def test_active_count(self):
        reg = PortfolioRegistry()
        reg.add(self._session("a1"))
        reg.add(self._session("a2"))
        assert reg.active_count() == 2

    def test_clear(self):
        reg = PortfolioRegistry()
        reg.add(self._session())
        reg.clear()
        assert reg.active_count() == 0


# ===========================================================================
# PortfolioHistory
# ===========================================================================

class TestPortfolioHistory:
    def test_record_and_retrieve_event(self):
        h = PortfolioHistory()
        e = make_portfolio_created("s1", "pf-001")
        h.record_event(e)
        assert h.latest_event() is e
        assert h.event_count() == 1

    def test_events_for_session(self):
        h  = PortfolioHistory()
        e1 = make_portfolio_created("s1", "pf")
        e2 = make_portfolio_created("s2", "pf")
        h.record_event(e1); h.record_event(e2)
        result = h.events_for_session("s1")
        assert len(result) == 1
        assert result[0] is e1

    def test_events_by_type(self):
        h  = PortfolioHistory()
        e1 = make_portfolio_created("s1", "pf")
        e2 = make_portfolio_activated("s1", "pf")
        h.record_event(e1); h.record_event(e2)
        created = h.events_by_type(PortfolioEventType.PORTFOLIO_CREATED)
        assert len(created) == 1

    def test_record_transition(self):
        h = PortfolioHistory()
        t = make_transition(
            "s1", PortfolioState.CREATED, PortfolioState.INITIALIZING,
            actor="a", reason=""
        )
        h.record_transition(t)
        assert h.transition_count() == 1
        assert h.latest_transition() is t

    def test_transitions_for_session(self):
        h  = PortfolioHistory()
        t1 = make_transition("s1", PortfolioState.CREATED, PortfolioState.INITIALIZING, actor="a", reason="")
        t2 = make_transition("s2", PortfolioState.CREATED, PortfolioState.INITIALIZING, actor="a", reason="")
        h.record_transition(t1); h.record_transition(t2)
        assert len(h.transitions_for_session("s1")) == 1

    def test_bounded_maxlen(self):
        h = PortfolioHistory(max_events=3)
        for i in range(5):
            h.record_event(make_portfolio_created(f"s{i}", "pf"))
        assert h.event_count() == 3

    def test_latest_event_none_when_empty(self):
        h = PortfolioHistory()
        assert h.latest_event() is None

    def test_clear(self):
        h = PortfolioHistory()
        h.record_event(make_portfolio_created("s1", "pf"))
        h.clear()
        assert h.event_count() == 0


# ===========================================================================
# PortfolioStatistics
# ===========================================================================

class TestPortfolioStatistics:
    def test_initial_zeros(self):
        s = PortfolioStatistics()
        snap = s.snapshot()
        assert snap["portfolio_sessions_created"]   == 0
        assert snap["portfolio_sessions_completed"] == 0
        assert snap["portfolio_sessions_failed"]    == 0
        assert snap["portfolio_sessions_archived"]  == 0
        assert snap["transition_count"]             == 0
        assert snap["average_session_duration_s"]   == 0.0

    def test_record_created(self):
        s = PortfolioStatistics()
        s.record_session_created()
        s.record_session_created()
        assert s.snapshot()["portfolio_sessions_created"] == 2

    def test_record_completed_with_duration(self):
        s = PortfolioStatistics()
        s.record_session_completed(duration_s=10.0)
        s.record_session_completed(duration_s=20.0)
        snap = s.snapshot()
        assert snap["portfolio_sessions_completed"] == 2
        assert snap["average_session_duration_s"]  == 15.0

    def test_record_failed(self):
        s = PortfolioStatistics()
        s.record_session_failed()
        assert s.snapshot()["portfolio_sessions_failed"] == 1

    def test_record_archived(self):
        s = PortfolioStatistics()
        s.record_session_archived()
        assert s.snapshot()["portfolio_sessions_archived"] == 1

    def test_record_transition(self):
        s = PortfolioStatistics()
        s.record_transition()
        assert s.snapshot()["transition_count"] == 1

    def test_ema_smoothed(self):
        s = PortfolioStatistics()
        s.record_session_completed(duration_s=100.0)
        s.record_session_completed(duration_s=0.0)  # zero → treated as "no duration"
        snap = s.snapshot()
        assert snap["ema_session_duration_s"] > 0

    def test_reset(self):
        s = PortfolioStatistics()
        s.record_session_created()
        s.record_session_failed()
        s.reset()
        snap = s.snapshot()
        assert snap["portfolio_sessions_created"] == 0
        assert snap["portfolio_sessions_failed"]  == 0

    def test_uptime_positive(self):
        s = PortfolioStatistics()
        time.sleep(0.01)
        assert s.snapshot()["uptime_s"] > 0


# ===========================================================================
# PortfolioValidator
# ===========================================================================

class TestPortfolioValidator:
    def _valid_session(self) -> PortfolioSession:
        s = PortfolioSession(portfolio_id="pf-001")
        return s

    def test_valid_session_passes_all_checks(self):
        v = PortfolioValidator()
        s = self._valid_session()
        r = v.validate(s)
        assert r.is_valid
        assert r.failed_count == 0
        assert r.passed_count == 5

    def test_invalid_session_id_fails(self):
        v = PortfolioValidator()
        s = PortfolioSession(portfolio_id="pf")
        # Manually corrupt session_id after creation to simulate empty
        s._session_id = ""
        r = v.validate(s)
        assert not r.is_valid
        assert any(
            c.code == PortfolioValidationCode.IDENTIFIER_CONSISTENCY and not c.passed
            for c in r.checks
        )

    def test_empty_portfolio_id_fails(self):
        v = PortfolioValidator()
        s = PortfolioSession(session_id="sid", portfolio_id="")
        r = v.validate(s)
        assert not r.is_valid

    def test_transition_validity_non_created_no_transitions_fails(self):
        """Manually corrupt state without using transitions (simulate bad state)."""
        v = PortfolioValidator()
        s = PortfolioSession(portfolio_id="pf")
        # Manually set state to simulate corruption
        s._state = PortfolioState.ACTIVE  # bypass transition enforcement
        r = v.validate(s)
        # Should fail transition validity (transitions list is empty but state != CREATED)
        assert not r.is_valid

    def test_valid_after_transition(self):
        v = PortfolioValidator()
        s = PortfolioSession(portfolio_id="pf")
        s.transition_to(PortfolioState.INITIALIZING)
        r = v.validate(s)
        assert r.is_valid

    def test_error_messages_populated_on_failure(self):
        v = PortfolioValidator()
        s = PortfolioSession(session_id="", portfolio_id="")
        r = v.validate(s)
        assert len(r.error_messages) > 0

    def test_failed_checks_subset_of_checks(self):
        v = PortfolioValidator()
        s = PortfolioSession(portfolio_id="pf")
        r = v.validate(s)
        for fc in r.failed_checks:
            assert fc in r.checks


# ===========================================================================
# PortfolioLifecycle — guard / not-running
# ===========================================================================

class TestPortfolioLifecycleGuard:
    def test_operations_blocked_when_stopped(self):
        lc = PortfolioLifecycle()
        # Do NOT start — lifecycle state is CREATED/STOPPED
        with pytest.raises(PortfolioLifecycleNotRunningError):
            lc.create("pf-001")

    def test_start_then_stop_then_create_blocked(self):
        lc = PortfolioLifecycle()
        lc.start()
        lc.stop()
        with pytest.raises(PortfolioLifecycleNotRunningError):
            lc.create("pf-001")


# ===========================================================================
# PortfolioLifecycle — creation
# ===========================================================================

class TestPortfolioLifecycleCreate:
    def test_create_returns_session(self):
        lc = _started_lc()
        s  = lc.create("pf-001")
        assert isinstance(s, PortfolioSession)
        assert s.state       == PortfolioState.CREATED
        assert s.portfolio_id == "pf-001"
        lc.stop()

    def test_create_explicit_session_id(self):
        lc = _started_lc()
        s  = lc.create("pf-002", session_id="explicit-sid")
        assert s.session_id == "explicit-sid"
        lc.stop()

    def test_create_increments_statistics(self):
        lc = _started_lc()
        lc.create("pf-003")
        lc.create("pf-004")
        snap = lc.statistics()
        assert snap["portfolio_sessions_created"] == 2
        lc.stop()

    def test_capacity_exceeded(self):
        lc = _started_lc(max_active_sessions=1)
        lc.create("pf-A")
        with pytest.raises(PortfolioCapacityExceededError):
            lc.create("pf-B")
        lc.stop()


# ===========================================================================
# PortfolioLifecycle — state transitions
# ===========================================================================

class TestPortfolioLifecycleTransitions:
    def test_initialize(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.initialize(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.INITIALIZING
        lc.stop()

    def test_load(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.initialize(s.session_id)
        lc.load(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.LOADING
        lc.stop()

    def test_validate_session(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.initialize(s.session_id)
        lc.load(s.session_id)
        lc.validate_session(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.VALIDATING
        lc.stop()

    def test_ready(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.initialize(s.session_id)
        lc.load(s.session_id)
        lc.validate_session(s.session_id)
        lc.ready(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.READY
        lc.stop()

    def test_activate(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.initialize(s.session_id)
        lc.load(s.session_id)
        lc.validate_session(s.session_id)
        lc.ready(s.session_id)
        lc.activate(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.ACTIVE
        lc.stop()

    def test_pause_and_resume(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.initialize(s.session_id)
        lc.load(s.session_id)
        lc.validate_session(s.session_id)
        lc.ready(s.session_id)
        lc.pause(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.PAUSED
        lc.resume(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.RESUMING
        lc.stop()

    def test_rebalance(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.initialize(s.session_id)
        lc.load(s.session_id)
        lc.validate_session(s.session_id)
        lc.ready(s.session_id)
        lc.activate(s.session_id)
        lc.rebalance(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.REBALANCING
        lc.stop()

    def test_complete(self):
        lc = _started_lc()
        s  = _full_lifecycle_session(lc)
        assert s.state == PortfolioState.COMPLETED
        lc.stop()

    def test_fail(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.fail(s.session_id, reason="test failure")
        session = lc.get_session(s.session_id)
        assert session.state          == PortfolioState.FAILED
        assert session.failure_reason == "test failure"
        lc.stop()

    def test_archive_after_completed(self):
        lc = _started_lc()
        s  = _full_lifecycle_session(lc)
        lc.archive(s.session_id)
        # After archiving, session is in archived registry
        archived = lc.get_session(s.session_id)
        assert archived.state == PortfolioState.ARCHIVED
        lc.stop()

    def test_archive_after_failed(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.fail(s.session_id)
        lc.archive(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.ARCHIVED
        lc.stop()

    def test_invalid_transition_propagates(self):
        lc = _started_lc()
        s  = lc.create("pf")
        with pytest.raises(PortfolioInvalidTransitionError):
            # Can't go directly CREATED → ACTIVE
            lc.activate(s.session_id)
        lc.stop()

    def test_session_not_found_raises(self):
        lc = _started_lc()
        with pytest.raises(PortfolioSessionNotFoundError):
            lc.initialize("nonexistent")
        lc.stop()


# ===========================================================================
# PortfolioLifecycle — statistics
# ===========================================================================

class TestPortfolioLifecycleStatistics:
    def test_full_lifecycle_statistics(self):
        lc   = _started_lc()
        _full_lifecycle_session(lc)
        snap = lc.statistics()
        assert snap["portfolio_sessions_created"]   >= 1
        assert snap["portfolio_sessions_completed"] >= 1
        assert snap["transition_count"]             >= 1
        lc.stop()

    def test_fail_recorded_in_statistics(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.fail(s.session_id)
        snap = lc.statistics()
        assert snap["portfolio_sessions_failed"] == 1
        lc.stop()

    def test_archive_recorded_in_statistics(self):
        lc = _started_lc()
        s  = _full_lifecycle_session(lc)
        lc.archive(s.session_id)
        snap = lc.statistics()
        assert snap["portfolio_sessions_archived"] == 1
        lc.stop()

    def test_active_sessions_count(self):
        lc = _started_lc()
        lc.create("pf1")
        lc.create("pf2")
        snap = lc.statistics()
        assert snap["active_sessions"] == 2
        lc.stop()


# ===========================================================================
# PortfolioLifecycle — history
# ===========================================================================

class TestPortfolioLifecycleHistory:
    def test_history_contains_events(self):
        lc = _started_lc()
        _full_lifecycle_session(lc)
        h = lc.history()
        assert len(h["events"])      > 0
        assert len(h["transitions"]) > 0
        lc.stop()

    def test_history_events_are_dicts(self):
        lc = _started_lc()
        lc.create("pf-x")
        h = lc.history()
        assert isinstance(h["events"][0], dict)
        lc.stop()


# ===========================================================================
# PortfolioLifecycle — validation
# ===========================================================================

class TestPortfolioLifecycleValidation:
    def test_validate_valid_session(self):
        lc = _started_lc()
        s  = lc.create("pf")
        r  = lc.validate(s.session_id)
        assert r.is_valid
        lc.stop()

    def test_validate_after_transition(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.initialize(s.session_id)
        r  = lc.validate(s.session_id)
        assert r.is_valid
        lc.stop()


# ===========================================================================
# PortfolioLifecycle — query methods
# ===========================================================================

class TestPortfolioLifecycleQueries:
    def test_get_session(self):
        lc = _started_lc()
        s  = lc.create("pf")
        got = lc.get_session(s.session_id)
        assert got.session_id == s.session_id
        lc.stop()

    def test_find_session_returns_none_for_missing(self):
        lc = _started_lc()
        assert lc.find_session("no-such") is None
        lc.stop()

    def test_sessions_for_portfolio(self):
        lc = _started_lc()
        lc.create("pf-X")
        lc.create("pf-X")
        lc.create("pf-Y")
        result = lc.sessions_for_portfolio("pf-X")
        assert len(result) == 2
        lc.stop()


# ===========================================================================
# PortfolioLifecycle — event listeners
# ===========================================================================

class TestPortfolioLifecycleListeners:
    def test_listener_receives_created_event(self):
        lc       = _started_lc()
        received = []
        lc.add_listener(received.append)
        lc.create("pf-001")
        assert len(received) == 1
        assert received[0].event_type == PortfolioEventType.PORTFOLIO_CREATED
        lc.stop()

    def test_listener_receives_all_events(self):
        lc       = _started_lc()
        received = []
        lc.add_listener(received.append)
        _full_lifecycle_session(lc)
        # created, initialized, loaded, validated, (no ready event), activated, completed
        assert len(received) >= 5
        lc.stop()

    def test_listener_removed(self):
        lc       = _started_lc()
        received = []
        lc.add_listener(received.append)
        lc.remove_listener(received.append)
        lc.create("pf-001")
        assert len(received) == 0
        lc.stop()

    def test_listener_error_does_not_propagate(self):
        lc = _started_lc()

        def bad_listener(event):
            raise RuntimeError("listener crash")

        lc.add_listener(bad_listener)
        # Should not raise
        lc.create("pf-001")
        lc.stop()

    def test_multiple_listeners(self):
        lc   = _started_lc()
        acc1 = []
        acc2 = []
        lc.add_listener(acc1.append)
        lc.add_listener(acc2.append)
        lc.create("pf-001")
        assert len(acc1) == 1
        assert len(acc2) == 1
        lc.stop()

    def test_duplicate_listener_not_added_twice(self):
        lc  = _started_lc()
        acc = []
        lc.add_listener(acc.append)
        lc.add_listener(acc.append)  # duplicate
        lc.create("pf-001")
        assert len(acc) == 1
        lc.stop()


# ===========================================================================
# PortfolioLifecycle — thread safety
# ===========================================================================

class TestPortfolioLifecycleThreadSafety:
    def test_concurrent_creates(self):
        lc      = _started_lc(max_active_sessions=200)
        errors  = []
        created = []

        def worker(i: int):
            try:
                s = lc.create(f"pf-{i}")
                created.append(s.session_id)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(errors)  == 0
        assert len(created) == 50
        lc.stop()

    def test_concurrent_statistics_reads(self):
        lc = _started_lc()
        lc.create("pf-1")

        errors = []

        def reader():
            try:
                lc.statistics()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(errors) == 0
        lc.stop()


# ===========================================================================
# Integration — full lifecycle scenario
# ===========================================================================

class TestFullLifecycleIntegration:
    def test_happy_path_completed_and_archived(self):
        lc = _started_lc()
        s  = _full_lifecycle_session(lc)
        assert s.state == PortfolioState.COMPLETED
        lc.archive(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.ARCHIVED
        snap = lc.statistics()
        assert snap["portfolio_sessions_created"]   >= 1
        assert snap["portfolio_sessions_completed"] >= 1
        assert snap["portfolio_sessions_archived"]  >= 1
        lc.stop()

    def test_fail_and_archive_path(self):
        lc = _started_lc()
        s  = lc.create("pf-fail")
        lc.initialize(s.session_id)
        lc.fail(s.session_id, reason="test")
        lc.archive(s.session_id)
        final = lc.get_session(s.session_id)
        assert final.state == PortfolioState.ARCHIVED
        lc.stop()

    def test_rebalance_path(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.initialize(s.session_id)
        lc.load(s.session_id)
        lc.validate_session(s.session_id)
        lc.ready(s.session_id)
        lc.activate(s.session_id)
        lc.rebalance(s.session_id)
        lc.complete(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.COMPLETED
        lc.stop()

    def test_pause_resume_path(self):
        lc = _started_lc()
        s  = lc.create("pf")
        lc.initialize(s.session_id)
        lc.load(s.session_id)
        lc.validate_session(s.session_id)
        lc.ready(s.session_id)
        lc.activate(s.session_id)
        lc.pause(s.session_id)
        lc.resume(s.session_id)
        lc.ready(s.session_id)
        lc.activate(s.session_id)
        lc.complete(s.session_id)
        assert lc.get_session(s.session_id).state == PortfolioState.COMPLETED
        lc.stop()

    def test_history_populated_after_full_path(self):
        lc     = _started_lc()
        _full_lifecycle_session(lc)
        h      = lc.history()
        types  = {e["event_type"] for e in h["events"]}
        assert "portfolio_created"   in types
        assert "portfolio_activated" in types
        assert "portfolio_completed" in types
        lc.stop()
