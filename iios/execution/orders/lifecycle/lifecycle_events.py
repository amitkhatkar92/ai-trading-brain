"""iios/execution/orders/lifecycle/lifecycle_events.py

Event dataclasses published on the internal event bus after each lifecycle transition.
These are plain data carriers — no threading, no I/O.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from ..order_constants import OrderStatus


@dataclass
class LifecycleEvent:
    event_type: str  = "lifecycle"
    order_id:   str  = ""
    from_status: OrderStatus = OrderStatus.DRAFT
    to_status:   OrderStatus = OrderStatus.CREATED
    reason:      str  = ""
    actor:       str  = "oms"
    timestamp:   float = field(default_factory=time.time)
    metadata:    dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type":  self.event_type,
            "order_id":    self.order_id,
            "from_status": self.from_status.value,
            "to_status":   self.to_status.value,
            "reason":      self.reason,
            "actor":       self.actor,
            "timestamp":   self.timestamp,
        }


@dataclass
class OrderFillEvent:
    event_type:    str   = "fill"
    order_id:      str   = ""
    fill_id:       str   = ""
    fill_quantity: float = 0.0
    fill_price:    float = 0.0
    is_complete:   bool  = False
    timestamp:     float = field(default_factory=time.time)
    metadata:      dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type":    self.event_type,
            "order_id":      self.order_id,
            "fill_id":       self.fill_id,
            "fill_quantity": self.fill_quantity,
            "fill_price":    self.fill_price,
            "is_complete":   self.is_complete,
            "timestamp":     self.timestamp,
        }


@dataclass
class OrderCancelEvent:
    event_type: str  = "cancel"
    order_id:   str  = ""
    reason:     str  = ""
    actor:      str  = "oms"
    timestamp:  float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "order_id":   self.order_id,
            "reason":     self.reason,
            "actor":      self.actor,
            "timestamp":  self.timestamp,
        }
