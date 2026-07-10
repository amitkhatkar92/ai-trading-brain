"""iios/integration/monitoring/provider_monitor.py

High-level monitor that combines latency, availability, health and statistics.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.integration.core.data_record import DataResponse
from iios.integration.monitoring.availability_monitor import AvailabilityMonitor
from iios.integration.monitoring.health_monitor import HealthMonitor
from iios.integration.monitoring.latency_monitor import LatencyMonitor
from iios.integration.monitoring.provider_statistics import RollingProviderStats


class ProviderMonitor:
    """
    Unified monitoring facade for the integration layer.

    Call observe_response() after every provider fetch.
    Call set_health() when a health_check() result arrives.
    """

    def __init__(
        self,
        health_monitor:       HealthMonitor       | None = None,
        latency_monitor:      LatencyMonitor      | None = None,
        availability_monitor: AvailabilityMonitor | None = None,
    ) -> None:
        self._health       = health_monitor       or HealthMonitor()
        self._latency      = latency_monitor      or LatencyMonitor()
        self._availability = availability_monitor or AvailabilityMonitor()
        self._stats:       dict[str, RollingProviderStats] = {}
        self._lock         = threading.RLock()

    def _get_stats(self, provider_id: str) -> RollingProviderStats:
        with self._lock:
            if provider_id not in self._stats:
                self._stats[provider_id] = RollingProviderStats(provider_id)
            return self._stats[provider_id]

    def observe_response(self, response: DataResponse) -> None:
        """Record the outcome of a provider fetch."""
        pid     = response.provider_id
        success = response.success
        self._latency.record(pid, response.latency_ms)
        self._availability.record(pid, success)
        self._get_stats(pid).record_request(
            success=success,
            latency_ms=response.latency_ms,
            record_count=response.record_count(),
        )

    def observe_error(self, provider_id: str, latency_ms: float = 0.0) -> None:
        self._latency.record(provider_id, latency_ms)
        self._availability.record(provider_id, False)
        self._get_stats(provider_id).record_request(success=False, latency_ms=latency_ms)

    def provider_snapshot(self, provider_id: str) -> dict[str, Any]:
        stats  = self._get_stats(provider_id).snapshot().to_dict()
        health = self._health.get_health(provider_id)
        return {
            "statistics": stats,
            "health": health.to_dict() if health else None,
            "latency": {
                "avg_ms": round(self._latency.avg_latency(provider_id), 2),
                "p95_ms": round(self._latency.p95_latency(provider_id), 2),
                "high":   self._latency.is_high_latency(provider_id),
            },
            "availability": {
                "pct":             round(self._availability.availability(provider_id), 4),
                "below_threshold": self._availability.is_below_threshold(provider_id),
            },
        }

    def all_snapshots(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            ids = list(self._stats.keys())
        return {pid: self.provider_snapshot(pid) for pid in ids}

    @property
    def health(self) -> HealthMonitor:
        return self._health

    @property
    def latency(self) -> LatencyMonitor:
        return self._latency

    @property
    def availability(self) -> AvailabilityMonitor:
        return self._availability

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            provider_count = len(self._stats)
        return {
            "tracked_providers": provider_count,
            "health":            self._health.statistics(),
            "latency":           self._latency.statistics(),
            "availability":      self._availability.statistics(),
        }
