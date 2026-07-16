"""iios/execution/oms/order_queue/queue_snapshot.py
==================================================
QueueSnapshot — immutable point-in-time view of the order queue.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.order_queue.constants import (
    ACTIVE_ENTRY_STATES,
    QueueEntryState,
    QueuePolicyType,
)
from iios.execution.oms.order_queue.queue_entry import QueueEntry


@dataclass(frozen=True)
class QueueSnapshot:
    """
    Immutable, point-in-time view of the queue state.

    All counts reflect the state at the moment taken_at was recorded.
    """
    snapshot_id:           str   = field(default_factory=lambda: str(uuid.uuid4()))
    policy_type:           QueuePolicyType = QueuePolicyType.FIFO
    peak_queue_size:       int   = 0

    total:                 int   = 0
    total_queued:          int   = 0
    total_waiting:         int   = 0
    total_ready:           int   = 0
    total_dispatch_pending: int  = 0
    total_dispatched:      int   = 0
    total_suspended:       int   = 0
    total_retry_pending:   int   = 0
    total_failed:          int   = 0
    total_expired:         int   = 0
    total_removed:         int   = 0

    entries:               tuple[QueueEntry, ...] = field(default_factory=tuple)
    taken_at:              float = field(default_factory=time.time)
    metadata:              dict[str, Any] = field(default_factory=dict)

    def active_entries(self) -> list[QueueEntry]:
        return [e for e in self.entries if e.state in ACTIVE_ENTRY_STATES]

    def ready_entries(self) -> list[QueueEntry]:
        return [e for e in self.entries if e.state == QueueEntryState.READY]

    def waiting_entries(self) -> list[QueueEntry]:
        return [e for e in self.entries if e.state == QueueEntryState.WAITING]

    def suspended_entries(self) -> list[QueueEntry]:
        return [e for e in self.entries if e.state == QueueEntryState.SUSPENDED]

    def retry_pending_entries(self) -> list[QueueEntry]:
        return [e for e in self.entries if e.state == QueueEntryState.RETRY_PENDING]

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":            self.snapshot_id,
            "policy_type":            self.policy_type.value,
            "peak_queue_size":        self.peak_queue_size,
            "total":                  self.total,
            "total_queued":           self.total_queued,
            "total_waiting":          self.total_waiting,
            "total_ready":            self.total_ready,
            "total_dispatch_pending": self.total_dispatch_pending,
            "total_dispatched":       self.total_dispatched,
            "total_suspended":        self.total_suspended,
            "total_retry_pending":    self.total_retry_pending,
            "total_failed":           self.total_failed,
            "total_expired":          self.total_expired,
            "total_removed":          self.total_removed,
            "taken_at":               self.taken_at,
        }
