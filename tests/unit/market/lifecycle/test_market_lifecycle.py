"""
test_market_lifecycle.py
=========================
Unit tests for C12 M1 — Market Lifecycle.

Coverage:
  Constants, Exceptions, Session, State, Transition,
  Context, Metadata, Events, Factory, History,
  Statistics, Registry, Validation, Lifecycle,
  Concurrency, Regression

Target: 95%+ coverage, ~230 tests.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from iios.market.lifecycle import (
    # Primary interface
    MarketLifecycle,
    # Session
    MarketSession,
    # Value objects
    MarketContext,
    MarketMetadata,
    MarketStateRecord,
    MarketTransition,
    # Events
    MarketEvent,
    MarketEventType,
    make_market_archived,
    make_market_analysis_started,
    make_market_collected,
    make_market_completed,
    make_market_created,
    make_market_failed,
    make_market_initialized,
    make_market_monitoring_started,
    make_market_paused,
    make_market_resumed,
    make_market_validated,
    # Factory / Registry
    MarketFactory,
    MarketHistory,
    MarketRegistry,
    MarketStatistics,
    # Validation
    MarketValidationCheckResult,
    MarketValidationResult,
    MarketValidator,
    MarketValidationCode,
    # State helpers
    can_transition,
    make_transition,
    # Enums
    MarketPriority,
    MarketScope,
    MarketState,
    MarketTimeframe,
    MarketType,
    # Constants
    ACTIVE_STATES,
    TERMINAL_STATES,
    IMMUTABLE_STATES,
    SUCCESS_STATES,
    VALID_TRANSITIONS,
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    # Exceptions
    MarketCapacityExceededError,
    MarketHistoryError,
    MarketInvalidTransitionError,
    MarketLifecycleError,
    MarketLifecycleNotRunningError,
    MarketRegistryError,
    MarketSessionNotFoundError,
    MarketSessionTerminatedError,
    MarketValidationError,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_session(
    market_analysis_id: str = "MKT-001",
    exchange: str = "NSE",
    **kwargs,
) -> MarketSession:
    f = MarketFactory()
    return f.create(market_analysis_id, exchange=exchange, **kwargs)


def _started_lifecycle(**kwargs) -> MarketLifecycle:
    lc = MarketLifecycle(**kwargs)
    lc.start()
    return lc


def _full_session(lc: MarketLifecycle, analysis_id: str = "MKT-001") -> MarketSession:
    """Create and advance a session through the full happy path."""
    s = lc.create(analysis_id, exchange="NSE")
    lc.initialize(s.session_id)
    lc.collect(s.session_id)
    lc.validate_session(s.session_id)
    lc.mark_ready(s.session_id)
    lc.start_analysis(s.session_id)
    lc.start_monitoring(s.session_id)
    lc.complete(s.session_id)
    lc.archive(s.session_id)
    return s


# ============================================================================
# 1  CONSTANTS
# ============================================================================

class TestConstants:
    def test_system_id(self):
        assert LIFECYCLE_SYSTEM_ID == "iios:market:lifecycle"

    def test_version_format(self):
        parts = VERSION.split(".")
        assert len(parts) == 3

    def test_market_state_count(self):
        assert len(MarketState) == 12

    def test_market_type_count(self):
        assert len(MarketType) == 9

    def test_market_scope_count(self):
        assert len(MarketScope) == 7

    def test_market_priority_count(self):
        assert len(MarketPriority) == 4

    def test_market_timeframe_count(self):
        assert len(MarketTimeframe) == 11

    def test_market_event_type_count(self):
        assert len(MarketEventType) == 11

    def test_market_validation_code_count(self):
        assert len(MarketValidationCode) == 5

    def test_active_states_excludes_terminal(self):
        for s in ACTIVE_STATES:
            assert s not in TERMINAL_STATES

    def test_archived_is_immutable(self):
        assert MarketState.ARCHIVED in IMMUTABLE_STATES

    def test_archived_has_no_transitions(self):
        assert VALID_TRANSITIONS[MarketState.ARCHIVED] == frozenset()

    def test_all_states_in_valid_transitions(self):
        for state in MarketState:
            assert state in VALID_TRANSITIONS

    def test_success_states_subset_of_terminal(self):
        assert SUCCESS_STATES.issubset(TERMINAL_STATES)

    def test_created_can_transition_to_initializing(self):
        assert MarketState.INITIALIZING in VALID_TRANSITIONS[MarketState.CREATED]

    def test_created_can_transition_to_failed(self):
        assert MarketState.FAILED in VALID_TRANSITIONS[MarketState.CREATED]


# ============================================================================
# 2  EXCEPTIONS
# ============================================================================

class TestExceptions:
    def test_base_error_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(MarketLifecycleError, IIOSError)

    def test_base_error_code(self):
        exc = MarketLifecycleError("test")
        assert exc.error_code == "ML-000"

    def test_session_not_found_code(self):
        exc = MarketSessionNotFoundError("SID")
        assert exc.error_code == "ML-001"
        assert exc.session_id == "SID"

    def test_invalid_transition_code(self):
        exc = MarketInvalidTransitionError(
            MarketState.ARCHIVED, MarketState.CREATED, "SID"
        )
        assert exc.error_code == "ML-002"

    def test_invalid_transition_message(self):
        exc = MarketInvalidTransitionError(MarketState.CREATED, MarketState.MONITORING)
        assert "created" in str(exc).lower()
        assert "monitoring" in str(exc).lower()

    def test_session_terminated_code(self):
        exc = MarketSessionTerminatedError("SID", "archived")
        assert exc.error_code == "ML-003"

    def test_lifecycle_not_running_code(self):
        exc = MarketLifecycleNotRunningError()
        assert exc.error_code == "ML-004"

    def test_capacity_exceeded_code(self):
        exc = MarketCapacityExceededError(100)
        assert exc.error_code == "ML-005"
        assert exc.limit == 100

    def test_validation_error_code(self):
        exc = MarketValidationError("bad")
        assert exc.error_code == "ML-006"

    def test_all_subclass_base(self):
        for exc_cls in [
            MarketSessionNotFoundError,
            MarketInvalidTransitionError,
            MarketSessionTerminatedError,
            MarketLifecycleNotRunningError,
            MarketCapacityExceededError,
            MarketValidationError,
            MarketHistoryError,
            MarketRegistryError,
        ]:
            assert issubclass(exc_cls, MarketLifecycleError)


# ============================================================================
# 3  MARKET STATE RECORD & can_transition
# ============================================================================

class TestMarketState:
    def test_state_record_fields(self):
        r = MarketStateRecord(
            state      = MarketState.CREATED,
            entered_at = 1.0,
        )
        assert r.state      == MarketState.CREATED
        assert r.entered_at == 1.0
        assert r.version    == VERSION

    def test_state_record_to_dict(self):
        r = MarketStateRecord(
            state      = MarketState.ANALYZING,
            entered_at = 2.0,
            actor      = "test",
            reason     = "because",
        )
        d = r.to_dict()
        assert d["state"]  == "analyzing"
        assert d["actor"]  == "test"
        assert d["reason"] == "because"

    def test_state_record_is_frozen(self):
        r = MarketStateRecord(state=MarketState.CREATED, entered_at=0.0)
        with pytest.raises((AttributeError, TypeError)):
            r.state = MarketState.FAILED  # type: ignore[misc]

    def test_can_transition_valid(self):
        assert can_transition(MarketState.CREATED,      MarketState.INITIALIZING) is True
        assert can_transition(MarketState.INITIALIZING, MarketState.COLLECTING)   is True
        assert can_transition(MarketState.COLLECTING,   MarketState.VALIDATING)   is True
        assert can_transition(MarketState.VALIDATING,   MarketState.READY)        is True
        assert can_transition(MarketState.READY,        MarketState.ANALYZING)    is True
        assert can_transition(MarketState.ANALYZING,    MarketState.MONITORING)   is True
        assert can_transition(MarketState.MONITORING,   MarketState.COMPLETED)    is True
        assert can_transition(MarketState.COMPLETED,    MarketState.ARCHIVED)     is True

    def test_can_transition_invalid(self):
        assert can_transition(MarketState.CREATED,  MarketState.MONITORING) is False
        assert can_transition(MarketState.ARCHIVED, MarketState.CREATED)    is False
        assert can_transition(MarketState.COMPLETED,MarketState.ANALYZING)  is False

    def test_re_collect_from_validating_is_valid(self):
        assert can_transition(MarketState.VALIDATING, MarketState.COLLECTING) is True

    def test_re_analyze_from_monitoring_is_valid(self):
        assert can_transition(MarketState.MONITORING, MarketState.ANALYZING) is True

    def test_pause_from_ready(self):
        assert can_transition(MarketState.READY, MarketState.PAUSED) is True

    def test_resume_to_analyzing(self):
        assert can_transition(MarketState.RESUMING, MarketState.ANALYZING) is True

    def test_fail_from_any_active(self):
        for s in ACTIVE_STATES:
            assert can_transition(s, MarketState.FAILED) is True


# ============================================================================
# 4  MARKET TRANSITION
# ============================================================================

class TestMarketTransition:
    def test_make_transition(self):
        t = make_transition(
            "SID",
            MarketState.CREATED,
            MarketState.INITIALIZING,
            actor="test",
        )
        assert t.session_id == "SID"
        assert t.from_state == MarketState.CREATED
        assert t.to_state   == MarketState.INITIALIZING
        assert t.actor      == "test"
        assert uuid.UUID(t.transition_id)

    def test_transition_is_frozen(self):
        t = make_transition("S", MarketState.CREATED, MarketState.INITIALIZING)
        with pytest.raises((AttributeError, TypeError)):
            t.session_id = "X"  # type: ignore[misc]

    def test_to_dict(self):
        t = make_transition("S", MarketState.CREATED, MarketState.INITIALIZING)
        d = t.to_dict()
        assert d["from_state"] == "created"
        assert d["to_state"]   == "initializing"
        assert d["session_id"] == "S"

    def test_unique_ids(self):
        t1 = make_transition("S", MarketState.CREATED, MarketState.INITIALIZING)
        t2 = make_transition("S", MarketState.CREATED, MarketState.INITIALIZING)
        assert t1.transition_id != t2.transition_id

    def test_timestamp_set(self):
        before = time.time()
        t = make_transition("S", MarketState.CREATED, MarketState.INITIALIZING)
        after  = time.time()
        assert before <= t.transitioned_at <= after


# ============================================================================
# 5  MARKET CONTEXT
# ============================================================================

class TestMarketContext:
    def test_create_minimal(self):
        ctx = MarketContext.create("MKT-001")
        assert ctx.market_analysis_id == "MKT-001"
        assert uuid.UUID(ctx.context_id)

    def test_create_with_options(self):
        ctx = MarketContext.create(
            "MKT-002",
            workflow_id="WF-1",
            exchange="BSE",
            market_type=MarketType.EQUITY,
            market_scope=MarketScope.DOMESTIC,
            market_priority=MarketPriority.HIGH,
            timeframe=MarketTimeframe.H1,
        )
        assert ctx.exchange        == "BSE"
        assert ctx.market_type     == MarketType.EQUITY
        assert ctx.market_priority == MarketPriority.HIGH
        assert ctx.timeframe       == MarketTimeframe.H1

    def test_context_is_frozen(self):
        ctx = MarketContext.create("MKT-003")
        with pytest.raises((AttributeError, TypeError)):
            ctx.exchange = "NSE"  # type: ignore[misc]

    def test_to_dict(self):
        ctx = MarketContext.create("MKT-004", exchange="NSE")
        d   = ctx.to_dict()
        assert d["market_analysis_id"] == "MKT-004"
        assert d["exchange"]           == "NSE"

    def test_explicit_context_id(self):
        ctx = MarketContext.create("MKT-005", context_id="CTX-1")
        assert ctx.context_id == "CTX-1"


# ============================================================================
# 6  MARKET METADATA
# ============================================================================

class TestMarketMetadata:
    def test_create_defaults(self):
        m = MarketMetadata.create()
        assert m.analysis_id   == ""
        assert m.exchange      == ""
        assert m.tags          == {}

    def test_create_with_values(self):
        m = MarketMetadata.create(
            analysis_id   = "A-1",
            source        = "system",
            exchange      = "NSE",
            instrument_id = "NIFTY",
            tags          = {"sector": "index"},
            notes         = "test note",
        )
        assert m.analysis_id   == "A-1"
        assert m.exchange      == "NSE"
        assert m.tags["sector"] == "index"

    def test_is_frozen(self):
        m = MarketMetadata.create()
        with pytest.raises((AttributeError, TypeError)):
            m.notes = "modified"  # type: ignore[misc]

    def test_to_dict(self):
        m = MarketMetadata.create(analysis_id="A-1", exchange="NSE")
        d = m.to_dict()
        assert d["analysis_id"] == "A-1"
        assert d["exchange"]    == "NSE"


# ============================================================================
# 7  MARKET SESSION
# ============================================================================

class TestMarketSession:
    def test_create_in_created_state(self):
        s = _make_session()
        assert s.state        == MarketState.CREATED
        assert s.is_active    is False
        assert s.is_terminal  is False
        assert s.is_immutable is False

    def test_session_id_generated(self):
        s = _make_session()
        assert uuid.UUID(s.session_id)

    def test_explicit_session_id(self):
        s = _make_session(session_id="MY-SID")
        assert s.session_id == "MY-SID"

    def test_market_analysis_id(self):
        s = _make_session(market_analysis_id="MKT-999")
        assert s.market_analysis_id == "MKT-999"

    def test_exchange_field(self):
        s = _make_session(exchange="BSE")
        assert s.exchange == "BSE"

    def test_initial_state_history_has_one_entry(self):
        s = _make_session()
        assert len(s.state_history) == 1
        assert s.state_history[0].state == MarketState.CREATED

    def test_transition_to_initializing(self):
        s = _make_session()
        s.transition_to(MarketState.INITIALIZING)
        assert s.state == MarketState.INITIALIZING

    def test_transition_increments_version(self):
        s   = _make_session()
        v0  = s.market_version
        s.transition_to(MarketState.INITIALIZING)
        assert s.market_version == v0 + 1

    def test_transition_records_history(self):
        s = _make_session()
        s.transition_to(MarketState.INITIALIZING)
        assert len(s.state_history)  == 2
        assert len(s.transitions)    == 1

    def test_invalid_transition_raises(self):
        s = _make_session()
        with pytest.raises(MarketInvalidTransitionError):
            s.transition_to(MarketState.MONITORING)

    def test_archived_is_immutable(self):
        s = _make_session()
        s.transition_to(MarketState.INITIALIZING)
        s.transition_to(MarketState.COLLECTING)
        s.transition_to(MarketState.VALIDATING)
        s.transition_to(MarketState.READY)
        s.transition_to(MarketState.ANALYZING)
        s.transition_to(MarketState.COMPLETED)
        s.transition_to(MarketState.ARCHIVED)
        with pytest.raises(MarketSessionTerminatedError):
            s.transition_to(MarketState.FAILED)

    def test_mark_failed(self):
        s = _make_session()
        s.mark_failed("test failure")
        assert s.state          == MarketState.FAILED
        assert s.failure_reason == "test failure"

    def test_start_time_set_on_analyzing(self):
        s = _make_session()
        assert s.start_time is None
        s.transition_to(MarketState.INITIALIZING)
        s.transition_to(MarketState.COLLECTING)
        s.transition_to(MarketState.VALIDATING)
        s.transition_to(MarketState.READY)
        s.transition_to(MarketState.ANALYZING)
        assert s.start_time is not None

    def test_end_time_set_on_terminal(self):
        s = _make_session()
        s.transition_to(MarketState.FAILED)
        assert s.end_time is not None

    def test_duration_s_after_completion(self):
        s = _make_session()
        s.transition_to(MarketState.INITIALIZING)
        s.transition_to(MarketState.COLLECTING)
        s.transition_to(MarketState.VALIDATING)
        s.transition_to(MarketState.READY)
        s.transition_to(MarketState.ANALYZING)
        s.transition_to(MarketState.COMPLETED)
        assert s.duration_s is not None
        assert s.duration_s >= 0.0

    def test_duration_s_none_before_analyzing(self):
        s = _make_session()
        assert s.duration_s is None

    def test_is_active_in_active_states(self):
        s = _make_session()
        s.transition_to(MarketState.INITIALIZING)
        assert s.is_active is True

    def test_is_terminal_after_complete(self):
        s = _make_session()
        s.transition_to(MarketState.FAILED)
        assert s.is_terminal is True

    def test_is_successful_after_complete(self):
        s = _make_session()
        s.transition_to(MarketState.INITIALIZING)
        s.transition_to(MarketState.COLLECTING)
        s.transition_to(MarketState.VALIDATING)
        s.transition_to(MarketState.READY)
        s.transition_to(MarketState.ANALYZING)
        s.transition_to(MarketState.COMPLETED)
        assert s.is_successful is True

    def test_to_dict(self):
        s = _make_session()
        d = s.to_dict()
        assert "session_id"          in d
        assert "market_analysis_id"  in d
        assert "state"               in d
        assert d["state"]            == "created"

    def test_repr_contains_session_id(self):
        s    = _make_session(session_id="TEST-SID")
        text = repr(s)
        assert "TEST-SID" in text


# ============================================================================
# 8  EVENTS
# ============================================================================

class TestMarketEvents:
    def test_make_market_created(self):
        e = make_market_created("SID", "MKT-001", "NSE")
        assert e.event_type == MarketEventType.MARKET_CREATED
        assert e.state      == MarketState.CREATED

    def test_make_market_initialized(self):
        e = make_market_initialized("SID", "MKT-001", "NSE")
        assert e.event_type == MarketEventType.MARKET_INITIALIZED

    def test_make_market_collected(self):
        e = make_market_collected("SID", "MKT-001", "NSE")
        assert e.event_type == MarketEventType.MARKET_COLLECTED

    def test_make_market_validated(self):
        e = make_market_validated("SID", "MKT-001", "NSE")
        assert e.event_type == MarketEventType.MARKET_VALIDATED

    def test_make_market_analysis_started(self):
        e = make_market_analysis_started("SID", "MKT-001", "NSE")
        assert e.event_type == MarketEventType.MARKET_ANALYSIS_STARTED

    def test_make_market_monitoring_started(self):
        e = make_market_monitoring_started("SID", "MKT-001", "NSE")
        assert e.event_type == MarketEventType.MARKET_MONITORING_STARTED

    def test_make_market_paused(self):
        e = make_market_paused("SID", "MKT-001", "NSE")
        assert e.event_type == MarketEventType.MARKET_PAUSED

    def test_make_market_resumed(self):
        e = make_market_resumed("SID", "MKT-001", "NSE")
        assert e.event_type == MarketEventType.MARKET_RESUMED

    def test_make_market_completed(self):
        e = make_market_completed("SID", "MKT-001", "NSE")
        assert e.event_type == MarketEventType.MARKET_COMPLETED

    def test_make_market_failed(self):
        e = make_market_failed("SID", "MKT-001", "NSE")
        assert e.event_type == MarketEventType.MARKET_FAILED

    def test_make_market_archived(self):
        e = make_market_archived("SID", "MKT-001", "NSE")
        assert e.event_type == MarketEventType.MARKET_ARCHIVED

    def test_event_is_frozen(self):
        e = make_market_created("SID", "MKT-001", "NSE")
        with pytest.raises((AttributeError, TypeError)):
            e.session_id = "X"  # type: ignore[misc]

    def test_event_ids_unique(self):
        e1 = make_market_created("SID", "MKT-001", "NSE")
        e2 = make_market_created("SID", "MKT-001", "NSE")
        assert e1.event_id != e2.event_id

    def test_to_dict(self):
        e = make_market_created("SID", "MKT-001", "NSE")
        d = e.to_dict()
        assert d["session_id"]         == "SID"
        assert d["market_analysis_id"] == "MKT-001"
        assert d["exchange"]           == "NSE"
        assert d["event_type"]         == MarketEventType.MARKET_CREATED.value

    def test_payload_passthrough(self):
        e = make_market_created(
            "SID", "MKT-001", "NSE",
            payload={"actor": "system", "priority": "high"},
        )
        assert e.payload["actor"]    == "system"
        assert e.payload["priority"] == "high"


# ============================================================================
# 9  FACTORY
# ============================================================================

class TestMarketFactory:
    def test_create_minimal(self):
        f = MarketFactory()
        s = f.create("MKT-001")
        assert s.market_analysis_id == "MKT-001"
        assert s.state              == MarketState.CREATED

    def test_create_with_all_options(self):
        f = MarketFactory()
        s = f.create(
            "MKT-002",
            session_id      = "SID-1",
            workflow_id     = "WF-1",
            exchange        = "NSE",
            market_scope    = MarketScope.DOMESTIC,
            market_type     = MarketType.EQUITY,
            market_priority = MarketPriority.HIGH,
            timeframe       = MarketTimeframe.H1,
            market_version  = 3,
            metadata        = {"key": "val"},
        )
        assert s.session_id      == "SID-1"
        assert s.exchange        == "NSE"
        assert s.market_type     == MarketType.EQUITY
        assert s.market_version  == 3

    def test_empty_analysis_id_raises(self):
        f = MarketFactory()
        with pytest.raises(ValueError):
            f.create("")

    def test_auto_session_id(self):
        f  = MarketFactory()
        s1 = f.create("MKT-003")
        s2 = f.create("MKT-004")
        assert s1.session_id != s2.session_id


# ============================================================================
# 10  HISTORY
# ============================================================================

class TestMarketHistory:
    def test_record_and_retrieve_event(self):
        h = MarketHistory()
        e = make_market_created("SID", "MKT-001", "NSE")
        h.record_event(e)
        assert h.event_count() == 1
        assert h.latest_event() is e

    def test_events_for_session(self):
        h = MarketHistory()
        e = make_market_created("SID-1", "MKT-001", "NSE")
        h.record_event(e)
        h.record_event(make_market_created("SID-2", "MKT-002", "BSE"))
        assert len(h.events_for_session("SID-1")) == 1

    def test_events_by_type(self):
        h = MarketHistory()
        h.record_event(make_market_created("S1", "M1", "NSE"))
        h.record_event(make_market_initialized("S1", "M1", "NSE"))
        created = h.events_by_type(MarketEventType.MARKET_CREATED)
        assert len(created) == 1

    def test_events_for_exchange(self):
        h = MarketHistory()
        h.record_event(make_market_created("S1", "M1", "NSE"))
        h.record_event(make_market_created("S2", "M2", "BSE"))
        nse_events = h.events_for_exchange("NSE")
        assert len(nse_events) == 1

    def test_record_and_retrieve_transition(self):
        h = MarketHistory()
        t = make_transition("SID", MarketState.CREATED, MarketState.INITIALIZING)
        h.record_transition(t)
        assert h.transition_count() == 1
        assert h.latest_transition() is t

    def test_transitions_for_session(self):
        h = MarketHistory()
        t1 = make_transition("SID-1", MarketState.CREATED, MarketState.INITIALIZING)
        t2 = make_transition("SID-2", MarketState.CREATED, MarketState.INITIALIZING)
        h.record_transition(t1)
        h.record_transition(t2)
        assert len(h.transitions_for_session("SID-1")) == 1

    def test_bounded_by_max_events(self):
        h = MarketHistory(max_events=3)
        for i in range(5):
            h.record_event(make_market_created(f"S{i}", "M", "NSE"))
        assert h.event_count() == 3

    def test_clear(self):
        h = MarketHistory()
        h.record_event(make_market_created("S", "M", "NSE"))
        h.record_transition(make_transition("S", MarketState.CREATED, MarketState.INITIALIZING))
        h.clear()
        assert h.event_count()      == 0
        assert h.transition_count() == 0

    def test_thread_safe(self):
        h      = MarketHistory()
        errors: List[str] = []

        def worker(i: int):
            try:
                h.record_event(make_market_created(f"S{i}", "M", "NSE"))
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert h.event_count() == 50
        assert errors == []


# ============================================================================
# 11  STATISTICS
# ============================================================================

class TestMarketStatistics:
    def test_initial_zeros(self):
        s = MarketStatistics()
        snap = s.snapshot()
        assert snap["market_sessions_created"]   == 0
        assert snap["market_sessions_completed"] == 0
        assert snap["market_sessions_failed"]    == 0
        assert snap["market_sessions_archived"]  == 0
        assert snap["transition_count"]          == 0

    def test_record_created(self):
        s = MarketStatistics()
        s.record_session_created()
        s.record_session_created()
        assert s.snapshot()["market_sessions_created"] == 2

    def test_record_completed(self):
        s = MarketStatistics()
        s.record_session_completed(duration_s=10.0)
        snap = s.snapshot()
        assert snap["market_sessions_completed"]  == 1
        assert snap["average_session_duration_s"] == pytest.approx(10.0)

    def test_record_failed(self):
        s = MarketStatistics()
        s.record_session_failed()
        assert s.snapshot()["market_sessions_failed"] == 1

    def test_record_archived(self):
        s = MarketStatistics()
        s.record_session_archived()
        assert s.snapshot()["market_sessions_archived"] == 1

    def test_record_transition(self):
        s = MarketStatistics()
        s.record_transition()
        s.record_transition()
        assert s.snapshot()["transition_count"] == 2

    def test_ema_duration(self):
        s = MarketStatistics()
        s.record_session_completed(duration_s=10.0)
        s.record_session_completed(duration_s=20.0)
        snap = s.snapshot()
        # EMA should be between 10 and 20
        assert 10.0 <= snap["ema_session_duration_s"] <= 20.0

    def test_uptime_positive(self):
        s = MarketStatistics()
        assert s.snapshot()["uptime_s"] >= 0.0

    def test_reset(self):
        s = MarketStatistics()
        s.record_session_created()
        s.record_session_failed()
        s.reset()
        snap = s.snapshot()
        assert snap["market_sessions_created"] == 0
        assert snap["market_sessions_failed"]  == 0

    def test_thread_safe(self):
        stats  = MarketStatistics()
        errors: List[str] = []

        def worker():
            for _ in range(100):
                stats.record_session_created()

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.snapshot()["market_sessions_created"] == 1000
        assert errors == []


# ============================================================================
# 12  REGISTRY
# ============================================================================

class TestMarketRegistry:
    def test_add_and_get(self):
        reg = MarketRegistry()
        s   = _make_session()
        reg.add(s)
        found = reg.get(s.session_id)
        assert found is s

    def test_get_not_found_raises(self):
        reg = MarketRegistry()
        with pytest.raises(MarketSessionNotFoundError):
            reg.get("GHOST")

    def test_find_returns_none(self):
        reg = MarketRegistry()
        assert reg.find("GHOST") is None

    def test_duplicate_raises(self):
        reg = MarketRegistry()
        s   = _make_session()
        reg.add(s)
        with pytest.raises(MarketRegistryError):
            reg.add(s)

    def test_capacity_limit(self):
        reg = MarketRegistry(max_active_sessions=2)
        reg.add(_make_session(session_id="S1"))
        reg.add(_make_session(session_id="S2"))
        with pytest.raises(MarketCapacityExceededError):
            reg.add(_make_session(session_id="S3"))

    def test_archive_moves_to_archived(self):
        reg = MarketRegistry()
        s   = _make_session()
        reg.add(s)
        reg.archive(s.session_id)
        assert reg.active_count()   == 0
        assert reg.archived_count() == 1
        # Still retrievable via get()
        assert reg.get(s.session_id) is s

    def test_get_active_after_archive_raises(self):
        reg = MarketRegistry()
        s   = _make_session()
        reg.add(s)
        reg.archive(s.session_id)
        with pytest.raises(MarketSessionNotFoundError):
            reg.get_active(s.session_id)

    def test_sessions_by_state(self):
        reg = MarketRegistry()
        s1  = _make_session(session_id="S1")
        s2  = _make_session(session_id="S2")
        reg.add(s1)
        reg.add(s2)
        s1.transition_to(MarketState.INITIALIZING)
        assert len(reg.sessions_by_state(MarketState.CREATED))      == 1
        assert len(reg.sessions_by_state(MarketState.INITIALIZING)) == 1

    def test_sessions_by_exchange(self):
        reg = MarketRegistry()
        s1  = _make_session(session_id="S1", exchange="NSE")
        s2  = _make_session(session_id="S2", exchange="BSE")
        reg.add(s1)
        reg.add(s2)
        assert len(reg.sessions_by_exchange("NSE")) == 1
        assert len(reg.sessions_by_exchange("BSE")) == 1

    def test_contains(self):
        reg = MarketRegistry()
        s   = _make_session()
        assert not reg.contains(s.session_id)
        reg.add(s)
        assert reg.contains(s.session_id)

    def test_clear(self):
        reg = MarketRegistry()
        reg.add(_make_session(session_id="S1"))
        reg.clear()
        assert reg.active_count() == 0

    def test_archive_capacity_evicts_oldest(self):
        reg = MarketRegistry(max_archived_sessions=2)
        sids = [f"S{i}" for i in range(3)]
        for sid in sids:
            s = _make_session(session_id=sid)
            reg.add(s)
            reg.archive(sid)
        assert reg.archived_count() == 2

    def test_thread_safe(self):
        reg    = MarketRegistry(max_active_sessions=200)
        errors: List[str] = []
        lock   = threading.Lock()

        def worker(i: int):
            try:
                s = _make_session(session_id=f"SID-{i}")
                reg.add(s)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors      == []
        assert reg.active_count() == 100


# ============================================================================
# 13  VALIDATION
# ============================================================================

class TestMarketValidation:
    def test_fresh_session_is_valid(self):
        v = MarketValidator()
        s = _make_session()
        r = v.validate(s)
        assert r.is_valid     is True
        assert r.failed_count == 0
        assert r.passed_count == 5

    def test_transitioned_session_is_valid(self):
        v = MarketValidator()
        s = _make_session()
        s.transition_to(MarketState.INITIALIZING)
        r = v.validate(s)
        assert r.is_valid is True

    def test_result_checks_count(self):
        v = MarketValidator()
        s = _make_session()
        r = v.validate(s)
        assert len(r.checks) == 5

    def test_failed_checks_attribute(self):
        v = MarketValidator()
        s = _make_session()
        r = v.validate(s)
        assert r.failed_checks == ()

    def test_error_messages_empty_when_valid(self):
        v = MarketValidator()
        s = _make_session()
        r = v.validate(s)
        assert r.error_messages == []

    def test_check_codes_covered(self):
        v = MarketValidator()
        s = _make_session()
        r = v.validate(s)
        codes = {c.code for c in r.checks}
        assert codes == set(MarketValidationCode)


# ============================================================================
# 14  LIFECYCLE — initialization
# ============================================================================

class TestLifecycleInitialization:
    def test_create_default(self):
        lc = MarketLifecycle()
        assert lc is not None

    def test_initial_state_not_running(self):
        lc = MarketLifecycle()
        assert lc.lifecycle_state().value != "running"

    def test_start_transitions_to_running(self):
        lc = MarketLifecycle()
        lc.start()
        assert lc.lifecycle_state().value == "running"
        lc.stop()

    def test_stop_transitions_out_of_running(self):
        lc = _started_lifecycle()
        lc.stop()
        assert lc.lifecycle_state().value != "running"

    def test_create_before_start_raises(self):
        lc = MarketLifecycle()
        with pytest.raises(MarketLifecycleNotRunningError):
            lc.create("MKT-001")


# ============================================================================
# 15  LIFECYCLE — session creation
# ============================================================================

class TestLifecycleSessionCreation:
    def test_create_returns_session(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        assert isinstance(s, MarketSession)
        lc.stop()

    def test_create_state_is_created(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        assert s.state == MarketState.CREATED
        lc.stop()

    def test_create_with_exchange(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001", exchange="NSE")
        assert s.exchange == "NSE"
        lc.stop()

    def test_create_emits_event(self):
        lc     = _started_lifecycle()
        events: List[MarketEvent] = []
        lc.add_listener(events.append)
        lc.create("MKT-001")
        assert any(e.event_type == MarketEventType.MARKET_CREATED for e in events)
        lc.stop()

    def test_create_increments_stats(self):
        lc = _started_lifecycle()
        lc.create("MKT-001")
        lc.create("MKT-002")
        assert lc.statistics()["market_sessions_created"] == 2
        lc.stop()

    def test_create_with_all_options(self):
        lc = _started_lifecycle()
        s  = lc.create(
            "MKT-001",
            exchange        = "BSE",
            market_type     = MarketType.EQUITY,
            market_scope    = MarketScope.DOMESTIC,
            market_priority = MarketPriority.HIGH,
            timeframe       = MarketTimeframe.H1,
        )
        assert s.market_type     == MarketType.EQUITY
        assert s.market_priority == MarketPriority.HIGH
        lc.stop()


# ============================================================================
# 16  LIFECYCLE — happy path transitions
# ============================================================================

class TestLifecycleTransitions:
    def test_initialize(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.initialize(s.session_id)
        assert s.state == MarketState.INITIALIZING
        lc.stop()

    def test_collect(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        assert s.state == MarketState.COLLECTING
        lc.stop()

    def test_validate_session(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        assert s.state == MarketState.VALIDATING
        lc.stop()

    def test_mark_ready(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        assert s.state == MarketState.READY
        lc.stop()

    def test_start_analysis(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_analysis(s.session_id)
        assert s.state == MarketState.ANALYZING
        lc.stop()

    def test_start_monitoring(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_analysis(s.session_id)
        lc.start_monitoring(s.session_id)
        assert s.state == MarketState.MONITORING
        lc.stop()

    def test_complete(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_analysis(s.session_id)
        lc.start_monitoring(s.session_id)
        lc.complete(s.session_id)
        assert s.state == MarketState.COMPLETED
        lc.stop()

    def test_archive(self):
        lc = _started_lifecycle()
        s  = _full_session(lc)
        assert s.state == MarketState.ARCHIVED
        lc.stop()

    def test_full_cycle_statistics(self):
        lc = _started_lifecycle()
        _full_session(lc)
        snap = lc.statistics()
        assert snap["market_sessions_created"]  == 1
        assert snap["market_sessions_completed"] == 1
        assert snap["market_sessions_archived"]  == 1
        assert snap["transition_count"]          == 8  # 8 transitions
        lc.stop()


# ============================================================================
# 17  LIFECYCLE — pause / resume
# ============================================================================

class TestLifecyclePauseResume:
    def _get_ready_session(self, lc: MarketLifecycle) -> MarketSession:
        s = lc.create("MKT-001")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        return s

    def test_pause_from_ready(self):
        lc = _started_lifecycle()
        s  = self._get_ready_session(lc)
        lc.pause(s.session_id)
        assert s.state == MarketState.PAUSED
        lc.stop()

    def test_resume_from_paused(self):
        lc = _started_lifecycle()
        s  = self._get_ready_session(lc)
        lc.pause(s.session_id)
        lc.resume(s.session_id)
        assert s.state == MarketState.RESUMING
        lc.stop()

    def test_resume_to_analyzing(self):
        lc = _started_lifecycle()
        s  = self._get_ready_session(lc)
        lc.pause(s.session_id)
        lc.resume(s.session_id)
        lc.start_analysis(s.session_id)
        assert s.state == MarketState.ANALYZING
        lc.stop()

    def test_pause_from_analyzing(self):
        lc = _started_lifecycle()
        s  = self._get_ready_session(lc)
        lc.start_analysis(s.session_id)
        lc.pause(s.session_id)
        assert s.state == MarketState.PAUSED
        lc.stop()


# ============================================================================
# 18  LIFECYCLE — failure path
# ============================================================================

class TestLifecycleFailure:
    def test_fail_from_created(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.fail(s.session_id, reason="bad data")
        assert s.state          == MarketState.FAILED
        assert s.failure_reason == "bad data"
        lc.stop()

    def test_fail_increments_stats(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.fail(s.session_id)
        assert lc.statistics()["market_sessions_failed"] == 1
        lc.stop()

    def test_fail_emits_event(self):
        lc     = _started_lifecycle()
        events: List[MarketEvent] = []
        lc.add_listener(events.append)
        s = lc.create("MKT-001")
        lc.fail(s.session_id, reason="test")
        assert any(e.event_type == MarketEventType.MARKET_FAILED for e in events)
        lc.stop()

    def test_fail_then_archive(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.fail(s.session_id)
        lc.archive(s.session_id)
        assert s.state == MarketState.ARCHIVED
        lc.stop()

    def test_session_not_found_raises(self):
        lc = _started_lifecycle()
        with pytest.raises(MarketSessionNotFoundError):
            lc.fail("GHOST")
        lc.stop()


# ============================================================================
# 19  LIFECYCLE — events and listeners
# ============================================================================

class TestLifecycleEvents:
    def test_listener_receives_events(self):
        events: List[MarketEvent] = []
        lc = _started_lifecycle()
        lc.add_listener(events.append)
        s = lc.create("MKT-001")
        lc.initialize(s.session_id)
        assert len(events) >= 2
        lc.stop()

    def test_remove_listener(self):
        events: List[MarketEvent] = []
        lc = _started_lifecycle()
        lc.add_listener(events.append)
        lc.remove_listener(events.append)
        lc.create("MKT-001")
        assert events == []
        lc.stop()

    def test_faulty_listener_does_not_crash(self):
        def bad(evt):
            raise RuntimeError("I crash")
        lc = _started_lifecycle()
        lc.add_listener(bad)
        s  = lc.create("MKT-001")
        lc.initialize(s.session_id)  # must not raise
        lc.stop()

    def test_all_event_types_emitted_in_happy_path(self):
        emitted: List[MarketEventType] = []
        lc = _started_lifecycle()
        lc.add_listener(lambda e: emitted.append(e.event_type))
        _full_session(lc)
        expected = {
            MarketEventType.MARKET_CREATED,
            MarketEventType.MARKET_INITIALIZED,
            MarketEventType.MARKET_COLLECTED,
            MarketEventType.MARKET_VALIDATED,
            MarketEventType.MARKET_ANALYSIS_STARTED,
            MarketEventType.MARKET_MONITORING_STARTED,
            MarketEventType.MARKET_COMPLETED,
            MarketEventType.MARKET_ARCHIVED,
        }
        assert expected.issubset(set(emitted))
        lc.stop()


# ============================================================================
# 20  LIFECYCLE — query API
# ============================================================================

class TestLifecycleQuery:
    def test_get_session(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        assert lc.get_session(s.session_id) is s
        lc.stop()

    def test_find_session_returns_none(self):
        lc = _started_lifecycle()
        assert lc.find_session("GHOST") is None
        lc.stop()

    def test_active_sessions(self):
        lc = _started_lifecycle()
        lc.create("MKT-001")
        lc.create("MKT-002")
        assert len(lc.active_sessions()) == 2
        lc.stop()

    def test_sessions_by_state(self):
        lc = _started_lifecycle()
        s1 = lc.create("MKT-001")
        s2 = lc.create("MKT-002")
        lc.initialize(s2.session_id)
        created = lc.sessions_by_state(MarketState.CREATED)
        assert len(created) == 1
        lc.stop()

    def test_sessions_by_exchange(self):
        lc = _started_lifecycle()
        lc.create("MKT-001", exchange="NSE")
        lc.create("MKT-002", exchange="BSE")
        assert len(lc.sessions_by_exchange("NSE")) == 1
        lc.stop()

    def test_validate_session(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        r  = lc.validate(s.session_id)
        assert r.is_valid is True
        lc.stop()


# ============================================================================
# 21  CONCURRENCY
# ============================================================================

class TestConcurrency:
    def test_concurrent_session_creation(self):
        lc     = _started_lifecycle()
        errors: List[str] = []
        lock   = threading.Lock()
        sessions: List[MarketSession] = []

        def worker(i: int):
            try:
                s = lc.create(f"MKT-{i}", exchange=f"EX-{i}")
                with lock:
                    sessions.append(s)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lc.stop()
        assert errors == []
        assert len(sessions) == 30
        assert lc.statistics()["market_sessions_created"] == 30

    def test_concurrent_transitions(self):
        lc     = _started_lifecycle()
        errors: List[str] = []
        lock   = threading.Lock()

        sessions = [lc.create(f"MKT-{i}") for i in range(20)]

        def worker(s: MarketSession):
            try:
                lc.initialize(s.session_id)
                lc.collect(s.session_id)
                lc.validate_session(s.session_id)
                lc.mark_ready(s.session_id)
                lc.start_analysis(s.session_id)
                lc.complete(s.session_id)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(s,)) for s in sessions]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lc.stop()
        assert errors == []

    def test_concurrent_statistics(self):
        stats  = MarketStatistics()
        errors: List[str] = []

        def worker():
            for _ in range(200):
                stats.record_session_created()

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert stats.snapshot()["market_sessions_created"] == 1000
        assert errors == []


# ============================================================================
# 22  REGRESSION
# ============================================================================

class TestRegression:
    def test_full_happy_path(self):
        lc = _started_lifecycle()
        s  = _full_session(lc)
        assert s.state == MarketState.ARCHIVED
        lc.stop()

    def test_transitions_list_immutable_copy(self):
        """Mutating the returned list must not affect the session."""
        s   = _make_session()
        lst = s.transitions
        lst.append("fake")
        assert len(s.transitions) == 0

    def test_state_history_immutable_copy(self):
        s = _make_session()
        h = s.state_history
        h.append("fake")  # type: ignore[arg-type]
        assert len(s.state_history) == 1

    def test_re_collect_from_validating(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.collect(s.session_id)   # allowed re-collect
        assert s.state == MarketState.COLLECTING
        lc.stop()

    def test_re_analyze_from_monitoring(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        lc.validate_session(s.session_id)
        lc.mark_ready(s.session_id)
        lc.start_analysis(s.session_id)
        lc.start_monitoring(s.session_id)
        lc.start_analysis(s.session_id)   # re-analyze allowed
        assert s.state == MarketState.ANALYZING
        lc.stop()

    def test_events_recorded_in_history(self):
        lc = _started_lifecycle()
        _full_session(lc)
        assert lc.statistics()["transition_count"] == 8
        assert len(lc.events()) >= 8
        lc.stop()

    def test_multiple_sessions_independent(self):
        lc = _started_lifecycle()
        s1 = lc.create("MKT-001", exchange="NSE")
        s2 = lc.create("MKT-002", exchange="BSE")
        lc.initialize(s1.session_id)
        assert s1.state == MarketState.INITIALIZING
        assert s2.state == MarketState.CREATED
        lc.stop()

    def test_session_state_history_correct_sequence(self):
        lc = _started_lifecycle()
        s  = lc.create("MKT-001")
        lc.initialize(s.session_id)
        lc.collect(s.session_id)
        history = s.state_history
        assert history[0].state == MarketState.CREATED
        assert history[1].state == MarketState.INITIALIZING
        assert history[2].state == MarketState.COLLECTING
        lc.stop()

    def test_recent_events(self):
        lc = _started_lifecycle()
        _full_session(lc)
        recent = lc.recent_events(3)
        assert len(recent) <= 3
        lc.stop()
