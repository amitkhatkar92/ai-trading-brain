"""iios/integration/monitoring/health_monitor.py

Periodically calls provider.health_check() and maintains ProviderHealth store.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from iios.integration.integration_constants import (
    DEFAULT_HEALTH_CHECK_INTERVAL_SEC,
    DEFAULT_HEALTH_CHECK_TIMEOUT_SEC,
)
from iios.integration.providers.provider_health import ProviderHealth
from iios.integration.providers.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class HealthMonitor:
    """
    Stores latest ProviderHealth snapshots and optionally runs periodic checks.

    Manual mode: call refresh_provider(provider_id) explicitly.
    Auto mode:   start() to begin background polling (requires async event loop).
    """

    def __init__(
        self,
        registry:           ProviderRegistry | None = None,
        check_interval_sec: float = DEFAULT_HEALTH_CHECK_INTERVAL_SEC,
        check_timeout_sec:  float = DEFAULT_HEALTH_CHECK_TIMEOUT_SEC,
    ) -> None:
        self._registry  = registry
        self._interval  = check_interval_sec
        self._timeout   = check_timeout_sec
        self._health:   dict[str, ProviderHealth] = {}
        self._lock      = threading.RLock()
        self._running   = False

    # ── Manual refresh ────────────────────────────────────────────────────────

    async def refresh_provider(self, provider_id: str) -> ProviderHealth | None:
        if self._registry is None:
            return None
        try:
            provider = self._registry.get(provider_id)
            health   = await asyncio.wait_for(
                provider.health_check(), timeout=self._timeout
            )
            with self._lock:
                self._health[provider_id] = health
            return health
        except Exception as exc:
            logger.warning("HealthMonitor: check failed for '%s': %s", provider_id, exc)
            return None

    async def refresh_all(self) -> dict[str, ProviderHealth]:
        if self._registry is None:
            return {}
        tasks  = {}
        for p in self._registry.all_providers():
            tasks[p.provider_id] = self.refresh_provider(p.provider_id)
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return {pid: r for pid, r in zip(tasks.keys(), results) if isinstance(r, ProviderHealth)}

    # ── Store ─────────────────────────────────────────────────────────────────

    def set_health(self, health: ProviderHealth) -> None:
        with self._lock:
            self._health[health.provider_id] = health

    def get_health(self, provider_id: str) -> ProviderHealth | None:
        with self._lock:
            return self._health.get(provider_id)

    def all_health(self) -> dict[str, ProviderHealth]:
        with self._lock:
            return dict(self._health)

    def unhealthy_providers(self) -> list[str]:
        with self._lock:
            return [pid for pid, h in self._health.items() if not h.is_healthy()]

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._health)
            healthy = sum(1 for h in self._health.values() if h.is_healthy())
            return {
                "total_tracked": total,
                "healthy":       healthy,
                "unhealthy":     total - healthy,
                "running":       self._running,
            }
