"""iios/execution/brokers/broker_manager.py

Top-level orchestrator.  Combines AdapterRegistry + BrokerRegistry +
BrokerFactory + BrokerMonitor into a single coherent API.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from iios.execution.brokers.broker_constants import DEFAULT_MAX_BROKERS
from iios.execution.brokers.broker_exceptions import (
    BrokerManagerNotInitializedError,
    BrokerNotConnectedError,
    BrokerNotFoundError,
)
from iios.execution.brokers.broker_factory import BrokerFactory
from iios.execution.brokers.broker_registry import BrokerRegistry
from iios.execution.brokers.connection.connection_health import ConnectionHealth
from iios.execution.brokers.core.base_broker_adapter import (
    BaseBrokerAdapter,
    BrokerAdapterConfig,
)
from iios.execution.brokers.core.broker_request import BrokerRequest
from iios.execution.brokers.core.broker_response import BrokerResponse
from iios.execution.brokers.models.broker_metadata import BrokerMetadata
from iios.execution.brokers.models.broker_statistics import BrokerStatistics
from iios.execution.brokers.monitoring.broker_monitor import BrokerMonitor

logger = logging.getLogger(__name__)

_manager_lock: threading.Lock = threading.Lock()
_manager_instance: BrokerManager | None = None


class BrokerManager:
    """
    Primary entry point for all broker operations.

    Responsibilities:
    - Register / unregister adapter classes
    - Load / unload live adapter instances
    - Route async calls (place_order, fetch_positions, …) to the correct adapter
    - Monitor adapter health
    - Maintain per-adapter statistics
    """

    def __init__(
        self,
        broker_registry: BrokerRegistry | None = None,
        broker_factory:  BrokerFactory  | None = None,
        broker_monitor:  BrokerMonitor  | None = None,
    ) -> None:
        self._registry  = broker_registry or BrokerRegistry()
        self._factory   = broker_factory  or BrokerFactory()
        self._monitor   = broker_monitor  or BrokerMonitor()
        self._statistics: dict[str, BrokerStatistics] = {}
        self._lock      = threading.RLock()
        self._started_at = time.time()

    # ── Adapter class management ──────────────────────────────────────────────

    def register_adapter_class(
        self,
        broker_id:     str,
        adapter_class: type[BaseBrokerAdapter],
        version:       str           = "1.0.0",
        metadata:      BrokerMetadata | None = None,
    ) -> None:
        self._factory.register_class(broker_id, adapter_class, metadata)
        logger.info("BrokerManager: registered adapter class '%s'", broker_id)

    # ── Adapter instance lifecycle ────────────────────────────────────────────

    def load_adapter(
        self,
        broker_id: str,
        config:    BrokerAdapterConfig | None = None,
        overwrite: bool = False,
    ) -> BaseBrokerAdapter:
        adapter = self._factory.create(broker_id, config)
        self._registry.register(adapter, overwrite=overwrite)
        with self._lock:
            self._statistics[broker_id] = BrokerStatistics(broker_id=broker_id)
        self._monitor.register(adapter)
        logger.info("BrokerManager: loaded adapter '%s'", broker_id)
        return adapter

    def unload_adapter(self, broker_id: str) -> None:
        self._registry.unregister(broker_id)
        self._monitor.unregister(broker_id)
        with self._lock:
            self._statistics.pop(broker_id, None)
        logger.info("BrokerManager: unloaded adapter '%s'", broker_id)

    def get_adapter(self, broker_id: str) -> BaseBrokerAdapter:
        return self._registry.get(broker_id)

    def list_broker_ids(self) -> list[str]:
        return self._registry.all_broker_ids()

    def has_adapter(self, broker_id: str) -> bool:
        return self._registry.has(broker_id)

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(
        self,
        broker_id:   str,
        credentials: dict[str, Any] = {},
    ) -> BrokerResponse:
        adapter = self._get_or_raise(broker_id)
        t0 = time.time()
        response = await adapter.connect()
        if response.success and credentials:
            response = await adapter.authenticate(credentials)
        self._record(broker_id, response.success, (time.time() - t0) * 1_000)
        return response

    async def disconnect(self, broker_id: str) -> BrokerResponse:
        adapter = self._get_or_raise(broker_id)
        t0      = time.time()
        response = await adapter.disconnect()
        self._record(broker_id, response.success, (time.time() - t0) * 1_000)
        return response

    # ── Orders ────────────────────────────────────────────────────────────────

    async def place_order(
        self, broker_id: str, request: BrokerRequest
    ) -> BrokerResponse:
        return await self._dispatch(broker_id, "place_order", request)

    async def modify_order(
        self, broker_id: str, request: BrokerRequest
    ) -> BrokerResponse:
        return await self._dispatch(broker_id, "modify_order", request)

    async def cancel_order(
        self, broker_id: str, request: BrokerRequest
    ) -> BrokerResponse:
        return await self._dispatch(broker_id, "cancel_order", request)

    async def fetch_order(
        self, broker_id: str, request: BrokerRequest
    ) -> BrokerResponse:
        return await self._dispatch(broker_id, "fetch_order", request)

    async def fetch_orders(
        self, broker_id: str, request: BrokerRequest
    ) -> BrokerResponse:
        return await self._dispatch(broker_id, "fetch_orders", request)

    # ── Portfolio ─────────────────────────────────────────────────────────────

    async def fetch_positions(
        self, broker_id: str, request: BrokerRequest
    ) -> BrokerResponse:
        return await self._dispatch(broker_id, "fetch_positions", request)

    async def fetch_holdings(
        self, broker_id: str, request: BrokerRequest
    ) -> BrokerResponse:
        return await self._dispatch(broker_id, "fetch_holdings", request)

    async def fetch_balance(
        self, broker_id: str, request: BrokerRequest
    ) -> BrokerResponse:
        return await self._dispatch(broker_id, "fetch_balance", request)

    async def fetch_margin(
        self, broker_id: str, request: BrokerRequest
    ) -> BrokerResponse:
        return await self._dispatch(broker_id, "fetch_margin", request)

    async def fetch_trades(
        self, broker_id: str, request: BrokerRequest
    ) -> BrokerResponse:
        return await self._dispatch(broker_id, "fetch_trades", request)

    # ── Health ────────────────────────────────────────────────────────────────

    async def health_check(self, broker_id: str) -> ConnectionHealth:
        return await self._monitor.check_health_async(broker_id)

    async def health_check_all(self) -> dict[str, ConnectionHealth]:
        return await self._monitor.check_all_async()

    # ── Statistics ────────────────────────────────────────────────────────────

    def get_statistics(self, broker_id: str) -> BrokerStatistics | None:
        with self._lock:
            return self._statistics.get(broker_id)

    def all_statistics(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {bid: s.to_dict() for bid, s in self._statistics.items()}

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "broker_count": self._registry.size(),
                "broker_ids":   self._registry.all_broker_ids(),
                "uptime_sec":   round(time.time() - self._started_at, 1),
                "statistics":   {
                    bid: s.to_dict() for bid, s in self._statistics.items()
                },
            }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_or_raise(self, broker_id: str) -> BaseBrokerAdapter:
        return self._registry.get(broker_id)

    async def _dispatch(
        self,
        broker_id: str,
        method:    str,
        request:   BrokerRequest,
    ) -> BrokerResponse:
        adapter = self._get_or_raise(broker_id)
        fn      = getattr(adapter, method)
        t0      = time.time()
        response = await fn(request)
        self._record(broker_id, response.success, (time.time() - t0) * 1_000)
        return response

    def _record(
        self, broker_id: str, success: bool, latency_ms: float
    ) -> None:
        with self._lock:
            stats = self._statistics.get(broker_id)
            if stats:
                stats.record_request(success, latency_ms)


# ── Singleton ─────────────────────────────────────────────────────────────────

def get_broker_manager() -> BrokerManager:
    global _manager_instance
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = BrokerManager()
    return _manager_instance


def reset_broker_manager() -> None:
    global _manager_instance
    with _manager_lock:
        _manager_instance = None
