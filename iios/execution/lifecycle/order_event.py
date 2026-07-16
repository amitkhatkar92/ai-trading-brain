"""iios/execution/lifecycle/order_event.py
==================================================
OrderEvent and OrderEventType.

Every state transition produces exactly one OrderEvent.
Events are immutable and form the observable interface
of the lifecycle system — downstream consumers subscribe
to events without coupling to the order's internals.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .order_state import OrderState
from .order_transition import OrderTransition


class OrderEventType(str, Enum):
    """Classification of lifecycle events."""
    ORDER_CREATED          = "ORDER_CREATED"
    ORDER_VALIDATED        = "ORDER_VALIDATED"
    ORDER_PENDING          = "ORDER_PENDING"
    ORDER_SUBMITTED        = "ORDER_SUBMITTED"
    ORDER_ACKNOWLEDGED     = "ORDER_ACKNOWLEDGED"
    ORDER_PARTIALLY_FILLED = "ORDER_PARTIALLY_FILLED"
    ORDER_FILLED           = "ORDER_FILLED"
    ORDER_CANCEL_PENDING   = "ORDER_CANCEL_PENDING"
    ORDER_CANCELLED        = "ORDER_CANCELLED"
    ORDER_REJECTED         = "ORDER_REJECTED"
    ORDER_EXPIRED          = "ORDER_EXPIRED"
    ORDER_FAILED           = "ORDER_FAILED"
    ORDER_RECOVERY_STARTED = "ORDER_RECOVERY_STARTED"
    ORDER_RECOVERED        = "ORDER_RECOVERED"


# Canonical mapping: target state → emitted event type
_STATE_EVENT_MAP: dict[OrderState, OrderEventType] = {
    OrderState.CREATED:            OrderEventType.ORDER_CREATED,
    OrderState.VALIDATED:          OrderEventType.ORDER_VALIDATED,
    OrderState.PENDING_SUBMISSION: OrderEventType.ORDER_PENDING,
    OrderState.SUBMITTED:          OrderEventType.ORDER_SUBMITTED,
    OrderState.ACKNOWLEDGED:       OrderEventType.ORDER_ACKNOWLEDGED,
    OrderState.PARTIALLY_FILLED:   OrderEventType.ORDER_PARTIALLY_FILLED,
    OrderState.FILLED:             OrderEventType.ORDER_FILLED,
    OrderState.CANCEL_PENDING:     OrderEventType.ORDER_CANCEL_PENDING,
    OrderState.CANCELLED:          OrderEventType.ORDER_CANCELLED,
    OrderState.REJECTED:           OrderEventType.ORDER_REJECTED,
    OrderState.EXPIRED:            OrderEventType.ORDER_EXPIRED,
    OrderState.FAILED:             OrderEventType.ORDER_FAILED,
    OrderState.RECOVERING:         OrderEventType.ORDER_RECOVERY_STARTED,
    OrderState.RECOVERED:          OrderEventType.ORDER_RECOVERED,
}


def event_type_for_state(state: OrderState) -> OrderEventType:
    """Return the canonical OrderEventType for entering *state*."""
    return _STATE_EVENT_MAP[state]


@dataclass(frozen=True)
class OrderEvent:
    """
    Immutable lifecycle event.

    Parameters
    ----------
    event_id : str
        UUID uniquely identifying this event.
    order_id : str
        The order this event belongs to.
    event_type : OrderEventType
        Classification of the event.
    occurred_at : float
        Unix timestamp when the event was emitted.
    transition : OrderTransition | None
        The underlying transition that produced this event.
        None only for synthetic/internal events.
    payload : dict[str, Any]
        Additional event data (fill quantity, fill price, etc.).
    """
    event_id:    str
    order_id:    str
    event_type:  OrderEventType
    occurred_at: float
    transition:  Optional[OrderTransition]
    payload:     dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "order_id":    self.order_id,
            "event_type":  self.event_type.value,
            "occurred_at": self.occurred_at,
            "transition":  self.transition.to_dict() if self.transition else None,
            "payload":     dict(self.payload),
        }

    def __repr__(self) -> str:
        return (
            f"OrderEvent(order_id={self.order_id!r}, "
            f"type={self.event_type.value})"
        )


def make_event(
    order_id:    str,
    event_type:  OrderEventType,
    transition:  Optional[OrderTransition] = None,
    payload:     dict[str, Any] | None = None,
    occurred_at: float | None = None,
) -> OrderEvent:
    """Factory: create an OrderEvent with a generated event_id."""
    return OrderEvent(
        event_id    = str(uuid.uuid4()),
        order_id    = order_id,
        event_type  = event_type,
        occurred_at = occurred_at if occurred_at is not None else time.time(),
        transition  = transition,
        payload     = payload or {},
    )
