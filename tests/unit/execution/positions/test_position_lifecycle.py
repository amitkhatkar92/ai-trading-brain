"""tests/unit/execution/positions/test_position_lifecycle.py
==================================================
Test suite for C6 Phase 3 M1 — IIOS Position Lifecycle.

Coverage targets:
  * PositionState enum and state machine (VALID_TRANSITIONS)
  * Position domain object — construction, transitions, updates
  * InvalidTransitionError raised for every disallowed transition
  * PositionHistory — append, filtering, eviction, recovery count
  * PositionStateRecord — duration_ms, with_exit, is_current
  * PositionTransition — factory, is_valid, is_recovery, is_terminal
  * PositionEvent — all 7 factory functions
  * PositionMetadata — tag CRUD, notes, version increment
  * PositionStatistics — all counters, derived properties
  * PositionContext — make_context, properties
  * PositionValidator — all validation sub-methods + full
  * PositionFactory — create, create_long, create_short, errors
  * PositionRegistry — CRUD, filtering, statistics, lifecycle guard
  * Thread-safety — concurrent transitions and registry operations
  * Regression guards — edge cases and boundary conditions

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

import threading
import time
import uuid
from decimal import Decimal
from typing import List

import pytest

from iios.execution.positions.lifecycle import (
    ACTIVE_STATES,
    CLOSED_STATES,
    SUSPENDED_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VERSION,
    DuplicatePositionError,
    InvalidTransitionError,
    Position,
    PositionContext,
    PositionDirection,
    PositionEvent,
    PositionEventType,
    PositionFactory,
    PositionHistory,
    PositionLifecycleError,
    PositionMetadata,
    PositionNotFoundError,
    PositionNotRunningError,
    PositionProduct,
    PositionRegistryCapacityError,
    PositionRegistry,
    PositionState,
    PositionStateError,
    PositionStateRecord,
    PositionStatistics,
    PositionTransition,
    PositionValidationError,
    PositionValidator,
    ValidationResult,
    make_context,
    make_position_archived,
    make_position_closed,
    make_position_created,
    make_position_opened,
    make_position_partially_closed,
    make_position_recovered,
    make_position_updated,
    make_transition,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_position(
    instrument: str = "NIFTY50",
    direction: PositionDirection = PositionDirection.LONG,
    quantity: Decimal = Decimal("100"),
    **kwargs,
) -> Position:
    factory = PositionFactory()
    return factory.create(
        instrument=instrument,
        exchange="NSE",
        product=PositionProduct.FUTURES,
        direction=direction,
        quantity=quantity,
        portfolio_id="portfolio-1",
        strategy_id="strat-1",
        decision_id="dec-1",
        workflow_id="wf-1",
        execution_id="exec-1",
        **kwargs,
    )


def _started_registry(max_positions: int = 1_000) -> PositionRegistry:
    reg = PositionRegistry(max_positions=max_positions)
    reg.start()
    return reg


# ══════════════════════════════════════════════════════════════════════════════
# PositionState
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionState:
    def test_all_ten_states_defined(self):
        states = list(PositionState)
        assert len(states) == 10

    def test_state_values_are_uppercase_strings(self):
        for s in PositionState:
            assert s.value == s.value.upper()
            assert isinstance(s.value, str)

    def test_terminal_states_has_only_archived(self):
        assert TERMINAL_STATES == frozenset({PositionState.ARCHIVED})

    def test_active_states_coverage(self):
        assert PositionState.OPEN in ACTIVE_STATES
        assert PositionState.OPENING in ACTIVE_STATES
        assert PositionState.PARTIALLY_CLOSED in ACTIVE_STATES
        assert PositionState.CLOSING in ACTIVE_STATES

    def test_suspended_states_coverage(self):
        assert PositionState.SUSPENDED in SUSPENDED_STATES
        assert PositionState.RECOVERING in SUSPENDED_STATES
        assert PositionState.RECOVERED in SUSPENDED_STATES

    def test_closed_states_coverage(self):
        assert PositionState.CLOSED in CLOSED_STATES
        assert PositionState.ARCHIVED in CLOSED_STATES

    def test_all_states_in_valid_transitions(self):
        for state in PositionState:
            assert state in VALID_TRANSITIONS

    def test_archived_has_no_outgoing_transitions(self):
        assert len(VALID_TRANSITIONS[PositionState.ARCHIVED]) == 0

    def test_created_transitions_only_to_opening(self):
        assert VALID_TRANSITIONS[PositionState.CREATED] == frozenset({PositionState.OPENING})


# ══════════════════════════════════════════════════════════════════════════════
# PositionStateRecord
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionStateRecord:
    def test_is_current_when_no_exit(self):
        rec = PositionStateRecord(state=PositionState.OPEN, entered_at=time.time())
        assert rec.is_current is True

    def test_not_current_after_exit(self):
        t = time.time()
        rec = PositionStateRecord(state=PositionState.OPEN, entered_at=t, exited_at=t + 1.0)
        assert rec.is_current is False

    def test_duration_ms_none_when_current(self):
        rec = PositionStateRecord(state=PositionState.OPEN, entered_at=time.time())
        assert rec.duration_ms is None

    def test_duration_ms_correct(self):
        t = time.time()
        rec = PositionStateRecord(state=PositionState.OPEN, entered_at=t, exited_at=t + 2.0)
        assert abs(rec.duration_ms - 2000.0) < 1.0

    def test_with_exit_returns_new_record(self):
        t = time.time()
        rec = PositionStateRecord(state=PositionState.OPEN, entered_at=t)
        closed = rec.with_exit(t + 5.0)
        assert closed.exited_at == pytest.approx(t + 5.0)
        assert rec.is_current  # original unchanged

    def test_with_exit_auto_timestamp(self):
        rec = PositionStateRecord(state=PositionState.OPEN, entered_at=time.time())
        closed = rec.with_exit()
        assert closed.exited_at is not None
        assert closed.exited_at >= rec.entered_at

    def test_to_dict_keys(self):
        rec = PositionStateRecord(state=PositionState.CREATED, entered_at=time.time())
        d = rec.to_dict()
        assert "state" in d and "entered_at" in d and "duration_ms" in d


# ══════════════════════════════════════════════════════════════════════════════
# PositionTransition
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionTransition:
    def test_make_transition_basic(self):
        t = make_transition("p1", PositionState.CREATED, PositionState.OPENING)
        assert t.position_id == "p1"
        assert t.from_state  == PositionState.CREATED
        assert t.to_state    == PositionState.OPENING
        assert uuid.UUID(t.transition_id)   # valid UUID

    def test_is_valid_true_for_allowed(self):
        t = make_transition("p", PositionState.OPEN, PositionState.CLOSING)
        assert t.is_valid is True

    def test_is_valid_false_for_disallowed(self):
        t = make_transition("p", PositionState.OPEN, PositionState.ARCHIVED)
        assert t.is_valid is False

    def test_is_terminal_for_archived(self):
        t = make_transition("p", PositionState.CLOSED, PositionState.ARCHIVED)
        assert t.is_terminal is True

    def test_is_not_terminal_for_open(self):
        t = make_transition("p", PositionState.OPENING, PositionState.OPEN)
        assert t.is_terminal is False

    def test_is_recovery_for_recovering(self):
        t = make_transition("p", PositionState.CLOSING, PositionState.RECOVERING)
        assert t.is_recovery is True

    def test_is_recovery_for_recovered(self):
        t = make_transition("p", PositionState.RECOVERING, PositionState.RECOVERED)
        assert t.is_recovery is True

    def test_is_not_recovery_for_open(self):
        t = make_transition("p", PositionState.OPENING, PositionState.OPEN)
        assert t.is_recovery is False

    def test_to_dict_has_required_keys(self):
        t = make_transition("p", PositionState.OPEN, PositionState.CLOSING)
        d = t.to_dict()
        for k in ("transition_id", "position_id", "from_state", "to_state",
                  "triggered_at", "actor", "reason", "metadata"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# PositionEvent
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionEvent:
    def _assert_event(self, event: PositionEvent, expected_type: PositionEventType):
        assert event.event_type == expected_type
        assert uuid.UUID(event.event_id)
        assert event.occurred_at > 0

    def test_make_position_created(self):
        e = make_position_created("p1", portfolio_id="port", strategy_id="strat")
        self._assert_event(e, PositionEventType.POSITION_CREATED)
        assert e.position_id == "p1"

    def test_make_position_opened(self):
        e = make_position_opened("p1")
        self._assert_event(e, PositionEventType.POSITION_OPENED)

    def test_make_position_updated(self):
        e = make_position_updated("p1", state=PositionState.OPENING)
        self._assert_event(e, PositionEventType.POSITION_UPDATED)
        assert e.state == PositionState.OPENING

    def test_make_position_partially_closed(self):
        e = make_position_partially_closed("p1")
        self._assert_event(e, PositionEventType.POSITION_PARTIALLY_CLOSED)

    def test_make_position_closed(self):
        e = make_position_closed("p1")
        self._assert_event(e, PositionEventType.POSITION_CLOSED)

    def test_make_position_recovered(self):
        e = make_position_recovered("p1")
        self._assert_event(e, PositionEventType.POSITION_RECOVERED)

    def test_make_position_archived(self):
        e = make_position_archived("p1")
        self._assert_event(e, PositionEventType.POSITION_ARCHIVED)

    def test_all_seven_event_types_covered(self):
        # All PositionEventType values have a factory function
        assert len(list(PositionEventType)) == 7

    def test_to_dict_keys(self):
        e = make_position_created("p1")
        d = e.to_dict()
        for k in ("event_id", "event_type", "position_id", "state", "actor", "occurred_at"):
            assert k in d


# ══════════════════════════════════════════════════════════════════════════════
# PositionHistory
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionHistory:
    def test_empty_on_init(self):
        h = PositionHistory()
        assert len(h) == 0
        assert h.transitions() == []

    def test_append_transition(self):
        h = PositionHistory()
        t = make_transition("p", PositionState.CREATED, PositionState.OPENING)
        h.append_transition(t)
        assert len(h) == 1
        assert h.transitions()[0] is t

    def test_append_state(self):
        h = PositionHistory()
        s = PositionStateRecord(state=PositionState.CREATED, entered_at=time.time())
        h.append_state(s)
        assert len(h.states()) == 1

    def test_update_last_state_exit(self):
        h = PositionHistory()
        now = time.time()
        s = PositionStateRecord(state=PositionState.OPEN, entered_at=now)
        h.append_state(s)
        h.update_last_state_exit(now + 1.0)
        assert h.states()[-1].exited_at == pytest.approx(now + 1.0)

    def test_transitions_to(self):
        h = PositionHistory()
        h.append_transition(make_transition("p", PositionState.CREATED, PositionState.OPENING))
        h.append_transition(make_transition("p", PositionState.OPENING, PositionState.OPEN))
        result = h.transitions_to(PositionState.OPEN)
        assert len(result) == 1
        assert result[0].to_state == PositionState.OPEN

    def test_transitions_from(self):
        h = PositionHistory()
        h.append_transition(make_transition("p", PositionState.CREATED, PositionState.OPENING))
        result = h.transitions_from(PositionState.CREATED)
        assert len(result) == 1

    def test_latest_transition(self):
        h = PositionHistory()
        t1 = make_transition("p", PositionState.CREATED, PositionState.OPENING)
        t2 = make_transition("p", PositionState.OPENING, PositionState.OPEN)
        h.append_transition(t1)
        h.append_transition(t2)
        latest = h.latest_transition(1)
        assert latest[0] is t2

    def test_eviction_when_at_capacity(self):
        h = PositionHistory(max_size=2)
        for from_s, to_s in [
            (PositionState.CREATED, PositionState.OPENING),
            (PositionState.OPENING, PositionState.OPEN),
            (PositionState.OPEN, PositionState.CLOSING),
        ]:
            h.append_transition(make_transition("p", from_s, to_s))
        assert len(h) == 2
        assert h.evicted_transitions == 1

    def test_total_transitions_includes_evicted(self):
        h = PositionHistory(max_size=1)
        h.append_transition(make_transition("p", PositionState.CREATED, PositionState.OPENING))
        h.append_transition(make_transition("p", PositionState.OPENING, PositionState.OPEN))
        assert h.total_transitions == 2

    def test_recovery_count(self):
        h = PositionHistory()
        h.append_transition(make_transition("p", PositionState.CLOSING, PositionState.RECOVERING))
        h.append_transition(make_transition("p", PositionState.RECOVERING, PositionState.RECOVERED))
        assert h.recovery_count == 2

    def test_iter(self):
        h = PositionHistory()
        t = make_transition("p", PositionState.CREATED, PositionState.OPENING)
        h.append_transition(t)
        items = list(h)
        assert items[0] is t


# ══════════════════════════════════════════════════════════════════════════════
# PositionStatistics
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionStatistics:
    def test_initial_values_are_zero(self):
        s = PositionStatistics()
        assert s.positions_created    == 0
        assert s.positions_opened     == 0
        assert s.positions_closed     == 0
        assert s.total_transitions    == 0
        assert s.recovery_count       == 0

    def test_record_created_increments(self):
        s = PositionStatistics()
        s.record_created(Decimal("50"))
        assert s.positions_created   == 1
        assert s.total_position_size == Decimal("50")

    def test_average_holding_time_zero_when_no_closes(self):
        s = PositionStatistics()
        assert s.average_holding_time_ms == 0.0

    def test_average_holding_time_computed(self):
        s = PositionStatistics()
        s.record_created(Decimal("100"))
        s.record_opened()
        s.record_closed(holding_time_ms=1000.0)
        s.record_closed(holding_time_ms=3000.0)
        assert s.average_holding_time_ms == pytest.approx(2000.0)

    def test_average_position_size(self):
        s = PositionStatistics()
        s.record_created(Decimal("100"))
        s.record_created(Decimal("200"))
        assert s.average_position_size == Decimal("150")

    def test_close_rate(self):
        s = PositionStatistics()
        s.record_created(Decimal("10"))
        s.record_opened()
        s.record_opened()
        s.record_closed()
        assert s.close_rate == pytest.approx(0.5)

    def test_record_transition_recovery(self):
        s = PositionStatistics()
        s.record_transition(is_recovery=True)
        assert s.total_transitions == 1
        assert s.recovery_count    == 1

    def test_to_dict_keys(self):
        s = PositionStatistics()
        d = s.to_dict()
        assert "positions_created" in d
        assert "average_holding_time_ms" in d
        assert "close_rate" in d


# ══════════════════════════════════════════════════════════════════════════════
# PositionContext
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionContext:
    def test_make_context_creates_uuid(self):
        ctx = make_context(portfolio_id="port", strategy_id="strat")
        assert uuid.UUID(ctx.context_id)
        assert ctx.portfolio_id == "port"
        assert ctx.strategy_id  == "strat"

    def test_has_workflow_true(self):
        ctx = make_context(workflow_id="wf-1")
        assert ctx.has_workflow is True

    def test_has_workflow_false(self):
        ctx = make_context()
        assert ctx.has_workflow is False

    def test_has_decision_true(self):
        ctx = make_context(decision_id="dec-1")
        assert ctx.has_decision is True

    def test_age_ms_positive(self):
        ctx = make_context()
        time.sleep(0.01)
        assert ctx.age_ms > 0

    def test_to_dict_keys(self):
        ctx = make_context()
        d = ctx.to_dict()
        assert "context_id" in d
        assert "correlation_id" in d


# ══════════════════════════════════════════════════════════════════════════════
# PositionMetadata
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionMetadata:
    def test_set_tag(self):
        m = PositionMetadata()
        m.set_tag("key1", "val1")
        assert m.get_tag("key1") == "val1"
        assert m.version == 2

    def test_remove_tag(self):
        m = PositionMetadata()
        m.set_tag("k", "v")
        m.remove_tag("k")
        assert not m.has_tag("k")

    def test_remove_tag_noop_if_missing(self):
        m = PositionMetadata()
        m.remove_tag("nonexistent")  # must not raise

    def test_set_notes(self):
        m = PositionMetadata()
        m.set_notes("a note")
        assert m.notes == "a note"

    def test_to_dict_roundtrip(self):
        m = PositionMetadata()
        m.set_tag("foo", "bar")
        m.set_notes("hello")
        d = m.to_dict()
        m2 = PositionMetadata.from_dict(d)
        assert m2.tags == {"foo": "bar"}
        assert m2.notes == "hello"

    def test_has_tag(self):
        m = PositionMetadata()
        assert m.has_tag("x") is False
        m.set_tag("x", "1")
        assert m.has_tag("x") is True


# ══════════════════════════════════════════════════════════════════════════════
# PositionValidator
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionValidator:
    def _pos(self, **kwargs) -> Position:
        return _make_position(**kwargs)

    def test_valid_transition_open_to_closing(self):
        v   = PositionValidator()
        pos = self._pos()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        result = v.validate_transition(pos, PositionState.CLOSING)
        assert result.is_valid

    def test_invalid_transition_open_to_archived(self):
        v   = PositionValidator()
        pos = self._pos()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        result = v.validate_transition(pos, PositionState.ARCHIVED)
        assert not result.is_valid
        assert result.error_count == 1

    def test_validate_identifiers_empty_instrument_fails(self):
        v = PositionValidator()
        # create via factory bypass to inject bad data
        pos = Position(
            position_id="p1", portfolio_id="", strategy_id="",
            decision_id="", workflow_id="", execution_id="",
            instrument="",  # bad
            exchange="NSE", product=PositionProduct.EQUITY,
            direction=PositionDirection.LONG,
            quantity=Decimal("10"),
        )
        result = v.validate_identifiers(pos)
        assert not result.is_valid

    def test_validate_quantities_negative_open(self):
        v   = PositionValidator()
        pos = self._pos()
        pos.update_quantities(Decimal("-1"), Decimal("0"))
        result = v.validate_quantities(pos)
        assert not result.is_valid

    def test_validate_quantities_sum_exceeds_total(self):
        v   = PositionValidator()
        pos = self._pos(quantity=Decimal("50"))
        pos.update_quantities(Decimal("40"), Decimal("20"))  # 40+20 > 50
        result = v.validate_quantities(pos)
        assert not result.is_valid

    def test_validate_quantities_valid(self):
        v   = PositionValidator()
        pos = self._pos(quantity=Decimal("100"))
        pos.update_quantities(Decimal("60"), Decimal("40"))
        result = v.validate_quantities(pos)
        assert result.is_valid

    def test_validate_prices_negative_entry(self):
        v   = PositionValidator()
        pos = self._pos()
        pos.update_prices(avg_entry=Decimal("-1"))
        result = v.validate_prices(pos)
        assert not result.is_valid

    def test_validate_timestamps_inverted(self):
        v   = PositionValidator()
        pos = self._pos()
        # Force updated_at < created_at by manipulating internal field
        pos._updated_at = pos._created_at - 1.0  # type: ignore[attr-defined]
        result = v.validate_timestamps(pos)
        assert not result.is_valid

    def test_validate_full_returns_aggregated_result(self):
        v   = PositionValidator()
        pos = self._pos(quantity=Decimal("100"))
        pos.update_quantities(Decimal("50"), Decimal("30"))
        result = v.validate_full(pos)
        assert result.is_valid  # all good

    def test_raise_if_invalid_raises_on_failure(self):
        v = PositionValidator()
        result = ValidationResult(is_valid=False, errors=("bad field",), warnings=())
        with pytest.raises(PositionValidationError):
            v.raise_if_invalid(result)

    def test_raise_if_invalid_passes_on_success(self):
        v = PositionValidator()
        result = ValidationResult(is_valid=True, errors=(), warnings=())
        v.raise_if_invalid(result)  # must not raise

    def test_validation_result_to_dict(self):
        r = ValidationResult(is_valid=True, errors=(), warnings=("w1",))
        d = r.to_dict()
        assert d["is_valid"] is True
        assert d["warning_count"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# Position — state machine
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionStateMachine:
    """Full traversal of the state machine graph."""

    def test_initial_state_is_created(self):
        pos = _make_position()
        assert pos.state == PositionState.CREATED

    def test_created_to_opening(self):
        pos = _make_position()
        t = pos.transition_to(PositionState.OPENING)
        assert pos.state == PositionState.OPENING
        assert t.from_state == PositionState.CREATED
        assert t.to_state   == PositionState.OPENING

    def test_opening_to_open(self):
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        assert pos.state == PositionState.OPEN

    def test_open_to_partially_closed(self):
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        pos.transition_to(PositionState.PARTIALLY_CLOSED)
        assert pos.state == PositionState.PARTIALLY_CLOSED

    def test_partially_closed_back_to_open(self):
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        pos.transition_to(PositionState.PARTIALLY_CLOSED)
        pos.transition_to(PositionState.OPEN)
        assert pos.state == PositionState.OPEN

    def test_open_to_closing_to_closed_to_archived(self):
        pos = _make_position()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED,
                  PositionState.ARCHIVED):
            pos.transition_to(s)
        assert pos.state    == PositionState.ARCHIVED
        assert pos.is_archived is True

    def test_full_recovery_path(self):
        pos = _make_position()
        path = [
            PositionState.OPENING,
            PositionState.OPEN,
            PositionState.CLOSING,
            PositionState.RECOVERING,
            PositionState.RECOVERED,
            PositionState.OPEN,
        ]
        for s in path:
            pos.transition_to(s)
        assert pos.state == PositionState.OPEN

    def test_suspension_path(self):
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        pos.transition_to(PositionState.SUSPENDED)
        pos.transition_to(PositionState.RECOVERING)
        pos.transition_to(PositionState.RECOVERED)
        pos.transition_to(PositionState.CLOSING)
        pos.transition_to(PositionState.CLOSED)
        assert pos.state == PositionState.CLOSED

    def test_opening_directly_to_closed(self):
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.CLOSED)
        assert pos.state == PositionState.CLOSED

    def test_invalid_transitions_raise(self):
        """Verify every invalid outgoing edge raises InvalidTransitionError."""
        all_states = set(PositionState)
        for from_state, allowed in VALID_TRANSITIONS.items():
            disallowed = all_states - allowed - {from_state}
            for bad in disallowed:
                pos = _make_position()
                # Fast-forward to from_state via the allowed path
                _fast_forward(pos, from_state)
                if pos.state == from_state:
                    with pytest.raises(InvalidTransitionError):
                        pos.transition_to(bad)

    def test_transition_returns_transition_object(self):
        pos = _make_position()
        t = pos.transition_to(PositionState.OPENING)
        assert isinstance(t, PositionTransition)

    def test_history_grows_with_transitions(self):
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        assert len(pos.history) == 2

    def test_transition_with_actor_and_reason(self):
        pos = _make_position()
        t = pos.transition_to(PositionState.OPENING, actor="strategy-1", reason="signal fired")
        assert t.actor  == "strategy-1"
        assert t.reason == "signal fired"

    def test_archived_is_terminal(self):
        pos = _make_position()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED,
                  PositionState.ARCHIVED):
            pos.transition_to(s)
        with pytest.raises(InvalidTransitionError):
            pos.transition_to(PositionState.OPEN)


def _fast_forward(pos: Position, target: PositionState) -> None:
    """Walk pos to *target* via a known valid path, or stop early."""
    paths: dict[PositionState, list[PositionState]] = {
        PositionState.CREATED:          [],
        PositionState.OPENING:          [PositionState.OPENING],
        PositionState.OPEN:             [PositionState.OPENING, PositionState.OPEN],
        PositionState.PARTIALLY_CLOSED: [PositionState.OPENING, PositionState.OPEN, PositionState.PARTIALLY_CLOSED],
        PositionState.CLOSING:          [PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING],
        PositionState.CLOSED:           [PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING, PositionState.CLOSED],
        PositionState.SUSPENDED:        [PositionState.OPENING, PositionState.OPEN, PositionState.SUSPENDED],
        PositionState.RECOVERING:       [PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING, PositionState.RECOVERING],
        PositionState.RECOVERED:        [PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING, PositionState.RECOVERING, PositionState.RECOVERED],
        PositionState.ARCHIVED:         [PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING, PositionState.CLOSED, PositionState.ARCHIVED],
    }
    for s in paths.get(target, []):
        if pos.state != s:
            try:
                pos.transition_to(s)
            except InvalidTransitionError:
                break


# ══════════════════════════════════════════════════════════════════════════════
# Position — field updates and properties
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionFields:
    def test_initial_quantities_are_zero(self):
        pos = _make_position(quantity=Decimal("100"))
        assert pos.open_quantity   == Decimal(0)
        assert pos.closed_quantity == Decimal(0)

    def test_update_quantities(self):
        pos = _make_position(quantity=Decimal("100"))
        pos.update_quantities(Decimal("60"), Decimal("40"))
        assert pos.open_quantity   == Decimal("60")
        assert pos.closed_quantity == Decimal("40")

    def test_fill_ratio(self):
        pos = _make_position(quantity=Decimal("100"))
        pos.update_quantities(Decimal("75"), Decimal("25"))
        assert pos.fill_ratio == pytest.approx(0.75)

    def test_fill_ratio_zero_when_no_open(self):
        pos = _make_position(quantity=Decimal("100"))
        assert pos.fill_ratio == pytest.approx(0.0)

    def test_update_prices(self):
        pos = _make_position()
        pos.update_prices(avg_entry=Decimal("200.5"), avg_exit=Decimal("210.0"))
        assert pos.average_entry_price == Decimal("200.5")
        assert pos.average_exit_price  == Decimal("210.0")

    def test_update_prices_partial(self):
        pos = _make_position()
        pos.update_prices(avg_entry=Decimal("100"))
        assert pos.average_entry_price == Decimal("100")
        assert pos.average_exit_price  == Decimal(0)

    def test_update_pnl(self):
        pos = _make_position()
        pos.update_pnl(realized=Decimal("500"), unrealized=Decimal("200"))
        assert pos.realized_pnl   == Decimal("500")
        assert pos.unrealized_pnl == Decimal("200")
        assert pos.total_pnl      == Decimal("700")

    def test_update_pnl_partial(self):
        pos = _make_position()
        pos.update_pnl(realized=Decimal("100"))
        assert pos.realized_pnl   == Decimal("100")
        assert pos.unrealized_pnl == Decimal(0)

    def test_is_active_for_open_position(self):
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        assert pos.is_active is True

    def test_is_not_active_for_archived(self):
        pos = _make_position()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED,
                  PositionState.ARCHIVED):
            pos.transition_to(s)
        assert pos.is_active is False

    def test_is_closed_after_close(self):
        pos = _make_position()
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED):
            pos.transition_to(s)
        assert pos.is_closed is True

    def test_is_suspended_in_suspended_state(self):
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        pos.transition_to(PositionState.SUSPENDED)
        assert pos.is_suspended is True

    def test_to_dict_all_keys_present(self):
        pos = _make_position()
        d = pos.to_dict()
        for k in (
            "position_id", "portfolio_id", "strategy_id", "decision_id",
            "workflow_id", "execution_id", "instrument", "exchange",
            "product", "direction", "quantity", "open_quantity",
            "closed_quantity", "average_entry_price", "average_exit_price",
            "realized_pnl", "unrealized_pnl", "total_pnl",
            "state", "created_at", "updated_at", "metadata", "version",
        ):
            assert k in d, f"Missing key: {k}"

    def test_snapshot_matches_to_dict(self):
        pos = _make_position()
        assert pos.snapshot() == pos.to_dict()

    def test_repr_contains_instrument(self):
        pos = _make_position(instrument="RELIANCE")
        assert "RELIANCE" in repr(pos)

    def test_updated_at_advances_after_transition(self):
        pos = _make_position()
        t0 = pos.updated_at
        time.sleep(0.01)
        pos.transition_to(PositionState.OPENING)
        assert pos.updated_at > t0

    def test_identity_fields_accessible(self):
        pos = _make_position()
        assert pos.portfolio_id  == "portfolio-1"
        assert pos.strategy_id   == "strat-1"
        assert pos.decision_id   == "dec-1"
        assert pos.workflow_id   == "wf-1"
        assert pos.execution_id  == "exec-1"


# ══════════════════════════════════════════════════════════════════════════════
# Position — event listeners
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionEventListeners:
    def test_listener_called_on_transition(self):
        pos = _make_position()
        received: List[PositionEvent] = []
        pos.add_event_listener(received.append)
        pos.transition_to(PositionState.OPENING)
        assert len(received) == 1

    def test_listener_removed(self):
        pos = _make_position()
        received: List[PositionEvent] = []
        pos.add_event_listener(received.append)
        pos.remove_event_listener(received.append)
        pos.transition_to(PositionState.OPENING)
        assert len(received) == 0

    def test_listener_receives_correct_state(self):
        pos = _make_position()
        received: List[PositionEvent] = []
        pos.add_event_listener(received.append)
        pos.transition_to(PositionState.OPENING)
        # The event state should reflect OPENING
        assert received[0].event_type == PositionEventType.POSITION_UPDATED or \
               received[0].state in (PositionState.OPENING, PositionState.OPEN)

    def test_failed_listener_does_not_crash_transition(self):
        pos = _make_position()
        def bad_listener(event):
            raise RuntimeError("boom")
        pos.add_event_listener(bad_listener)
        pos.transition_to(PositionState.OPENING)  # must not raise
        assert pos.state == PositionState.OPENING

    def test_open_event_type_is_position_opened(self):
        pos = _make_position()
        received: List[PositionEvent] = []
        pos.add_event_listener(received.append)
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        open_events = [e for e in received if e.event_type == PositionEventType.POSITION_OPENED]
        assert len(open_events) == 1

    def test_archived_event_type_is_position_archived(self):
        pos = _make_position()
        received: List[PositionEvent] = []
        pos.add_event_listener(received.append)
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED,
                  PositionState.ARCHIVED):
            pos.transition_to(s)
        archived_events = [e for e in received if e.event_type == PositionEventType.POSITION_ARCHIVED]
        assert len(archived_events) == 1


# ══════════════════════════════════════════════════════════════════════════════
# PositionFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionFactory:
    def test_create_returns_position(self):
        f   = PositionFactory()
        pos = f.create(
            instrument="NIFTY50", exchange="NSE",
            product=PositionProduct.FUTURES,
            direction=PositionDirection.LONG,
            quantity=Decimal("100"),
        )
        assert isinstance(pos, Position)
        assert pos.state == PositionState.CREATED

    def test_create_assigns_custom_id(self):
        f   = PositionFactory()
        pos = f.create(
            instrument="X", exchange="NSE",
            product=PositionProduct.EQUITY,
            direction=PositionDirection.SHORT,
            quantity=Decimal("10"),
            position_id="my-id",
        )
        assert pos.position_id == "my-id"

    def test_create_generates_uuid_if_no_id(self):
        f   = PositionFactory()
        pos = f.create("X", "NSE", PositionProduct.EQUITY, PositionDirection.LONG, Decimal("1"))
        assert uuid.UUID(pos.position_id)

    def test_create_long_is_long_direction(self):
        f   = PositionFactory()
        pos = f.create_long("RELIANCE", "BSE", PositionProduct.EQUITY, Decimal("50"))
        assert pos.direction == PositionDirection.LONG

    def test_create_short_is_short_direction(self):
        f   = PositionFactory()
        pos = f.create_short("RELIANCE", "BSE", PositionProduct.EQUITY, Decimal("50"))
        assert pos.direction == PositionDirection.SHORT

    def test_create_raises_on_empty_instrument(self):
        f = PositionFactory()
        with pytest.raises(PositionValidationError):
            f.create("", "NSE", PositionProduct.EQUITY, PositionDirection.LONG, Decimal("10"))

    def test_create_raises_on_empty_exchange(self):
        f = PositionFactory()
        with pytest.raises(PositionValidationError):
            f.create("X", "", PositionProduct.EQUITY, PositionDirection.LONG, Decimal("10"))

    def test_create_raises_on_zero_quantity(self):
        f = PositionFactory()
        with pytest.raises(PositionValidationError):
            f.create("X", "NSE", PositionProduct.EQUITY, PositionDirection.LONG, Decimal("0"))

    def test_create_raises_on_negative_quantity(self):
        f = PositionFactory()
        with pytest.raises(PositionValidationError):
            f.create("X", "NSE", PositionProduct.EQUITY, PositionDirection.LONG, Decimal("-5"))

    def test_make_created_event(self):
        f   = PositionFactory()
        pos = f.create_long("NIFTY", "NSE", PositionProduct.FUTURES, Decimal("10"))
        event = f.make_created_event(pos)
        assert event.event_type  == PositionEventType.POSITION_CREATED
        assert event.position_id == pos.position_id


# ══════════════════════════════════════════════════════════════════════════════
# PositionRegistry
# ══════════════════════════════════════════════════════════════════════════════

class TestPositionRegistry:
    # ── Lifecycle guard ───────────────────────────────────────────────────────

    def test_register_raises_if_not_started(self):
        reg = PositionRegistry()
        pos = _make_position()
        with pytest.raises(PositionNotRunningError):
            reg.register(pos)

    def test_register_works_after_start(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        assert reg.count == 1

    def test_registry_lifecycle_state_running_after_start(self):
        reg = PositionRegistry()
        reg.start()
        assert reg.lifecycle_state().value == "running"

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def test_get_returns_position(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        assert reg.get(pos.position_id) is pos

    def test_get_returns_none_for_unknown(self):
        reg = _started_registry()
        assert reg.get("unknown") is None

    def test_require_returns_position(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        assert reg.require(pos.position_id) is pos

    def test_require_raises_for_unknown(self):
        reg = _started_registry()
        with pytest.raises(PositionNotFoundError):
            reg.require("unknown")

    def test_deregister_removes_position(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        reg.deregister(pos.position_id)
        assert reg.get(pos.position_id) is None

    def test_deregister_raises_for_unknown(self):
        reg = _started_registry()
        with pytest.raises(PositionNotFoundError):
            reg.deregister("nonexistent")

    def test_duplicate_register_raises(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        with pytest.raises(DuplicatePositionError):
            reg.register(pos)

    def test_capacity_error_when_full(self):
        reg = _started_registry(max_positions=1)
        reg.register(_make_position())
        with pytest.raises(PositionRegistryCapacityError):
            reg.register(_make_position())

    def test_contains(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        assert reg.contains(pos.position_id) is True
        assert reg.contains("ghost")        is False

    # ── Filtering ─────────────────────────────────────────────────────────────

    def test_all_returns_all_positions(self):
        reg = _started_registry()
        for _ in range(3):
            reg.register(_make_position())
        assert len(reg.all()) == 3

    def test_by_state(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        assert pos in reg.by_state(PositionState.OPEN)
        assert pos not in reg.by_state(PositionState.CREATED)

    def test_by_portfolio(self):
        reg = _started_registry()
        factory = PositionFactory()
        p1 = factory.create_long("X", "NSE", PositionProduct.EQUITY, Decimal("10"), portfolio_id="A")
        p2 = factory.create_long("X", "NSE", PositionProduct.EQUITY, Decimal("10"), portfolio_id="B")
        reg.register(p1)
        reg.register(p2)
        assert reg.by_portfolio("A") == [p1]

    def test_by_strategy(self):
        reg = _started_registry()
        factory = PositionFactory()
        p1 = factory.create_long("X", "NSE", PositionProduct.EQUITY, Decimal("10"), strategy_id="s1")
        p2 = factory.create_long("X", "NSE", PositionProduct.EQUITY, Decimal("10"), strategy_id="s2")
        reg.register(p1)
        reg.register(p2)
        assert reg.by_strategy("s2") == [p2]

    def test_by_instrument(self):
        reg = _started_registry()
        factory = PositionFactory()
        p1 = factory.create_long("NIFTY", "NSE", PositionProduct.FUTURES, Decimal("10"))
        p2 = factory.create_long("RELIANCE", "NSE", PositionProduct.EQUITY, Decimal("10"))
        reg.register(p1)
        reg.register(p2)
        assert reg.by_instrument("NIFTY") == [p1]

    def test_active_filter(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        assert pos in reg.active()

    def test_closed_filter(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED):
            pos.transition_to(s)
        assert pos in reg.closed()

    def test_archived_filter(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        for s in (PositionState.OPENING, PositionState.OPEN,
                  PositionState.CLOSING, PositionState.CLOSED,
                  PositionState.ARCHIVED):
            pos.transition_to(s)
        assert pos in reg.archived()

    def test_suspended_filter(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        pos.transition_to(PositionState.SUSPENDED)
        assert pos in reg.suspended()

    # ── Statistics ────────────────────────────────────────────────────────────

    def test_statistics_created_increments(self):
        reg = _started_registry()
        reg.register(_make_position(quantity=Decimal("100")))
        s = reg.statistics()
        assert s.positions_created == 1
        assert s.total_position_size == Decimal("100")

    def test_statistics_notify_transition(self):
        reg = _started_registry()
        pos = _make_position()
        reg.register(pos)
        reg.notify_transition(PositionState.OPEN)
        s = reg.statistics()
        assert s.positions_opened == 1
        assert s.total_transitions == 1

    def test_statistics_returns_copy(self):
        reg = _started_registry()
        s1 = reg.statistics()
        s2 = reg.statistics()
        assert s1 is not s2

    # ── len / iter ────────────────────────────────────────────────────────────

    def test_len(self):
        reg = _started_registry()
        assert len(reg) == 0
        reg.register(_make_position())
        assert len(reg) == 1

    def test_iter(self):
        reg = _started_registry()
        p1 = _make_position()
        p2 = _make_position()
        reg.register(p1)
        reg.register(p2)
        items = list(reg)
        assert p1 in items and p2 in items

    def test_is_empty(self):
        reg = _started_registry()
        assert reg.is_empty is True
        reg.register(_make_position())
        assert reg.is_empty is False


# ══════════════════════════════════════════════════════════════════════════════
# Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_all_inherit_lifecycle_error(self):
        for exc_class in (
            InvalidTransitionError,
            PositionNotFoundError,
            DuplicatePositionError,
            PositionValidationError,
            PositionRegistryCapacityError,
            PositionNotRunningError,
            PositionStateError,
        ):
            assert issubclass(exc_class, PositionLifecycleError)

    def test_invalid_transition_error_fields(self):
        err = InvalidTransitionError("p1", PositionState.OPEN, PositionState.ARCHIVED)
        assert err.position_id == "p1"
        assert err.from_state  == PositionState.OPEN
        assert err.to_state    == PositionState.ARCHIVED
        assert "PL-001" in str(err.code)

    def test_position_not_found_error_fields(self):
        err = PositionNotFoundError("missing-id")
        assert err.position_id == "missing-id"
        assert "PL-002" in str(err.code)

    def test_duplicate_position_error_fields(self):
        err = DuplicatePositionError("dup-id")
        assert err.position_id == "dup-id"
        assert "PL-003" in str(err.code)

    def test_capacity_error_fields(self):
        err = PositionRegistryCapacityError(500)
        assert err.max_positions == 500
        assert "PL-005" in str(err.code)

    def test_state_error_fields(self):
        err = PositionStateError("p1", PositionState.SUSPENDED, "manual check")
        assert err.position_id   == "p1"
        assert err.current_state == PositionState.SUSPENDED
        assert "PL-007" in str(err.code)


# ══════════════════════════════════════════════════════════════════════════════
# Thread safety
# ══════════════════════════════════════════════════════════════════════════════

class TestThreadSafety:
    def test_concurrent_registry_register(self):
        """50 threads each register a unique position without collision."""
        reg = _started_registry(max_positions=100)
        errors: List[Exception] = []

        def register_one():
            try:
                reg.register(_make_position())
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=register_one) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        assert reg.count == 50

    def test_concurrent_transitions_on_single_position(self):
        """Only one thread should succeed in driving the state machine; the rest raise."""
        pos = _make_position()
        successes = []
        failures  = []

        def attempt():
            try:
                pos.transition_to(PositionState.OPENING)
                successes.append(1)
            except InvalidTransitionError:
                failures.append(1)

        threads = [threading.Thread(target=attempt) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one thread should have succeeded
        assert sum(successes) == 1
        assert sum(failures)  == 9

    def test_concurrent_history_appends(self):
        """50 threads each append a transition; history should have 50 entries."""
        h = PositionHistory(max_size=100)
        errors: List[Exception] = []

        def append_one(i: int):
            try:
                h.append_transition(make_transition(
                    f"pos-{i}", PositionState.CREATED, PositionState.OPENING
                ))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=append_one, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(h)  == 50


# ══════════════════════════════════════════════════════════════════════════════
# Regression guards
# ══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    def test_invalid_transition_does_not_change_state(self):
        """A failed transition must leave the position state unchanged."""
        pos = _make_position()
        with pytest.raises(InvalidTransitionError):
            pos.transition_to(PositionState.ARCHIVED)
        assert pos.state == PositionState.CREATED

    def test_invalid_transition_does_not_grow_history(self):
        pos = _make_position()
        initial_len = len(pos.history)
        with pytest.raises(InvalidTransitionError):
            pos.transition_to(PositionState.ARCHIVED)
        assert len(pos.history) == initial_len

    def test_state_records_count_equals_transitions_plus_one(self):
        """After N transitions there should be N+1 state records (initial + one per move)."""
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        pos.transition_to(PositionState.OPEN)
        records     = pos.history.states()
        transitions = pos.history.transitions()
        assert len(records) == len(transitions) + 1

    def test_factory_position_has_no_open_quantity(self):
        pos = _make_position()
        assert pos.open_quantity   == Decimal(0)
        assert pos.closed_quantity == Decimal(0)

    def test_position_id_never_changes(self):
        pos = _make_position()
        pid = pos.position_id
        pos.transition_to(PositionState.OPENING)
        pos.update_quantities(Decimal("50"), Decimal("50"))
        assert pos.position_id == pid

    def test_registry_stop_prevents_register(self):
        reg = _started_registry()
        reg.stop()
        with pytest.raises(PositionNotRunningError):
            reg.register(_make_position())

    def test_history_state_exit_stamped_on_transition(self):
        pos = _make_position()
        pos.transition_to(PositionState.OPENING)
        states = pos.history.states()
        # The CREATED record should have an exit timestamp
        assert states[0].exited_at is not None

    def test_total_pnl_is_sum_of_realized_and_unrealized(self):
        pos = _make_position()
        pos.update_pnl(realized=Decimal("300"), unrealized=Decimal("-50"))
        assert pos.total_pnl == Decimal("250")

    def test_position_quantity_immutable_via_property(self):
        pos = _make_position(quantity=Decimal("100"))
        # quantity is read-only; open/closed are mutable via update_quantities
        assert pos.quantity == Decimal("100")

    def test_direction_preserved_across_transitions(self):
        pos = _make_position(direction=PositionDirection.SHORT)
        pos.transition_to(PositionState.OPENING)
        assert pos.direction == PositionDirection.SHORT

    def test_statistics_copy_is_independent(self):
        reg = _started_registry()
        s1 = reg.statistics()
        reg.register(_make_position())
        s2 = reg.statistics()
        assert s1.positions_created == 0
        assert s2.positions_created == 1
