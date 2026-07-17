"""tests/unit/execution/risk/test_execution_risk_lifecycle.py
==================================================
Test suite for C6 Phase 4 M1 — IIOS Execution Risk Lifecycle.

Coverage targets:
  * RiskState enum and state machine (VALID_TRANSITIONS)
  * ExecutionRisk domain object — construction, transitions, status
  * InvalidRiskTransitionError raised for every disallowed transition
  * RiskHistory — append, filtering, eviction, override count
  * RiskStateRecord — duration_ms, with_exit, is_current
  * RiskTransition — factory, is_valid, is_pass, is_block, is_override
  * RiskEvent — all 8 factory functions, to_dict
  * RiskMetadata — tag CRUD, notes, override_by, version increment
  * RiskStatistics — all counters, derived rates, serialisation
  * RiskContext — make_risk_context, properties, to_dict
  * RiskValidator — all validation sub-methods + full
  * RiskFactory — create, all 9 convenience wrappers, created event
  * RiskRegistry — CRUD, filtering, statistics, lifecycle guard
  * Thread-safety — concurrent transitions and registry operations
  * Regression guards — edge cases and boundary conditions

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import List

import pytest

from iios.execution.risk.lifecycle import (
    ACTIVE_STATES,
    ACTOR_FACTORY,
    ACTOR_LIFECYCLE,
    BLOCKING_STATES,
    DEFAULT_MAX_EVALUATIONS,
    DEFAULT_MAX_HISTORY,
    ENDED_STATES,
    OUTCOME_STATES,
    PASS_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VERSION,
    DuplicateRiskError,
    ExecutionRisk,
    ExecutionRiskLifecycleError,
    InvalidRiskTransitionError,
    RiskCategory,
    RiskContext,
    RiskEvent,
    RiskEventType,
    RiskFactory,
    RiskHistory,
    RiskMetadata,
    RiskNotFoundError,
    RiskRegistryCapacityError,
    RiskRegistryNotRunningError,
    RiskRegistry,
    RiskState,
    RiskStateError,
    RiskStateRecord,
    RiskStatistics,
    RiskTransition,
    RiskValidationError,
    RiskValidator,
    ValidationResult,
    make_risk_archived,
    make_risk_blocked,
    make_risk_context,
    make_risk_created,
    make_risk_evaluation_started,
    make_risk_expired,
    make_risk_overridden,
    make_risk_passed,
    make_risk_transition,
    make_risk_warning,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_risk(
    category:     RiskCategory = RiskCategory.EXPOSURE,
    execution_id: str = "exec-1",
    portfolio_id: str = "portfolio-1",
    strategy_id:  str = "strat-1",
    **kwargs,
) -> ExecutionRisk:
    factory = RiskFactory()
    return factory.create(
        category,
        execution_id=execution_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        workflow_id=kwargs.pop("workflow_id", "wf-1"),
        order_id=kwargs.pop("order_id", "ord-1"),
        position_id=kwargs.pop("position_id", "pos-1"),
        decision_id=kwargs.pop("decision_id", "dec-1"),
        **kwargs,
    )


def _advance_to_evaluating(risk: ExecutionRisk) -> None:
    risk.transition_to(RiskState.PENDING_EVALUATION)
    risk.transition_to(RiskState.EVALUATING)


def _started_registry(max_evaluations: int = 100) -> RiskRegistry:
    reg = RiskRegistry(max_evaluations=max_evaluations)
    reg.start()
    return reg


# ══════════════════════════════════════════════════════════════════════════════
# 1. Constants & enumerations
# ══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_risk_state_count(self):
        assert len(RiskState) == 10

    def test_all_states_present(self):
        expected = {
            "CREATED", "PENDING_EVALUATION", "EVALUATING",
            "PASSED", "WARNING", "BLOCKED", "OVERRIDDEN",
            "EXPIRED", "FAILED", "ARCHIVED",
        }
        assert {s.value for s in RiskState} == expected

    def test_risk_category_count(self):
        assert len(RiskCategory) == 9

    def test_all_categories_present(self):
        expected = {
            "EXPOSURE", "MARGIN", "LIQUIDITY", "CONCENTRATION",
            "ORDER_SIZE", "PRICE", "EXECUTION", "COMPLIANCE", "OPERATIONAL",
        }
        assert {c.value for c in RiskCategory} == expected

    def test_risk_event_type_count(self):
        assert len(RiskEventType) == 8

    def test_terminal_states(self):
        assert TERMINAL_STATES == frozenset({RiskState.ARCHIVED})

    def test_active_states(self):
        assert ACTIVE_STATES == frozenset({
            RiskState.PENDING_EVALUATION, RiskState.EVALUATING
        })

    def test_pass_states(self):
        assert PASS_STATES == frozenset({
            RiskState.PASSED, RiskState.WARNING, RiskState.OVERRIDDEN
        })

    def test_blocking_states(self):
        assert BLOCKING_STATES == frozenset({RiskState.BLOCKED})

    def test_ended_states(self):
        assert RiskState.EXPIRED  in ENDED_STATES
        assert RiskState.FAILED   in ENDED_STATES
        assert RiskState.ARCHIVED in ENDED_STATES

    def test_version_string(self):
        assert VERSION == "1.0.0"

    def test_valid_transitions_covers_all_states(self):
        for state in RiskState:
            assert state in VALID_TRANSITIONS

    def test_archived_is_terminal(self):
        assert VALID_TRANSITIONS[RiskState.ARCHIVED] == frozenset()

    def test_risk_state_is_str_enum(self):
        assert isinstance(RiskState.CREATED, str)

    def test_risk_category_is_str_enum(self):
        assert isinstance(RiskCategory.EXPOSURE, str)


# ══════════════════════════════════════════════════════════════════════════════
# 2. State machine transitions — valid
# ══════════════════════════════════════════════════════════════════════════════

class TestValidTransitions:
    def test_created_to_pending(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION)
        assert r.state == RiskState.PENDING_EVALUATION

    def test_pending_to_evaluating(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION)
        r.transition_to(RiskState.EVALUATING)
        assert r.state == RiskState.EVALUATING

    def test_evaluating_to_passed(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        assert r.state == RiskState.PASSED

    def test_evaluating_to_warning(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.WARNING)
        assert r.state == RiskState.WARNING

    def test_evaluating_to_blocked(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.BLOCKED)
        assert r.state == RiskState.BLOCKED

    def test_evaluating_to_expired(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.EXPIRED)
        assert r.state == RiskState.EXPIRED

    def test_evaluating_to_failed(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.FAILED)
        assert r.state == RiskState.FAILED

    def test_passed_to_overridden(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        r.transition_to(RiskState.OVERRIDDEN)
        assert r.state == RiskState.OVERRIDDEN

    def test_passed_to_archived(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        r.transition_to(RiskState.ARCHIVED)
        assert r.state == RiskState.ARCHIVED

    def test_warning_to_blocked(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.WARNING)
        r.transition_to(RiskState.BLOCKED)
        assert r.state == RiskState.BLOCKED

    def test_warning_to_overridden(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.WARNING)
        r.transition_to(RiskState.OVERRIDDEN)
        assert r.state == RiskState.OVERRIDDEN

    def test_blocked_to_overridden(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.BLOCKED)
        r.transition_to(RiskState.OVERRIDDEN)
        assert r.state == RiskState.OVERRIDDEN

    def test_expired_to_archived(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION)
        r.transition_to(RiskState.EXPIRED)
        r.transition_to(RiskState.ARCHIVED)
        assert r.state == RiskState.ARCHIVED

    def test_failed_to_archived(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION)
        r.transition_to(RiskState.FAILED)
        r.transition_to(RiskState.ARCHIVED)
        assert r.state == RiskState.ARCHIVED

    def test_created_directly_to_failed(self):
        r = _make_risk()
        r.transition_to(RiskState.FAILED)
        assert r.state == RiskState.FAILED

    def test_created_directly_to_expired(self):
        r = _make_risk()
        r.transition_to(RiskState.EXPIRED)
        assert r.state == RiskState.EXPIRED


# ══════════════════════════════════════════════════════════════════════════════
# 3. State machine transitions — invalid
# ══════════════════════════════════════════════════════════════════════════════

class TestInvalidTransitions:
    def test_created_to_evaluating(self):
        r = _make_risk()
        with pytest.raises(InvalidRiskTransitionError):
            r.transition_to(RiskState.EVALUATING)

    def test_created_to_passed(self):
        r = _make_risk()
        with pytest.raises(InvalidRiskTransitionError):
            r.transition_to(RiskState.PASSED)

    def test_created_to_archived(self):
        r = _make_risk()
        with pytest.raises(InvalidRiskTransitionError):
            r.transition_to(RiskState.ARCHIVED)

    def test_evaluating_to_pending(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        with pytest.raises(InvalidRiskTransitionError):
            r.transition_to(RiskState.PENDING_EVALUATION)

    def test_passed_to_evaluating(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        with pytest.raises(InvalidRiskTransitionError):
            r.transition_to(RiskState.EVALUATING)

    def test_passed_to_failed(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        with pytest.raises(InvalidRiskTransitionError):
            r.transition_to(RiskState.FAILED)

    def test_archived_to_any(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        r.transition_to(RiskState.ARCHIVED)
        for target in RiskState:
            with pytest.raises(InvalidRiskTransitionError):
                r.transition_to(target)

    def test_blocked_to_passed(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.BLOCKED)
        with pytest.raises(InvalidRiskTransitionError):
            r.transition_to(RiskState.PASSED)

    def test_error_carries_identifiers(self):
        r = _make_risk()
        with pytest.raises(InvalidRiskTransitionError) as exc_info:
            r.transition_to(RiskState.ARCHIVED)
        err = exc_info.value
        assert err.from_state == RiskState.CREATED
        assert err.to_state   == RiskState.ARCHIVED
        assert err.risk_id    == r.risk_id

    def test_state_unchanged_on_error(self):
        r = _make_risk()
        with pytest.raises(InvalidRiskTransitionError):
            r.transition_to(RiskState.ARCHIVED)
        assert r.state == RiskState.CREATED


# ══════════════════════════════════════════════════════════════════════════════
# 4. ExecutionRisk domain object
# ══════════════════════════════════════════════════════════════════════════════

class TestExecutionRisk:
    def test_initial_state(self):
        r = _make_risk()
        assert r.state == RiskState.CREATED

    def test_identity_fields(self):
        r = _make_risk(
            execution_id="ex1",
            portfolio_id="p1",
            strategy_id="s1",
            workflow_id="wf1",
            order_id="o1",
            position_id="pos1",
            decision_id="d1",
        )
        assert r.execution_id  == "ex1"
        assert r.portfolio_id  == "p1"
        assert r.strategy_id   == "s1"
        assert r.workflow_id   == "wf1"
        assert r.order_id      == "o1"
        assert r.position_id   == "pos1"
        assert r.decision_id   == "d1"

    def test_category_set(self):
        r = _make_risk(category=RiskCategory.COMPLIANCE)
        assert r.risk_category == RiskCategory.COMPLIANCE

    def test_is_active_true_when_evaluating(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        assert r.is_active is True

    def test_is_active_false_after_outcome(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        assert r.is_active is False

    def test_is_passed_true(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        assert r.is_passed is True

    def test_is_passed_for_warning(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.WARNING)
        assert r.is_passed is True

    def test_is_passed_for_overridden(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.BLOCKED)
        r.transition_to(RiskState.OVERRIDDEN)
        assert r.is_passed is True

    def test_is_blocked_true(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.BLOCKED)
        assert r.is_blocked is True

    def test_is_archived_true(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        r.transition_to(RiskState.ARCHIVED)
        assert r.is_archived is True

    def test_is_expired_by_state(self):
        r = _make_risk()
        r.transition_to(RiskState.EXPIRED)
        assert r.is_expired is True

    def test_is_expired_by_wall_clock(self):
        r = _make_risk(expiry_time=time.time() - 1.0)
        assert r.is_expired is True

    def test_evaluation_time_recorded(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED, evaluation_time_ms=42.0)
        assert r.evaluation_time_ms == 42.0

    def test_updated_at_changes_on_transition(self):
        r = _make_risk()
        t0 = r.updated_at
        time.sleep(0.001)
        r.transition_to(RiskState.PENDING_EVALUATION)
        assert r.updated_at >= t0

    def test_history_grows_on_transition(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION)
        assert len(r.history.transitions()) == 1

    def test_to_dict_contains_required_keys(self):
        r = _make_risk()
        d = r.to_dict()
        for key in ("risk_id", "execution_id", "portfolio_id", "strategy_id",
                    "risk_category", "state", "evaluation_time_ms", "created_at"):
            assert key in d

    def test_to_dict_state_value(self):
        r = _make_risk()
        assert r.to_dict()["state"] == "CREATED"

    def test_correlation_id_stored(self):
        r = _make_risk(correlation_id="corr-xyz")
        assert r.correlation_id == "corr-xyz"


# ══════════════════════════════════════════════════════════════════════════════
# 5. RiskStateRecord
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskStateRecord:
    def test_is_current_when_no_exit(self):
        rec = RiskStateRecord(state=RiskState.CREATED, entered_at=time.time())
        assert rec.is_current is True

    def test_is_not_current_after_exit(self):
        now = time.time()
        rec = RiskStateRecord(state=RiskState.CREATED, entered_at=now, exited_at=now + 1)
        assert rec.is_current is False

    def test_duration_ms_none_when_no_exit(self):
        rec = RiskStateRecord(state=RiskState.CREATED, entered_at=time.time())
        assert rec.duration_ms is None

    def test_duration_ms_calculated(self):
        now = time.time()
        rec = RiskStateRecord(state=RiskState.CREATED, entered_at=now, exited_at=now + 0.5)
        assert abs(rec.duration_ms - 500.0) < 1.0

    def test_with_exit_creates_new_record(self):
        rec  = RiskStateRecord(state=RiskState.CREATED, entered_at=time.time())
        rec2 = rec.with_exit()
        assert rec.exited_at  is None
        assert rec2.exited_at is not None

    def test_to_dict_keys(self):
        rec = RiskStateRecord(state=RiskState.CREATED, entered_at=time.time())
        d   = rec.to_dict()
        assert "state"       in d
        assert "entered_at"  in d
        assert "exited_at"   in d
        assert "duration_ms" in d
        assert "is_current"  in d

    def test_frozen(self):
        rec = RiskStateRecord(state=RiskState.CREATED, entered_at=time.time())
        with pytest.raises((AttributeError, TypeError)):
            rec.state = RiskState.PASSED  # type: ignore


# ══════════════════════════════════════════════════════════════════════════════
# 6. RiskTransition
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskTransition:
    def test_make_transition_creates_uuid(self):
        t = make_risk_transition("rid", RiskState.CREATED, RiskState.PENDING_EVALUATION)
        assert len(t.transition_id) == 36

    def test_is_valid_for_allowed_transition(self):
        t = make_risk_transition("rid", RiskState.CREATED, RiskState.PENDING_EVALUATION)
        assert t.is_valid is True

    def test_is_not_valid_for_forbidden_transition(self):
        t = make_risk_transition("rid", RiskState.CREATED, RiskState.ARCHIVED)
        assert t.is_valid is False

    def test_is_terminal_for_archived(self):
        t = make_risk_transition("rid", RiskState.PASSED, RiskState.ARCHIVED)
        assert t.is_terminal is True

    def test_is_not_terminal_for_passed(self):
        t = make_risk_transition("rid", RiskState.EVALUATING, RiskState.PASSED)
        assert t.is_terminal is False

    def test_is_override(self):
        t = make_risk_transition("rid", RiskState.BLOCKED, RiskState.OVERRIDDEN)
        assert t.is_override is True

    def test_is_block(self):
        t = make_risk_transition("rid", RiskState.EVALUATING, RiskState.BLOCKED)
        assert t.is_block is True

    def test_is_pass_for_passed(self):
        t = make_risk_transition("rid", RiskState.EVALUATING, RiskState.PASSED)
        assert t.is_pass is True

    def test_is_pass_for_warning(self):
        t = make_risk_transition("rid", RiskState.EVALUATING, RiskState.WARNING)
        assert t.is_pass is True

    def test_is_not_pass_for_blocked(self):
        t = make_risk_transition("rid", RiskState.EVALUATING, RiskState.BLOCKED)
        assert t.is_pass is False

    def test_to_dict_keys(self):
        t = make_risk_transition("rid", RiskState.CREATED, RiskState.PENDING_EVALUATION)
        d = t.to_dict()
        for key in ("transition_id", "risk_id", "from_state", "to_state",
                    "triggered_at", "actor", "reason"):
            assert key in d

    def test_frozen(self):
        t = make_risk_transition("rid", RiskState.CREATED, RiskState.PENDING_EVALUATION)
        with pytest.raises((AttributeError, TypeError)):
            t.actor = "hacker"  # type: ignore


# ══════════════════════════════════════════════════════════════════════════════
# 7. RiskEvent
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskEvent:
    def test_make_risk_created(self):
        e = make_risk_created("rid-1", portfolio_id="p1")
        assert e.event_type == RiskEventType.RISK_CREATED
        assert e.state      == RiskState.CREATED
        assert e.risk_id    == "rid-1"

    def test_make_risk_evaluation_started(self):
        e = make_risk_evaluation_started("rid-1")
        assert e.event_type == RiskEventType.RISK_EVALUATION_STARTED
        assert e.state      == RiskState.EVALUATING

    def test_make_risk_passed(self):
        e = make_risk_passed("rid-1")
        assert e.event_type == RiskEventType.RISK_PASSED
        assert e.state      == RiskState.PASSED

    def test_make_risk_warning(self):
        e = make_risk_warning("rid-1")
        assert e.event_type == RiskEventType.RISK_WARNING
        assert e.state      == RiskState.WARNING

    def test_make_risk_blocked(self):
        e = make_risk_blocked("rid-1")
        assert e.event_type == RiskEventType.RISK_BLOCKED
        assert e.state      == RiskState.BLOCKED

    def test_make_risk_overridden(self):
        e = make_risk_overridden("rid-1")
        assert e.event_type == RiskEventType.RISK_OVERRIDDEN
        assert e.state      == RiskState.OVERRIDDEN

    def test_make_risk_expired(self):
        e = make_risk_expired("rid-1")
        assert e.event_type == RiskEventType.RISK_EXPIRED
        assert e.state      == RiskState.EXPIRED

    def test_make_risk_archived(self):
        e = make_risk_archived("rid-1")
        assert e.event_type == RiskEventType.RISK_ARCHIVED
        assert e.state      == RiskState.ARCHIVED

    def test_event_has_unique_id(self):
        e1 = make_risk_created("rid-1")
        e2 = make_risk_created("rid-1")
        assert e1.event_id != e2.event_id

    def test_to_dict_keys(self):
        e = make_risk_created("rid-1")
        d = e.to_dict()
        for key in ("event_id", "event_type", "risk_id", "state", "actor",
                    "occurred_at", "version"):
            assert key in d

    def test_frozen(self):
        e = make_risk_created("rid-1")
        with pytest.raises((AttributeError, TypeError)):
            e.risk_id = "hacker"  # type: ignore

    def test_event_listener_receives_event(self):
        received: List[RiskEvent] = []
        r = _make_risk()
        r.add_event_listener(received.append)
        r.transition_to(RiskState.PENDING_EVALUATION)
        r.transition_to(RiskState.EVALUATING)
        r.transition_to(RiskState.PASSED)
        # EVALUATING and PASSED trigger events
        types = [e.event_type for e in received]
        assert RiskEventType.RISK_EVALUATION_STARTED in types
        assert RiskEventType.RISK_PASSED             in types

    def test_event_listener_removed(self):
        received: List[RiskEvent] = []
        r = _make_risk()
        r.add_event_listener(received.append)
        r.remove_event_listener(received.append)
        r.transition_to(RiskState.PENDING_EVALUATION)
        assert len(received) == 0

    def test_faulty_listener_does_not_crash(self):
        def bad_listener(e):
            raise RuntimeError("listener error")

        r = _make_risk()
        r.add_event_listener(bad_listener)
        r.transition_to(RiskState.PENDING_EVALUATION)   # must not raise
        assert r.state == RiskState.PENDING_EVALUATION


# ══════════════════════════════════════════════════════════════════════════════
# 8. RiskHistory
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskHistory:
    def test_initial_state_seeded(self):
        r = _make_risk()
        states = r.history.states()
        assert len(states) == 1
        assert states[0].state == RiskState.CREATED

    def test_transition_appended(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION)
        assert len(r.history.transitions()) == 1

    def test_transitions_to_filter(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        passed_ts = r.history.transitions_to(RiskState.PASSED)
        assert len(passed_ts) == 1

    def test_transitions_from_filter(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        from_eval = r.history.transitions_from(RiskState.EVALUATING)
        assert len(from_eval) == 1

    def test_latest_transition(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.BLOCKED)
        latest = r.history.latest_transition(1)
        assert latest[0].to_state == RiskState.BLOCKED

    def test_override_count(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.BLOCKED)
        r.transition_to(RiskState.OVERRIDDEN)
        assert r.history.override_count == 1

    def test_eviction_on_capacity(self):
        h = RiskHistory(max_size=2)
        t1 = make_risk_transition("r", RiskState.CREATED, RiskState.PENDING_EVALUATION)
        t2 = make_risk_transition("r", RiskState.PENDING_EVALUATION, RiskState.EVALUATING)
        t3 = make_risk_transition("r", RiskState.EVALUATING, RiskState.PASSED)
        h.append_transition(t1)
        h.append_transition(t2)
        h.append_transition(t3)
        assert len(h.transitions()) == 2
        assert h.evicted_transitions == 1

    def test_total_transitions_includes_evicted(self):
        h = RiskHistory(max_size=1)
        h.append_transition(make_risk_transition("r", RiskState.CREATED, RiskState.PENDING_EVALUATION))
        h.append_transition(make_risk_transition("r", RiskState.PENDING_EVALUATION, RiskState.EVALUATING))
        assert h.total_transitions == 2

    def test_is_empty_initially(self):
        h = RiskHistory()
        assert h.is_empty() is True

    def test_len(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION)
        assert len(r.history) == 1

    def test_state_exit_stamped_on_transition(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION)
        states = r.history.states()
        assert states[0].exited_at is not None


# ══════════════════════════════════════════════════════════════════════════════
# 9. RiskMetadata
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskMetadata:
    def test_set_and_get_tag(self):
        m = RiskMetadata()
        m.set_tag("env", "prod")
        assert m.get_tag("env") == "prod"

    def test_remove_tag(self):
        m = RiskMetadata()
        m.set_tag("k", "v")
        m.remove_tag("k")
        assert not m.has_tag("k")

    def test_remove_missing_tag_no_error(self):
        m = RiskMetadata()
        m.remove_tag("nonexistent")   # should not raise

    def test_has_tag(self):
        m = RiskMetadata()
        m.set_tag("x", "1")
        assert m.has_tag("x") is True
        assert m.has_tag("y") is False

    def test_get_tag_default(self):
        m = RiskMetadata()
        assert m.get_tag("missing", "fallback") == "fallback"

    def test_set_notes(self):
        m = RiskMetadata()
        m.set_notes("review required")
        assert m.notes == "review required"

    def test_set_override_by(self):
        m = RiskMetadata()
        m.set_override_by("risk-officer")
        assert m.override_by == "risk-officer"

    def test_version_increments(self):
        m = RiskMetadata()
        v0 = m.version
        m.set_tag("a", "b")
        assert m.version == v0 + 1

    def test_to_dict(self):
        m = RiskMetadata()
        m.set_tag("k", "v")
        d = m.to_dict()
        assert d["tags"] == {"k": "v"}
        assert "notes" in d
        assert "override_by" in d

    def test_from_dict_roundtrip(self):
        m = RiskMetadata()
        m.set_tag("a", "1")
        m.set_notes("note")
        m.set_override_by("officer")
        m2 = RiskMetadata.from_dict(m.to_dict())
        assert m2.tags        == {"a": "1"}
        assert m2.notes       == "note"
        assert m2.override_by == "officer"


# ══════════════════════════════════════════════════════════════════════════════
# 10. RiskStatistics
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskStatistics:
    def test_initial_zeros(self):
        s = RiskStatistics()
        assert s.evaluations_created  == 0
        assert s.evaluations_passed   == 0
        assert s.evaluations_blocked  == 0
        assert s.total_transitions    == 0

    def test_record_created(self):
        s = RiskStatistics()
        s.record_created()
        assert s.evaluations_created == 1

    def test_record_passed(self):
        s = RiskStatistics()
        s.record_passed(evaluation_time_ms=20.0)
        assert s.evaluations_passed == 1
        assert s.total_evaluation_time_ms == 20.0

    def test_record_warned(self):
        s = RiskStatistics()
        s.record_warned(evaluation_time_ms=15.0)
        assert s.evaluations_warned == 1

    def test_record_blocked(self):
        s = RiskStatistics()
        s.record_blocked(evaluation_time_ms=5.0)
        assert s.evaluations_blocked == 1

    def test_record_overridden(self):
        s = RiskStatistics()
        s.record_overridden()
        assert s.evaluations_overridden == 1
        # override_count is incremented by record_transition(is_override=True)
        assert s.override_count == 0

    def test_record_expired(self):
        s = RiskStatistics()
        s.record_expired()
        assert s.evaluations_expired == 1

    def test_record_failed(self):
        s = RiskStatistics()
        s.record_failed()
        assert s.evaluations_failed == 1

    def test_record_archived(self):
        s = RiskStatistics()
        s.record_archived()
        assert s.evaluations_archived == 1

    def test_average_evaluation_time_ms(self):
        s = RiskStatistics()
        s.record_passed(evaluation_time_ms=20.0)
        s.record_passed(evaluation_time_ms=40.0)
        assert s.average_evaluation_time_ms == 30.0

    def test_average_evaluation_time_ms_zero_when_no_completions(self):
        s = RiskStatistics()
        assert s.average_evaluation_time_ms == 0.0

    def test_pass_rate(self):
        s = RiskStatistics()
        s.record_passed()
        s.record_passed()
        s.record_blocked()
        # 2/(2+1) ≈ 0.667
        assert abs(s.pass_rate - 2 / 3) < 0.001

    def test_block_rate(self):
        s = RiskStatistics()
        s.record_passed()
        s.record_blocked()
        assert s.block_rate == pytest.approx(0.5)

    def test_override_rate(self):
        s = RiskStatistics()
        s.record_passed()
        s.record_overridden()
        assert s.override_rate == pytest.approx(0.5)

    def test_rates_zero_when_no_outcomes(self):
        s = RiskStatistics()
        assert s.pass_rate     == 0.0
        assert s.block_rate    == 0.0
        assert s.override_rate == 0.0

    def test_to_dict_keys(self):
        s = RiskStatistics()
        d = s.to_dict()
        for key in ("evaluations_created", "evaluations_passed", "evaluations_blocked",
                    "average_evaluation_time_ms", "pass_rate", "block_rate"):
            assert key in d

    def test_record_transition(self):
        s = RiskStatistics()
        s.record_transition()
        assert s.total_transitions == 1

    def test_record_transition_is_override(self):
        s = RiskStatistics()
        s.record_transition(is_override=True)
        assert s.override_count == 1


# ══════════════════════════════════════════════════════════════════════════════
# 11. RiskContext
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskContext:
    def test_make_risk_context(self):
        ctx = make_risk_context(
            risk_id="rid",
            execution_id="exec",
            portfolio_id="port",
            strategy_id="strat",
            order_id="ord",
            position_id="pos",
            decision_id="dec",
            workflow_id="wf",
            requester="user",
        )
        assert ctx.risk_id       == "rid"
        assert ctx.execution_id  == "exec"
        assert ctx.portfolio_id  == "port"
        assert ctx.strategy_id   == "strat"
        assert ctx.order_id      == "ord"
        assert ctx.position_id   == "pos"
        assert ctx.decision_id   == "dec"
        assert ctx.workflow_id   == "wf"
        assert ctx.requester     == "user"

    def test_unique_context_ids(self):
        c1 = make_risk_context()
        c2 = make_risk_context()
        assert c1.context_id != c2.context_id

    def test_age_ms_positive(self):
        ctx = make_risk_context()
        time.sleep(0.001)
        assert ctx.age_ms > 0

    def test_has_order(self):
        ctx = make_risk_context(order_id="o1")
        assert ctx.has_order is True
        ctx2 = make_risk_context()
        assert ctx2.has_order is False

    def test_has_position(self):
        ctx = make_risk_context(position_id="p1")
        assert ctx.has_position is True

    def test_has_decision(self):
        ctx = make_risk_context(decision_id="d1")
        assert ctx.has_decision is True

    def test_has_workflow(self):
        ctx = make_risk_context(workflow_id="wf1")
        assert ctx.has_workflow is True

    def test_to_dict(self):
        ctx = make_risk_context(risk_id="rid")
        d   = ctx.to_dict()
        assert d["risk_id"]    == "rid"
        assert "context_id"    in d
        assert "created_at"    in d

    def test_frozen(self):
        ctx = make_risk_context()
        with pytest.raises((AttributeError, TypeError)):
            ctx.risk_id = "hack"  # type: ignore

    def test_metadata_stored(self):
        ctx = make_risk_context(metadata={"key": "val"})
        assert ctx.metadata["key"] == "val"


# ══════════════════════════════════════════════════════════════════════════════
# 12. RiskValidator
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskValidator:
    def _v(self) -> RiskValidator:
        return RiskValidator()

    def test_valid_transition(self):
        r   = _make_risk()
        res = self._v().validate_transition(r, RiskState.PENDING_EVALUATION)
        assert res.is_valid is True

    def test_invalid_transition(self):
        r   = _make_risk()
        res = self._v().validate_transition(r, RiskState.ARCHIVED)
        assert res.is_valid is False
        assert res.error_count == 1

    def test_identifiers_valid(self):
        r   = _make_risk()
        res = self._v().validate_identifiers(r)
        assert res.is_valid is True

    def test_identifiers_empty_risk_id_fails(self):
        # Force an empty risk_id via direct construction
        r = ExecutionRisk(
            risk_id="",
            execution_id="e",
            workflow_id="w",
            order_id="o",
            position_id="p",
            portfolio_id="port",
            strategy_id="s",
            decision_id="d",
            risk_category=RiskCategory.EXPOSURE,
        )
        res = self._v().validate_identifiers(r)
        assert res.is_valid is False

    def test_identifiers_warns_empty_portfolio(self):
        r = ExecutionRisk(
            risk_id="rid",
            execution_id="e",
            workflow_id="",
            order_id="",
            position_id="",
            portfolio_id="",
            strategy_id="",
            decision_id="",
            risk_category=RiskCategory.EXPOSURE,
        )
        res = self._v().validate_identifiers(r)
        assert res.warning_count > 0

    def test_timestamps_valid(self):
        r   = _make_risk()
        res = self._v().validate_timestamps(r)
        assert res.is_valid is True

    def test_timestamps_expiry_before_created_fails(self):
        r = _make_risk(expiry_time=time.time() - 100)
        res = self._v().validate_timestamps(r)
        assert res.is_valid is False

    def test_lifecycle_valid(self):
        r   = _make_risk()
        res = self._v().validate_lifecycle(r)
        assert res.is_valid is True

    def test_category_valid(self):
        r   = _make_risk()
        res = self._v().validate_category(r)
        assert res.is_valid is True

    def test_full_validate_valid(self):
        r   = _make_risk()
        res = self._v().validate_full(r)
        assert res.is_valid is True

    def test_validation_result_to_dict(self):
        r   = _make_risk()
        res = self._v().validate_full(r)
        d   = res.to_dict()
        assert "is_valid"      in d
        assert "errors"        in d
        assert "warnings"      in d
        assert "error_count"   in d
        assert "warning_count" in d

    def test_raise_if_invalid_does_not_raise_on_valid(self):
        r   = _make_risk()
        res = self._v().validate_full(r)
        self._v().raise_if_invalid(res)   # should not raise

    def test_raise_if_invalid_raises_on_failure(self):
        r   = _make_risk()
        res = self._v().validate_transition(r, RiskState.ARCHIVED)
        with pytest.raises(RiskValidationError):
            self._v().raise_if_invalid(res)


# ══════════════════════════════════════════════════════════════════════════════
# 13. RiskFactory
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskFactory:
    def _f(self) -> RiskFactory:
        return RiskFactory()

    def test_create_returns_execution_risk(self):
        r = self._f().create(RiskCategory.EXPOSURE)
        assert isinstance(r, ExecutionRisk)

    def test_create_initial_state(self):
        r = self._f().create(RiskCategory.MARGIN)
        assert r.state == RiskState.CREATED

    def test_create_generates_uuid(self):
        r1 = self._f().create(RiskCategory.EXPOSURE)
        r2 = self._f().create(RiskCategory.EXPOSURE)
        assert r1.risk_id != r2.risk_id

    def test_create_uses_provided_risk_id(self):
        r = self._f().create(RiskCategory.COMPLIANCE, risk_id="custom-id")
        assert r.risk_id == "custom-id"

    def test_create_exposure_risk(self):
        r = self._f().create_exposure_risk()
        assert r.risk_category == RiskCategory.EXPOSURE

    def test_create_margin_risk(self):
        r = self._f().create_margin_risk()
        assert r.risk_category == RiskCategory.MARGIN

    def test_create_liquidity_risk(self):
        r = self._f().create_liquidity_risk()
        assert r.risk_category == RiskCategory.LIQUIDITY

    def test_create_compliance_risk(self):
        r = self._f().create_compliance_risk()
        assert r.risk_category == RiskCategory.COMPLIANCE

    def test_create_order_size_risk(self):
        r = self._f().create_order_size_risk()
        assert r.risk_category == RiskCategory.ORDER_SIZE

    def test_create_concentration_risk(self):
        r = self._f().create_concentration_risk()
        assert r.risk_category == RiskCategory.CONCENTRATION

    def test_create_price_risk(self):
        r = self._f().create_price_risk()
        assert r.risk_category == RiskCategory.PRICE

    def test_create_execution_risk(self):
        r = self._f().create_execution_risk()
        assert r.risk_category == RiskCategory.EXECUTION

    def test_create_operational_risk(self):
        r = self._f().create_operational_risk()
        assert r.risk_category == RiskCategory.OPERATIONAL

    def test_make_created_event(self):
        r = self._f().create(RiskCategory.EXPOSURE, portfolio_id="p1")
        e = self._f().make_created_event(r)
        assert e.event_type  == RiskEventType.RISK_CREATED
        assert e.risk_id     == r.risk_id
        assert e.actor       == ACTOR_FACTORY

    def test_expiry_time_stored(self):
        t = time.time() + 300
        r = self._f().create(RiskCategory.EXPOSURE, expiry_time=t)
        assert r.expiry_time == t

    def test_none_category_raises(self):
        with pytest.raises((RiskValidationError, TypeError)):
            self._f().create(None)  # type: ignore


# ══════════════════════════════════════════════════════════════════════════════
# 14. RiskRegistry — lifecycle guard
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskRegistryLifecycleGuard:
    def test_register_before_start_raises(self):
        reg  = RiskRegistry()
        risk = _make_risk()
        with pytest.raises(RiskRegistryNotRunningError):
            reg.register(risk)

    def test_deregister_before_start_raises(self):
        reg = RiskRegistry()
        with pytest.raises(RiskRegistryNotRunningError):
            reg.deregister("nonexistent")

    def test_notify_before_start_raises(self):
        reg  = RiskRegistry()
        risk = _make_risk()
        with pytest.raises(RiskRegistryNotRunningError):
            reg.notify_transition(risk, RiskState.PENDING_EVALUATION)

    def test_start_and_stop(self):
        reg = _started_registry()
        reg.stop()   # should not raise


# ══════════════════════════════════════════════════════════════════════════════
# 15. RiskRegistry — CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskRegistryCRUD:
    def test_register_and_get(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        assert reg.get(risk.risk_id) is risk
        reg.stop()

    def test_require_raises_when_missing(self):
        reg = _started_registry()
        with pytest.raises(RiskNotFoundError):
            reg.require("nonexistent")
        reg.stop()

    def test_contains_true_after_register(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        assert reg.contains(risk.risk_id) is True
        reg.stop()

    def test_deregister_removes(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        reg.deregister(risk.risk_id)
        assert reg.get(risk.risk_id) is None
        reg.stop()

    def test_deregister_missing_raises(self):
        reg = _started_registry()
        with pytest.raises(RiskNotFoundError):
            reg.deregister("missing-id")
        reg.stop()

    def test_duplicate_registration_raises(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        with pytest.raises(DuplicateRiskError):
            reg.register(risk)
        reg.stop()

    def test_capacity_enforced(self):
        reg  = _started_registry(max_evaluations=1)
        risk = _make_risk()
        reg.register(risk)
        with pytest.raises(RiskRegistryCapacityError):
            reg.register(_make_risk())
        reg.stop()

    def test_count_increments(self):
        reg = _started_registry()
        reg.register(_make_risk())
        reg.register(_make_risk())
        assert reg.count == 2
        reg.stop()

    def test_is_empty(self):
        reg = _started_registry()
        assert reg.is_empty is True
        reg.register(_make_risk())
        assert reg.is_empty is False
        reg.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 16. RiskRegistry — filtering
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskRegistryFiltering:
    def test_all(self):
        reg = _started_registry()
        reg.register(_make_risk())
        reg.register(_make_risk())
        assert len(reg.all()) == 2
        reg.stop()

    def test_by_state(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        risk.transition_to(RiskState.PENDING_EVALUATION)
        result = reg.by_state(RiskState.PENDING_EVALUATION)
        assert risk in result
        reg.stop()

    def test_by_category(self):
        reg  = _started_registry()
        r1   = _make_risk(category=RiskCategory.COMPLIANCE)
        r2   = _make_risk(category=RiskCategory.MARGIN)
        reg.register(r1)
        reg.register(r2)
        result = reg.by_category(RiskCategory.COMPLIANCE)
        assert r1 in result
        assert r2 not in result
        reg.stop()

    def test_by_portfolio(self):
        reg  = _started_registry()
        risk = _make_risk(portfolio_id="port-A")
        reg.register(risk)
        result = reg.by_portfolio("port-A")
        assert risk in result
        assert reg.by_portfolio("port-B") == []
        reg.stop()

    def test_by_strategy(self):
        reg  = _started_registry()
        risk = _make_risk(strategy_id="strat-X")
        reg.register(risk)
        assert risk in reg.by_strategy("strat-X")
        reg.stop()

    def test_by_execution(self):
        reg  = _started_registry()
        risk = _make_risk(execution_id="ex-99")
        reg.register(risk)
        assert risk in reg.by_execution("ex-99")
        reg.stop()

    def test_active(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        risk.transition_to(RiskState.PENDING_EVALUATION)
        assert risk in reg.active()
        reg.stop()

    def test_passed(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        _advance_to_evaluating(risk)
        risk.transition_to(RiskState.PASSED)
        assert risk in reg.passed()
        reg.stop()

    def test_blocked(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        _advance_to_evaluating(risk)
        risk.transition_to(RiskState.BLOCKED)
        assert risk in reg.blocked()
        reg.stop()

    def test_archived(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        _advance_to_evaluating(risk)
        risk.transition_to(RiskState.PASSED)
        risk.transition_to(RiskState.ARCHIVED)
        assert risk in reg.archived()
        reg.stop()

    def test_ended(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        risk.transition_to(RiskState.FAILED)
        assert risk in reg.ended()
        reg.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 17. RiskRegistry — statistics
# ══════════════════════════════════════════════════════════════════════════════

class TestRiskRegistryStatistics:
    def test_created_count(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        assert reg.statistics().evaluations_created == 1
        reg.stop()

    def test_notify_transition_passed(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        _advance_to_evaluating(risk)
        risk.transition_to(RiskState.PASSED)
        reg.notify_transition(risk, RiskState.PASSED, evaluation_time_ms=10.0)
        stats = reg.statistics()
        assert stats.evaluations_passed == 1
        assert stats.total_transitions  == 1
        reg.stop()

    def test_notify_transition_blocked(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        _advance_to_evaluating(risk)
        risk.transition_to(RiskState.BLOCKED)
        reg.notify_transition(risk, RiskState.BLOCKED, evaluation_time_ms=5.0)
        assert reg.statistics().evaluations_blocked == 1
        reg.stop()

    def test_notify_transition_overridden(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        _advance_to_evaluating(risk)
        risk.transition_to(RiskState.BLOCKED)
        risk.transition_to(RiskState.OVERRIDDEN)
        reg.notify_transition(risk, RiskState.OVERRIDDEN)
        stats = reg.statistics()
        assert stats.evaluations_overridden == 1
        assert stats.override_count         == 1
        reg.stop()

    def test_statistics_is_copy(self):
        reg   = _started_registry()
        stats = reg.statistics()
        reg.register(_make_risk())
        assert stats.evaluations_created == 0   # copy is not affected
        reg.stop()


# ══════════════════════════════════════════════════════════════════════════════
# 18. Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_invalid_transition_error_attrs(self):
        err = InvalidRiskTransitionError(
            "rid", RiskState.CREATED, RiskState.ARCHIVED
        )
        assert err.risk_id    == "rid"
        assert err.from_state == RiskState.CREATED
        assert err.to_state   == RiskState.ARCHIVED
        assert "ERL-001"      in str(err)

    def test_risk_not_found_error(self):
        err = RiskNotFoundError("rid")
        assert err.risk_id == "rid"
        assert "ERL-002"   in str(err)

    def test_duplicate_risk_error(self):
        err = DuplicateRiskError("rid")
        assert err.risk_id == "rid"
        assert "ERL-003"   in str(err)

    def test_risk_validation_error(self):
        err = RiskValidationError("bad field")
        assert "ERL-004" in str(err)

    def test_capacity_error(self):
        err = RiskRegistryCapacityError(5_000)
        assert err.max_capacity == 5_000
        assert "ERL-005"        in str(err)

    def test_not_running_error(self):
        err = RiskRegistryNotRunningError()
        assert "ERL-006" in str(err)

    def test_state_error(self):
        err = RiskStateError("rid", RiskState.EVALUATING, RiskState.CREATED)
        assert err.risk_id        == "rid"
        assert err.expected_state == RiskState.EVALUATING
        assert err.actual_state   == RiskState.CREATED
        assert "ERL-007"          in str(err)

    def test_all_errors_inherit_from_base(self):
        for cls in (
            InvalidRiskTransitionError,
            RiskNotFoundError,
            DuplicateRiskError,
            RiskValidationError,
            RiskRegistryCapacityError,
            RiskRegistryNotRunningError,
            RiskStateError,
        ):
            assert issubclass(cls, ExecutionRiskLifecycleError)


# ══════════════════════════════════════════════════════════════════════════════
# 19. Full lifecycle walk-through
# ══════════════════════════════════════════════════════════════════════════════

class TestFullLifecycle:
    def test_happy_path_passed_to_archived(self):
        r = _make_risk()
        assert r.state == RiskState.CREATED

        r.transition_to(RiskState.PENDING_EVALUATION)
        assert r.state == RiskState.PENDING_EVALUATION

        r.transition_to(RiskState.EVALUATING)
        assert r.state == RiskState.EVALUATING

        r.transition_to(RiskState.PASSED, evaluation_time_ms=8.0)
        assert r.state == RiskState.PASSED
        assert r.is_passed is True

        r.transition_to(RiskState.ARCHIVED)
        assert r.state == RiskState.ARCHIVED
        assert r.is_archived is True

        # Verify history
        transitions = r.history.transitions()
        assert len(transitions) == 4

    def test_blocked_then_overridden_to_archived(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION)
        r.transition_to(RiskState.EVALUATING)
        r.transition_to(RiskState.BLOCKED)
        assert r.is_blocked is True

        r.transition_to(RiskState.OVERRIDDEN)
        assert r.is_passed is True

        r.transition_to(RiskState.ARCHIVED)
        assert r.is_archived is True

    def test_warning_to_blocked_to_overridden(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.WARNING)
        r.transition_to(RiskState.BLOCKED)
        r.transition_to(RiskState.OVERRIDDEN)
        r.transition_to(RiskState.ARCHIVED)
        assert r.state == RiskState.ARCHIVED

    def test_failed_to_archived(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION)
        r.transition_to(RiskState.FAILED)
        r.transition_to(RiskState.ARCHIVED)
        assert r.is_archived is True

    def test_expired_from_evaluating(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.EXPIRED)
        r.transition_to(RiskState.ARCHIVED)
        assert r.is_archived is True

    def test_evaluation_time_carried_forward(self):
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.WARNING, evaluation_time_ms=25.5)
        assert r.evaluation_time_ms == 25.5


# ══════════════════════════════════════════════════════════════════════════════
# 20. Thread safety
# ══════════════════════════════════════════════════════════════════════════════

class TestThreadSafety:
    def test_concurrent_register(self):
        reg    = _started_registry(max_evaluations=500)
        errors: List[Exception] = []

        def worker():
            try:
                reg.register(_make_risk())
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert reg.count == 50
        reg.stop()

    def test_concurrent_transitions(self):
        """Multiple threads each transition a separate risk object without error."""
        risks  = [_make_risk() for _ in range(20)]
        errors: List[Exception] = []

        def worker(r: ExecutionRisk):
            try:
                r.transition_to(RiskState.PENDING_EVALUATION)
                r.transition_to(RiskState.EVALUATING)
                r.transition_to(RiskState.PASSED)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(r,)) for r in risks]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        for r in risks:
            assert r.state == RiskState.PASSED


# ══════════════════════════════════════════════════════════════════════════════
# 21. Regression & edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_history_min_size_one(self):
        h = RiskHistory(max_size=0)   # clamped to 1
        t = make_risk_transition("r", RiskState.CREATED, RiskState.PENDING_EVALUATION)
        h.append_transition(t)
        assert len(h.transitions()) == 1

    def test_multiple_event_listeners(self):
        received_a: List[RiskEvent] = []
        received_b: List[RiskEvent] = []
        r = _make_risk()
        r.add_event_listener(received_a.append)
        r.add_event_listener(received_b.append)
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        assert len(received_a) > 0
        assert len(received_b) > 0

    def test_transition_metadata_stored(self):
        r = _make_risk()
        r.transition_to(
            RiskState.PENDING_EVALUATION,
            metadata={"source": "unit-test"},
        )
        tr = r.history.transitions()[0]
        assert tr.metadata["source"] == "unit-test"

    def test_transition_actor_stored(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION, actor="risk-engine-v2")
        tr = r.history.transitions()[0]
        assert tr.actor == "risk-engine-v2"

    def test_transition_reason_stored(self):
        r = _make_risk()
        r.transition_to(RiskState.PENDING_EVALUATION, reason="queued by scheduler")
        tr = r.history.transitions()[0]
        assert tr.reason == "queued by scheduler"

    def test_risk_id_not_mutated_by_transition(self):
        r   = _make_risk()
        rid = r.risk_id
        r.transition_to(RiskState.PENDING_EVALUATION)
        assert r.risk_id == rid

    def test_registry_read_after_stop(self):
        reg  = _started_registry()
        risk = _make_risk()
        reg.register(risk)
        reg.stop()
        # Read ops are permitted after stop
        assert reg.get(risk.risk_id) is risk

    def test_all_categories_creatable(self):
        f = RiskFactory()
        for cat in RiskCategory:
            r = f.create(cat)
            assert r.risk_category == cat

    def test_to_dict_is_serialisable(self):
        import json
        r = _make_risk()
        _advance_to_evaluating(r)
        r.transition_to(RiskState.PASSED)
        d = r.to_dict()
        json.dumps(d)   # must not raise
