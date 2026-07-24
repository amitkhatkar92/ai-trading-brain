"""
knowledge_integration_statistics.py — iios.knowledge.integration
-----------------------------------------------------------------
Thread-safe counters tracking integration system activity.

8 statistics metrics matching the spec:
  1. integration_requests
  2. successful_integrations
  3. failed_integrations
  4. knowledge_publications
  5. snapshot_publications
  6. total_processing_time_ms  (used to compute average)
  7. total_response_time_ms    (used to compute average)
  8. knowledge_availability    (float 0.0–1.0, moving window)

C14 Enterprise Knowledge Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class KnowledgeStatistics:
    """Point-in-time statistics report for the integration system."""
    integration_requests:     int
    successful_integrations:  int
    failed_integrations:      int
    knowledge_publications:   int
    snapshot_publications:    int
    average_processing_time_ms: float
    average_response_time_ms:   float
    knowledge_availability:   float   # 0.0–1.0
    captured_at:              str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_requests":     self.integration_requests,
            "successful_integrations":  self.successful_integrations,
            "failed_integrations":      self.failed_integrations,
            "knowledge_publications":   self.knowledge_publications,
            "snapshot_publications":    self.snapshot_publications,
            "average_processing_time_ms": self.average_processing_time_ms,
            "average_response_time_ms":   self.average_response_time_ms,
            "knowledge_availability":   self.knowledge_availability,
            "captured_at":              self.captured_at,
        }


class KnowledgeIntegrationStatistics:
    """Thread-safe rolling statistics for the integration engine."""

    def __init__(self) -> None:
        self._lock                        = threading.Lock()
        self._integration_requests        = 0
        self._successful_integrations     = 0
        self._failed_integrations         = 0
        self._knowledge_publications      = 0
        self._snapshot_publications       = 0
        self._total_processing_time_ms    = 0.0
        self._total_response_time_ms      = 0.0
        # Sliding availability: ratio of successful to total
        # Computed from success/total at report() time

    # ----------------------------------------------------------------
    # Increment
    # ----------------------------------------------------------------

    def record_request(self) -> None:
        with self._lock:
            self._integration_requests += 1

    def record_success(
        self,
        *,
        processing_ms: float = 0.0,
        response_ms:   float = 0.0,
    ) -> None:
        with self._lock:
            self._successful_integrations  += 1
            self._total_processing_time_ms += processing_ms
            self._total_response_time_ms   += response_ms

    def record_failure(self) -> None:
        with self._lock:
            self._failed_integrations += 1

    def record_knowledge_publication(self) -> None:
        with self._lock:
            self._knowledge_publications += 1

    def record_snapshot_publication(self) -> None:
        with self._lock:
            self._snapshot_publications += 1

    # ----------------------------------------------------------------
    # Report
    # ----------------------------------------------------------------

    def report(self) -> KnowledgeStatistics:
        with self._lock:
            total_completed = (
                self._successful_integrations + self._failed_integrations
            )
            avg_proc = (
                self._total_processing_time_ms / total_completed
                if total_completed > 0 else 0.0
            )
            avg_resp = (
                self._total_response_time_ms / total_completed
                if total_completed > 0 else 0.0
            )
            availability = (
                self._successful_integrations / total_completed
                if total_completed > 0 else 1.0
            )
            return KnowledgeStatistics(
                integration_requests     = self._integration_requests,
                successful_integrations  = self._successful_integrations,
                failed_integrations      = self._failed_integrations,
                knowledge_publications   = self._knowledge_publications,
                snapshot_publications    = self._snapshot_publications,
                average_processing_time_ms = round(avg_proc, 3),
                average_response_time_ms   = round(avg_resp, 3),
                knowledge_availability   = round(availability, 4),
                captured_at              = datetime.now(tz=timezone.utc).isoformat(),
            )

    def reset(self) -> None:
        with self._lock:
            self._integration_requests     = 0
            self._successful_integrations  = 0
            self._failed_integrations      = 0
            self._knowledge_publications   = 0
            self._snapshot_publications    = 0
            self._total_processing_time_ms = 0.0
            self._total_response_time_ms   = 0.0
