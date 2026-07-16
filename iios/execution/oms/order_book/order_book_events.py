"""iios/execution/oms/order_book/order_book_events.py
==================================================
Events emitted by the Order Book lifecycle.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.execution.oms.order_book.constants import BookEntryStatus, BookEventType


@dataclass(frozen=True)
class OrderBookEvent:
    """Immutable event emitted by the Order Book."""

    event_id:      str            = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:    BookEventType  = BookEventType.ORDER_ADDED
    order_id:      str            = ""
    instrument:    str            = ""
    status:        Optional[BookEntryStatus] = None
    occurred_at:   float         = field(default_factory=time.time)
    actor:         str            = "iios:system"
    reason:        str            = ""
    payload:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "order_id":    self.order_id,
            "instrument":  self.instrument,
            "status":      self.status.value if self.status else None,
            "occurred_at": self.occurred_at,
            "actor":       self.actor,
            "reason":      self.reason,
            "payload":     self.payload,
        }

    def __repr__(self) -> str:
        return (
            f"OrderBookEvent(type={self.event_type.value}, "
            f"order={self.order_id!r})"
        )


def make_book_event(
    event_type: BookEventType,
    order_id:   str,
    *,
    instrument: str = "",
    status:     Optional[BookEntryStatus] = None,
    actor:      str = "iios:system",
    reason:     str = "",
    payload:    dict[str, Any] | None = None,
    occurred_at: float = 0.0,
) -> OrderBookEvent:
    return OrderBookEvent(
        event_type  = event_type,
        order_id    = order_id,
        instrument  = instrument,
        status      = status,
        occurred_at = occurred_at or time.time(),
        actor       = actor,
        reason      = reason,
        payload     = payload or {},
    )
