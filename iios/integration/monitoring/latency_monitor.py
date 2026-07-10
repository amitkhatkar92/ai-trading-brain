"""iios/integration/monitoring/latency_monitor.py"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any

from iios.integration.integration_constants import DEFAULT_HIGH_LATENCY_WARNING_MS, DEFAULT_HIGH_LATENCY_CRITICAL_MS


class LatencyMonitor:
    """
    Tracks fetch latencies per provider.
    Raises flags when thresholds are breached.
    Thread-safe.
    """

    def __init__(
        self,
        warning_ms:  float = DEFAULT_HIGH_LATENCY_WARNING_MS,
        critical_ms: float = DEFAULT_HIGH_LATENCY_CRITICAL_MS,
        window:      int   = 100,
    ) -> None:
        self._warning_ms  = warning_ms
        self._critical_ms = critical_ms
        self._window      = window
        self._data:  dict[str, deque[float]] = {}
        self._lock   = threading.RLock()

    def record(self, provider_id: str, latency_ms: float) -> None:
        with self._lock:
            if provider_id not in self._data:
                self._data[provider_id] = deque(maxlen=self._window)
            self._data[provider_id].append(latency_ms)

    def avg_latency(self, provider_id: str) -> float:
        with self._lock:
            vals = list(self._data.get(provider_id, []))
        return sum(vals) / len(vals) if vals else 0.0

    def p95_latency(self, provider_id: str) -> float:
        with self._lock:
            vals = sorted(self._data.get(provider_id, []))
        if not vals:
            return 0.0
        idx = int(len(vals) * 0.95)
        return vals[min(idx, len(vals) - 1)]

    def is_high_latency(self, provider_id: str) -> bool:
        return self.avg_latency(provider_id) >= self._warning_ms

    def is_critical_latency(self, provider_id: str) -> bool:
        return self.avg_latency(provider_id) >= self._critical_ms

    def all_provider_ids(self) -> list[str]:
        with self._lock:
            return list(self._data.keys())

    def statistics(self) -> dict[str, Any]:
        result = {}
        for pid in self.all_provider_ids():
            result[pid] = {
                "avg_ms": round(self.avg_latency(pid), 2),
                "p95_ms": round(self.p95_latency(pid), 2),
                "high":   self.is_high_latency(pid),
            }
        return result
