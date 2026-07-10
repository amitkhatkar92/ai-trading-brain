"""iios/integration/market_data/monitoring/market_data_monitor.py

Monitors all registered providers and aggregates health metrics.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from iios.integration.market_data.providers.provider_health import ProviderHealth

logger = logging.getLogger(__name__)


class MarketDataMonitor:
    """
    Polls provider health_check() at a configurable interval.

    Stores the latest ProviderHealth per provider_id and exposes
    aggregated system health.
    """

    def __init__(self, poll_interval_sec: float = 30.0) -> None:
        self._poll_interval  = poll_interval_sec
        self._lock           = threading.RLock()
        self._latest:        dict[str, ProviderHealth] = {}
        self._providers:     dict[str, Any] = {}   # id → BaseMarketDataProvider
        self._running        = False
        self._poll_task:     asyncio.Task | None = None  # type: ignore[type-arg]
        self._stats: dict[str, int] = {"polls": 0, "errors": 0}

    # ── Provider registration ──────────────────────────────────────────────────

    def register_provider(self, provider: Any) -> None:
        with self._lock:
            self._providers[provider.provider_id] = provider

    def unregister_provider(self, provider_id: str) -> None:
        with self._lock:
            self._providers.pop(provider_id, None)
            self._latest.pop(provider_id, None)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._poll_task = asyncio.ensure_future(self._poll_loop())

    async def stop(self) -> None:
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

    # ── Health access ─────────────────────────────────────────────────────────

    def get_health(self, provider_id: str) -> ProviderHealth | None:
        with self._lock:
            return self._latest.get(provider_id)

    def all_health(self) -> dict[str, ProviderHealth]:
        with self._lock:
            return dict(self._latest)

    def is_all_healthy(self) -> bool:
        with self._lock:
            if not self._latest:
                return False
            return all(h.is_healthy() for h in self._latest.values())

    def unhealthy_providers(self) -> list[str]:
        with self._lock:
            return [pid for pid, h in self._latest.items() if not h.is_healthy()]

    # ── Stats ──────────────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._providers)
            healthy = sum(1 for h in self._latest.values() if h.is_healthy())
            return {
                **self._stats,
                "provider_count": total,
                "healthy":        healthy,
                "unhealthy":      total - healthy,
            }

    # ── Internals ─────────────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        while self._running:
            await self._poll_all()
            await asyncio.sleep(self._poll_interval)

    async def _poll_all(self) -> None:
        with self._lock:
            providers = list(self._providers.values())

        tasks = [self._poll_one(p) for p in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                self._stats["errors"] += 1
                logger.warning("[MarketDataMonitor] Poll error: %s", r)
        self._stats["polls"] += 1

    async def _poll_one(self, provider: Any) -> None:
        try:
            health = await provider.health_check()
            with self._lock:
                self._latest[provider.provider_id] = health
        except Exception as exc:
            with self._lock:
                self._latest[provider.provider_id] = ProviderHealth(
                    provider_id  = provider.provider_id,
                    is_connected = False,
                    last_error   = str(exc),
                    checked_at   = time.time(),
                )
            raise
