"""iios/execution/orders/lifecycle/order_lifecycle.py

State-machine rules for order status transitions.
Pure logic — no I/O, no threading.
"""
from __future__ import annotations

import time

from ..order_constants import TERMINAL_STATUSES, VALID_TRANSITIONS, OrderStatus
from ..core.order import Order
from ..core.order_status import OrderStatusTransition
from ..order_exceptions import InvalidOrderStatusError, OrderTerminalError


class OrderLifecycle:
    """Stateless rules engine for OMS lifecycle transitions."""

    # ── Queries ───────────────────────────────────────────────────────────────

    @staticmethod
    def can_transition(from_status: OrderStatus, to_status: OrderStatus) -> bool:
        return to_status in VALID_TRANSITIONS.get(from_status, frozenset())

    @staticmethod
    def is_terminal(status: OrderStatus) -> bool:
        return status in TERMINAL_STATUSES

    @staticmethod
    def terminal_statuses() -> frozenset[OrderStatus]:
        return TERMINAL_STATUSES

    @staticmethod
    def allowed_next(status: OrderStatus) -> frozenset[OrderStatus]:
        return VALID_TRANSITIONS.get(status, frozenset())

    # ── Mutation ──────────────────────────────────────────────────────────────

    def transition(
        self,
        order: Order,
        new_status: OrderStatus,
        *,
        reason: str = "",
        actor: str  = "oms",
    ) -> OrderStatusTransition:
        """Apply a transition to *order* and return the audit record."""
        # Allow terminal → ARCHIVED (explicit archiving of closed orders).
        # Block all other transitions out of a terminal state.
        if order.status in TERMINAL_STATUSES and new_status != OrderStatus.ARCHIVED:
            raise OrderTerminalError(
                order_id=order.order_id,
                status=order.status.value,
            )
        if not self.can_transition(order.status, new_status):
            raise InvalidOrderStatusError(
                order_id=order.order_id,
                from_status=order.status.value,
                to_status=new_status.value,
            )

        record = OrderStatusTransition(
            order_id    = order.order_id,
            from_status = order.status,
            to_status   = new_status,
            reason      = reason,
            actor       = actor,
            timestamp   = time.time(),
        )

        # Delegate mutation to Order so its own timestamps stay in sync
        order.transition_to(new_status, reason=reason)
        return record
