"""iios/execution/oms/order_queue/order_queue.py
==================================================
OrderQueue — IIOS v1.0 primary facade for queue management.

Manages WHEN queued orders become eligible for dispatch.
NEVER executes orders, communicates with brokers, or performs routing.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

from iios.common.logging.audit_logger import get_audit_logger
from iios.common.logging.logging_manager import get_logger
from iios.investment.workflow.engine_lifecycle import EngineState, LifecycleAwareMixin

from iios.execution.oms.order_queue.constants import (
    ACTIVE_ENTRY_STATES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_QUEUE_SIZE,
    QUEUE_SYSTEM_ID,
    VERSION,
    QueueEntryState,
    QueueEventType,
    QueuePolicyType,
)
from iios.execution.oms.order_queue.exceptions import (
    QueueEntryNotFoundError,
    QueueEntryStateError,
    QueueNotRunning,
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
from iios.execution.oms.order_queue.queue_policy import get_policy
from iios.execution.oms.order_queue.queue_registry import QueueRegistry
from iios.execution.oms.order_queue.queue_scheduler import QueueScheduler
from iios.execution.oms.order_queue.queue_snapshot import QueueSnapshot
from iios.execution.oms.order_queue.queue_statistics import QueueStatistics
from iios.execution.oms.order_queue.queue_validation import QueueValidator


class OrderQueue(LifecycleAwareMixin):
    """
    Institutional Order Queue.

    Responsibilities
    ----------------
    1. Accept routed orders via enqueue().
    2. Maintain priority and FIFO ordering.
    3. Advance WAITING/RETRY_PENDING entries on tick().
    4. Expire entries that have exceeded their TTL.
    5. Support suspend, resume, retry, and remove operations.
    6. Produce QueueDispatchPlan and QueueSnapshot on demand.
    7. Emit events and maintain statistics.

    No execution. No broker communication. No routing.
    """

    def __init__(
        self,
        registry:     Optional[QueueRegistry] = None,
        max_size:     int = DEFAULT_MAX_QUEUE_SIZE,
        max_history:  int = DEFAULT_MAX_HISTORY,
        policy:       QueuePolicyType = QueuePolicyType.FIFO,
        retry_delay:  float = 5.0,
    ) -> None:
        super().__init__()
        self._registry   = registry or QueueRegistry(max_size=max_size)
        self._factory    = QueueFactory()
        self._validator  = QueueValidator()
        self._scheduler  = QueueScheduler(base_retry_delay=retry_delay)
        self._history    = QueueHistory(max_size=max_history)
        self._stats      = QueueStatistics()
        self._policy     = policy
        self._events:    list[QueueEvent] = []
        self._event_lock = threading.Lock()
        self._log        = get_logger(__name__, engine_id=QUEUE_SYSTEM_ID)
        self._audit      = get_audit_logger(__name__, engine_id=QUEUE_SYSTEM_ID)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        if self._registry.lifecycle_state() != EngineState.RUNNING:
            self._registry.start()
        self._audit.log_lifecycle_event(
            QUEUE_SYSTEM_ID, EngineState.STOPPED, EngineState.RUNNING, VERSION
        )
        self._log.info("OrderQueue started.", policy=self._policy.value)

    def _on_stop(self) -> None:
        self._audit.log_lifecycle_event(
            QUEUE_SYSTEM_ID, EngineState.RUNNING, EngineState.STOPPED, VERSION
        )
        self._log.info("OrderQueue stopped.", size=self._registry.size)

    def _assert_running(self) -> None:
        if self.lifecycle_state() != EngineState.RUNNING:
            raise QueueNotRunning("OrderQueue is not running — call start() first")

    # ── Enqueue ───────────────────────────────────────────────────────────────

    def enqueue(self, context: QueueContext) -> QueueEntry:
        """
        Enqueue an order from a QueueContext.

        Returns the created QueueEntry (READY or WAITING).
        Raises QueueValidationError if the context is invalid.
        """
        self._assert_running()
        self._validator.validate_context(
            context,
            existing_order_ids = self._registry.active_order_ids(),
            current_size       = self._registry.size,
            max_size           = self._registry._max_size,
        )
        entry = self._factory.make_entry(context)
        self._registry.register(entry)
        self._stats.record_enqueue()
        self._emit(make_order_queued(
            entry.order_id, entry.entry_id,
            entry.priority.name, entry.policy_type.value,
        ))
        return entry

    def enqueue_entry(self, entry: QueueEntry) -> QueueEntry:
        """
        Directly enqueue a pre-built QueueEntry.
        Use when entry_id, metadata, or timestamps must be preserved.
        """
        self._assert_running()
        self._validator.validate_entry(
            entry,
            existing_order_ids = self._registry.active_order_ids(),
            current_size       = self._registry.size,
            max_size           = self._registry._max_size,
        )
        self._registry.register(entry)
        self._stats.record_enqueue()
        self._emit(make_order_queued(
            entry.order_id, entry.entry_id,
            entry.priority.name, entry.policy_type.value,
        ))
        return entry

    # ── State transitions ─────────────────────────────────────────────────────

    def _transition(self, entry_id: str, new_state: QueueEntryState) -> QueueEntry:
        """Atomically validate and apply a state transition."""
        entry = self._registry.get(entry_id)
        if entry is None:
            raise QueueEntryNotFoundError(entry_id)
        self._validator.validate_transition(entry, new_state)
        old_state    = entry.state
        entry.state  = new_state
        self._emit(make_queue_updated(
            entry.order_id, entry.entry_id,
            old_state.value, new_state.value,
        ))
        return entry

    def mark_ready(self, entry_id: str) -> QueueEntry:
        """Force-transition an entry to READY."""
        self._assert_running()
        return self._transition(entry_id, QueueEntryState.READY)

    def mark_waiting(self, entry_id: str) -> QueueEntry:
        """Transition a QUEUED entry to WAITING (scheduled)."""
        self._assert_running()
        return self._transition(entry_id, QueueEntryState.WAITING)

    def suspend(self, entry_id: str, reason: str = "") -> QueueEntry:
        """Suspend an active entry."""
        self._assert_running()
        entry = self._transition(entry_id, QueueEntryState.SUSPENDED)
        entry.suspend_reason = reason
        entry.suspended_at   = time.time()
        self._stats.record_suspend()
        self._emit(make_queue_suspended(entry.order_id, entry.entry_id, reason))
        return entry

    def resume(self, entry_id: str) -> QueueEntry:
        """Resume a SUSPENDED entry back to READY."""
        self._assert_running()
        entry = self._transition(entry_id, QueueEntryState.READY)
        entry.suspend_reason = ""
        self._emit(make_queue_resumed(entry.order_id, entry.entry_id))
        return entry

    def mark_dispatching(self, entry_id: str) -> QueueEntry:
        """Transition READY → DISPATCH_PENDING (dispatch in flight)."""
        self._assert_running()
        entry = self._registry.get(entry_id)
        if entry is None:
            raise QueueEntryNotFoundError(entry_id)
        self._validator.validate_dispatch_eligible(entry)
        return self._transition(entry_id, QueueEntryState.DISPATCH_PENDING)

    def mark_dispatched(self, entry_id: str) -> QueueEntry:
        """Transition DISPATCH_PENDING → DISPATCHED (terminal)."""
        self._assert_running()
        entry = self._transition(entry_id, QueueEntryState.DISPATCHED)
        entry.dispatched_at = time.time()
        wait_ms = (entry.dispatched_at - entry.queued_at) * 1_000
        self._stats.record_dispatch(wait_ms)
        self._history.append(entry)
        self._registry.remove(entry_id)
        self._emit(make_order_dispatched(
            entry.order_id, entry.entry_id, entry.broker_id, entry.exchange
        ))
        return entry

    def schedule_retry(self, entry_id: str) -> QueueEntry:
        """
        Transition DISPATCH_PENDING → RETRY_PENDING.
        Schedules the next retry using exponential back-off.
        Raises QueueValidationError if retry limit is exhausted.
        """
        self._assert_running()
        entry = self._registry.get(entry_id)
        if entry is None:
            raise QueueEntryNotFoundError(entry_id)
        self._validator.validate_retry_eligible(entry)
        entry.retry_count    += 1
        entry.next_retry_at   = self._scheduler.compute_retry_at(entry)
        self._transition(entry_id, QueueEntryState.RETRY_PENDING)
        self._stats.record_retry()
        self._emit(make_retry_scheduled(
            entry.order_id, entry.entry_id,
            entry.retry_count, entry.next_retry_at,
        ))
        return entry

    def mark_failed(self, entry_id: str, reason: str = "") -> QueueEntry:
        """Transition to FAILED (terminal)."""
        self._assert_running()
        entry = self._transition(entry_id, QueueEntryState.FAILED)
        entry.failure_reason = reason
        entry.failed_at      = time.time()
        self._stats.record_failure()
        self._history.append(entry)
        self._registry.remove(entry_id)
        return entry

    def expire(self, entry_id: str) -> QueueEntry:
        """Transition to EXPIRED (terminal)."""
        self._assert_running()
        entry = self._transition(entry_id, QueueEntryState.EXPIRED)
        entry.expired_at = time.time()
        self._stats.record_expiry()
        self._history.append(entry)
        self._registry.remove(entry_id)
        return entry

    def remove(self, entry_id: str) -> QueueEntry:
        """Remove a SUSPENDED entry (terminal REMOVED)."""
        self._assert_running()
        entry = self._transition(entry_id, QueueEntryState.REMOVED)
        self._stats.record_remove()
        self._history.append(entry)
        self._registry.remove(entry_id)
        return entry

    def change_priority(
        self,
        entry_id:     str,
        new_priority: "QueuePriorityLevel",
    ) -> QueueEntry:
        """Change the priority of an active entry."""
        from iios.execution.oms.order_queue.constants import QueuePriorityLevel
        self._assert_running()
        entry = self._registry.get(entry_id)
        if entry is None:
            raise QueueEntryNotFoundError(entry_id)
        old_priority   = entry.priority
        entry.priority = new_priority
        self._emit(make_priority_changed(
            entry.order_id, entry.entry_id,
            old_priority.name, new_priority.name,
        ))
        return entry

    # ── Tick — advance scheduler state ────────────────────────────────────────

    def tick(self) -> int:
        """
        Advance scheduler state:
          - WAITING/RETRY_PENDING entries whose time has come → READY
          - Active entries past TTL → EXPIRED

        Returns the count of transitions performed.
        """
        self._assert_running()
        now       = time.time()
        entries   = self._registry.all()
        promoted  = 0

        # Expire first
        for entry in self._scheduler.get_expired_entries(entries, now):
            try:
                self.expire(entry.entry_id)
                promoted += 1
            except (QueueEntryNotFoundError, QueueEntryStateError):
                pass

        # Promote WAITING/RETRY_PENDING → READY
        entries = self._registry.all()   # refresh after expiry
        for entry in self._scheduler.get_promotable_entries(entries, now):
            try:
                self._transition(entry.entry_id, QueueEntryState.READY)
                promoted += 1
            except (QueueEntryNotFoundError, QueueEntryStateError):
                pass

        return promoted

    # ── Dequeue ───────────────────────────────────────────────────────────────

    def dequeue(self, n: int = 1) -> list[QueueEntry]:
        """
        Return up to n READY entries atomically marked DISPATCH_PENDING.

        The policy applied is the queue's configured policy.
        """
        self._assert_running()
        policy  = get_policy(self._policy)
        entries = self._registry.all()
        ordered = policy.select(entries)

        result: list[QueueEntry] = []
        for entry in ordered[:n]:
            try:
                self.mark_dispatching(entry.entry_id)
                result.append(entry)
            except (QueueEntryNotFoundError, QueueValidationError, QueueEntryStateError):
                pass

        return result

    def peek(self) -> Optional[QueueEntry]:
        """Return the next READY entry without changing its state."""
        self._assert_running()
        policy  = get_policy(self._policy)
        entries = self._registry.all()
        ordered = policy.select(entries)
        return ordered[0] if ordered else None

    # ── Dispatch plan ─────────────────────────────────────────────────────────

    def dispatch_plan(self, max_entries: int = 100) -> QueueDispatchPlan:
        """
        Build an immutable ordered plan of entries ready for dispatch.
        Does NOT change any entry state.
        """
        self._assert_running()
        all_entries = self._registry.all()
        policy      = get_policy(self._policy)
        ordered     = policy.select(all_entries)[:max_entries]
        total_waiting = sum(
            1 for e in all_entries if e.state == QueueEntryState.WAITING
        )
        return self._factory.make_dispatch_plan(
            ordered_entries = ordered,
            policy_type     = self._policy,
            total_queued    = self._registry.size,
            total_waiting   = total_waiting,
        )

    # ── Query ─────────────────────────────────────────────────────────────────

    def get(self, entry_id: str) -> Optional[QueueEntry]:
        self._assert_running()
        return self._registry.get(entry_id)

    def get_by_order_id(self, order_id: str) -> Optional[QueueEntry]:
        self._assert_running()
        return self._registry.get_by_order_id(order_id)

    # ── Clear ─────────────────────────────────────────────────────────────────

    def clear(self) -> int:
        """Remove all active entries. Returns count cleared."""
        self._assert_running()
        count = self._registry.clear()
        self._stats.set_queue_size(0)
        self._emit(make_queue_cleared(count))
        return count

    # ── Snapshot / Stats / History / Events ──────────────────────────────────

    def snapshot(self) -> QueueSnapshot:
        self._assert_running()
        entries = self._registry.all()
        return self._factory.make_snapshot(
            entries          = entries,
            policy_type      = self._policy,
            peak_queue_size  = self._stats.peak_queue_size,
        )

    def statistics(self) -> QueueStatistics:
        return self._stats

    def history(self) -> QueueHistory:
        return self._history

    def events(self) -> list[QueueEvent]:
        with self._event_lock:
            return list(self._events)

    def clear_events(self) -> None:
        with self._event_lock:
            self._events.clear()

    def info(self) -> dict[str, Any]:
        return {
            "system_id":  QUEUE_SYSTEM_ID,
            "version":    VERSION,
            "state":      self.lifecycle_state().value,
            "policy":     self._policy.value,
            "statistics": self._stats.to_dict(),
            "history":    self._history.to_dict(),
            "registry":   self._registry.to_dict(),
        }

    # ── Internal ─────────────────────────────────────────────────────────────

    def _emit(self, event: QueueEvent) -> None:
        with self._event_lock:
            self._events.append(event)
