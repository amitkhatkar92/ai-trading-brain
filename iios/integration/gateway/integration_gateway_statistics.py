"""
integration_gateway_statistics.py — iios.integration.gateway
--------------------------------------------------------------
IntegrationStatistics (frozen report) and IntegrationGatewayStatistics
(thread-safe accumulator).

C15 Enterprise Integration & Connectivity — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class IntegrationStatistics:
    """
    Immutable statistics report returned by the public ``statistics()`` API.
    """
    gateway_requests:           int
    successful_requests:        int
    failed_requests:            int
    rejected_requests:          int
    snapshot_publications:      int
    average_processing_time_ms: float
    average_response_time_ms:   float
    gateway_availability:       float   # ratio: successful / total (0.0–1.0)
    generated_at:               str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "gateway_requests":           self.gateway_requests,
            "successful_requests":        self.successful_requests,
            "failed_requests":            self.failed_requests,
            "rejected_requests":          self.rejected_requests,
            "snapshot_publications":      self.snapshot_publications,
            "average_processing_time_ms": round(self.average_processing_time_ms, 3),
            "average_response_time_ms":   round(self.average_response_time_ms, 3),
            "gateway_availability":       round(self.gateway_availability, 6),
            "generated_at":               self.generated_at,
        }


class IntegrationGatewayStatistics:
    """
    Thread-safe accumulator for gateway operation metrics.
    Call ``snapshot()`` to produce an IntegrationStatistics report.
    """

    def __init__(self) -> None:
        self._gateway_requests:      int   = 0
        self._successful_requests:   int   = 0
        self._failed_requests:       int   = 0
        self._rejected_requests:     int   = 0
        self._snapshot_publications: int   = 0
        self._total_processing_ms:   float = 0.0
        self._total_response_ms:     float = 0.0
        self._processing_count:      int   = 0
        self._response_count:        int   = 0
        self._lock = threading.Lock()

    # ─── increment methods ────────────────────────────────────────────

    def increment_request(self, n: int = 1) -> None:
        with self._lock:
            self._gateway_requests += n

    def increment_success(self, n: int = 1) -> None:
        with self._lock:
            self._successful_requests += n

    def increment_failed(self, n: int = 1) -> None:
        with self._lock:
            self._failed_requests += n

    def increment_rejected(self, n: int = 1) -> None:
        with self._lock:
            self._rejected_requests += n

    def increment_snapshot_publications(self, n: int = 1) -> None:
        with self._lock:
            self._snapshot_publications += n

    def record_processing_time(self, ms: float) -> None:
        with self._lock:
            self._total_processing_ms += ms
            self._processing_count    += 1

    def record_response_time(self, ms: float) -> None:
        with self._lock:
            self._total_response_ms += ms
            self._response_count    += 1

    # ─── report ───────────────────────────────────────────────────────

    def snapshot(self) -> IntegrationStatistics:
        with self._lock:
            total   = self._gateway_requests
            success = self._successful_requests
            avail   = (success / total) if total > 0 else 1.0

            avg_proc = (
                self._total_processing_ms / self._processing_count
                if self._processing_count > 0 else 0.0
            )
            avg_resp = (
                self._total_response_ms / self._response_count
                if self._response_count > 0 else 0.0
            )

            return IntegrationStatistics(
                gateway_requests           = total,
                successful_requests        = success,
                failed_requests            = self._failed_requests,
                rejected_requests          = self._rejected_requests,
                snapshot_publications      = self._snapshot_publications,
                average_processing_time_ms = avg_proc,
                average_response_time_ms   = avg_resp,
                gateway_availability       = avail,
                generated_at               = datetime.now(timezone.utc).isoformat(),
            )

    def reset(self) -> None:
        with self._lock:
            self._gateway_requests      = 0
            self._successful_requests   = 0
            self._failed_requests       = 0
            self._rejected_requests     = 0
            self._snapshot_publications = 0
            self._total_processing_ms   = 0.0
            self._total_response_ms     = 0.0
            self._processing_count      = 0
            self._response_count        = 0
