"""iios/execution/orders/lifecycle/lifecycle_engine.py

High-level lifecycle operations built on OrderLifecycle.
"""
from __future__ import annotations

import logging
from typing import Callable

from ..order_constants import OrderStatus
from ..core.order import Order
from ..core.order_history import OrderHistory
from ..core.order_status import OrderStatusTransition
from .order_lifecycle import OrderLifecycle

_log = logging.getLogger(__name__)

# Transition hook type: (order, transition) -> None
TransitionHook = Callable[[Order, OrderStatusTransition], None]


class LifecycleEngine:
    """Orchestrates lifecycle transitions with history recording and hooks."""

    def __init__(self, history: OrderHistory) -> None:
        self._lifecycle = OrderLifecycle()
        self._history   = history
        self._hooks:    list[TransitionHook] = []

    # ── Hook registration ─────────────────────────────────────────────────────

    def register_hook(self, hook: TransitionHook) -> None:
        self._hooks.append(hook)

    def unregister_hook(self, hook: TransitionHook) -> None:
        self._hooks = [h for h in self._hooks if h is not hook]

    # ── Core transition ───────────────────────────────────────────────────────

    def advance(
        self,
        order: Order,
        new_status: OrderStatus,
        *,
        reason: str = "",
        actor: str  = "oms",
    ) -> OrderStatusTransition:
        record = self._lifecycle.transition(order, new_status, reason=reason, actor=actor)
        self._history.add_transition(order.order_id, record)
        _log.debug("order=%s  %s → %s", order.order_id, record.from_status.value, record.to_status.value)
        for hook in self._hooks:
            try:
                hook(order, record)
            except Exception:
                _log.exception("Lifecycle hook error for order=%s", order.order_id)
        return record

    # ── Named helpers ─────────────────────────────────────────────────────────

    def create(self, order: Order) -> OrderStatusTransition:
        return self.advance(order, OrderStatus.CREATED, reason="order created")

    def validate(self, order: Order) -> OrderStatusTransition:
        return self.advance(order, OrderStatus.VALIDATED, reason="validation passed")

    def approve(self, order: Order) -> OrderStatusTransition:
        return self.advance(order, OrderStatus.APPROVED, reason="approved by oms")

    def enqueue(self, order: Order) -> OrderStatusTransition:
        return self.advance(order, OrderStatus.QUEUED, reason="enqueued")

    def submit(self, order: Order) -> OrderStatusTransition:
        return self.advance(order, OrderStatus.SUBMITTED, reason="submitted to venue")

    def acknowledge(self, order: Order) -> OrderStatusTransition:
        return self.advance(order, OrderStatus.ACKNOWLEDGED, reason="acknowledged by venue")

    def partially_fill(self, order: Order, reason: str = "") -> OrderStatusTransition:
        return self.advance(order, OrderStatus.PARTIALLY_FILLED, reason=reason or "partial fill")

    def fill(self, order: Order, reason: str = "") -> OrderStatusTransition:
        return self.advance(order, OrderStatus.FILLED, reason=reason or "fully filled")

    def cancel(self, order: Order, reason: str = "") -> OrderStatusTransition:
        return self.advance(order, OrderStatus.CANCELLED, reason=reason or "cancelled")

    def expire(self, order: Order) -> OrderStatusTransition:
        return self.advance(order, OrderStatus.EXPIRED, reason="time in force expired")

    def reject(self, order: Order, reason: str = "") -> OrderStatusTransition:
        return self.advance(order, OrderStatus.REJECTED, reason=reason or "rejected")

    def fail(self, order: Order, reason: str = "") -> OrderStatusTransition:
        return self.advance(order, OrderStatus.FAILED, reason=reason or "failed")

    def archive(self, order: Order) -> OrderStatusTransition:
        return self.advance(order, OrderStatus.ARCHIVED, reason="archived")
