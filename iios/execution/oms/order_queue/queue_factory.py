"""iios/execution/oms/order_queue/queue_factory.py
==================================================
QueueFactory — creates QueueEntry, QueueSnapshot, and QueueDispatchPlan.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import time
from typing import Any

from iios.execution.oms.order_queue.constants import (
    FACTORY_SYSTEM_ID,
    QueueEntryState,
    QueuePolicyType,
)
from iios.execution.oms.order_queue.queue_context import QueueContext
from iios.execution.oms.order_queue.queue_dispatch_plan import QueueDispatchPlan
from iios.execution.oms.order_queue.queue_entry import QueueEntry
from iios.execution.oms.order_queue.queue_snapshot import QueueSnapshot


class QueueFactory:
    """Stateless factory for Order Queue domain objects."""

    __slots__ = ("_system_id",)

    def __init__(self) -> None:
        self._system_id = FACTORY_SYSTEM_ID

    def make_entry(self, context: QueueContext) -> QueueEntry:
        """
        Build a QueueEntry from an immutable QueueContext.

        The entry starts in READY (immediate) or WAITING (scheduled).
        """
        now = time.time()
        is_scheduled = context.ready_at > 0 and context.ready_at > now
        initial_state = QueueEntryState.WAITING if is_scheduled else QueueEntryState.READY

        return QueueEntry(
            order_id            = context.order_id,
            priority            = context.priority,
            state               = initial_state,
            policy_type         = context.policy_type,
            execution_mode      = context.execution_mode,
            queued_at           = now,
            ready_at            = context.ready_at,
            retry_count         = 0,
            max_retries         = context.max_retries,
            ttl_sec             = context.ttl_sec,
            broker_id           = context.broker_id,
            exchange            = context.exchange,
            routing_decision_id = context.routing_decision_id,
            workflow_id         = context.workflow_id,
            portfolio_id        = context.portfolio_id,
            strategy_id         = context.strategy_id,
            decision_id         = context.decision_id,
            correlation_id      = context.correlation_id,
            metadata            = dict(context.metadata),
        )

    def make_snapshot(
        self,
        entries:          list[QueueEntry],
        policy_type:      QueuePolicyType,
        peak_queue_size:  int = 0,
        metadata:         dict[str, Any] | None = None,
    ) -> QueueSnapshot:
        """Build an immutable snapshot from a list of QueueEntry objects."""
        counts: dict[QueueEntryState, int] = {}
        for e in entries:
            counts[e.state] = counts.get(e.state, 0) + 1

        return QueueSnapshot(
            policy_type           = policy_type,
            peak_queue_size       = peak_queue_size,
            total                 = len(entries),
            total_queued          = counts.get(QueueEntryState.QUEUED, 0),
            total_waiting         = counts.get(QueueEntryState.WAITING, 0),
            total_ready           = counts.get(QueueEntryState.READY, 0),
            total_dispatch_pending = counts.get(QueueEntryState.DISPATCH_PENDING, 0),
            total_dispatched      = counts.get(QueueEntryState.DISPATCHED, 0),
            total_suspended       = counts.get(QueueEntryState.SUSPENDED, 0),
            total_retry_pending   = counts.get(QueueEntryState.RETRY_PENDING, 0),
            total_failed          = counts.get(QueueEntryState.FAILED, 0),
            total_expired         = counts.get(QueueEntryState.EXPIRED, 0),
            total_removed         = counts.get(QueueEntryState.REMOVED, 0),
            entries               = tuple(entries),
            metadata              = metadata or {},
        )

    def make_dispatch_plan(
        self,
        ordered_entries: list[QueueEntry],
        policy_type:     QueuePolicyType,
        total_queued:    int,
        total_waiting:   int,
        metadata:        dict[str, Any] | None = None,
    ) -> QueueDispatchPlan:
        """Build an immutable dispatch plan from ordered, eligible entries."""
        return QueueDispatchPlan(
            entries       = tuple(ordered_entries),
            policy_type   = policy_type,
            total_ready   = len(ordered_entries),
            total_queued  = total_queued,
            total_waiting = total_waiting,
            metadata      = metadata or {},
        )
