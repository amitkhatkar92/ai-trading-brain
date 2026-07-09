"""iios/execution/orders/order_management_system.py

Top-level OMS facade — the single entry-point for all order operations.

Follows the singleton pattern established by the other IIOS engines:
    oms = get_oms()          # returns (and initialises if needed) the singleton
    reset_oms()              # tears down the singleton (for testing)
"""
from __future__ import annotations

import asyncio
import functools
import logging
import threading
import time
from typing import Any

from .order_constants import OMS_SYSTEM_ID, OMS_VERSION
from .core.order import Order
from .core.order_execution import OrderExecution
from .core.order_request import OrderRequest
from .core.order_response import OrderResponse
from .order_exceptions import OMSNotInitializedError
from .order_manager import OrderManager

_log = logging.getLogger(__name__)

# ── Module-level singleton lock ────────────────────────────────────────────────

_singleton_lock: threading.Lock = threading.Lock()
_instance: OrderManagementSystem | None = None


class OrderManagementSystem:
    """Facade that unifies all OMS subsystems behind a single coherent API.

    Lifecycle
    ---------
    1. Call ``initialize()`` (or use the ``get_oms()`` singleton helper, which
       initialises on first call).
    2. Submit orders via ``create_order`` / ``submit_order`` / ``fill_order``.
    3. Call ``shutdown()`` on clean exit.
    """

    def __init__(self, manager: OrderManager | None = None) -> None:
        self._manager    = manager or OrderManager()
        self._running    = False
        self._started_at: float | None = None
        self._lock       = threading.Lock()

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Activate the OMS.  Idempotent — safe to call multiple times."""
        with self._lock:
            if self._running:
                return
            self._running    = True
            self._started_at = time.time()
        _log.info(
            "OrderManagementSystem initialised  system_id=%s version=%s",
            OMS_SYSTEM_ID, OMS_VERSION,
        )

    def shutdown(self) -> None:
        """Deactivate the OMS.  Idempotent."""
        with self._lock:
            if not self._running:
                return
            self._running = False
        _log.info("OrderManagementSystem shut down  system_id=%s", OMS_SYSTEM_ID)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def version(self) -> str:
        return OMS_VERSION

    @property
    def system_id(self) -> str:
        return OMS_SYSTEM_ID

    def _require_running(self) -> None:
        if not self._running:
            raise OMSNotInitializedError("OMS is not initialised; call initialize() first")

    # ── Core order operations ─────────────────────────────────────────────────

    def create_order(self, request: OrderRequest) -> Order:
        self._require_running()
        return self._manager.create_order(request)

    def submit_order(self, order_id: str) -> OrderResponse:
        self._require_running()
        return self._manager.submit_order(order_id)

    def acknowledge_order(self, order_id: str) -> Order:
        self._require_running()
        return self._manager.acknowledge_order(order_id)

    def fill_order(
        self,
        order_id: str,
        fill_qty: float,
        fill_price: float,
        *,
        commission: float = 0.0,
        slippage: float   = 0.0,
        venue: str        = "",
    ) -> Order:
        self._require_running()
        return self._manager.fill_order(
            order_id, fill_qty, fill_price,
            commission=commission, slippage=slippage, venue=venue,
        )

    def cancel_order(self, order_id: str, *, reason: str = "") -> OrderResponse:
        self._require_running()
        return self._manager.cancel_order(order_id, reason=reason)

    def reject_order(self, order_id: str, *, reason: str = "") -> Order:
        self._require_running()
        return self._manager.reject_order(order_id, reason=reason)

    def expire_order(self, order_id: str) -> Order:
        self._require_running()
        return self._manager.expire_order(order_id)

    def modify_order(self, order_id: str, changes: dict[str, Any]) -> Order:
        self._require_running()
        return self._manager.modify_order(order_id, changes)

    def requeue_modified_order(self, order_id: str) -> OrderResponse:
        self._require_running()
        return self._manager.requeue_modified_order(order_id)

    def archive_order(self, order_id: str) -> Order:
        self._require_running()
        return self._manager.archive_order(order_id)

    # ── Async variants ────────────────────────────────────────────────────────

    async def create_order_async(self, request: OrderRequest) -> Order:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.create_order, request)

    async def submit_order_async(self, order_id: str) -> OrderResponse:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.submit_order, order_id)

    async def cancel_order_async(self, order_id: str, reason: str = "") -> OrderResponse:
        loop = asyncio.get_running_loop()
        fn   = functools.partial(self.cancel_order, order_id, reason=reason)
        return await loop.run_in_executor(None, fn)

    async def fill_order_async(
        self,
        order_id: str,
        fill_qty: float,
        fill_price: float,
        *,
        commission: float = 0.0,
        venue: str = "",
    ) -> Order:
        loop = asyncio.get_running_loop()
        fn   = functools.partial(
            self.fill_order, order_id, fill_qty, fill_price,
            commission=commission, venue=venue,
        )
        return await loop.run_in_executor(None, fn)

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_order(self, order_id: str) -> Order:
        return self._manager.get_order(order_id)

    def get_orders_by_portfolio(self, portfolio_id: str) -> list[Order]:
        return self._manager.get_orders_by_portfolio(portfolio_id)

    def get_orders_by_strategy(self, strategy_id: str) -> list[Order]:
        return self._manager.get_orders_by_strategy(strategy_id)

    def get_active_orders(self) -> list[Order]:
        return self._manager.get_active_orders()

    def get_fills(self, order_id: str) -> list[OrderExecution]:
        return self._manager.get_fills(order_id)

    def get_transitions(self, order_id: str) -> list:
        return self._manager.get_transitions(order_id)

    # ── Health / stats ────────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        h = self._manager.health()
        h["running"]    = self._running
        h["version"]    = OMS_VERSION
        h["system_id"]  = OMS_SYSTEM_ID
        if self._started_at is not None:
            h["uptime_sec"] = round(time.time() - self._started_at, 2)
        return h

    def stats(self) -> dict[str, Any]:
        return self._manager.statistics()

    # ── Internal access (for testing / advanced use) ──────────────────────────

    @property
    def manager(self) -> OrderManager:
        return self._manager


# ── Singleton helpers ──────────────────────────────────────────────────────────

def get_oms(manager: OrderManager | None = None) -> OrderManagementSystem:
    """Return the module-level OMS singleton, creating and initialising it on
    first call.

    Parameters
    ----------
    manager:
        Optional pre-built ``OrderManager``.  Ignored if the singleton already
        exists.
    """
    global _instance
    with _singleton_lock:
        if _instance is None:
            _instance = OrderManagementSystem(manager)
            _instance.initialize()
    return _instance


def reset_oms() -> None:
    """Tear down and discard the singleton (intended for tests)."""
    global _instance
    with _singleton_lock:
        if _instance is not None:
            _instance.shutdown()
        _instance = None
