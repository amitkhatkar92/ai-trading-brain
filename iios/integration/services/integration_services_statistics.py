"""
integration_services_statistics.py — iios.integration.services
----------------------------------------------------------------
IntegrationServicesStatistics — collects and reports 10 service-layer
metrics.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from iios.common.logging.logging_manager import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class ServicesStatisticsReport:
    """Immutable snapshot of all 10 statistics metrics."""
    # 10 metrics
    connectors_active:   int
    adapters_loaded:     int
    connections_open:    int
    requests_processed:  int
    messages_delivered:  int
    events_published:    int
    average_latency_ms:  float
    retry_count:         int
    failure_count:       int
    availability:        float     # 0.0 – 1.0

    generated_at: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "connectors_active":   self.connectors_active,
            "adapters_loaded":     self.adapters_loaded,
            "connections_open":    self.connections_open,
            "requests_processed":  self.requests_processed,
            "messages_delivered":  self.messages_delivered,
            "events_published":    self.events_published,
            "average_latency_ms":  round(self.average_latency_ms, 3),
            "retry_count":         self.retry_count,
            "failure_count":       self.failure_count,
            "availability":        round(self.availability, 4),
            "generated_at":        self.generated_at,
        }


class IntegrationServicesStatistics:
    """
    Thread-safe accumulator for 10 integration service metrics.
    """

    def __init__(self) -> None:
        self._lock                = threading.Lock()
        self._connectors_active   = 0
        self._adapters_loaded     = 0
        self._connections_open    = 0
        self._requests_processed  = 0
        self._messages_delivered  = 0
        self._events_published    = 0
        self._total_latency_ms    = 0.0
        self._retry_count         = 0
        self._failure_count       = 0
        self._success_count       = 0

    # ── Mutators ──────────────────────────────────────────────────────────

    def increment_connectors(self, delta: int = 1) -> None:
        with self._lock:
            self._connectors_active = max(0, self._connectors_active + delta)

    def increment_adapters(self, delta: int = 1) -> None:
        with self._lock:
            self._adapters_loaded = max(0, self._adapters_loaded + delta)

    def increment_connections(self, delta: int = 1) -> None:
        with self._lock:
            self._connections_open = max(0, self._connections_open + delta)

    def record_request(
        self,
        success:    bool,
        latency_ms: float,
        retries:    int = 0,
    ) -> None:
        with self._lock:
            self._requests_processed += 1
            self._total_latency_ms   += latency_ms
            self._retry_count        += retries
            if success:
                self._success_count += 1
            else:
                self._failure_count += 1

    def record_message(self) -> None:
        with self._lock:
            self._messages_delivered += 1

    def record_event(self) -> None:
        with self._lock:
            self._events_published += 1

    # ── Snapshot ──────────────────────────────────────────────────────────

    def snapshot(self) -> ServicesStatisticsReport:
        with self._lock:
            total = self._requests_processed
            avg   = (self._total_latency_ms / total) if total else 0.0
            avail = (self._success_count / total)     if total else 1.0
            return ServicesStatisticsReport(
                connectors_active  = self._connectors_active,
                adapters_loaded    = self._adapters_loaded,
                connections_open   = self._connections_open,
                requests_processed = self._requests_processed,
                messages_delivered = self._messages_delivered,
                events_published   = self._events_published,
                average_latency_ms = avg,
                retry_count        = self._retry_count,
                failure_count      = self._failure_count,
                availability       = avail,
                generated_at       = datetime.now(timezone.utc).isoformat(),
            )

    def reset(self) -> None:
        with self._lock:
            self._connectors_active   = 0
            self._adapters_loaded     = 0
            self._connections_open    = 0
            self._requests_processed  = 0
            self._messages_delivered  = 0
            self._events_published    = 0
            self._total_latency_ms    = 0.0
            self._retry_count         = 0
            self._failure_count       = 0
            self._success_count       = 0
