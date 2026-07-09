"""iios/execution/orders/tracking/order_tracker.py

Per-order state tracker: stores the current Order reference and computes
per-order fill metrics in O(1).
"""
from __future__ import annotations

import threading
import time
from typing import Any

from ..core.order import Order
from ..core.order_execution import OrderExecution
from ..order_exceptions import OrderNotFoundError


class OrderTracker:
    """Thread-safe registry of live order references + per-order fill data."""

    def __init__(self) -> None:
        self._orders:   dict[str, Order]             = {}
        self._fills:    dict[str, list[OrderExecution]] = {}
        self._latency:  dict[str, float]             = {}   # order_id → fill latency ms
        self._lock:     threading.RLock              = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def track(self, order: Order) -> None:
        with self._lock:
            self._orders[order.order_id] = order
            self._fills.setdefault(order.order_id, [])

    def untrack(self, order_id: str) -> None:
        with self._lock:
            self._orders.pop(order_id, None)
            self._fills.pop(order_id, None)
            self._latency.pop(order_id, None)

    # ── Updates ───────────────────────────────────────────────────────────────

    def update(self, order: Order) -> None:
        with self._lock:
            self._orders[order.order_id] = order

    def record_fill(self, order_id: str, fill: OrderExecution) -> None:
        with self._lock:
            self._fills.setdefault(order_id, []).append(fill)
            # Compute latency: created_at → first fill timestamp
            order = self._orders.get(order_id)
            if order and order.created_at:
                self._latency[order_id] = (fill.timestamp - order.created_at) * 1000.0

    # ── Queries ───────────────────────────────────────────────────────────────

    def get(self, order_id: str) -> Order:
        with self._lock:
            o = self._orders.get(order_id)
            if o is None:
                raise OrderNotFoundError(order_id=order_id)
            return o

    def get_optional(self, order_id: str) -> Order | None:
        with self._lock:
            return self._orders.get(order_id)

    def fills(self, order_id: str) -> list[OrderExecution]:
        with self._lock:
            return list(self._fills.get(order_id, []))

    def fill_latency_ms(self, order_id: str) -> float | None:
        with self._lock:
            return self._latency.get(order_id)

    def all_orders(self) -> list[Order]:
        with self._lock:
            return list(self._orders.values())

    def active_order_ids(self) -> list[str]:
        with self._lock:
            return [oid for oid, o in self._orders.items() if o.is_active()]

    def __len__(self) -> int:
        with self._lock:
            return len(self._orders)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "tracked":         len(self._orders),
                "active":          sum(1 for o in self._orders.values() if o.is_active()),
                "with_fills":      sum(1 for fills in self._fills.values() if fills),
            }
