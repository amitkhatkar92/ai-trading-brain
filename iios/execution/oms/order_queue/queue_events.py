"""iios/execution/oms/order_queue/queue_events.py
==================================================
Queue events — frozen dataclasses emitted by the Order Queue.

Events: OrderQueued, QueueUpdated, PriorityChanged, OrderDispatched,
         RetryScheduled, QueueSuspended, QueueResumed, QueueCleared

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.order_queue.constants import QueueEventType, QueueEntryState


@dataclass(frozen=True)
class QueueEvent:
    """Base queue event."""
    event_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:  QueueEventType = QueueEventType.ORDER_QUEUED
    order_id:    str   = ""
    entry_id:    str   = ""
    occurred_at: float = field(default_factory=time.time)
    actor:       str   = "iios:execution:oms:order_queue"
    metadata:    dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "order_id":    self.order_id,
            "entry_id":    self.entry_id,
            "occurred_at": self.occurred_at,
            "actor":       self.actor,
            "metadata":    self.metadata,
        }


def make_order_queued(
    order_id:  str,
    entry_id:  str,
    priority:  str,
    policy:    str = "",
) -> QueueEvent:
    return QueueEvent(
        event_type=QueueEventType.ORDER_QUEUED,
        order_id=order_id,
        entry_id=entry_id,
        metadata={"priority": priority, "policy": policy},
    )


def make_queue_updated(
    order_id:  str,
    entry_id:  str,
    old_state: str,
    new_state: str,
) -> QueueEvent:
    return QueueEvent(
        event_type=QueueEventType.QUEUE_UPDATED,
        order_id=order_id,
        entry_id=entry_id,
        metadata={"old_state": old_state, "new_state": new_state},
    )


def make_priority_changed(
    order_id:     str,
    entry_id:     str,
    old_priority: str,
    new_priority: str,
) -> QueueEvent:
    return QueueEvent(
        event_type=QueueEventType.PRIORITY_CHANGED,
        order_id=order_id,
        entry_id=entry_id,
        metadata={"old_priority": old_priority, "new_priority": new_priority},
    )


def make_order_dispatched(
    order_id:  str,
    entry_id:  str,
    broker_id: str = "",
    exchange:  str = "",
) -> QueueEvent:
    return QueueEvent(
        event_type=QueueEventType.ORDER_DISPATCHED,
        order_id=order_id,
        entry_id=entry_id,
        metadata={"broker_id": broker_id, "exchange": exchange},
    )


def make_retry_scheduled(
    order_id:      str,
    entry_id:      str,
    retry_count:   int,
    next_retry_at: float,
) -> QueueEvent:
    return QueueEvent(
        event_type=QueueEventType.RETRY_SCHEDULED,
        order_id=order_id,
        entry_id=entry_id,
        metadata={"retry_count": retry_count, "next_retry_at": next_retry_at},
    )


def make_queue_suspended(
    order_id: str,
    entry_id: str,
    reason:   str = "",
) -> QueueEvent:
    return QueueEvent(
        event_type=QueueEventType.QUEUE_SUSPENDED,
        order_id=order_id,
        entry_id=entry_id,
        metadata={"reason": reason},
    )


def make_queue_resumed(
    order_id: str,
    entry_id: str,
) -> QueueEvent:
    return QueueEvent(
        event_type=QueueEventType.QUEUE_RESUMED,
        order_id=order_id,
        entry_id=entry_id,
        metadata={},
    )


def make_queue_cleared(count: int) -> QueueEvent:
    return QueueEvent(
        event_type=QueueEventType.QUEUE_CLEARED,
        order_id="",
        entry_id="",
        metadata={"cleared_count": count},
    )
