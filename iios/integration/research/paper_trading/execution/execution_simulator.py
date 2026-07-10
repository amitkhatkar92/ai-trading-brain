"""execution/execution_simulator.py — Main execution simulation engine."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.paper_trading.paper_trading_constants import (
    PaperOrderStatus,
    TimeInForce,
)
from iios.integration.research.paper_trading.paper_trading_exceptions import (
    OrderNotFoundError,
    OrderStateError,
    ExecutionError,
)
from iios.integration.research.paper_trading.core.paper_order import PaperOrder
from iios.integration.research.paper_trading.market.market_simulator import PriceBar
from iios.integration.research.paper_trading.execution.fill_simulator import FillResult, FillSimulator


class ExecutionSimulator:
    """
    Routes orders through the FillSimulator and manages their lifecycle.

    Thread-safe via a single RLock.
    """

    def __init__(
        self,
        fill_simulator:    FillSimulator,
        *,
        max_pending_orders: int = 10_000,
    ) -> None:
        self._filler    = fill_simulator
        self._max       = max_pending_orders
        self._orders:   dict[str, PaperOrder] = {}
        self._pending:  list[str]              = []   # order_ids of non-terminal orders
        self._filled:   list[str]              = []
        self._lock      = threading.RLock()
        self._total_submitted = 0
        self._total_filled    = 0
        self._total_rejected  = 0

    # ── Order submission ──────────────────────────────────────────────────────

    def submit_order(self, order: PaperOrder) -> PaperOrder:
        """Validate and queue an order for fill processing."""
        with self._lock:
            if len(self._pending) >= self._max:
                raise ExecutionError(f"Pending order limit ({self._max}) reached")
            if order.quantity <= 0.0:
                order.status        = PaperOrderStatus.REJECTED
                order.reject_reason = "Quantity must be positive"
                self._total_rejected += 1
                self._orders[order.order_id] = order
                return order
            order.status = PaperOrderStatus.OPEN
            order.touch()
            self._orders[order.order_id] = order
            self._pending.append(order.order_id)
            self._total_submitted += 1
        return order

    # ── Bar processing ────────────────────────────────────────────────────────

    def process_bar(self, bars: dict[str, PriceBar]) -> list[FillResult]:
        """Attempt to fill all pending orders against the current bar prices."""
        fills: list[FillResult] = []
        with self._lock:
            still_pending: list[str] = []
            for oid in self._pending:
                order = self._orders.get(oid)
                if order is None or order.is_terminal():
                    continue
                bar = bars.get(order.symbol)
                if bar is None:
                    still_pending.append(oid)
                    continue
                fill = self._filler.try_fill(order, bar)
                if fill is not None:
                    order.apply_fill(
                        fill.quantity,
                        fill.fill_price,
                        fill.commission,
                        fill.slippage,
                        fill.timestamp,
                    )
                    fills.append(fill)
                    if order.is_terminal():
                        self._filled.append(oid)
                        self._total_filled += 1
                    else:
                        still_pending.append(oid)
                else:
                    still_pending.append(oid)
            self._pending = still_pending
        return fills

    # ── Order management ──────────────────────────────────────────────────────

    def cancel_order(self, order_id: str) -> PaperOrder:
        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                raise OrderNotFoundError(f"Order {order_id!r} not found")
            if order.is_terminal():
                raise OrderStateError(
                    f"Cannot cancel terminal order {order_id!r} (status={order.status.value})"
                )
            order.status = PaperOrderStatus.CANCELLED
            order.touch()
            self._pending = [o for o in self._pending if o != order_id]
        return order

    def expire_orders(self, current_ts: float) -> list[PaperOrder]:
        """Cancel all DAY / expired-GTD orders whose expiry has passed."""
        expired: list[PaperOrder] = []
        with self._lock:
            still_pending: list[str] = []
            for oid in self._pending:
                order = self._orders.get(oid)
                if order is None:
                    continue
                should_expire = (
                    order.tif == TimeInForce.DAY
                    or (order.expires_at is not None and current_ts >= order.expires_at)
                )
                if should_expire:
                    order.status = PaperOrderStatus.EXPIRED
                    order.touch()
                    expired.append(order)
                else:
                    still_pending.append(oid)
            self._pending = still_pending
        return expired

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_order(self, order_id: str) -> PaperOrder:
        with self._lock:
            order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(f"Order {order_id!r} not found")
        return order

    def pending_orders(self) -> list[PaperOrder]:
        with self._lock:
            return [self._orders[oid] for oid in self._pending if oid in self._orders]

    def all_orders(self) -> list[PaperOrder]:
        with self._lock:
            return list(self._orders.values())

    def filled_orders(self) -> list[PaperOrder]:
        with self._lock:
            return [self._orders[oid] for oid in self._filled if oid in self._orders]

    # ── State reset ───────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._orders.clear()
            self._pending.clear()
            self._filled.clear()

    # ── Stats ─────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_submitted": self._total_submitted,
                "total_filled":    self._total_filled,
                "total_rejected":  self._total_rejected,
                "pending_count":   len(self._pending),
                "total_orders":    len(self._orders),
            }
