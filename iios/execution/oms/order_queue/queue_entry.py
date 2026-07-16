"""iios/execution/oms/order_queue/queue_entry.py
==================================================
QueueEntry — mutable dataclass representing one order in the queue.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.order_queue.constants import (
    ACTIVE_ENTRY_STATES,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TTL_SEC,
    DISPATCHABLE_STATES,
    TERMINAL_ENTRY_STATES,
    ExecutionMode,
    QueueEntryState,
    QueuePolicyType,
    QueuePriorityLevel,
)


@dataclass
class QueueEntry:
    """
    Represents a single routed order waiting in the queue.

    Mutable: state, retry counts, timestamps, and reason fields
    are updated in-place as the entry progresses.

    Never communicates with brokers or performs execution.
    """
    entry_id:           str   = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:           str   = ""
    priority:           QueuePriorityLevel = QueuePriorityLevel.NORMAL
    state:              QueueEntryState    = QueueEntryState.QUEUED
    policy_type:        QueuePolicyType    = QueuePolicyType.FIFO
    execution_mode:     ExecutionMode      = ExecutionMode.LIVE

    queued_at:          float = field(default_factory=time.time)
    ready_at:           float = 0.0   # 0 = immediately ready; >0 = scheduled
    dispatched_at:      float = 0.0
    suspended_at:       float = 0.0
    failed_at:          float = 0.0
    expired_at:         float = 0.0

    retry_count:        int   = 0
    max_retries:        int   = DEFAULT_MAX_RETRIES
    next_retry_at:      float = 0.0

    ttl_sec:            float = DEFAULT_TTL_SEC

    broker_id:          str   = ""
    exchange:           str   = ""
    routing_decision_id: str  = ""
    workflow_id:        str   = ""
    portfolio_id:       str   = ""
    strategy_id:        str   = ""
    decision_id:        str   = ""
    correlation_id:     str   = ""

    suspend_reason:     str   = ""
    failure_reason:     str   = ""
    metadata:           dict[str, Any] = field(default_factory=dict)

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        """True if the TTL has elapsed (not applicable to terminal entries)."""
        if self.state in TERMINAL_ENTRY_STATES:
            return False
        return (time.time() - self.queued_at) > self.ttl_sec

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    @property
    def is_dispatchable(self) -> bool:
        return self.state in DISPATCHABLE_STATES and not self.is_expired

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_ENTRY_STATES

    @property
    def is_active(self) -> bool:
        return self.state in ACTIVE_ENTRY_STATES

    @property
    def wait_time_ms(self) -> float:
        """Elapsed milliseconds since this entry was queued."""
        return (time.time() - self.queued_at) * 1_000

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id":           self.entry_id,
            "order_id":           self.order_id,
            "priority":           self.priority.name,
            "state":              self.state.value,
            "policy_type":        self.policy_type.value,
            "execution_mode":     self.execution_mode.value,
            "queued_at":          self.queued_at,
            "ready_at":           self.ready_at,
            "dispatched_at":      self.dispatched_at,
            "retry_count":        self.retry_count,
            "max_retries":        self.max_retries,
            "next_retry_at":      self.next_retry_at,
            "ttl_sec":            self.ttl_sec,
            "broker_id":          self.broker_id,
            "exchange":           self.exchange,
            "is_expired":         self.is_expired,
            "can_retry":          self.can_retry,
            "failure_reason":     self.failure_reason,
            "suspend_reason":     self.suspend_reason,
        }
