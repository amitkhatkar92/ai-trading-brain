"""iios/execution/brokers/monitoring/broker_monitor.py"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from iios.execution.brokers.connection.connection_health import ConnectionHealth
from iios.execution.brokers.core.base_broker_adapter import BaseBrokerAdapter

logger = logging.getLogger(__name__)


class BrokerMonitor:
    """
    Manages health-check probes for all registered broker adapters.

    Keeps the latest ConnectionHealth snapshot for each broker.
    Async health checks are run synchronously via a dedicated event loop
    so the monitor stays thread-safe.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, BaseBrokerAdapter] = {}
        self._health:   dict[str, ConnectionHealth]  = {}
        self._lock      = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, adapter: BaseBrokerAdapter) -> None:
        with self._lock:
            self._adapters[adapter.broker_id] = adapter

    def unregister(self, broker_id: str) -> None:
        with self._lock:
            self._adapters.pop(broker_id, None)
            self._health.pop(broker_id, None)

    # ── Health snapshots ──────────────────────────────────────────────────────

    def get_health(self, broker_id: str) -> ConnectionHealth | None:
        with self._lock:
            return self._health.get(broker_id)

    def all_health(self) -> dict[str, ConnectionHealth]:
        with self._lock:
            return dict(self._health)

    # ── Probe ─────────────────────────────────────────────────────────────────

    async def check_health_async(self, broker_id: str) -> ConnectionHealth:
        """Run one health-check cycle for *broker_id* (async)."""
        with self._lock:
            adapter = self._adapters.get(broker_id)
        if adapter is None:
            return ConnectionHealth.unhealthy(broker_id, "adapter not registered")
        t0 = time.time()
        try:
            response   = await adapter.health_check()
            latency_ms = (time.time() - t0) * 1_000
            if response.success:
                health = ConnectionHealth.healthy(
                    broker_id, response_time_ms=latency_ms
                )
            else:
                health = ConnectionHealth.unhealthy(
                    broker_id, response.error_message
                )
        except Exception as exc:
            latency_ms = (time.time() - t0) * 1_000
            health     = ConnectionHealth.unhealthy(broker_id, str(exc))
        with self._lock:
            self._health[broker_id] = health
        return health

    def check_health(self, broker_id: str) -> ConnectionHealth:
        """Synchronous wrapper around check_health_async."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                future = asyncio.run_coroutine_threadsafe(
                    self.check_health_async(broker_id), loop
                )
                return future.result(timeout=30.0)
            else:
                return loop.run_until_complete(self.check_health_async(broker_id))
        except Exception as exc:
            return ConnectionHealth.unhealthy(broker_id, str(exc))

    async def check_all_async(self) -> dict[str, ConnectionHealth]:
        with self._lock:
            broker_ids = list(self._adapters.keys())
        results = {}
        for bid in broker_ids:
            results[bid] = await self.check_health_async(bid)
        return results

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total   = len(self._adapters)
            healthy = sum(1 for h in self._health.values() if h.is_healthy)
            return {
                "registered": total,
                "healthy":    healthy,
                "unhealthy":  total - healthy,
                "checked":    len(self._health),
            }
