"""iios/execution/orders/core/order_history.py

Per-order ring-buffer history: status transitions + fill executions.
Thread-safe. Bounded by DEFAULT_MAX_HISTORY entries per slot.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any

from ..order_constants import DEFAULT_MAX_HISTORY
from .order_execution import OrderExecution
from .order_status import OrderStatusTransition


class _OrderTimeline:
    """Ring-buffer of transitions and fills for one order."""

    __slots__ = ("_transitions", "_executions", "_maxlen")

    def __init__(self, maxlen: int) -> None:
        self._maxlen     = maxlen
        self._transitions: deque[OrderStatusTransition] = deque(maxlen=maxlen)
        self._executions:  deque[OrderExecution]         = deque(maxlen=maxlen)

    def add_transition(self, t: OrderStatusTransition) -> None:
        self._transitions.append(t)

    def add_execution(self, e: OrderExecution) -> None:
        self._executions.append(e)

    def transitions(self) -> list[OrderStatusTransition]:
        return list(self._transitions)

    def executions(self) -> list[OrderExecution]:
        return list(self._executions)


class OrderHistory:
    """Thread-safe store of per-order timelines (status changes + fills)."""

    def __init__(self, max_orders: int = 100_000, maxlen_per_order: int = DEFAULT_MAX_HISTORY) -> None:
        self._max_orders         = max_orders
        self._maxlen_per_order   = maxlen_per_order
        self._timelines:  dict[str, _OrderTimeline] = {}
        self._lock:       threading.RLock            = threading.RLock()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get_or_create(self, order_id: str) -> _OrderTimeline:
        if order_id not in self._timelines:
            self._timelines[order_id] = _OrderTimeline(self._maxlen_per_order)
        return self._timelines[order_id]

    # ── Public API ────────────────────────────────────────────────────────────

    def add_transition(self, order_id: str, transition: OrderStatusTransition) -> None:
        with self._lock:
            self._get_or_create(order_id).add_transition(transition)

    def add_execution(self, order_id: str, execution: OrderExecution) -> None:
        with self._lock:
            self._get_or_create(order_id).add_execution(execution)

    def get_transitions(self, order_id: str) -> list[OrderStatusTransition]:
        with self._lock:
            tl = self._timelines.get(order_id)
            return tl.transitions() if tl else []

    def get_executions(self, order_id: str) -> list[OrderExecution]:
        with self._lock:
            tl = self._timelines.get(order_id)
            return tl.executions() if tl else []

    def all_order_ids(self) -> list[str]:
        with self._lock:
            return list(self._timelines.keys())

    def order_count(self) -> int:
        with self._lock:
            return len(self._timelines)

    def drop_order(self, order_id: str) -> None:
        """Remove all history for an order (used during hard archive)."""
        with self._lock:
            self._timelines.pop(order_id, None)

    def clear(self) -> None:
        with self._lock:
            self._timelines.clear()

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "order_count": len(self._timelines),
                "max_orders":  self._max_orders,
            }
