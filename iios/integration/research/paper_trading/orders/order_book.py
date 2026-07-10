"""orders/order_book.py — Thread-safe order lifecycle management."""
from __future__ import annotations

import threading
from typing import Any

from iios.integration.research.paper_trading.paper_trading_constants import PaperOrderStatus
from iios.integration.research.paper_trading.paper_trading_exceptions import (
    OrderNotFoundError,
    OrderStateError,
)
from iios.integration.research.paper_trading.core.paper_order import PaperOrder


class OrderBook:
    """
    Central store for all orders in a paper trading session.

    Thread-safe via a single RLock.
    """

    def __init__(self) -> None:
        self._orders: dict[str, PaperOrder] = {}
        self._lock    = threading.RLock()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def add(self, order: PaperOrder) -> None:
        with self._lock:
            self._orders[order.order_id] = order

    def get(self, order_id: str) -> PaperOrder:
        with self._lock:
            if order_id not in self._orders:
                raise OrderNotFoundError(f"Order {order_id!r} not found")
            return self._orders[order_id]

    def update(self, order: PaperOrder) -> None:
        with self._lock:
            if order.order_id not in self._orders:
                raise OrderNotFoundError(f"Order {order.order_id!r} not found")
            self._orders[order.order_id] = order

    def cancel(self, order_id: str) -> PaperOrder:
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                raise OrderNotFoundError(f"Order {order_id!r} not found")
            if order.is_terminal():
                raise OrderStateError(
                    f"Cannot cancel terminal order {order_id!r} "
                    f"(status={order.status.value})"
                )
            order.status = PaperOrderStatus.CANCELLED
            order.touch()
        return order

    def has(self, order_id: str) -> bool:
        with self._lock:
            return order_id in self._orders

    # ── Queries ───────────────────────────────────────────────────────────────

    def all_orders(self) -> list[PaperOrder]:
        with self._lock:
            return list(self._orders.values())

    def pending(self) -> list[PaperOrder]:
        with self._lock:
            return [
                o for o in self._orders.values()
                if o.status in (PaperOrderStatus.PENDING, PaperOrderStatus.OPEN,
                                PaperOrderStatus.PARTIALLY_FILLED)
            ]

    def open_orders(self) -> list[PaperOrder]:
        with self._lock:
            return [
                o for o in self._orders.values()
                if o.status == PaperOrderStatus.OPEN
            ]

    def filled_orders(self) -> list[PaperOrder]:
        with self._lock:
            return [
                o for o in self._orders.values()
                if o.status == PaperOrderStatus.FILLED
            ]

    def find_by_symbol(self, symbol: str) -> list[PaperOrder]:
        with self._lock:
            return [o for o in self._orders.values() if o.symbol == symbol]

    def count(self) -> int:
        with self._lock:
            return len(self._orders)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for o in self._orders.values():
                by_status[o.status.value] = by_status.get(o.status.value, 0) + 1
            return {
                "total_orders": len(self._orders),
                "by_status":    by_status,
            }
