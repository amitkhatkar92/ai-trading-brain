"""iios/execution/orders/core/order_status.py

Status-transition record — one entry per state change.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..order_constants import OrderStatus


@dataclass
class OrderStatusTransition:
    """Immutable audit record of one status transition."""

    transition_id: str         = field(default_factory=lambda: str(uuid.uuid4()))
    order_id:      str         = ""
    from_status:   OrderStatus = OrderStatus.DRAFT
    to_status:     OrderStatus = OrderStatus.CREATED
    reason:        str         = ""
    actor:         str         = "oms"      # "oms" | "broker" | "risk" | "user"
    timestamp:     float       = field(default_factory=time.time)
    metadata:      dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "order_id":      self.order_id,
            "from_status":   self.from_status.value,
            "to_status":     self.to_status.value,
            "reason":        self.reason,
            "actor":         self.actor,
            "timestamp":     self.timestamp,
            "metadata":      dict(self.metadata),
        }
