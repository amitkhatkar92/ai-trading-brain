"""iios/integration/news/monitoring/news_monitor.py

Polls provider health_check() on a background thread and raises alerts
when any provider exceeds configured error or latency thresholds.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from iios.integration.news.providers.base_news_provider import BaseNewsProvider
from iios.integration.news.providers.provider_health   import NewsProviderHealth

logger = logging.getLogger(__name__)

AlertCallback = Callable[[str, NewsProviderHealth], None]


class NewsMonitor:
    """
    Background health monitor for registered news providers.

    The monitor calls ``health_check()`` on each provider every
    ``poll_interval_sec`` seconds and invokes registered alert callbacks
    when a provider appears unhealthy.
    """

    def __init__(
        self,
        poll_interval_sec: int = 60,
        max_latency_ms:    float = 5_000.0,
    ) -> None:
        self._interval  = poll_interval_sec
        self._max_lat   = max_latency_ms
        self._lock      = threading.RLock()
        self._providers: dict[str, BaseNewsProvider] = {}
        self._health:    dict[str, NewsProviderHealth] = {}
        self._callbacks: list[AlertCallback] = []
        self._thread:    threading.Thread | None = None
        self._stop_event = threading.Event()
        self._stats: dict[str, int] = {"polls": 0, "alerts": 0, "errors": 0}

    # ── Provider management ───────────────────────────────────────────────────

    def register(self, provider: BaseNewsProvider) -> None:
        with self._lock:
            self._providers[provider.provider_id] = provider

    def unregister(self, provider_id: str) -> None:
        with self._lock:
            self._providers.pop(provider_id, None)
            self._health.pop(provider_id, None)

    def on_alert(self, callback: AlertCallback) -> None:
        self._callbacks.append(callback)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="NewsMonitor")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    # ── Public query ─────────────────────────────────────────────────────────

    def get_health(self, provider_id: str) -> NewsProviderHealth | None:
        with self._lock:
            return self._health.get(provider_id)

    def all_health(self) -> dict[str, NewsProviderHealth]:
        with self._lock:
            return dict(self._health)

    def stats(self) -> dict[str, Any]:
        return dict(self._stats)

    # ── Background loop ───────────────────────────────────────────────────────

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._poll_all()
            self._stop_event.wait(self._interval)

    def _poll_all(self) -> None:
        with self._lock:
            providers = dict(self._providers)

        for pid, prov in providers.items():
            try:
                health = prov.health_check()
                with self._lock:
                    self._health[pid] = health
                self._stats["polls"] += 1

                if not health.is_healthy() or health.latency_ms > self._max_lat:
                    self._fire_alert(pid, health)

            except Exception as exc:
                self._stats["errors"] += 1
                logger.warning("[NewsMonitor] health_check failed for '%s': %s", pid, exc)

    def _fire_alert(self, provider_id: str, health: NewsProviderHealth) -> None:
        self._stats["alerts"] += 1
        logger.warning("[NewsMonitor] Alert for provider '%s': healthy=%s latency=%.1fms",
                       provider_id, health.is_healthy(), health.latency_ms)
        for cb in self._callbacks:
            try:
                cb(provider_id, health)
            except Exception as exc:
                logger.warning("[NewsMonitor] Alert callback error: %s", exc)
