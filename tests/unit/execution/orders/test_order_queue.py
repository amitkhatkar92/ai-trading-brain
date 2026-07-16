"""tests/unit/execution/orders/test_order_queue.py
==================================================
Comprehensive test suite for C6 Phase 2 M4 — Order Queue.

Coverage targets: 95%+

Test classes
------------
TestConstants             — enum completeness, state sets, transitions
TestExceptions            — hierarchy, fields, codes
TestQueueEntry            — properties, expiry, retry
TestQueuePriority         — sort keys, comparison, helpers
TestQueueContext          — frozen, scheduling helpers
TestQueuePolicy           — all 8 named policies
TestQueueScheduler        — is_ready, expiry, retry_at
TestQueueDispatchPlan     — frozen, count helpers
TestQueueSnapshot         — frozen, count helpers, filter methods
TestQueueEvents           — all 8 event factories
TestQueueStatistics       — thread-safe counters
TestQueueHistory          — bounded deque, filters
TestQueueValidator        — all validation paths
TestQueueRegistry         — lifecycle, operations
TestQueueFactory          — entry, snapshot, dispatch_plan
TestOrderQueue            — full pipeline
TestOrderQueueConcurrency — 100-thread stress
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any

import pytest

from iios.execution.oms.order_queue.constants import (
    ACTIVE_ENTRY_STATES,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TTL_SEC,
    DISPATCHABLE_STATES,
    TERMINAL_ENTRY_STATES,
    VALID_ENTRY_TRANSITIONS,
    ExecutionMode,
    QueueEntryState,
    QueueEventType,
    QueuePolicyType,
    QueuePriorityLevel,
    QueueValidationCode,
)
from iios.execution.oms.order_queue.exceptions import (
    DuplicateQueueEntryError,
    QueueCapacityError,
    QueueEntryExpiredError,
    QueueEntryNotFoundError,
    QueueEntryStateError,
    QueueError,
    QueueNotRunning,
    QueuePolicyError,
    QueueSchedulerError,
    QueueValidationError,
)
from iios.execution.oms.order_queue.queue_context import QueueContext
from iios.execution.oms.order_queue.queue_dispatch_plan import QueueDispatchPlan
from iios.execution.oms.order_queue.queue_entry import QueueEntry
from iios.execution.oms.order_queue.queue_events import (
    QueueEvent,
    make_order_dispatched,
    make_order_queued,
    make_priority_changed,
    make_queue_cleared,
    make_queue_resumed,
    make_queue_suspended,
    make_queue_updated,
    make_retry_scheduled,
)
from iios.execution.oms.order_queue.queue_factory import QueueFactory
from iios.execution.oms.order_queue.queue_history import QueueHistory
from iios.execution.oms.order_queue.queue_policy import (
    QueuePolicy,
    get_policy,
    make_backtest_policy,
    make_delayed_policy,
    make_fifo_policy,
    make_paper_trading_policy,
    make_priority_policy,
    make_recovery_policy,
    make_replay_policy,
    make_scheduled_policy,
)
from iios.execution.oms.order_queue.queue_priority import (
    compare_priority,
    highest_priority,
    lowest_priority,
    priority_sort_key,
)
from iios.execution.oms.order_queue.queue_registry import QueueRegistry
from iios.execution.oms.order_queue.queue_scheduler import QueueScheduler
from iios.execution.oms.order_queue.queue_snapshot import QueueSnapshot
from iios.execution.oms.order_queue.queue_statistics import QueueStatistics
from iios.execution.oms.order_queue.queue_validation import QueueValidator
from iios.execution.oms.order_queue.order_queue import OrderQueue


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures & helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ctx(
    order_id:   str = "",
    priority:   QueuePriorityLevel = QueuePriorityLevel.NORMAL,
    policy:     QueuePolicyType    = QueuePolicyType.FIFO,
    mode:       ExecutionMode      = ExecutionMode.LIVE,
    ready_at:   float = 0.0,
    ttl:        float = 60.0,
    max_retries: int  = 3,
) -> QueueContext:
    return QueueContext(
        order_id    = order_id or str(uuid.uuid4()),
        priority    = priority,
        policy_type = policy,
        execution_mode = mode,
        ready_at    = ready_at,
        ttl_sec     = ttl,
        max_retries = max_retries,
    )


def _entry(
    order_id:  str = "",
    priority:  QueuePriorityLevel = QueuePriorityLevel.NORMAL,
    state:     QueueEntryState    = QueueEntryState.READY,
    mode:      ExecutionMode      = ExecutionMode.LIVE,
    policy:    QueuePolicyType    = QueuePolicyType.FIFO,
    ttl:       float = 60.0,
    queued_at: float | None = None,
    ready_at:  float = 0.0,
) -> QueueEntry:
    e = QueueEntry(
        order_id       = order_id or str(uuid.uuid4()),
        priority       = priority,
        state          = state,
        policy_type    = policy,
        execution_mode = mode,
        ttl_sec        = ttl,
        ready_at       = ready_at,
    )
    if queued_at is not None:
        e.queued_at = queued_at
    return e


@pytest.fixture()
def registry():
    r = QueueRegistry()
    r.start()
    yield r
    if r.lifecycle_state().value == "running":
        r.stop()


@pytest.fixture()
def queue():
    q = OrderQueue(policy=QueuePolicyType.FIFO)
    q.start()
    yield q
    if q.lifecycle_state().value == "running":
        q.stop()


@pytest.fixture()
def priority_queue():
    q = OrderQueue(policy=QueuePolicyType.PRIORITY)
    q.start()
    yield q
    if q.lifecycle_state().value == "running":
        q.stop()


# ─────────────────────────────────────────────────────────────────────────────
# TestConstants
# ─────────────────────────────────────────────────────────────────────────────

class TestConstants:
    def test_all_queue_states_defined(self):
        states = {s.value for s in QueueEntryState}
        for name in ("QUEUED", "WAITING", "READY", "DISPATCH_PENDING",
                     "DISPATCHED", "SUSPENDED", "RETRY_PENDING",
                     "FAILED", "EXPIRED", "REMOVED"):
            assert name in states

    def test_terminal_states(self):
        for s in (QueueEntryState.DISPATCHED, QueueEntryState.FAILED,
                  QueueEntryState.EXPIRED, QueueEntryState.REMOVED):
            assert s in TERMINAL_ENTRY_STATES

    def test_active_states(self):
        for s in (QueueEntryState.QUEUED, QueueEntryState.WAITING,
                  QueueEntryState.READY, QueueEntryState.SUSPENDED,
                  QueueEntryState.RETRY_PENDING):
            assert s in ACTIVE_ENTRY_STATES

    def test_dispatchable_states_is_ready_only(self):
        assert QueueEntryState.READY in DISPATCHABLE_STATES
        assert QueueEntryState.WAITING not in DISPATCHABLE_STATES

    def test_all_priority_levels(self):
        levels = {p.name for p in QueuePriorityLevel}
        for name in ("CRITICAL", "HIGH", "NORMAL", "LOW", "BACKGROUND"):
            assert name in levels

    def test_priority_ordering(self):
        assert QueuePriorityLevel.CRITICAL.value < QueuePriorityLevel.HIGH.value
        assert QueuePriorityLevel.HIGH.value < QueuePriorityLevel.NORMAL.value
        assert QueuePriorityLevel.NORMAL.value < QueuePriorityLevel.LOW.value
        assert QueuePriorityLevel.LOW.value < QueuePriorityLevel.BACKGROUND.value

    def test_all_policy_types(self):
        types = {p.value for p in QueuePolicyType}
        for name in ("FIFO", "PRIORITY", "SCHEDULED", "DELAYED",
                     "RECOVERY", "REPLAY", "PAPER_TRADING", "BACKTEST"):
            assert name in types

    def test_valid_transitions_cover_all_states(self):
        for state in QueueEntryState:
            assert state in VALID_ENTRY_TRANSITIONS

    def test_terminal_states_have_no_transitions(self):
        for s in TERMINAL_ENTRY_STATES:
            assert VALID_ENTRY_TRANSITIONS[s] == frozenset()

    def test_event_types(self):
        types = {e.value for e in QueueEventType}
        for name in ("ORDER_QUEUED", "QUEUE_UPDATED", "PRIORITY_CHANGED",
                     "ORDER_DISPATCHED", "RETRY_SCHEDULED",
                     "QUEUE_SUSPENDED", "QUEUE_RESUMED", "QUEUE_CLEARED"):
            assert name in types

    def test_validation_codes(self):
        codes = {c.value for c in QueueValidationCode}
        for name in ("MISSING_ORDER_ID", "DUPLICATE_ENTRY", "QUEUE_FULL",
                     "RETRY_LIMIT_EXCEEDED", "ENTRY_EXPIRED",
                     "INVALID_STATE_TRANSITION"):
            assert name in codes


# ─────────────────────────────────────────────────────────────────────────────
# TestExceptions
# ─────────────────────────────────────────────────────────────────────────────

class TestExceptions:
    def test_base_inherits_iios_error(self):
        from iios.common.errors.exceptions import IIOSError
        assert issubclass(QueueError, IIOSError)

    def test_all_subclass_base(self):
        for cls in (DuplicateQueueEntryError, QueueEntryNotFoundError,
                    QueueCapacityError, QueueNotRunning, QueueValidationError,
                    QueuePolicyError, QueueSchedulerError,
                    QueueEntryExpiredError, QueueEntryStateError):
            assert issubclass(cls, QueueError)

    def test_duplicate_entry_fields(self):
        e = DuplicateQueueEntryError("ORD-1")
        assert e.order_id == "ORD-1"
        assert "QE-002" in e.code

    def test_entry_not_found_fields(self):
        e = QueueEntryNotFoundError("ENTRY-1")
        assert e.entry_id == "ENTRY-1"
        assert "QE-003" in e.code

    def test_entry_expired_fields(self):
        e = QueueEntryExpiredError("E1", "ORD-1")
        assert e.entry_id == "E1"
        assert e.order_id == "ORD-1"
        assert "QE-009" in e.code

    def test_entry_state_error_fields(self):
        e = QueueEntryStateError("E1", "READY", "DISPATCHED")
        assert e.entry_id   == "E1"
        assert e.from_state == "READY"
        assert e.to_state   == "DISPATCHED"
        assert "QE-010" in e.code

    def test_validation_error_stores_errors_tuple(self):
        e = QueueValidationError("bad", errors=("E1", "E2"))
        assert e.errors == ("E1", "E2")

    def test_default_codes(self):
        assert QueueError.DEFAULT_CODE              == "QE-000"
        assert DuplicateQueueEntryError.DEFAULT_CODE == "QE-002"
        assert QueueEntryNotFoundError.DEFAULT_CODE  == "QE-003"
        assert QueueCapacityError.DEFAULT_CODE       == "QE-004"
        assert QueueNotRunning.DEFAULT_CODE          == "QE-005"
        assert QueueValidationError.DEFAULT_CODE     == "QE-006"
        assert QueuePolicyError.DEFAULT_CODE         == "QE-007"
        assert QueueSchedulerError.DEFAULT_CODE      == "QE-008"
        assert QueueEntryExpiredError.DEFAULT_CODE   == "QE-009"
        assert QueueEntryStateError.DEFAULT_CODE     == "QE-010"


# ─────────────────────────────────────────────────────────────────────────────
# TestQueueEntry
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueEntry:
    def test_default_state_is_queued(self):
        e = QueueEntry(order_id="ORD-1")
        assert e.state == QueueEntryState.QUEUED

    def test_entry_id_is_uuid(self):
        e = QueueEntry(order_id="ORD-1")
        uuid.UUID(e.entry_id)  # must not raise

    def test_not_expired_when_fresh(self):
        e = _entry(ttl=60.0)
        assert not e.is_expired

    def test_expired_when_past_ttl(self):
        e = _entry(ttl=0.001, queued_at=time.time() - 1)
        assert e.is_expired

    def test_terminal_entry_never_expires(self):
        e = _entry(state=QueueEntryState.DISPATCHED, ttl=0.001)
        e.queued_at = time.time() - 100
        assert not e.is_expired

    def test_can_retry_within_limit(self):
        e = QueueEntry(order_id="ORD-1", retry_count=1, max_retries=3)
        assert e.can_retry

    def test_cannot_retry_at_limit(self):
        e = QueueEntry(order_id="ORD-1", retry_count=3, max_retries=3)
        assert not e.can_retry

    def test_is_dispatchable_when_ready(self):
        e = _entry(state=QueueEntryState.READY, ttl=60.0)
        assert e.is_dispatchable

    def test_not_dispatchable_when_waiting(self):
        e = _entry(state=QueueEntryState.WAITING)
        assert not e.is_dispatchable

    def test_not_dispatchable_when_expired(self):
        e = _entry(state=QueueEntryState.READY, ttl=0.001, queued_at=time.time() - 1)
        assert not e.is_dispatchable

    def test_is_terminal_dispatched(self):
        e = _entry(state=QueueEntryState.DISPATCHED)
        assert e.is_terminal

    def test_is_active(self):
        e = _entry(state=QueueEntryState.READY)
        assert e.is_active

    def test_wait_time_ms_positive(self):
        e = _entry(queued_at=time.time() - 0.01)
        assert e.wait_time_ms >= 0

    def test_to_dict_keys(self):
        d = _entry().to_dict()
        for k in ("entry_id", "order_id", "priority", "state",
                  "retry_count", "is_expired", "can_retry"):
            assert k in d


# ─────────────────────────────────────────────────────────────────────────────
# TestQueuePriority
# ─────────────────────────────────────────────────────────────────────────────

class TestQueuePriority:
    def test_fifo_key_is_queued_at(self):
        e = _entry(queued_at=1000.0)
        k = priority_sort_key(e, QueuePolicyType.FIFO)
        assert k == (1000.0,)

    def test_priority_key_includes_level_and_time(self):
        e = _entry(priority=QueuePriorityLevel.HIGH, queued_at=1000.0)
        k = priority_sort_key(e, QueuePolicyType.PRIORITY)
        assert k[0] == QueuePriorityLevel.HIGH.value
        assert k[1] == 1000.0

    def test_scheduled_key_uses_ready_at(self):
        e = _entry(ready_at=2000.0, queued_at=1000.0)
        k = priority_sort_key(e, QueuePolicyType.SCHEDULED)
        assert k == (2000.0,)

    def test_recovery_key_includes_retry_count(self):
        e = QueueEntry(order_id="O", retry_count=2, next_retry_at=3000.0)
        e.queued_at = 1000.0
        k = priority_sort_key(e, QueuePolicyType.RECOVERY)
        assert k[0] == 2

    def test_compare_priority_lower_value_wins(self):
        a = _entry(priority=QueuePriorityLevel.HIGH, queued_at=1.0)
        b = _entry(priority=QueuePriorityLevel.NORMAL, queued_at=2.0)
        assert compare_priority(a, b) == -1
        assert compare_priority(b, a) == 1

    def test_compare_priority_equal_level_tiebreak_time(self):
        a = _entry(priority=QueuePriorityLevel.NORMAL, queued_at=1.0)
        b = _entry(priority=QueuePriorityLevel.NORMAL, queued_at=2.0)
        assert compare_priority(a, b) == -1

    def test_compare_priority_equal(self):
        a = _entry(priority=QueuePriorityLevel.NORMAL, queued_at=1.0)
        b = _entry(priority=QueuePriorityLevel.NORMAL, queued_at=1.0)
        assert compare_priority(a, b) == 0

    def test_highest_priority(self):
        entries = [
            _entry(priority=QueuePriorityLevel.NORMAL),
            _entry(priority=QueuePriorityLevel.CRITICAL),
            _entry(priority=QueuePriorityLevel.LOW),
        ]
        assert highest_priority(entries) == QueuePriorityLevel.CRITICAL

    def test_lowest_priority(self):
        entries = [
            _entry(priority=QueuePriorityLevel.HIGH),
            _entry(priority=QueuePriorityLevel.BACKGROUND),
        ]
        assert lowest_priority(entries) == QueuePriorityLevel.BACKGROUND

    def test_highest_priority_empty(self):
        assert highest_priority([]) == QueuePriorityLevel.BACKGROUND

    def test_lowest_priority_empty(self):
        assert lowest_priority([]) == QueuePriorityLevel.CRITICAL


# ─────────────────────────────────────────────────────────────────────────────
# TestQueueContext
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueContext:
    def test_is_frozen(self):
        ctx = _ctx()
        with pytest.raises((AttributeError, TypeError)):
            ctx.order_id = "NEW"  # type: ignore[misc]

    def test_is_immediate_when_no_ready_at(self):
        ctx = _ctx(ready_at=0.0)
        assert ctx.is_immediate

    def test_is_scheduled_when_future_ready_at(self):
        ctx = _ctx(ready_at=time.time() + 60.0)
        assert ctx.is_scheduled
        assert not ctx.is_immediate

    def test_context_id_is_uuid(self):
        ctx = _ctx()
        uuid.UUID(ctx.context_id)

    def test_to_dict_keys(self):
        d = _ctx().to_dict()
        for k in ("context_id", "order_id", "priority", "policy_type",
                  "is_immediate", "is_scheduled"):
            assert k in d


# ─────────────────────────────────────────────────────────────────────────────
# TestQueuePolicy
# ─────────────────────────────────────────────────────────────────────────────

class TestQueuePolicy:
    def test_all_policies_have_correct_type(self):
        for ptype in QueuePolicyType:
            p = get_policy(ptype)
            assert p.policy_type == ptype

    def test_fifo_orders_by_arrival(self):
        p   = make_fifo_policy()
        now = time.time()
        e1  = _entry(state=QueueEntryState.READY, queued_at=now - 1.0)
        e2  = _entry(state=QueueEntryState.READY, queued_at=now)
        ordered = p.select([e2, e1])
        assert ordered[0].queued_at < ordered[1].queued_at

    def test_priority_orders_by_level(self):
        p = make_priority_policy()
        e_low  = _entry(state=QueueEntryState.READY, priority=QueuePriorityLevel.LOW)
        e_high = _entry(state=QueueEntryState.READY, priority=QueuePriorityLevel.HIGH)
        ordered = p.select([e_low, e_high])
        assert ordered[0].priority == QueuePriorityLevel.HIGH

    def test_priority_tiebreak_by_arrival(self):
        p   = make_priority_policy()
        now = time.time()
        e1  = _entry(state=QueueEntryState.READY, priority=QueuePriorityLevel.NORMAL,
                     queued_at=now - 1.0)
        e2  = _entry(state=QueueEntryState.READY, priority=QueuePriorityLevel.NORMAL,
                     queued_at=now)
        ordered = p.select([e2, e1])
        assert ordered[0].queued_at < ordered[1].queued_at

    def test_scheduled_excludes_waiting_entries(self):
        p = make_scheduled_policy()
        e_ready   = _entry(state=QueueEntryState.READY)
        e_waiting = _entry(state=QueueEntryState.WAITING)
        result = p.select([e_ready, e_waiting])
        assert all(e.state == QueueEntryState.READY for e in result)

    def test_recovery_includes_retry_pending(self):
        p = make_recovery_policy()
        e_retry = _entry(state=QueueEntryState.RETRY_PENDING)
        e_retry.next_retry_at = time.time() - 1  # already due
        e_ready = _entry(state=QueueEntryState.READY)
        result = p.select([e_retry, e_ready])
        assert len(result) == 2

    def test_recovery_excludes_future_retry(self):
        p = make_recovery_policy()
        e = _entry(state=QueueEntryState.RETRY_PENDING)
        e.next_retry_at = time.time() + 3600  # far future
        result = p.select([e])
        assert len(result) == 0

    def test_paper_trading_filters_to_paper_mode(self):
        p = make_paper_trading_policy()
        e_paper = _entry(state=QueueEntryState.READY, mode=ExecutionMode.PAPER)
        e_live  = _entry(state=QueueEntryState.READY, mode=ExecutionMode.LIVE)
        result = p.select([e_paper, e_live])
        assert len(result) == 1
        assert result[0].execution_mode == ExecutionMode.PAPER

    def test_backtest_filters_to_backtest_mode(self):
        p = make_backtest_policy()
        e_bt   = _entry(state=QueueEntryState.READY, mode=ExecutionMode.BACKTEST)
        e_live = _entry(state=QueueEntryState.READY, mode=ExecutionMode.LIVE)
        result = p.select([e_bt, e_live])
        assert len(result) == 1

    def test_replay_filters_to_backtest_mode(self):
        p = make_replay_policy()
        e_bt = _entry(state=QueueEntryState.READY, mode=ExecutionMode.BACKTEST)
        result = p.select([e_bt])
        assert len(result) == 1

    def test_inactive_policy_returns_empty(self):
        p = make_fifo_policy()
        p.is_active = False
        e = _entry(state=QueueEntryState.READY)
        assert p.select([e]) == []

    def test_policy_excludes_expired_entries(self):
        p = make_fifo_policy()
        e = _entry(state=QueueEntryState.READY, ttl=0.001,
                   queued_at=time.time() - 1)
        result = p.select([e])
        assert len(result) == 0

    def test_policy_to_dict(self):
        d = make_fifo_policy().to_dict()
        assert "policy_type" in d
        assert "is_active" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestQueueScheduler
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueScheduler:
    def test_ready_entry_is_ready(self):
        s = QueueScheduler()
        e = _entry(state=QueueEntryState.READY)
        assert s.is_ready(e)

    def test_waiting_entry_becomes_ready_when_time_passes(self):
        s = QueueScheduler()
        e = _entry(state=QueueEntryState.WAITING, ready_at=time.time() - 1)
        assert s.is_ready(e)

    def test_waiting_entry_not_ready_when_future(self):
        s = QueueScheduler()
        e = _entry(state=QueueEntryState.WAITING, ready_at=time.time() + 3600)
        assert not s.is_ready(e)

    def test_queued_with_zero_ready_at_is_ready(self):
        s = QueueScheduler()
        e = _entry(state=QueueEntryState.QUEUED, ready_at=0.0)
        assert s.is_ready(e)

    def test_retry_pending_ready_when_due(self):
        s = QueueScheduler()
        e = _entry(state=QueueEntryState.RETRY_PENDING)
        e.next_retry_at = time.time() - 1
        assert s.is_ready(e)

    def test_retry_pending_not_ready_when_future(self):
        s = QueueScheduler()
        e = _entry(state=QueueEntryState.RETRY_PENDING)
        e.next_retry_at = time.time() + 3600
        assert not s.is_ready(e)

    def test_suspended_not_ready(self):
        s = QueueScheduler()
        e = _entry(state=QueueEntryState.SUSPENDED)
        assert not s.is_ready(e)

    def test_should_expire(self):
        s = QueueScheduler()
        e = _entry(ttl=0.001, queued_at=time.time() - 1)
        assert s.should_expire(e)

    def test_should_not_expire_fresh(self):
        s = QueueScheduler()
        e = _entry(ttl=60.0)
        assert not s.should_expire(e)

    def test_compute_retry_at_exponential(self):
        s = QueueScheduler(base_retry_delay=2.0)
        e = QueueEntry(order_id="O", retry_count=0)
        t1 = s.compute_retry_at(e)
        e.retry_count = 1
        t2 = s.compute_retry_at(e)
        assert t2 > t1

    def test_compute_retry_at_capped_at_32(self):
        s = QueueScheduler(base_retry_delay=1.0)
        e = QueueEntry(order_id="O", retry_count=100)
        now = time.time()
        at  = s.compute_retry_at(e, now=now)
        assert at == pytest.approx(now + 1.0 * 32, abs=0.01)

    def test_remaining_ttl_positive(self):
        s = QueueScheduler()
        e = _entry(ttl=60.0)
        assert s.remaining_ttl(e) > 0

    def test_remaining_ttl_negative_when_expired(self):
        s = QueueScheduler()
        e = _entry(ttl=0.001, queued_at=time.time() - 1)
        assert s.remaining_ttl(e) < 0

    def test_get_ready_entries(self):
        s = QueueScheduler()
        e1 = _entry(state=QueueEntryState.READY)
        e2 = _entry(state=QueueEntryState.WAITING, ready_at=time.time() + 60)
        result = s.get_ready_entries([e1, e2])
        assert e1 in result
        assert e2 not in result

    def test_get_promotable_entries(self):
        s = QueueScheduler()
        e_due     = _entry(state=QueueEntryState.WAITING, ready_at=time.time() - 1)
        e_future  = _entry(state=QueueEntryState.WAITING, ready_at=time.time() + 60)
        promoted  = s.get_promotable_entries([e_due, e_future])
        assert e_due in promoted
        assert e_future not in promoted

    def test_get_expired_entries(self):
        s = QueueScheduler()
        e_exp = _entry(state=QueueEntryState.READY, ttl=0.001,
                       queued_at=time.time() - 1)
        e_ok  = _entry(state=QueueEntryState.READY, ttl=60.0)
        result = s.get_expired_entries([e_exp, e_ok])
        assert e_exp in result
        assert e_ok not in result


# ─────────────────────────────────────────────────────────────────────────────
# TestQueueDispatchPlan
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueDispatchPlan:
    def test_is_frozen(self):
        plan = QueueDispatchPlan()
        with pytest.raises((AttributeError, TypeError)):
            plan.count = 1  # type: ignore[misc]

    def test_empty_plan(self):
        plan = QueueDispatchPlan()
        assert plan.is_empty
        assert plan.count == 0
        assert plan.top() is None

    def test_non_empty_plan(self):
        e    = _entry()
        plan = QueueDispatchPlan(entries=(e,), total_ready=1)
        assert not plan.is_empty
        assert plan.count == 1
        assert plan.top() is e

    def test_to_dict_keys(self):
        d = QueueDispatchPlan().to_dict()
        for k in ("plan_id", "count", "policy_type", "total_ready", "is_empty"):
            assert k in d


# ─────────────────────────────────────────────────────────────────────────────
# TestQueueSnapshot
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueSnapshot:
    def _snap_with(self, *states: QueueEntryState) -> QueueSnapshot:
        entries = [_entry(state=s) for s in states]
        return QueueSnapshot(
            entries              = tuple(entries),
            total                = len(entries),
            total_ready          = sum(1 for s in states if s == QueueEntryState.READY),
            total_waiting        = sum(1 for s in states if s == QueueEntryState.WAITING),
            total_suspended      = sum(1 for s in states if s == QueueEntryState.SUSPENDED),
            total_retry_pending  = sum(1 for s in states if s == QueueEntryState.RETRY_PENDING),
        )

    def test_is_frozen(self):
        snap = QueueSnapshot()
        with pytest.raises((AttributeError, TypeError)):
            snap.total = 5  # type: ignore[misc]

    def test_ready_entries_filter(self):
        snap = self._snap_with(QueueEntryState.READY, QueueEntryState.WAITING)
        assert len(snap.ready_entries()) == 1

    def test_waiting_entries_filter(self):
        snap = self._snap_with(QueueEntryState.WAITING, QueueEntryState.READY)
        assert len(snap.waiting_entries()) == 1

    def test_suspended_entries_filter(self):
        snap = self._snap_with(QueueEntryState.SUSPENDED, QueueEntryState.READY)
        assert len(snap.suspended_entries()) == 1

    def test_retry_pending_filter(self):
        snap = self._snap_with(QueueEntryState.RETRY_PENDING)
        assert len(snap.retry_pending_entries()) == 1

    def test_active_entries_excludes_terminal(self):
        snap = self._snap_with(
            QueueEntryState.READY,
            QueueEntryState.DISPATCHED,
            QueueEntryState.FAILED,
        )
        active = snap.active_entries()
        assert all(e.state in ACTIVE_ENTRY_STATES for e in active)

    def test_to_dict_keys(self):
        d = QueueSnapshot().to_dict()
        for k in ("snapshot_id", "total", "total_ready", "policy_type"):
            assert k in d


# ─────────────────────────────────────────────────────────────────────────────
# TestQueueEvents
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueEvents:
    def test_order_queued_event(self):
        e = make_order_queued("ORD-1", "EID-1", "NORMAL", "FIFO")
        assert e.event_type == QueueEventType.ORDER_QUEUED
        assert e.order_id   == "ORD-1"
        assert e.metadata["priority"] == "NORMAL"

    def test_queue_updated_event(self):
        e = make_queue_updated("ORD-1", "EID-1", "QUEUED", "READY")
        assert e.event_type == QueueEventType.QUEUE_UPDATED
        assert e.metadata["old_state"] == "QUEUED"
        assert e.metadata["new_state"] == "READY"

    def test_priority_changed_event(self):
        e = make_priority_changed("ORD-1", "EID-1", "NORMAL", "HIGH")
        assert e.event_type == QueueEventType.PRIORITY_CHANGED
        assert e.metadata["old_priority"] == "NORMAL"

    def test_order_dispatched_event(self):
        e = make_order_dispatched("ORD-1", "EID-1", "BRK", "NSE")
        assert e.event_type == QueueEventType.ORDER_DISPATCHED
        assert e.metadata["broker_id"] == "BRK"

    def test_retry_scheduled_event(self):
        t = time.time() + 5
        e = make_retry_scheduled("ORD-1", "EID-1", 2, t)
        assert e.event_type == QueueEventType.RETRY_SCHEDULED
        assert e.metadata["retry_count"] == 2

    def test_queue_suspended_event(self):
        e = make_queue_suspended("ORD-1", "EID-1", "manual_pause")
        assert e.event_type == QueueEventType.QUEUE_SUSPENDED
        assert e.metadata["reason"] == "manual_pause"

    def test_queue_resumed_event(self):
        e = make_queue_resumed("ORD-1", "EID-1")
        assert e.event_type == QueueEventType.QUEUE_RESUMED

    def test_queue_cleared_event(self):
        e = make_queue_cleared(42)
        assert e.event_type == QueueEventType.QUEUE_CLEARED
        assert e.metadata["cleared_count"] == 42

    def test_events_are_frozen(self):
        e = make_order_queued("ORD-1", "EID-1", "NORMAL")
        with pytest.raises((AttributeError, TypeError)):
            e.order_id = "CHANGED"  # type: ignore[misc]

    def test_each_event_has_unique_id(self):
        ids = {make_order_queued("ORD-1", "EID-1", "NORMAL").event_id for _ in range(5)}
        assert len(ids) == 5

    def test_event_to_dict_keys(self):
        d = make_order_queued("ORD-1", "EID-1", "NORMAL").to_dict()
        for k in ("event_id", "event_type", "order_id", "entry_id"):
            assert k in d


# ─────────────────────────────────────────────────────────────────────────────
# TestQueueStatistics
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueStatistics:
    def test_initial_zeros(self):
        s = QueueStatistics()
        assert s.queue_size == 0
        assert s.total_enqueued == 0
        assert s.avg_wait_time_ms == 0.0

    def test_record_enqueue(self):
        s = QueueStatistics()
        s.record_enqueue()
        s.record_enqueue()
        assert s.total_enqueued == 2
        assert s.queue_size == 2

    def test_peak_queue_size(self):
        s = QueueStatistics()
        s.record_enqueue()
        s.record_enqueue()
        assert s.peak_queue_size == 2
        s.record_dispatch()
        assert s.peak_queue_size == 2  # peak preserved

    def test_record_dispatch(self):
        s = QueueStatistics()
        s.record_enqueue()
        s.record_dispatch(wait_ms=10.0)
        assert s.total_dispatched == 1
        assert s.queue_size == 0
        assert s.avg_wait_time_ms == pytest.approx(10.0)

    def test_record_failure(self):
        s = QueueStatistics()
        s.record_enqueue()
        s.record_failure()
        assert s.total_failed == 1
        assert s.queue_size == 0

    def test_record_expiry(self):
        s = QueueStatistics()
        s.record_enqueue()
        s.record_expiry()
        assert s.total_expired == 1

    def test_record_retry(self):
        s = QueueStatistics()
        s.record_retry()
        assert s.total_retried == 1

    def test_record_suspend(self):
        s = QueueStatistics()
        s.record_suspend()
        assert s.total_suspended == 1

    def test_record_remove(self):
        s = QueueStatistics()
        s.record_enqueue()
        s.record_remove()
        assert s.total_removed == 1
        assert s.queue_size == 0

    def test_set_queue_size(self):
        s = QueueStatistics()
        s.set_queue_size(50)
        assert s.queue_size == 50
        assert s.peak_queue_size == 50

    def test_set_queue_size_negative_becomes_zero(self):
        s = QueueStatistics()
        s.set_queue_size(-5)
        assert s.queue_size == 0

    def test_reset_clears_all(self):
        s = QueueStatistics()
        s.record_enqueue()
        s.record_dispatch()
        s.record_retry()
        s.reset()
        assert s.total_enqueued == 0
        assert s.total_dispatched == 0
        assert s.total_retried == 0

    def test_to_dict_keys(self):
        d = QueueStatistics().to_dict()
        for k in ("queue_size", "peak_queue_size", "total_enqueued",
                  "total_dispatched", "avg_wait_time_ms"):
            assert k in d

    def test_thread_safe_concurrent_enqueue(self):
        s = QueueStatistics()
        threads = [threading.Thread(target=s.record_enqueue) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert s.total_enqueued == 100


# ─────────────────────────────────────────────────────────────────────────────
# TestQueueHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueHistory:
    def test_empty_initially(self):
        h = QueueHistory(max_size=10)
        assert h.size == 0
        assert h.total == 0

    def test_append_increments(self):
        h = QueueHistory(max_size=10)
        h.append(_entry())
        assert h.size == 1
        assert h.total == 1

    def test_bounded_eviction(self):
        h = QueueHistory(max_size=3)
        for i in range(5):
            h.append(_entry(order_id=f"ORD-{i}"))
        assert h.size == 3
        assert h.total == 5
        assert h.evicted == 2

    def test_latest(self):
        h = QueueHistory(max_size=10)
        for i in range(5):
            h.append(_entry(order_id=f"ORD-{i}"))
        last = h.latest(3)
        assert len(last) == 3

    def test_for_order(self):
        h = QueueHistory(max_size=10)
        h.append(_entry(order_id="A"))
        h.append(_entry(order_id="B"))
        h.append(_entry(order_id="A"))
        assert len(h.for_order("A")) == 2
        assert len(h.for_order("B")) == 1

    def test_dispatched_filter(self):
        h = QueueHistory(max_size=10)
        h.append(_entry(state=QueueEntryState.DISPATCHED))
        h.append(_entry(state=QueueEntryState.FAILED))
        assert len(h.dispatched()) == 1

    def test_failed_filter(self):
        h = QueueHistory(max_size=10)
        h.append(_entry(state=QueueEntryState.FAILED))
        assert len(h.failed()) == 1

    def test_expired_filter(self):
        h = QueueHistory(max_size=10)
        h.append(_entry(state=QueueEntryState.EXPIRED))
        assert len(h.expired()) == 1

    def test_len_dunder(self):
        h = QueueHistory(max_size=10)
        h.append(_entry())
        assert len(h) == 1

    def test_iter(self):
        h = QueueHistory(max_size=10)
        h.append(_entry(order_id="A"))
        h.append(_entry(order_id="B"))
        ids = [e.order_id for e in h]
        assert "A" in ids

    def test_clear(self):
        h = QueueHistory(max_size=10)
        h.append(_entry())
        h.clear()
        assert h.size == 0

    def test_invalid_max_size_raises(self):
        with pytest.raises(ValueError):
            QueueHistory(max_size=0)

    def test_to_dict(self):
        d = QueueHistory().to_dict()
        assert "max_size" in d
        assert "total" in d

    def test_concurrent_appends(self):
        h = QueueHistory(max_size=200)
        def _append(i):
            h.append(_entry(order_id=f"ORD-{i}"))
        threads = [threading.Thread(target=_append, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert h.total == 100


# ─────────────────────────────────────────────────────────────────────────────
# TestQueueValidator
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueValidator:
    def test_valid_context_passes(self):
        v = QueueValidator()
        v.validate_context(_ctx(), set(), 0, 100)  # must not raise

    def test_missing_order_id_raises(self):
        v = QueueValidator()
        ctx = _ctx()
        ctx_bad = QueueContext(order_id="", ttl_sec=60.0)
        with pytest.raises(QueueValidationError) as exc:
            v.validate_context(ctx_bad, set(), 0, 100)
        assert QueueValidationCode.MISSING_ORDER_ID.value in str(exc.value.errors)

    def test_duplicate_order_id_raises(self):
        v = QueueValidator()
        ctx = _ctx(order_id="ORD-DUP")
        with pytest.raises(QueueValidationError) as exc:
            v.validate_context(ctx, {"ORD-DUP"}, 0, 100)
        assert QueueValidationCode.DUPLICATE_ENTRY.value in str(exc.value.errors)

    def test_queue_full_raises(self):
        v = QueueValidator()
        ctx = _ctx()
        with pytest.raises(QueueValidationError) as exc:
            v.validate_context(ctx, set(), 10, 10)  # size == max
        assert QueueValidationCode.QUEUE_FULL.value in str(exc.value.errors)

    def test_invalid_ttl_raises(self):
        v = QueueValidator()
        ctx = QueueContext(order_id="ORD-1", ttl_sec=-1.0)
        with pytest.raises(QueueValidationError) as exc:
            v.validate_context(ctx, set(), 0, 100)
        assert QueueValidationCode.INVALID_SCHEDULE.value in str(exc.value.errors)

    def test_valid_transition_passes(self):
        v = QueueValidator()
        e = _entry(state=QueueEntryState.READY)
        v.validate_transition(e, QueueEntryState.DISPATCH_PENDING)  # must not raise

    def test_invalid_transition_raises(self):
        v = QueueValidator()
        e = _entry(state=QueueEntryState.READY)
        with pytest.raises(QueueEntryStateError):
            v.validate_transition(e, QueueEntryState.DISPATCHED)

    def test_terminal_state_no_transitions(self):
        v = QueueValidator()
        e = _entry(state=QueueEntryState.DISPATCHED)
        with pytest.raises(QueueEntryStateError):
            v.validate_transition(e, QueueEntryState.READY)

    def test_retry_eligible_passes(self):
        v = QueueValidator()
        e = QueueEntry(order_id="O", retry_count=1, max_retries=3)
        v.validate_retry_eligible(e)  # must not raise

    def test_retry_exhausted_raises(self):
        v = QueueValidator()
        e = QueueEntry(order_id="O", retry_count=3, max_retries=3)
        with pytest.raises(QueueValidationError) as exc:
            v.validate_retry_eligible(e)
        assert QueueValidationCode.RETRY_LIMIT_EXCEEDED.value in str(exc.value.errors)

    def test_dispatch_eligible_passes(self):
        v = QueueValidator()
        e = _entry(state=QueueEntryState.READY, ttl=60.0)
        v.validate_dispatch_eligible(e)

    def test_dispatch_ineligible_wrong_state_raises(self):
        v = QueueValidator()
        e = _entry(state=QueueEntryState.WAITING)
        with pytest.raises(QueueValidationError):
            v.validate_dispatch_eligible(e)

    def test_dispatch_ineligible_expired_raises(self):
        v = QueueValidator()
        e = _entry(state=QueueEntryState.READY, ttl=0.001, queued_at=time.time() - 1)
        with pytest.raises(QueueValidationError):
            v.validate_dispatch_eligible(e)

    def test_validate_entry_missing_order_id(self):
        v = QueueValidator()
        e = QueueEntry(order_id="")
        with pytest.raises(QueueValidationError):
            v.validate_entry(e, set(), 0, 100)

    def test_validate_entry_duplicate(self):
        v = QueueValidator()
        e = QueueEntry(order_id="ORD-1")
        with pytest.raises(QueueValidationError):
            v.validate_entry(e, {"ORD-1"}, 0, 100)


# ─────────────────────────────────────────────────────────────────────────────
# TestQueueRegistry
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueRegistry:
    def test_start_stop_lifecycle(self):
        from iios.investment.workflow.engine_lifecycle import EngineState
        r = QueueRegistry()
        r.start()
        assert r.lifecycle_state() == EngineState.RUNNING
        r.stop()
        assert r.lifecycle_state() != EngineState.RUNNING

    def test_register_and_get(self, registry):
        e = _entry(order_id="ORD-R")
        registry.register(e)
        result = registry.get(e.entry_id)
        assert result is e

    def test_get_by_order_id(self, registry):
        e = _entry(order_id="ORD-Q")
        registry.register(e)
        assert registry.get_by_order_id("ORD-Q") is e

    def test_get_missing_returns_none(self, registry):
        assert registry.get("GHOST") is None
        assert registry.get_by_order_id("GHOST") is None

    def test_remove(self, registry):
        e = _entry(order_id="ORD-DEL")
        registry.register(e)
        removed = registry.remove(e.entry_id)
        assert removed
        assert registry.get(e.entry_id) is None

    def test_remove_missing_returns_false(self, registry):
        assert not registry.remove("GHOST")

    def test_all_returns_all(self, registry):
        e1, e2 = _entry(), _entry()
        registry.register(e1)
        registry.register(e2)
        ids = {e.entry_id for e in registry.all()}
        assert e1.entry_id in ids
        assert e2.entry_id in ids

    def test_by_state(self, registry):
        e_ready   = _entry(state=QueueEntryState.READY)
        e_waiting = _entry(state=QueueEntryState.WAITING)
        registry.register(e_ready)
        registry.register(e_waiting)
        ready_list = registry.by_state(QueueEntryState.READY)
        assert all(e.state == QueueEntryState.READY for e in ready_list)

    def test_contains(self, registry):
        e = _entry()
        registry.register(e)
        assert registry.contains(e.entry_id)
        assert not registry.contains("GHOST")

    def test_contains_order(self, registry):
        e = _entry(order_id="ORD-CO")
        registry.register(e)
        assert registry.contains_order("ORD-CO")

    def test_capacity_raises(self):
        r = QueueRegistry(max_size=2)
        r.start()
        r.register(_entry())
        r.register(_entry())
        with pytest.raises(QueueCapacityError):
            r.register(_entry())
        r.stop()

    def test_empty_entry_id_raises(self, registry):
        e = QueueEntry(order_id="ORD-1")
        e.entry_id = ""
        with pytest.raises(ValueError):
            registry.register(e)

    def test_operations_require_running(self):
        r = QueueRegistry()
        with pytest.raises(QueueNotRunning):
            r.get("any")

    def test_active_order_ids(self, registry):
        e = _entry(order_id="ORD-AID")
        registry.register(e)
        assert "ORD-AID" in registry.active_order_ids()

    def test_clear_removes_all(self, registry):
        for _ in range(3):
            registry.register(_entry())
        count = registry.clear()
        assert count == 3
        assert registry.size == 0

    def test_to_dict(self, registry):
        d = registry.to_dict()
        assert "size" in d
        assert "max_size" in d


# ─────────────────────────────────────────────────────────────────────────────
# TestQueueFactory
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueFactory:
    def test_make_entry_immediate(self):
        f   = QueueFactory()
        ctx = _ctx(ready_at=0.0)
        e   = f.make_entry(ctx)
        assert e.state    == QueueEntryState.READY
        assert e.order_id == ctx.order_id

    def test_make_entry_scheduled(self):
        f   = QueueFactory()
        ctx = _ctx(ready_at=time.time() + 3600)
        e   = f.make_entry(ctx)
        assert e.state == QueueEntryState.WAITING

    def test_make_entry_copies_metadata(self):
        f   = QueueFactory()
        ctx = QueueContext(order_id="ORD-1", ttl_sec=60.0,
                           metadata={"k": "v"})
        e   = f.make_entry(ctx)
        assert e.metadata == {"k": "v"}

    def test_make_snapshot_counts(self):
        f       = QueueFactory()
        entries = [
            _entry(state=QueueEntryState.READY),
            _entry(state=QueueEntryState.WAITING),
            _entry(state=QueueEntryState.DISPATCHED),
        ]
        snap = f.make_snapshot(entries, QueuePolicyType.FIFO)
        assert snap.total         == 3
        assert snap.total_ready   == 1
        assert snap.total_waiting == 1

    def test_make_dispatch_plan(self):
        f       = QueueFactory()
        entries = [_entry(state=QueueEntryState.READY) for _ in range(3)]
        plan    = f.make_dispatch_plan(entries, QueuePolicyType.FIFO, 5, 2)
        assert plan.count        == 3
        assert plan.total_queued == 5
        assert plan.total_waiting == 2
        assert not plan.is_empty


# ─────────────────────────────────────────────────────────────────────────────
# TestOrderQueue
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderQueue:
    def test_requires_start(self):
        q = OrderQueue()
        with pytest.raises(QueueNotRunning):
            q.enqueue(_ctx())

    def test_enqueue_returns_ready_entry(self, queue):
        e = queue.enqueue(_ctx())
        assert e.state == QueueEntryState.READY

    def test_enqueue_scheduled_returns_waiting(self, queue):
        ctx = _ctx(ready_at=time.time() + 3600)
        e   = queue.enqueue(ctx)
        assert e.state == QueueEntryState.WAITING

    def test_enqueue_invalid_raises(self, queue):
        ctx = QueueContext(order_id="", ttl_sec=60.0)
        with pytest.raises(QueueValidationError):
            queue.enqueue(ctx)

    def test_enqueue_duplicate_raises(self, queue):
        oid = str(uuid.uuid4())
        queue.enqueue(_ctx(order_id=oid))
        with pytest.raises(QueueValidationError):
            queue.enqueue(_ctx(order_id=oid))

    def test_dequeue_returns_dispatch_pending(self, queue):
        queue.enqueue(_ctx())
        result = queue.dequeue(1)
        assert len(result) == 1
        assert result[0].state == QueueEntryState.DISPATCH_PENDING

    def test_dequeue_empty_returns_empty_list(self, queue):
        assert queue.dequeue(1) == []

    def test_dequeue_fifo_order(self, queue):
        q = OrderQueue(policy=QueuePolicyType.FIFO)
        q.start()
        oid_a, oid_b = str(uuid.uuid4()), str(uuid.uuid4())
        e_a = queue.enqueue(_ctx(order_id=oid_a))
        time.sleep(0.001)
        e_b = queue.enqueue(_ctx(order_id=oid_b))
        result = queue.dequeue(2)
        assert result[0].order_id == oid_a
        q.stop()

    def test_peek_does_not_change_state(self, queue):
        queue.enqueue(_ctx())
        entry = queue.peek()
        assert entry is not None
        assert entry.state == QueueEntryState.READY  # unchanged

    def test_peek_empty_returns_none(self, queue):
        assert queue.peek() is None

    def test_suspend_and_resume(self, queue):
        e = queue.enqueue(_ctx())
        queue.suspend(e.entry_id, reason="test_pause")
        assert e.state == QueueEntryState.SUSPENDED
        assert e.suspend_reason == "test_pause"
        queue.resume(e.entry_id)
        assert e.state == QueueEntryState.READY

    def test_mark_dispatched_moves_to_history(self, queue):
        e = queue.enqueue(_ctx())
        queue.mark_dispatching(e.entry_id)
        queue.mark_dispatched(e.entry_id)
        assert e.state == QueueEntryState.DISPATCHED
        assert queue.history().total == 1
        assert queue.get(e.entry_id) is None  # removed from registry

    def test_schedule_retry(self, queue):
        ctx = _ctx(max_retries=3)
        e   = queue.enqueue(ctx)
        queue.mark_dispatching(e.entry_id)
        queue.schedule_retry(e.entry_id)
        assert e.state == QueueEntryState.RETRY_PENDING
        assert e.retry_count == 1
        assert e.next_retry_at > time.time()

    def test_retry_exhausted_raises(self, queue):
        ctx = _ctx(max_retries=1)
        e   = queue.enqueue(ctx)
        queue.mark_dispatching(e.entry_id)
        queue.schedule_retry(e.entry_id)   # retry_count → 1 (== max_retries)
        # Now mark dispatching again (need to transition back to DISPATCH_PENDING)
        # Manually set to DISPATCH_PENDING for this test
        e.state = QueueEntryState.DISPATCH_PENDING
        with pytest.raises(QueueValidationError):
            queue.schedule_retry(e.entry_id)

    def test_mark_failed_moves_to_history(self, queue):
        e = queue.enqueue(_ctx())
        queue.mark_dispatching(e.entry_id)
        queue.mark_failed(e.entry_id, reason="test_fail")
        assert e.state == QueueEntryState.FAILED
        assert e.failure_reason == "test_fail"
        assert queue.history().total == 1

    def test_expire_moves_to_history(self, queue):
        e = queue.enqueue(_ctx())
        queue.expire(e.entry_id)
        assert e.state == QueueEntryState.EXPIRED
        assert queue.history().total == 1

    def test_remove_suspended_entry(self, queue):
        e = queue.enqueue(_ctx())
        queue.suspend(e.entry_id)
        queue.remove(e.entry_id)
        assert e.state == QueueEntryState.REMOVED
        assert queue.history().total == 1

    def test_change_priority(self, queue):
        e = queue.enqueue(_ctx(priority=QueuePriorityLevel.LOW))
        queue.change_priority(e.entry_id, QueuePriorityLevel.CRITICAL)
        assert e.priority == QueuePriorityLevel.CRITICAL

    def test_tick_promotes_waiting_to_ready(self, queue):
        ctx = _ctx(ready_at=time.time() - 1)   # past-due
        e   = queue.enqueue(ctx)
        # Force WAITING state for this test
        e.state = QueueEntryState.WAITING
        count = queue.tick()
        assert count >= 1
        assert e.state == QueueEntryState.READY

    def test_tick_expires_stale_entries(self, queue):
        e = queue.enqueue(_ctx(ttl=0.001))
        time.sleep(0.01)
        queue.tick()
        # Entry should have been expired and removed from registry
        assert queue.get(e.entry_id) is None

    def test_tick_promotes_retry_pending(self, queue):
        ctx = _ctx(max_retries=3)
        e   = queue.enqueue(ctx)
        queue.mark_dispatching(e.entry_id)
        queue.schedule_retry(e.entry_id)
        # Back-date next_retry_at
        e.next_retry_at = time.time() - 1
        count = queue.tick()
        assert count >= 1
        assert e.state == QueueEntryState.READY

    def test_dispatch_plan_is_ordered(self, queue):
        for _ in range(3):
            queue.enqueue(_ctx())
        plan = queue.dispatch_plan(max_entries=10)
        assert isinstance(plan, QueueDispatchPlan)
        assert plan.count == 3

    def test_dispatch_plan_empty(self, queue):
        plan = queue.dispatch_plan()
        assert plan.is_empty

    def test_snapshot_counts(self, queue):
        queue.enqueue(_ctx())
        queue.enqueue(_ctx(ready_at=time.time() + 3600))
        snap = queue.snapshot()
        assert snap.total_ready   == 1
        assert snap.total_waiting == 1

    def test_get_and_get_by_order_id(self, queue):
        oid = str(uuid.uuid4())
        e   = queue.enqueue(_ctx(order_id=oid))
        assert queue.get(e.entry_id) is e
        assert queue.get_by_order_id(oid) is e

    def test_get_missing_returns_none(self, queue):
        assert queue.get("GHOST") is None
        assert queue.get_by_order_id("GHOST") is None

    def test_clear_removes_all_entries(self, queue):
        for _ in range(5):
            queue.enqueue(_ctx())
        count = queue.clear()
        assert count == 5
        assert queue.snapshot().total == 0

    def test_events_emitted_on_enqueue(self, queue):
        queue.clear_events()
        queue.enqueue(_ctx())
        ev_types = [e.event_type for e in queue.events()]
        assert QueueEventType.ORDER_QUEUED in ev_types

    def test_events_emitted_on_dispatched(self, queue):
        queue.clear_events()
        e = queue.enqueue(_ctx())
        queue.mark_dispatching(e.entry_id)
        queue.mark_dispatched(e.entry_id)
        ev_types = [ev.event_type for ev in queue.events()]
        assert QueueEventType.ORDER_DISPATCHED in ev_types

    def test_events_emitted_on_suspend_resume(self, queue):
        queue.clear_events()
        e = queue.enqueue(_ctx())
        queue.suspend(e.entry_id, "paused")
        queue.resume(e.entry_id)
        ev_types = [ev.event_type for ev in queue.events()]
        assert QueueEventType.QUEUE_SUSPENDED in ev_types
        assert QueueEventType.QUEUE_RESUMED   in ev_types

    def test_events_emitted_on_retry(self, queue):
        queue.clear_events()
        ctx = _ctx(max_retries=3)
        e   = queue.enqueue(ctx)
        queue.mark_dispatching(e.entry_id)
        queue.schedule_retry(e.entry_id)
        ev_types = [ev.event_type for ev in queue.events()]
        assert QueueEventType.RETRY_SCHEDULED in ev_types

    def test_statistics_updated(self, queue):
        queue.enqueue(_ctx())
        s = queue.statistics()
        assert s.total_enqueued >= 1

    def test_priority_ordering_through_queue(self):
        q = OrderQueue(policy=QueuePolicyType.PRIORITY)
        q.start()
        e_low  = q.enqueue(_ctx(priority=QueuePriorityLevel.LOW))
        e_crit = q.enqueue(_ctx(priority=QueuePriorityLevel.CRITICAL))
        e_norm = q.enqueue(_ctx(priority=QueuePriorityLevel.NORMAL))
        result = q.dequeue(3)
        assert result[0].priority == QueuePriorityLevel.CRITICAL
        assert result[1].priority == QueuePriorityLevel.NORMAL
        assert result[2].priority == QueuePriorityLevel.LOW
        q.stop()

    def test_enqueue_entry_directly(self, queue):
        e = _entry()
        queue.enqueue_entry(e)
        assert queue.get(e.entry_id) is e

    def test_mark_ready(self, queue):
        ctx = _ctx(ready_at=time.time() + 3600)
        e   = queue.enqueue(ctx)
        assert e.state == QueueEntryState.WAITING
        queue.mark_ready(e.entry_id)
        assert e.state == QueueEntryState.READY

    def test_mark_waiting(self, queue):
        e = queue.enqueue(_ctx())  # READY
        queue.mark_waiting(e.entry_id)
        assert e.state == QueueEntryState.WAITING
        # Can return to READY
        queue.mark_ready(e.entry_id)
        assert e.state == QueueEntryState.READY

    def test_not_found_operations_raise(self, queue):
        with pytest.raises(QueueEntryNotFoundError):
            queue.suspend("GHOST")
        with pytest.raises(QueueEntryNotFoundError):
            queue.mark_dispatched("GHOST")
        with pytest.raises(QueueEntryNotFoundError):
            queue.change_priority("GHOST", QueuePriorityLevel.HIGH)

    def test_clear_events(self, queue):
        queue.enqueue(_ctx())
        queue.clear_events()
        assert queue.events() == []

    def test_info_snapshot(self, queue):
        d = queue.info()
        for k in ("system_id", "version", "state", "policy",
                  "statistics", "history", "registry"):
            assert k in d


# ─────────────────────────────────────────────────────────────────────────────
# TestOrderQueueConcurrency
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderQueueConcurrency:
    def test_concurrent_enqueue_100_threads(self, queue):
        errors:  list[Exception] = []
        entries: list[QueueEntry] = []
        lock = threading.Lock()

        def _enqueue():
            try:
                e = queue.enqueue(_ctx())
                with lock:
                    entries.append(e)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_enqueue) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Unexpected errors: {errors}"
        assert len(entries) == 100

    def test_concurrent_enqueue_dequeue(self, queue):
        """50 threads enqueue, 50 threads dequeue simultaneously."""
        errors: list[Exception] = []
        lock = threading.Lock()

        def _enqueue():
            try:
                queue.enqueue(_ctx())
            except Exception as exc:
                with lock:
                    errors.append(exc)

        def _dequeue():
            try:
                queue.dequeue(1)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        # Pre-fill queue
        for _ in range(50):
            queue.enqueue(_ctx())

        producers = [threading.Thread(target=_enqueue) for _ in range(50)]
        consumers = [threading.Thread(target=_dequeue) for _ in range(50)]

        for t in producers + consumers:
            t.start()
        for t in producers + consumers:
            t.join()

        assert errors == [], f"Unexpected errors: {errors}"

    def test_statistics_accurate_under_concurrency(self, queue):
        n = 50

        def _cycle():
            e = queue.enqueue(_ctx())
            queue.mark_dispatching(e.entry_id)
            queue.mark_dispatched(e.entry_id)

        threads = [threading.Thread(target=_cycle) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert queue.statistics().total_dispatched == n
        assert queue.history().total == n

    def test_history_bounded_under_concurrency(self):
        q = OrderQueue(max_history=20)
        q.start()

        def _cycle():
            e = q.enqueue(_ctx())
            q.mark_dispatching(e.entry_id)
            q.mark_dispatched(e.entry_id)

        threads = [threading.Thread(target=_cycle) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert q.history().size <= 20
        q.stop()

    def test_concurrent_tick_and_enqueue(self, queue):
        """Tick and enqueue simultaneously — no deadlock, no exceptions."""
        errors: list[Exception] = []
        lock = threading.Lock()

        def _enqueue():
            try:
                for _ in range(5):
                    queue.enqueue(_ctx(ttl=60.0))
            except Exception as exc:
                with lock:
                    errors.append(exc)

        def _tick():
            try:
                for _ in range(10):
                    queue.tick()
            except Exception as exc:
                with lock:
                    errors.append(exc)

        t1 = threading.Thread(target=_enqueue)
        t2 = threading.Thread(target=_tick)
        t1.start(); t2.start()
        t1.join();  t2.join()

        assert errors == [], f"Errors: {errors}"
