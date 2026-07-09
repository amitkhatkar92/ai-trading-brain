"""iios/execution/brokers/connection/connection_monitor.py"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from iios.execution.brokers.broker_constants import DEFAULT_HEARTBEAT_INTERVAL_SEC
from iios.execution.brokers.connection.connection_health import ConnectionHealth

logger = logging.getLogger(__name__)

HealthCheckFn = Callable[[str], ConnectionHealth]


class ConnectionMonitor:
    """
    Periodically polls registered broker adapters and tracks their health.

    Consumers register (broker_id, health_check_fn) pairs.  The monitor
    runs a background thread that calls each function at *interval_sec* and
    stores the result.  Callers can read snapshots at any time without
    blocking.
    """

    def __init__(self, interval_sec: float = DEFAULT_HEARTBEAT_INTERVAL_SEC) -> None:
        self._interval_sec   = interval_sec
        self._health_fns:    dict[str, HealthCheckFn] = {}
        self._latest_health: dict[str, ConnectionHealth] = {}
        self._lock           = threading.RLock()
        self._running        = False
        self._thread:        threading.Thread | None = None

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, broker_id: str, health_fn: HealthCheckFn) -> None:
        with self._lock:
            self._health_fns[broker_id] = health_fn
            logger.debug("ConnectionMonitor: registered broker %s", broker_id)

    def unregister(self, broker_id: str) -> None:
        with self._lock:
            self._health_fns.pop(broker_id, None)
            self._latest_health.pop(broker_id, None)

    # ── Health snapshot ───────────────────────────────────────────────────────

    def get_health(self, broker_id: str) -> ConnectionHealth | None:
        with self._lock:
            return self._latest_health.get(broker_id)

    def all_health(self) -> dict[str, ConnectionHealth]:
        with self._lock:
            return dict(self._latest_health)

    def healthy_broker_ids(self) -> list[str]:
        with self._lock:
            return [
                bid for bid, h in self._latest_health.items() if h.is_healthy
            ]

    # ── Background loop ───────────────────────────────────────────────────────

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            name="ConnectionMonitor",
            daemon=True,
        )
        self._thread.start()
        logger.info("ConnectionMonitor started (interval=%.1fs)", self._interval_sec)

    def stop(self) -> None:
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("ConnectionMonitor stopped")

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
                broker_ids = list(self._health_fns.keys())
            for bid in broker_ids:
                self._poll_one(bid)
            time.sleep(self._interval_sec)

    def _poll_one(self, broker_id: str) -> None:
        with self._lock:
            fn = self._health_fns.get(broker_id)
        if fn is None:
            return
        try:
            health = fn(broker_id)
            with self._lock:
                self._latest_health[broker_id] = health
        except Exception as exc:
            logger.warning("Health check failed for broker %s: %s", broker_id, exc)
            with self._lock:
                self._latest_health[broker_id] = ConnectionHealth.unhealthy(
                    broker_id, str(exc)
                )

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            total   = len(self._health_fns)
            healthy = sum(1 for h in self._latest_health.values() if h.is_healthy)
            return {
                "registered": total,
                "healthy":    healthy,
                "unhealthy":  total - healthy,
                "is_running": self._running,
                "interval_sec": self._interval_sec,
            }
