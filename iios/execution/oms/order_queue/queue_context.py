"""iios/execution/oms/order_queue/queue_context.py
==================================================
QueueContext — immutable input describing a single enqueue operation.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.order_queue.constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TTL_SEC,
    ExecutionMode,
    QueuePolicyType,
    QueuePriorityLevel,
)


@dataclass(frozen=True)
class QueueContext:
    """
    Immutable context submitted to OrderQueue.enqueue().

    Carries every field required to build a QueueEntry without
    any mutable state leaking into the queue.
    """
    context_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:            str   = ""
    priority:            QueuePriorityLevel = QueuePriorityLevel.NORMAL
    policy_type:         QueuePolicyType    = QueuePolicyType.FIFO
    execution_mode:      ExecutionMode      = ExecutionMode.LIVE

    ready_at:            float = 0.0     # 0 = immediately ready
    ttl_sec:             float = DEFAULT_TTL_SEC
    max_retries:         int   = DEFAULT_MAX_RETRIES

    broker_id:           str   = ""
    exchange:            str   = ""
    routing_decision_id: str   = ""
    workflow_id:         str   = ""
    portfolio_id:        str   = ""
    strategy_id:         str   = ""
    decision_id:         str   = ""
    correlation_id:      str   = ""

    created_at:          float = field(default_factory=time.time)
    metadata:            dict[str, Any] = field(default_factory=dict)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_immediate(self) -> bool:
        """True if the entry should be READY immediately."""
        return self.ready_at <= 0 or self.ready_at <= time.time()

    @property
    def is_scheduled(self) -> bool:
        """True if dispatch should be delayed until ready_at."""
        return self.ready_at > time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id":    self.context_id,
            "order_id":      self.order_id,
            "priority":      self.priority.name,
            "policy_type":   self.policy_type.value,
            "execution_mode": self.execution_mode.value,
            "ready_at":      self.ready_at,
            "ttl_sec":       self.ttl_sec,
            "max_retries":   self.max_retries,
            "broker_id":     self.broker_id,
            "exchange":      self.exchange,
            "is_immediate":  self.is_immediate,
            "is_scheduled":  self.is_scheduled,
        }
