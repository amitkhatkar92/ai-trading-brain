"""iios/execution/orders/order_registry.py

Thread-safe in-memory registry of all Order objects managed by the OMS.
"""
from __future__ import annotations

import threading
from typing import Any

from .order_constants import (
    ACTIVE_STATUSES,
    DEFAULT_MAX_ORDERS,
    TERMINAL_STATUSES,
    OrderStatus,
)
from .core.order import Order
from .order_exceptions import (
    OMSCapacityError,
    OrderAlreadyExistsError,
    OrderNotFoundError,
)


class OrderRegistry:
    """Thread-safe, bounded in-memory registry of Order objects.

    Indexed by order_id for O(1) lookups.  Secondary indexes on portfolio_id,
    strategy_id, and execution_id are maintained eagerly for O(n) list queries.
    """

    def __init__(self, max_orders: int = DEFAULT_MAX_ORDERS) -> None:
        self._max_orders   = max_orders
        self._orders:      dict[str, Order]        = {}
        self._by_portfolio: dict[str, set[str]]    = {}   # portfolio_id → {order_id}
        self._by_strategy:  dict[str, set[str]]    = {}   # strategy_id  → {order_id}
        self._by_execution: dict[str, set[str]]    = {}   # execution_id → {order_id}
        self._lock         = threading.RLock()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _index_add(self, order: Order) -> None:
        """Add secondary index entries (must be called under lock)."""
        if order.portfolio_id:
            self._by_portfolio.setdefault(order.portfolio_id, set()).add(order.order_id)
        if order.strategy_id:
            self._by_strategy.setdefault(order.strategy_id, set()).add(order.order_id)
        if order.execution_id:
            self._by_execution.setdefault(order.execution_id, set()).add(order.order_id)

    def _index_remove(self, order: Order) -> None:
        """Remove secondary index entries (must be called under lock)."""
        if order.portfolio_id and order.portfolio_id in self._by_portfolio:
            self._by_portfolio[order.portfolio_id].discard(order.order_id)
        if order.strategy_id and order.strategy_id in self._by_strategy:
            self._by_strategy[order.strategy_id].discard(order.order_id)
        if order.execution_id and order.execution_id in self._by_execution:
            self._by_execution[order.execution_id].discard(order.order_id)

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, order: Order) -> None:
        """Register a new order.  Raises if duplicate or capacity exceeded."""
        with self._lock:
            if order.order_id in self._orders:
                raise OrderAlreadyExistsError(order_id=order.order_id)
            if len(self._orders) >= self._max_orders:
                raise OMSCapacityError(max_orders=self._max_orders)
            self._orders[order.order_id] = order
            self._index_add(order)

    def update(self, order: Order) -> None:
        """Replace the stored reference for an existing order."""
        with self._lock:
            if order.order_id not in self._orders:
                raise OrderNotFoundError(order_id=order.order_id)
            self._index_remove(self._orders[order.order_id])
            self._orders[order.order_id] = order
            self._index_add(order)

    def unregister(self, order_id: str) -> None:
        """Remove an order from the registry (silently ignored if absent)."""
        with self._lock:
            order = self._orders.pop(order_id, None)
            if order is not None:
                self._index_remove(order)

    # ── Lookups ───────────────────────────────────────────────────────────────

    def get(self, order_id: str) -> Order:
        with self._lock:
            o = self._orders.get(order_id)
            if o is None:
                raise OrderNotFoundError(order_id=order_id)
            return o

    def get_optional(self, order_id: str) -> Order | None:
        with self._lock:
            return self._orders.get(order_id)

    def is_registered(self, order_id: str) -> bool:
        with self._lock:
            return order_id in self._orders

    # ── Filtered queries ──────────────────────────────────────────────────────

    def all_orders(self) -> list[Order]:
        with self._lock:
            return list(self._orders.values())

    def all_order_ids(self) -> list[str]:
        with self._lock:
            return list(self._orders.keys())

    def get_by_status(self, status: OrderStatus) -> list[Order]:
        with self._lock:
            return [o for o in self._orders.values() if o.status == status]

    def get_active(self) -> list[Order]:
        with self._lock:
            return [o for o in self._orders.values() if o.status not in TERMINAL_STATUSES]

    def get_terminal(self) -> list[Order]:
        with self._lock:
            return [o for o in self._orders.values() if o.status in TERMINAL_STATUSES]

    def get_by_portfolio(self, portfolio_id: str) -> list[Order]:
        with self._lock:
            ids = self._by_portfolio.get(portfolio_id, set())
            return [self._orders[oid] for oid in ids if oid in self._orders]

    def get_by_strategy(self, strategy_id: str) -> list[Order]:
        with self._lock:
            ids = self._by_strategy.get(strategy_id, set())
            return [self._orders[oid] for oid in ids if oid in self._orders]

    def get_by_execution(self, execution_id: str) -> list[Order]:
        with self._lock:
            ids = self._by_execution.get(execution_id, set())
            return [self._orders[oid] for oid in ids if oid in self._orders]

    # ── Metrics ───────────────────────────────────────────────────────────────

    def count(self) -> int:
        with self._lock:
            return len(self._orders)

    def count_by_status(self, status: OrderStatus) -> int:
        with self._lock:
            return sum(1 for o in self._orders.values() if o.status == status)

    def count_active(self) -> int:
        with self._lock:
            return sum(1 for o in self._orders.values() if o.status not in TERMINAL_STATUSES)

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._orders)
            by_status: dict[str, int] = {}
            for o in self._orders.values():
                key = o.status.value
                by_status[key] = by_status.get(key, 0) + 1
            active    = sum(1 for o in self._orders.values() if o.status not in TERMINAL_STATUSES)
            terminal  = total - active
            return {
                "total_orders":    total,
                "active_orders":   active,
                "terminal_orders": terminal,
                "by_status":       by_status,
                "max_orders":      self._max_orders,
                "portfolios":      len(self._by_portfolio),
                "strategies":      len(self._by_strategy),
            }

    def clear(self) -> None:
        """Clear all orders.  Intended for testing only."""
        with self._lock:
            self._orders.clear()
            self._by_portfolio.clear()
            self._by_strategy.clear()
            self._by_execution.clear()
