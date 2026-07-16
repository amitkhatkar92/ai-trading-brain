"""iios/execution/oms/order_queue/queue_dispatch_plan.py
==================================================
QueueDispatchPlan — immutable snapshot of entries ready for dispatch.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.order_queue.constants import QueuePolicyType
from iios.execution.oms.order_queue.queue_entry import QueueEntry


@dataclass(frozen=True)
class QueueDispatchPlan:
    """
    Immutable list of QueueEntries ordered for dispatch.

    Produced by OrderQueue.dispatch_plan(). Callers read the
    ordered entries to decide what to dispatch — they never
    mutate this object.
    """
    plan_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    entries:       tuple[QueueEntry, ...] = field(default_factory=tuple)
    policy_type:   QueuePolicyType = QueuePolicyType.FIFO
    total_ready:   int  = 0
    total_queued:  int  = 0    # all active entries (including WAITING)
    total_waiting: int  = 0
    created_at:    float = field(default_factory=time.time)
    metadata:      dict[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.entries)

    @property
    def is_empty(self) -> bool:
        return len(self.entries) == 0

    def top(self) -> QueueEntry | None:
        """Return the first (highest-priority) entry, or None if empty."""
        return self.entries[0] if self.entries else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id":      self.plan_id,
            "count":        self.count,
            "policy_type":  self.policy_type.value,
            "total_ready":  self.total_ready,
            "total_queued": self.total_queued,
            "total_waiting": self.total_waiting,
            "created_at":   self.created_at,
            "is_empty":     self.is_empty,
        }
