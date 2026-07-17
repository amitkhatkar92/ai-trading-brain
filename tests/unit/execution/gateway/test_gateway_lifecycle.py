"""tests/unit/execution/gateway/test_gateway_lifecycle.py
==================================================
Unit tests for C6 Phase 5 M1 — Execution Gateway Lifecycle.

Coverage:
  TestConstants               — enums, sentinel sets, system IDs
  TestExceptions              — hierarchy, error codes, fields
  TestGatewayContext          — construction, properties, to_dict
  TestGatewayMetadata         — tags, notes, priority, to_dict
  TestGatewayStateRecord      — immutability, duration_ms, with_exit
  TestGatewayTransition       — construction, derived props, to_dict
  TestGatewayHistory          — append, filters, eviction, to_dict
  TestGatewayStatistics       — counters, derived rates, copy, reset
  TestGatewayEvents           — all 9 factory functions, to_dict
  TestValidationResult        — bool, error/warning counts, to_dict
  TestGatewayValidator        — valid/invalid transitions, identifiers
  TestGatewayFactory          — create, create_from_context, create_with_event
  TestGatewayRequest          — construction, transition_to, history, events
  TestStateMachine            — all valid transitions, invalid transitions
  TestGatewayRegistry         — register, get, filters, capacity, lifecycle
  TestGatewayLifecycle        — full workflow, fail, cancel, archive, query
  TestStatisticsIntegration   — stats updated by transitions
  TestEventsIntegration       — listener receives all events
  TestConcurrency             — concurrent transitions, concurrent creates
  TestRegression              — edge cases, double-start guard

95%+ coverage
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import List
from unittest.mock import MagicMock

import pytest

from iios.execution.gateway.lifecycle import (
    ACTIVE_STATES,
    ACTOR_LIFECYCLE,
    ENDED_STATES,
    FAILURE_STATES,
    GatewayEvent,
    GatewayEventType,
    GatewayFactory,
    GatewayHistory,
    GatewayLifecycle,
    GatewayLifecycleNotRunningError,
    GatewayMetadata,
    GatewayRegistryCapacityError,
    GatewayRegistry,
    GatewayRequest,
    GatewayRequestNotFoundError,
    GatewayState,
    GatewayStateRecord,
    GatewayStatistics,
    GatewayTransition,
    GatewayValidator,
    InvalidGatewayTransitionError,
    LIFECYCLE_SYSTEM_ID,
    OUTCOME_STATES,
    REGISTRY_SYSTEM_ID,
    SUCCESS_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    ValidationResult,
    VERSION,
    DuplicateGatewayRequestError,
    ExecutionGatewayLifecycleError,
    GatewayContext,
    GatewayValidationError,
    make_gateway_archived,
    make_gateway_cancelled,
    make_gateway_completed,
    make_gateway_context,
    make_gateway_created,
    make_gateway_dispatched,
    make_gateway_failed,
    make_gateway_queued,
    make_gateway_received,
    make_gateway_transition,
    make_gateway_validated,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _gid() -> str:
    return str(uuid.uuid4())


def _request(gateway_id: str = "", **kw) -> GatewayRequest:
    return GatewayRequest(
        gateway_id=gateway_id or _gid(),
        execution_id=kw.get("execution_id", "EX-1"),
        workflow_id=kw.get("workflow_id", "WF-1"),
        order_id=kw.get("order_id", "ORD-1"),
        position_id=kw.get("position_id", ""),
        portfolio_id=kw.get("portfolio_id", "PORT-1"),
        strategy_id=kw.get("strategy_id", "STRAT-1"),
        decision_id=kw.get("decision_id", ""),
        correlation_id=kw.get("correlation_id", ""),
    )


def _lifecycle(**kw) -> GatewayLifecycle:
    lc = GatewayLifecycle(**kw)
    lc.start()
    return lc


def _full_workflow(lc: GatewayLifecycle, **kw) -> GatewayRequest:
    """Drive a request through the happy-path lifecycle end-to-end."""
    req = lc.create(execution_id="EX-1", order_id="ORD-1",
                    portfolio_id="PORT-1", strategy_id="STRAT-1", **kw)
    gid = req.gateway_id
    lc.receive(gid)
    lc.start_validation(gid)
    lc.mark_ready(gid)
    lc.queue(gid)
    lc.start_routing(gid)
    lc.dispatch(gid)
    lc.complete(gid)
    return req


# ═══════════════════════════════════════════════════════════════════════════════
# TestConstants
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_system_id_prefix(self):
        assert LIFECYCLE_SYSTEM_ID.startswith("iios:")

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_state_values(self):
        vals = {s.value for s in GatewayState}
        for expected in ("CREATED","RECEIVED","VALIDATING","READY","QUEUED",
                         "ROUTING","DISPATCHED","COMPLETED","FAILED","CANCELLED","ARCHIVED"):
            assert expected in vals

    def test_event_type_values(self):
        vals = {e.value for e in GatewayEventType}
        assert "GATEWAY_CREATED"    in vals
        assert "GATEWAY_COMPLETED"  in vals
        assert "GATEWAY_ARCHIVED"   in vals

    def test_active_states_not_in_ended(self):
        for s in ACTIVE_STATES:
            assert s not in ENDED_STATES

    def test_terminal_subset_of_ended(self):
        assert TERMINAL_STATES.issubset(ENDED_STATES)

    def test_outcome_subset_of_ended(self):
        assert OUTCOME_STATES.issubset(ENDED_STATES)

    def test_archived_is_terminal(self):
        assert GatewayState.ARCHIVED in TERMINAL_STATES

    def test_valid_transitions_all_states_covered(self):
        for s in GatewayState:
            assert s in VALID_TRANSITIONS

    def test_archived_has_no_transitions(self):
        assert len(VALID_TRANSITIONS[GatewayState.ARCHIVED]) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# TestExceptions
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    def test_base_is_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(ExecutionGatewayLifecycleError, IIOSError)

    def test_invalid_transition_fields(self):
        e = InvalidGatewayTransitionError("GW-1", GatewayState.CREATED, GatewayState.DISPATCHED)
        assert e.gateway_id == "GW-1"
        assert e.from_state == GatewayState.CREATED
        assert e.to_state   == GatewayState.DISPATCHED
        assert "CREATED"    in str(e)
        assert "DISPATCHED" in str(e)

    def test_not_found_fields(self):
        e = GatewayRequestNotFoundError("GW-99")
        assert e.gateway_id == "GW-99"
        assert "GW-99" in str(e)

    def test_duplicate_fields(self):
        e = DuplicateGatewayRequestError("GW-DUP")
        assert e.gateway_id == "GW-DUP"

    def test_capacity_fields(self):
        e = GatewayRegistryCapacityError(100)
        assert e.max_capacity == 100

    def test_not_running_message(self):
        e = GatewayLifecycleNotRunningError()
        assert "not running" in str(e).lower()

    def test_validation_error_has_message(self):
        e = GatewayValidationError("bad data")
        assert e.message == "bad data"

    def test_all_subclass_base(self):
        from iios.execution.gateway.lifecycle.exceptions import GatewayStateError
        for cls in (
            InvalidGatewayTransitionError, GatewayRequestNotFoundError,
            DuplicateGatewayRequestError, GatewayValidationError,
            GatewayRegistryCapacityError, GatewayLifecycleNotRunningError,
            GatewayStateError,
        ):
            assert issubclass(cls, ExecutionGatewayLifecycleError)


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayContext
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayContext:
    def test_required_fields(self):
        ctx = make_gateway_context("EX-1", "ORD-1", "PORT-1", "STRAT-1")
        assert ctx.execution_id == "EX-1"
        assert ctx.order_id     == "ORD-1"
        assert ctx.portfolio_id == "PORT-1"
        assert ctx.strategy_id  == "STRAT-1"

    def test_optional_fields_default(self):
        ctx = make_gateway_context("E", "O", "P", "S")
        assert ctx.symbol       == ""
        assert ctx.quantity     == 0.0
        assert ctx.price        == 0.0

    def test_full_construction(self):
        ctx = make_gateway_context(
            "EX-1","ORD-1","PORT-1","STRAT-1",
            symbol="INFY", side="BUY", quantity=200.0, price=1450.0,
            asset_class="EQUITY",
        )
        assert ctx.symbol     == "INFY"
        assert ctx.side       == "BUY"
        assert ctx.quantity   == 200.0
        assert ctx.asset_class == "EQUITY"

    def test_immutable(self):
        ctx = make_gateway_context("E","O","P","S")
        with pytest.raises((TypeError, AttributeError)):
            ctx.execution_id = "changed"  # type: ignore

    def test_has_execution_payload_false(self):
        ctx = make_gateway_context("E","O","P","S")
        assert ctx.has_execution_payload is False

    def test_has_execution_payload_true(self):
        ctx = make_gateway_context("E","O","P","S", execution_payload={"a": 1})
        assert ctx.has_execution_payload is True

    def test_age_ms_non_negative(self):
        ctx = make_gateway_context("E","O","P","S")
        time.sleep(0.01)
        assert ctx.age_ms >= 0

    def test_to_dict(self):
        ctx = make_gateway_context("EX-1","ORD-1","PORT-1","STRAT-1")
        d = ctx.to_dict()
        assert d["execution_id"] == "EX-1"
        assert "received_at" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayMetadata
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayMetadata:
    def test_initial_defaults(self):
        m = GatewayMetadata()
        assert m.notes    == ""
        assert m.priority == 0
        assert m.version  == 1

    def test_set_tag(self):
        m = GatewayMetadata()
        m.set_tag("env", "prod")
        assert m.get_tag("env") == "prod"

    def test_has_tag(self):
        m = GatewayMetadata()
        assert m.has_tag("x") is False
        m.set_tag("x", "1")
        assert m.has_tag("x") is True

    def test_remove_tag(self):
        m = GatewayMetadata()
        m.set_tag("k", "v")
        m.remove_tag("k")
        assert m.has_tag("k") is False

    def test_remove_tag_noop_if_missing(self):
        m = GatewayMetadata()
        m.remove_tag("missing")  # no exception

    def test_set_notes(self):
        m = GatewayMetadata()
        m.set_notes("test note")
        assert m.notes == "test note"

    def test_set_priority(self):
        m = GatewayMetadata()
        m.set_priority(10)
        assert m.priority == 10

    def test_version_increments_on_change(self):
        m = GatewayMetadata()
        before = m.version
        m.set_tag("a", "b")
        assert m.version == before + 1

    def test_to_dict(self):
        m = GatewayMetadata()
        d = m.to_dict()
        assert "tags"     in d
        assert "priority" in d
        assert "version"  in d

    def test_from_dict(self):
        m = GatewayMetadata()
        m.set_tag("foo", "bar")
        m.set_priority(5)
        d = m.to_dict()
        m2 = GatewayMetadata.from_dict(d)
        assert m2.get_tag("foo") == "bar"
        assert m2.priority       == 5


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayStateRecord
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayStateRecord:
    def test_construction(self):
        now = time.time()
        r = GatewayStateRecord(state=GatewayState.CREATED, entered_at=now)
        assert r.state      == GatewayState.CREATED
        assert r.entered_at == now
        assert r.exited_at  is None

    def test_is_current_true(self):
        r = GatewayStateRecord(GatewayState.CREATED, time.time())
        assert r.is_current is True

    def test_is_current_false_after_exit(self):
        r = GatewayStateRecord(GatewayState.CREATED, time.time(), exited_at=time.time())
        assert r.is_current is False

    def test_duration_ms_none_when_no_exit(self):
        r = GatewayStateRecord(GatewayState.CREATED, time.time())
        assert r.duration_ms is None

    def test_duration_ms_computed(self):
        t = time.time()
        r = GatewayStateRecord(GatewayState.CREATED, t, exited_at=t + 1.0)
        assert abs(r.duration_ms - 1000.0) < 1.0

    def test_with_exit_returns_new_record(self):
        r = GatewayStateRecord(GatewayState.CREATED, time.time())
        r2 = r.with_exit()
        assert r.exited_at  is None   # original unchanged
        assert r2.exited_at is not None

    def test_immutable(self):
        r = GatewayStateRecord(GatewayState.CREATED, time.time())
        with pytest.raises((TypeError, AttributeError)):
            r.state = GatewayState.RECEIVED  # type: ignore

    def test_to_dict(self):
        r = GatewayStateRecord(GatewayState.CREATED, time.time())
        d = r.to_dict()
        assert d["state"]      == "CREATED"
        assert d["is_current"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayTransition
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayTransition:
    def test_construction(self):
        t = make_gateway_transition("GW-1", GatewayState.CREATED, GatewayState.RECEIVED)
        assert t.gateway_id == "GW-1"
        assert t.from_state == GatewayState.CREATED
        assert t.to_state   == GatewayState.RECEIVED

    def test_is_valid_true(self):
        t = make_gateway_transition("GW-1", GatewayState.CREATED, GatewayState.RECEIVED)
        assert t.is_valid is True

    def test_is_valid_false(self):
        t = make_gateway_transition("GW-1", GatewayState.CREATED, GatewayState.DISPATCHED)
        assert t.is_valid is False

    def test_is_terminal_true(self):
        t = make_gateway_transition("GW-1", GatewayState.COMPLETED, GatewayState.ARCHIVED)
        assert t.is_terminal is True

    def test_is_terminal_false(self):
        t = make_gateway_transition("GW-1", GatewayState.CREATED, GatewayState.RECEIVED)
        assert t.is_terminal is False

    def test_is_success(self):
        t = make_gateway_transition("GW-1", GatewayState.DISPATCHED, GatewayState.COMPLETED)
        assert t.is_success is True

    def test_is_failure(self):
        t = make_gateway_transition("GW-1", GatewayState.ROUTING, GatewayState.FAILED)
        assert t.is_failure is True

    def test_is_cancellation(self):
        t = make_gateway_transition("GW-1", GatewayState.QUEUED, GatewayState.CANCELLED)
        assert t.is_cancellation is True

    def test_immutable(self):
        t = make_gateway_transition("GW-1", GatewayState.CREATED, GatewayState.RECEIVED)
        with pytest.raises((TypeError, AttributeError)):
            t.gateway_id = "changed"  # type: ignore

    def test_to_dict(self):
        t = make_gateway_transition("GW-1", GatewayState.CREATED, GatewayState.RECEIVED,
                                    actor="test", reason="unit-test")
        d = t.to_dict()
        assert d["gateway_id"] == "GW-1"
        assert d["from_state"] == "CREATED"
        assert d["to_state"]   == "RECEIVED"
        assert d["actor"]      == "test"


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayHistory
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayHistory:
    def test_append_transition(self):
        h = GatewayHistory()
        t = make_gateway_transition("GW-1", GatewayState.CREATED, GatewayState.RECEIVED)
        h.append_transition(t)
        assert h.transition_count == 1

    def test_append_state(self):
        h = GatewayHistory()
        r = GatewayStateRecord(GatewayState.CREATED, time.time())
        h.append_state(r)
        assert h.state_count == 1

    def test_latest_transition(self):
        h = GatewayHistory()
        t1 = make_gateway_transition("GW-1", GatewayState.CREATED, GatewayState.RECEIVED)
        t2 = make_gateway_transition("GW-1", GatewayState.RECEIVED, GatewayState.VALIDATING)
        h.append_transition(t1)
        h.append_transition(t2)
        latest = h.latest_transition(1)
        assert latest[0].to_state == GatewayState.VALIDATING

    def test_transitions_to(self):
        h = GatewayHistory()
        h.append_transition(make_gateway_transition("G", GatewayState.CREATED, GatewayState.RECEIVED))
        h.append_transition(make_gateway_transition("G", GatewayState.RECEIVED, GatewayState.VALIDATING))
        assert len(h.transitions_to(GatewayState.RECEIVED)) == 1

    def test_transitions_from(self):
        h = GatewayHistory()
        h.append_transition(make_gateway_transition("G", GatewayState.CREATED, GatewayState.RECEIVED))
        assert len(h.transitions_from(GatewayState.CREATED)) == 1

    def test_update_last_state_exit(self):
        h = GatewayHistory()
        h.append_state(GatewayStateRecord(GatewayState.CREATED, time.time()))
        h.update_last_state_exit(time.time() + 1)
        assert h.states()[0].exited_at is not None

    def test_eviction_at_capacity(self):
        h = GatewayHistory(max_size=2)
        for i in range(3):
            h.append_transition(
                make_gateway_transition("G", GatewayState.CREATED, GatewayState.RECEIVED)
            )
        assert h.transition_count   == 2
        assert h.evicted_transitions == 1

    def test_current_state_record(self):
        h = GatewayHistory()
        h.append_state(GatewayStateRecord(GatewayState.CREATED, time.time()))
        current = h.current_state_record()
        assert current is not None
        assert current.state == GatewayState.CREATED

    def test_to_dict_structure(self):
        h = GatewayHistory()
        d = h.to_dict()
        assert "transitions"      in d
        assert "states"           in d
        assert "transition_count" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayStatistics
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayStatistics:
    def test_initial_zeroes(self):
        s = GatewayStatistics()
        assert s.requests_received  == 0
        assert s.requests_completed == 0

    def test_record_received(self):
        s = GatewayStatistics()
        s.record_received()
        assert s.requests_received == 1

    def test_record_completed(self):
        s = GatewayStatistics()
        s.record_received()
        s.record_completed(100.0)
        assert s.requests_completed == 1
        assert s.total_lifecycle_time_ms == 100.0

    def test_record_failed(self):
        s = GatewayStatistics()
        s.record_received()
        s.record_failed(50.0)
        assert s.requests_failed == 1

    def test_record_cancelled(self):
        s = GatewayStatistics()
        s.record_received()
        s.record_cancelled(30.0)
        assert s.requests_cancelled == 1

    def test_record_archived(self):
        s = GatewayStatistics()
        s.record_archived()
        assert s.requests_archived == 1

    def test_record_transition(self):
        s = GatewayStatistics()
        s.record_transition()
        assert s.total_transitions == 1

    def test_requests_ended(self):
        s = GatewayStatistics()
        s.record_completed()
        s.record_failed()
        s.record_cancelled()
        assert s.requests_ended == 3

    def test_average_lifecycle_time(self):
        s = GatewayStatistics()
        s.record_completed(100.0)
        s.record_completed(200.0)
        assert s.average_lifecycle_time_ms == 150.0

    def test_completion_rate(self):
        s = GatewayStatistics()
        s.record_completed()
        s.record_completed()
        s.record_failed()
        assert abs(s.completion_rate - 2/3) < 0.001

    def test_failure_rate(self):
        s = GatewayStatistics()
        s.record_failed()
        s.record_completed()
        assert abs(s.failure_rate - 0.5) < 0.001

    def test_cancellation_rate(self):
        s = GatewayStatistics()
        s.record_cancelled()
        assert s.cancellation_rate == 1.0

    def test_copy_independent(self):
        s = GatewayStatistics()
        s.record_received()
        c = s.copy()
        s.record_received()
        assert c.requests_received == 1
        assert s.requests_received == 2

    def test_reset(self):
        s = GatewayStatistics()
        s.record_received()
        s.record_completed(100.0)
        s.reset()
        assert s.requests_received   == 0
        assert s.requests_completed  == 0
        assert s.total_lifecycle_time_ms == 0.0

    def test_to_dict(self):
        s = GatewayStatistics()
        d = s.to_dict()
        assert "requests_received"        in d
        assert "completion_rate"          in d
        assert "average_lifecycle_time_ms" in d


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayEvents
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayEvents:
    def _check(self, event: GatewayEvent, expected_type: GatewayEventType,
               expected_state: GatewayState):
        assert isinstance(event, GatewayEvent)
        assert event.event_type   == expected_type
        assert event.state        == expected_state
        assert event.event_id
        assert event.occurred_at > 0

    def test_created(self):
        e = make_gateway_created("GW-1", execution_id="EX-1", portfolio_id="P-1")
        self._check(e, GatewayEventType.GATEWAY_CREATED, GatewayState.CREATED)
        assert e.gateway_id   == "GW-1"
        assert e.execution_id == "EX-1"

    def test_received(self):
        e = make_gateway_received("GW-1")
        self._check(e, GatewayEventType.GATEWAY_RECEIVED, GatewayState.RECEIVED)

    def test_validated(self):
        e = make_gateway_validated("GW-1")
        self._check(e, GatewayEventType.GATEWAY_VALIDATED, GatewayState.READY)

    def test_queued(self):
        e = make_gateway_queued("GW-1")
        self._check(e, GatewayEventType.GATEWAY_QUEUED, GatewayState.QUEUED)

    def test_dispatched(self):
        e = make_gateway_dispatched("GW-1")
        self._check(e, GatewayEventType.GATEWAY_DISPATCHED, GatewayState.DISPATCHED)

    def test_completed(self):
        e = make_gateway_completed("GW-1")
        self._check(e, GatewayEventType.GATEWAY_COMPLETED, GatewayState.COMPLETED)

    def test_failed(self):
        e = make_gateway_failed("GW-1")
        self._check(e, GatewayEventType.GATEWAY_FAILED, GatewayState.FAILED)

    def test_cancelled(self):
        e = make_gateway_cancelled("GW-1")
        self._check(e, GatewayEventType.GATEWAY_CANCELLED, GatewayState.CANCELLED)

    def test_archived(self):
        e = make_gateway_archived("GW-1")
        self._check(e, GatewayEventType.GATEWAY_ARCHIVED, GatewayState.ARCHIVED)

    def test_to_dict_fields(self):
        e = make_gateway_completed("GW-1", portfolio_id="P-1", strategy_id="S-1")
        d = e.to_dict()
        assert "event_id"     in d
        assert "event_type"   in d
        assert "gateway_id"   in d
        assert "portfolio_id" in d
        assert "occurred_at"  in d
        assert "version"      in d

    def test_immutable(self):
        e = make_gateway_created("GW-1")
        with pytest.raises((TypeError, AttributeError)):
            e.gateway_id = "changed"  # type: ignore


# ═══════════════════════════════════════════════════════════════════════════════
# TestValidationResult
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidationResult:
    def test_valid_result(self):
        r = ValidationResult(True, (), ())
        assert r.is_valid       is True
        assert r.error_count    == 0
        assert r.warning_count  == 0
        assert bool(r)          is True

    def test_invalid_result(self):
        r = ValidationResult(False, ("err1", "err2"), ("warn1",))
        assert r.is_valid       is False
        assert r.error_count    == 2
        assert r.warning_count  == 1
        assert bool(r)          is False

    def test_to_dict(self):
        r = ValidationResult(True, (), ("minor warning",))
        d = r.to_dict()
        assert d["is_valid"]     is True
        assert d["warning_count"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayValidator
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayValidator:
    def test_valid_transition(self):
        req = _request()
        v   = GatewayValidator()
        r   = v.validate_transition(req, GatewayState.RECEIVED)
        assert r.is_valid is True

    def test_invalid_transition(self):
        req = _request()
        v   = GatewayValidator()
        r   = v.validate_transition(req, GatewayState.DISPATCHED)
        assert r.is_valid is False
        assert r.error_count >= 1

    def test_raise_if_invalid_raises(self):
        req = _request()
        v   = GatewayValidator()
        r   = v.validate_transition(req, GatewayState.DISPATCHED)
        with pytest.raises(GatewayValidationError):
            v.raise_if_invalid(r, gateway_id="GW-1")

    def test_raise_if_invalid_noop_for_valid(self):
        req = _request()
        v   = GatewayValidator()
        r   = v.validate_transition(req, GatewayState.RECEIVED)
        v.raise_if_invalid(r)  # no exception

    def test_validate_identifiers_all_present(self):
        v = GatewayValidator()
        r = v.validate_identifiers("GW-1", "EX-1", "ORD-1", "PORT-1")
        assert r.is_valid is True

    def test_validate_identifiers_missing_gateway_id(self):
        v = GatewayValidator()
        r = v.validate_identifiers("", "EX-1", "ORD-1", "PORT-1")
        assert r.is_valid is False

    def test_validate_request_valid(self):
        req = _request()
        v   = GatewayValidator()
        r   = v.validate_request(req)
        assert r.is_valid is True

    def test_validate_history_empty(self):
        req = _request()
        v   = GatewayValidator()
        r   = v.validate_history(req)
        assert r.is_valid is True


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayFactory
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayFactory:
    def test_create_generates_id(self):
        f = GatewayFactory()
        req = f.create(execution_id="EX-1")
        assert req.gateway_id
        assert req.state == GatewayState.CREATED

    def test_create_explicit_id(self):
        f = GatewayFactory()
        req = f.create(gateway_id="GW-EXPLICIT")
        assert req.gateway_id == "GW-EXPLICIT"

    def test_create_sets_identifiers(self):
        f = GatewayFactory()
        req = f.create(
            execution_id="EX-1", workflow_id="WF-1", order_id="ORD-1",
            portfolio_id="PORT-1", strategy_id="STRAT-1",
        )
        assert req.execution_id  == "EX-1"
        assert req.workflow_id   == "WF-1"
        assert req.portfolio_id  == "PORT-1"

    def test_create_from_context(self):
        ctx = make_gateway_context("EX-1","ORD-1","PORT-1","STRAT-1",
                                   symbol="RELIANCE", side="BUY")
        f   = GatewayFactory()
        req = f.create_from_context(ctx)
        assert req.execution_id == "EX-1"
        assert req.context      is ctx

    def test_create_with_event(self):
        f = GatewayFactory()
        req, event = f.create_with_event(execution_id="EX-1", portfolio_id="PORT-1")
        assert isinstance(req, GatewayRequest)
        assert isinstance(event, GatewayEvent)
        assert event.event_type   == GatewayEventType.GATEWAY_CREATED
        assert event.gateway_id   == req.gateway_id
        assert event.portfolio_id == "PORT-1"


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayRequest
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayRequest:
    def test_initial_state(self):
        req = _request()
        assert req.state     == GatewayState.CREATED
        assert req.is_active is True
        assert req.version   == VERSION

    def test_identity_fields(self):
        req = _request(
            gateway_id="GW-1",
            execution_id="EX-1",
            workflow_id="WF-1",
            order_id="ORD-1",
            portfolio_id="PORT-1",
            strategy_id="STRAT-1",
        )
        assert req.gateway_id   == "GW-1"
        assert req.execution_id == "EX-1"
        assert req.workflow_id  == "WF-1"

    def test_timestamps_set_on_creation(self):
        req = _request()
        assert req.created_at > 0
        assert req.updated_at >= req.created_at

    def test_completion_time_none_initially(self):
        req = _request()
        assert req.completion_time is None

    def test_transition_to_valid(self):
        req = _request()
        t   = req.transition_to(GatewayState.RECEIVED, actor="test")
        assert req.state    == GatewayState.RECEIVED
        assert t.from_state == GatewayState.CREATED
        assert t.to_state   == GatewayState.RECEIVED

    def test_transition_to_invalid_raises(self):
        req = _request()
        with pytest.raises(InvalidGatewayTransitionError):
            req.transition_to(GatewayState.DISPATCHED)

    def test_history_records_transition(self):
        req = _request()
        req.transition_to(GatewayState.RECEIVED)
        assert req.history.transition_count == 1

    def test_history_has_initial_state_record(self):
        req = _request()
        assert req.history.state_count >= 1
        assert req.history.states()[0].state == GatewayState.CREATED

    def test_completion_time_set_on_outcome(self):
        req = _request()
        req.transition_to(GatewayState.FAILED)
        assert req.completion_time is not None

    def test_lifecycle_elapsed_ms_positive(self):
        req = _request()
        time.sleep(0.01)
        assert req.lifecycle_elapsed_ms > 0

    def test_is_failed(self):
        req = _request()
        req.transition_to(GatewayState.FAILED)
        assert req.is_failed is True

    def test_is_cancelled(self):
        req = _request()
        req.transition_to(GatewayState.CANCELLED)
        assert req.is_cancelled is True

    def test_is_completed_after_complete(self):
        req = _request()
        for s in (GatewayState.RECEIVED, GatewayState.VALIDATING,
                  GatewayState.READY, GatewayState.QUEUED,
                  GatewayState.ROUTING, GatewayState.DISPATCHED,
                  GatewayState.COMPLETED):
            req.transition_to(s)
        assert req.is_completed is True

    def test_is_archived_after_archive(self):
        req = _request()
        req.transition_to(GatewayState.FAILED)
        req.transition_to(GatewayState.ARCHIVED)
        assert req.is_archived is True

    def test_event_listener_invoked(self):
        received: List[GatewayEvent] = []
        req = _request()
        req.add_event_listener(received.append)
        req.transition_to(GatewayState.RECEIVED)
        assert len(received) == 1
        assert received[0].event_type == GatewayEventType.GATEWAY_RECEIVED

    def test_listener_exception_does_not_propagate(self):
        def bad_listener(_): raise RuntimeError("boom")
        req = _request()
        req.add_event_listener(bad_listener)
        req.transition_to(GatewayState.RECEIVED)  # must not raise
        assert req.state == GatewayState.RECEIVED

    def test_remove_listener(self):
        calls: List[GatewayEvent] = []
        req = _request()
        req.add_event_listener(calls.append)
        req.remove_event_listener(calls.append)
        req.transition_to(GatewayState.RECEIVED)
        assert len(calls) == 0

    def test_to_dict(self):
        req = _request(gateway_id="GW-1")
        d = req.to_dict()
        assert d["gateway_id"]   == "GW-1"
        assert d["state"]        == "CREATED"
        assert "created_at"      in d
        assert "transition_count" in d

    def test_repr(self):
        req = _request(gateway_id="GW-1")
        r   = repr(req)
        assert "GW-1" in r
        assert "CREATED" in r


# ═══════════════════════════════════════════════════════════════════════════════
# TestStateMachine
# ═══════════════════════════════════════════════════════════════════════════════

class TestStateMachine:
    def test_happy_path_all_transitions(self):
        """Drive a request through the full happy-path state chain."""
        req = _request()
        chain = [
            GatewayState.RECEIVED,
            GatewayState.VALIDATING,
            GatewayState.READY,
            GatewayState.QUEUED,
            GatewayState.ROUTING,
            GatewayState.DISPATCHED,
            GatewayState.COMPLETED,
            GatewayState.ARCHIVED,
        ]
        for state in chain:
            req.transition_to(state)
        assert req.state == GatewayState.ARCHIVED
        assert req.history.transition_count == len(chain)

    def test_fail_from_created(self):
        req = _request()
        req.transition_to(GatewayState.FAILED)
        assert req.is_failed

    def test_fail_from_routing(self):
        req = _request()
        for s in (GatewayState.RECEIVED, GatewayState.VALIDATING,
                  GatewayState.READY, GatewayState.QUEUED, GatewayState.ROUTING):
            req.transition_to(s)
        req.transition_to(GatewayState.FAILED)
        assert req.is_failed

    def test_cancel_from_queued(self):
        req = _request()
        for s in (GatewayState.RECEIVED, GatewayState.VALIDATING,
                  GatewayState.READY, GatewayState.QUEUED):
            req.transition_to(s)
        req.transition_to(GatewayState.CANCELLED)
        assert req.is_cancelled

    def test_invalid_skip_transition(self):
        req = _request()
        with pytest.raises(InvalidGatewayTransitionError):
            req.transition_to(GatewayState.COMPLETED)

    def test_no_transition_from_archived(self):
        req = _request()
        req.transition_to(GatewayState.FAILED)
        req.transition_to(GatewayState.ARCHIVED)
        for s in GatewayState:
            if s != GatewayState.ARCHIVED:
                with pytest.raises(InvalidGatewayTransitionError):
                    req.transition_to(s)

    def test_all_valid_transitions_accepted(self):
        """Verify every edge in VALID_TRANSITIONS is accepted by transition_to()."""
        for from_state, targets in VALID_TRANSITIONS.items():
            for to_state in targets:
                req = GatewayRequest(
                    gateway_id=_gid(),
                    execution_id="EX", workflow_id="WF", order_id="ORD",
                    position_id="", portfolio_id="PORT", strategy_id="S",
                    decision_id="",
                )
                # Force the request into from_state without going through the machine
                # (we test the machine itself — patch the internal state for this edge test)
                req._state = from_state  # noqa: SLF001 — needed for state machine test
                req._history.update_last_state_exit(time.time())
                req.transition_to(to_state)  # should not raise


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayRegistry
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayRegistry:
    def _reg(self) -> GatewayRegistry:
        r = GatewayRegistry()
        r.start()
        return r

    def test_register_and_get(self):
        reg = self._reg()
        req = _request(gateway_id="GW-1")
        reg.register(req)
        assert reg.get("GW-1") is req
        reg.stop()

    def test_get_not_found(self):
        reg = self._reg()
        with pytest.raises(GatewayRequestNotFoundError):
            reg.get("nonexistent")
        reg.stop()

    def test_get_optional_returns_none(self):
        reg = self._reg()
        assert reg.get_optional("missing") is None
        reg.stop()

    def test_exists(self):
        reg = self._reg()
        req = _request()
        reg.register(req)
        assert reg.exists(req.gateway_id) is True
        assert reg.exists("missing")       is False
        reg.stop()

    def test_duplicate_raises(self):
        reg = self._reg()
        req = _request(gateway_id="GW-1")
        reg.register(req)
        with pytest.raises(DuplicateGatewayRequestError):
            reg.register(_request(gateway_id="GW-1"))
        reg.stop()

    def test_capacity_exceeded(self):
        reg = GatewayRegistry(max_requests=2)
        reg.start()
        reg.register(_request())
        reg.register(_request())
        with pytest.raises(GatewayRegistryCapacityError):
            reg.register(_request())
        reg.stop()

    def test_unregister(self):
        reg = self._reg()
        req = _request()
        reg.register(req)
        reg.unregister(req.gateway_id)
        assert reg.exists(req.gateway_id) is False
        reg.stop()

    def test_unregister_not_found(self):
        reg = self._reg()
        with pytest.raises(GatewayRequestNotFoundError):
            reg.unregister("missing")
        reg.stop()

    def test_count(self):
        reg = self._reg()
        assert reg.count == 0
        reg.register(_request())
        assert reg.count == 1
        reg.stop()

    def test_all(self):
        reg = self._reg()
        for _ in range(3):
            reg.register(_request())
        assert len(reg.all()) == 3
        reg.stop()

    def test_filter_active(self):
        reg = self._reg()
        req = _request()
        reg.register(req)
        assert len(reg.active()) == 1
        reg.stop()

    def test_filter_failed(self):
        reg = self._reg()
        req = _request()
        req.transition_to(GatewayState.FAILED)
        reg.register(req)
        assert len(reg.failed()) == 1
        assert len(reg.active()) == 0
        reg.stop()

    def test_filter_completed(self):
        reg = self._reg()
        req = _request()
        for s in (GatewayState.RECEIVED, GatewayState.VALIDATING,
                  GatewayState.READY, GatewayState.QUEUED,
                  GatewayState.ROUTING, GatewayState.DISPATCHED,
                  GatewayState.COMPLETED):
            req.transition_to(s)
        reg.register(req)
        assert len(reg.completed()) == 1
        reg.stop()

    def test_by_execution_id(self):
        reg = self._reg()
        r1 = _request(execution_id="EX-A")
        r2 = _request(execution_id="EX-B")
        reg.register(r1)
        reg.register(r2)
        assert len(reg.by_execution_id("EX-A")) == 1
        reg.stop()

    def test_write_requires_running(self):
        reg = GatewayRegistry()
        with pytest.raises(GatewayLifecycleNotRunningError):
            reg.register(_request())

    def test_read_allowed_after_stop(self):
        reg = self._reg()
        req = _request()
        reg.register(req)
        reg.stop()
        # get() is a read operation — permitted after stop
        assert reg.get_optional(req.gateway_id) is req


# ═══════════════════════════════════════════════════════════════════════════════
# TestGatewayLifecycle
# ═══════════════════════════════════════════════════════════════════════════════

class TestGatewayLifecycle:
    def test_start_stop(self):
        lc = GatewayLifecycle()
        lc.start()
        assert lc.is_running is True
        lc.stop()
        assert lc.is_running is False

    def test_not_running_raises(self):
        lc = GatewayLifecycle()
        with pytest.raises(GatewayLifecycleNotRunningError):
            lc.create(execution_id="EX-1")

    def test_create_returns_request(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1", order_id="ORD-1",
                        portfolio_id="PORT-1", strategy_id="STRAT-1")
        lc.stop()
        assert isinstance(req, GatewayRequest)
        assert req.state == GatewayState.CREATED

    def test_create_from_context(self):
        lc  = _lifecycle()
        ctx = make_gateway_context("EX-1","ORD-1","PORT-1","STRAT-1")
        req = lc.create_from_context(ctx)
        lc.stop()
        assert req.execution_id == "EX-1"
        assert req.context      is ctx

    def test_full_happy_path(self):
        lc = _lifecycle()
        req = _full_workflow(lc)
        lc.stop()
        assert req.state      == GatewayState.COMPLETED
        assert req.is_completed is True

    def test_receive_transitions(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        lc.receive(req.gateway_id)
        lc.stop()
        assert req.state == GatewayState.RECEIVED

    def test_start_validation_transitions(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        lc.receive(req.gateway_id)
        lc.start_validation(req.gateway_id)
        lc.stop()
        assert req.state == GatewayState.VALIDATING

    def test_mark_ready_transitions(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        lc.receive(req.gateway_id)
        lc.start_validation(req.gateway_id)
        lc.mark_ready(req.gateway_id)
        lc.stop()
        assert req.state == GatewayState.READY

    def test_queue_transitions(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        lc.receive(req.gateway_id)
        lc.start_validation(req.gateway_id)
        lc.mark_ready(req.gateway_id)
        lc.queue(req.gateway_id)
        lc.stop()
        assert req.state == GatewayState.QUEUED

    def test_start_routing_transitions(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        lc.receive(req.gateway_id)
        lc.start_validation(req.gateway_id)
        lc.mark_ready(req.gateway_id)
        lc.queue(req.gateway_id)
        lc.start_routing(req.gateway_id)
        lc.stop()
        assert req.state == GatewayState.ROUTING

    def test_dispatch_transitions(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        lc.receive(req.gateway_id)
        lc.start_validation(req.gateway_id)
        lc.mark_ready(req.gateway_id)
        lc.queue(req.gateway_id)
        lc.start_routing(req.gateway_id)
        lc.dispatch(req.gateway_id)
        lc.stop()
        assert req.state == GatewayState.DISPATCHED

    def test_fail_from_routing(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        lc.receive(req.gateway_id)
        lc.start_validation(req.gateway_id)
        lc.mark_ready(req.gateway_id)
        lc.queue(req.gateway_id)
        lc.start_routing(req.gateway_id)
        lc.fail(req.gateway_id, reason="broker timeout")
        lc.stop()
        assert req.is_failed is True

    def test_cancel_from_queued(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        lc.receive(req.gateway_id)
        lc.start_validation(req.gateway_id)
        lc.mark_ready(req.gateway_id)
        lc.queue(req.gateway_id)
        lc.cancel(req.gateway_id, reason="user cancelled")
        lc.stop()
        assert req.is_cancelled is True

    def test_archive_after_complete(self):
        lc = _lifecycle()
        req = _full_workflow(lc)
        lc.archive(req.gateway_id)
        lc.stop()
        assert req.is_archived is True

    def test_archive_after_fail(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        lc.fail(req.gateway_id)
        lc.archive(req.gateway_id)
        lc.stop()
        assert req.is_archived is True

    def test_get_returns_request(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        assert lc.get(req.gateway_id) is req
        lc.stop()

    def test_get_not_found(self):
        lc = _lifecycle()
        with pytest.raises(GatewayRequestNotFoundError):
            lc.get("nonexistent")
        lc.stop()

    def test_all_query(self):
        lc = _lifecycle()
        for _ in range(3):
            lc.create(execution_id="EX-1")
        assert len(lc.all()) == 3
        lc.stop()

    def test_active_query(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        assert len(lc.active()) == 1
        lc.stop()

    def test_completed_query(self):
        lc = _lifecycle()
        _full_workflow(lc)
        assert len(lc.completed()) == 1
        lc.stop()

    def test_failed_query(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        lc.fail(req.gateway_id)
        assert len(lc.failed()) == 1
        lc.stop()

    def test_cancelled_query(self):
        lc = _lifecycle()
        req = lc.create(execution_id="EX-1")
        lc.cancel(req.gateway_id)
        assert len(lc.cancelled()) == 1
        lc.stop()

    def test_by_execution_id(self):
        lc = _lifecycle()
        lc.create(execution_id="EX-A")
        lc.create(execution_id="EX-B")
        assert len(lc.by_execution_id("EX-A")) == 1
        lc.stop()

    def test_by_portfolio_id(self):
        lc = _lifecycle()
        lc.create(portfolio_id="PORT-X")
        lc.create(portfolio_id="PORT-Y")
        assert len(lc.by_portfolio_id("PORT-X")) == 1
        lc.stop()

    def test_by_strategy_id(self):
        lc = _lifecycle()
        lc.create(strategy_id="S-1")
        lc.create(strategy_id="S-2")
        assert len(lc.by_strategy_id("S-1")) == 1
        lc.stop()

    def test_by_state(self):
        lc = _lifecycle()
        req = lc.create()
        assert len(lc.by_state(GatewayState.CREATED)) == 1
        lc.stop()

    def test_request_count(self):
        lc = _lifecycle()
        lc.create()
        lc.create()
        assert lc.request_count() == 2
        lc.stop()

    def test_validate_request(self):
        lc  = _lifecycle()
        req = lc.create(execution_id="EX-1")
        r   = lc.validate_request(req.gateway_id)
        lc.stop()
        assert r.is_valid is True

    def test_validate_transition(self):
        lc  = _lifecycle()
        req = lc.create()
        r   = lc.validate_transition(req.gateway_id, GatewayState.RECEIVED)
        lc.stop()
        assert r.is_valid is True

    def test_validate_history(self):
        lc  = _lifecycle()
        req = lc.create()
        lc.receive(req.gateway_id)
        r = lc.validate_history(req.gateway_id)
        lc.stop()
        assert r.is_valid is True


# ═══════════════════════════════════════════════════════════════════════════════
# TestStatisticsIntegration
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatisticsIntegration:
    def test_received_incremented(self):
        lc = _lifecycle()
        req = lc.create()
        lc.receive(req.gateway_id)
        stats = lc.statistics()
        lc.stop()
        assert stats.requests_received == 1

    def test_completed_incremented(self):
        lc = _lifecycle()
        _full_workflow(lc)
        stats = lc.statistics()
        lc.stop()
        assert stats.requests_completed == 1

    def test_failed_incremented(self):
        lc = _lifecycle()
        req = lc.create()
        lc.fail(req.gateway_id)
        stats = lc.statistics()
        lc.stop()
        assert stats.requests_failed == 1

    def test_cancelled_incremented(self):
        lc = _lifecycle()
        req = lc.create()
        lc.cancel(req.gateway_id)
        stats = lc.statistics()
        lc.stop()
        assert stats.requests_cancelled == 1

    def test_transition_count_incremented(self):
        lc = _lifecycle()
        req = lc.create()
        lc.receive(req.gateway_id)
        lc.start_validation(req.gateway_id)
        stats = lc.statistics()
        lc.stop()
        assert stats.total_transitions >= 2

    def test_statistics_copy_independent(self):
        lc = _lifecycle()
        req = lc.create()
        lc.receive(req.gateway_id)
        s1 = lc.statistics()
        lc.start_validation(req.gateway_id)
        s2 = lc.statistics()
        lc.stop()
        assert s2.total_transitions > s1.total_transitions


# ═══════════════════════════════════════════════════════════════════════════════
# TestEventsIntegration
# ═══════════════════════════════════════════════════════════════════════════════

class TestEventsIntegration:
    def test_global_listener_receives_events(self):
        received: List[GatewayEvent] = []
        lc = _lifecycle()
        lc.add_event_listener(received.append)

        req = lc.create(execution_id="EX-1")
        lc.receive(req.gateway_id)
        lc.stop()

        event_types = [e.event_type for e in received]
        # GATEWAY_CREATED emitted on create(); GATEWAY_RECEIVED on receive()
        assert GatewayEventType.GATEWAY_CREATED  in event_types
        assert GatewayEventType.GATEWAY_RECEIVED in event_types

    def test_remove_global_listener(self):
        received: List[GatewayEvent] = []
        lc = _lifecycle()
        lc.add_event_listener(received.append)
        lc.remove_event_listener(received.append)

        req = lc.create()
        lc.receive(req.gateway_id)
        lc.stop()

        # GATEWAY_CREATED fires from _fire_global_event() BEFORE listener is removed
        # GATEWAY_RECEIVED fires from per-request listener (wired at create time)
        # Since listener was removed before wiring happened for this request, only
        # the global CREATED event may have been received
        # The key assertion: no GATEWAY_RECEIVED (per-request listener was never added)
        types = [e.event_type for e in received]
        assert GatewayEventType.GATEWAY_RECEIVED not in types

    def test_full_workflow_events(self):
        received: List[GatewayEvent] = []
        lc = _lifecycle()
        lc.add_event_listener(received.append)
        req = _full_workflow(lc)
        lc.stop()

        types = {e.event_type for e in received}
        assert GatewayEventType.GATEWAY_CREATED   in types
        assert GatewayEventType.GATEWAY_RECEIVED  in types
        assert GatewayEventType.GATEWAY_VALIDATED in types
        assert GatewayEventType.GATEWAY_QUEUED    in types
        assert GatewayEventType.GATEWAY_DISPATCHED in types
        assert GatewayEventType.GATEWAY_COMPLETED in types


# ═══════════════════════════════════════════════════════════════════════════════
# TestConcurrency
# ═══════════════════════════════════════════════════════════════════════════════

class TestConcurrency:
    def test_concurrent_creates(self):
        lc     = _lifecycle(max_requests=200)
        errors = []
        ids    = []
        lock   = threading.Lock()

        def _create():
            try:
                req = lc.create(execution_id="EX-1")
                with lock:
                    ids.append(req.gateway_id)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=_create) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lc.stop()
        assert len(errors) == 0
        assert len(ids)    == 50
        assert len(set(ids)) == 50  # all IDs unique

    def test_concurrent_transitions_same_request(self):
        """Multiple threads should not corrupt a single request's state."""
        lc  = _lifecycle()
        req = lc.create()
        lc.receive(req.gateway_id)

        # Attempt concurrent transitions from RECEIVED
        # Only one can succeed (VALIDATING); the rest must raise
        outcomes    = []
        exceptions  = []
        lock        = threading.Lock()

        def _try_validate():
            try:
                lc.start_validation(req.gateway_id)
                with lock:
                    outcomes.append("ok")
            except InvalidGatewayTransitionError:
                with lock:
                    exceptions.append("invalid")
            except Exception as e:
                with lock:
                    exceptions.append(str(e))

        threads = [threading.Thread(target=_try_validate) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lc.stop()
        assert len(outcomes) == 1           # exactly one succeeded
        assert req.state == GatewayState.VALIDATING

    def test_concurrent_statistics(self):
        lc     = _lifecycle(max_requests=100)
        errors = []
        lock   = threading.Lock()

        def _workflow():
            try:
                req = lc.create()
                lc.receive(req.gateway_id)
                lc.start_validation(req.gateway_id)
                lc.mark_ready(req.gateway_id)
                lc.queue(req.gateway_id)
                lc.start_routing(req.gateway_id)
                lc.dispatch(req.gateway_id)
                lc.complete(req.gateway_id)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=_workflow) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = lc.statistics()
        lc.stop()

        assert len(errors) == 0
        assert stats.requests_completed == 10


# ═══════════════════════════════════════════════════════════════════════════════
# TestRegression
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegression:
    def test_request_with_context_preserves_context(self):
        lc  = _lifecycle()
        ctx = make_gateway_context("EX-1","ORD-1","PORT-1","STRAT-1",
                                   symbol="RELIANCE", quantity=100.0)
        req = lc.create_from_context(ctx)
        lc.stop()
        assert req.context is ctx
        assert req.context.symbol   == "RELIANCE"
        assert req.context.quantity == 100.0

    def test_history_chain_consistent_after_full_workflow(self):
        """Transition chain: each to_state must equal the next from_state."""
        lc  = _lifecycle()
        req = _full_workflow(lc)
        lc.stop()

        transitions = req.history.transitions()
        for i in range(len(transitions) - 1):
            assert transitions[i].to_state == transitions[i + 1].from_state, (
                f"Gap at {i}: {transitions[i].to_state} != {transitions[i+1].from_state}"
            )

    def test_state_records_count_matches_transitions_plus_one(self):
        """State records = transitions + 1 (initial CREATED record)."""
        lc  = _lifecycle()
        req = lc.create()
        lc.receive(req.gateway_id)
        lc.start_validation(req.gateway_id)
        lc.stop()

        t_count = req.history.transition_count
        s_count = req.history.state_count
        assert s_count == t_count + 1

    def test_completion_time_only_set_on_outcome_states(self):
        lc  = _lifecycle()
        req = lc.create()
        lc.receive(req.gateway_id)
        assert req.completion_time is None
        lc.fail(req.gateway_id)
        assert req.completion_time is not None
        lc.stop()

    def test_no_event_fired_on_created_state_in_request(self):
        """CREATED state does NOT fire a per-request listener (factory sends it globally)."""
        calls: List[GatewayEvent] = []
        req = _request()
        req.add_event_listener(calls.append)
        # No transition yet — listener should have received 0 events
        assert len(calls) == 0

    def test_double_stop_raises_engine_not_running(self):
        """The IIOS framework raises EngineNotRunningError on double stop."""
        from iios.investment.workflow.engine_lifecycle import EngineNotRunningError
        lc = _lifecycle()
        lc.stop()
        with pytest.raises(EngineNotRunningError):
            lc.stop()

    def test_lifecycle_elapsed_ms_grows(self):
        lc  = _lifecycle()
        req = lc.create()
        t1  = req.lifecycle_elapsed_ms
        time.sleep(0.02)
        t2  = req.lifecycle_elapsed_ms
        lc.stop()
        assert t2 > t1

    def test_validate_request_detects_empty_gateway_id(self):
        req = GatewayRequest(
            gateway_id="",  # intentionally empty
            execution_id="EX-1", workflow_id="", order_id="",
            position_id="", portfolio_id="", strategy_id="", decision_id="",
        )
        v = GatewayValidator()
        r = v.validate_request(req)
        assert r.is_valid is False
        assert any("gateway_id" in e for e in r.errors)
