"""iios/execution/lifecycle/order_transition.py
==================================================
OrderTransition — immutable record of one state change.

Every successful state transition produces exactly one
OrderTransition appended to the order's OrderHistory.
The record is frozen (immutable after creation) so that
the audit trail cannot be tampered with.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .order_state import OrderState


@dataclass(frozen=True)
class OrderTransition:
    """
    Immutable audit record of a single order state transition.

    Parameters
    ----------
    transition_id : str
        UUID uniquely identifying this transition record.
    order_id : str
        The order that changed state.
    from_state : OrderState
        State before the transition.
    to_state : OrderState
        State after the transition.
    reason : str
        Human-readable explanation (e.g. "validation passed",
        "broker rejected: insufficient margin").
    actor : str
        System component that initiated the transition
        (e.g. "validator", "broker", "exchange", "scheduler").
    occurred_at : float
        Unix timestamp (time.time()) when the transition was applied.
    metadata : dict[str, Any]
        Arbitrary additional context (fill price, broker ref, etc.).
    """
    transition_id: str
    order_id:      str
    from_state:    OrderState
    to_state:      OrderState
    reason:        str
    actor:         str
    occurred_at:   float
    metadata:      dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "order_id":      self.order_id,
            "from_state":    self.from_state.value,
            "to_state":      self.to_state.value,
            "reason":        self.reason,
            "actor":         self.actor,
            "occurred_at":   self.occurred_at,
            "metadata":      dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"OrderTransition("
            f"order_id={self.order_id!r}, "
            f"{self.from_state.value}→{self.to_state.value}, "
            f"actor={self.actor!r})"
        )


def make_transition(
    order_id:    str,
    from_state:  OrderState,
    to_state:    OrderState,
    reason:      str,
    actor:       str,
    metadata:    dict[str, Any] | None = None,
    occurred_at: float | None = None,
) -> OrderTransition:
    """
    Factory: create an OrderTransition with an auto-generated
    transition_id and the current timestamp if *occurred_at* is omitted.
    """
    return OrderTransition(
        transition_id = str(uuid.uuid4()),
        order_id      = order_id,
        from_state    = from_state,
        to_state      = to_state,
        reason        = reason,
        actor         = actor,
        occurred_at   = occurred_at if occurred_at is not None else time.time(),
        metadata      = dict(metadata) if metadata else {},
    )
