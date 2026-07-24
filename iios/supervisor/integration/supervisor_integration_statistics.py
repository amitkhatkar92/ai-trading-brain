"""
supervisor_integration_statistics.py — iios.supervisor.integration
-------------------------------------------------------------------
Thread-safe accumulator for AI Supervisor Integration metrics.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class SupervisorIntegrationStatistics:
    """
    Thread-safe accumulator for integration-layer operational metrics.

    Tracks request counts, outcome counts, timing averages,
    snapshot publications, and availability.
    """

    _lock:                  threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    _integration_requests:  int   = field(default=0, init=False)
    _successful:            int   = field(default=0, init=False)
    _failed:                int   = field(default=0, init=False)
    _snapshot_publications: int   = field(default=0, init=False)

    _total_processing_s:    float = field(default=0.0, init=False)
    _total_response_s:      float = field(default=0.0, init=False)

    _started_at:            float = field(default_factory=time.time, init=False)

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def record_integration_started(self) -> None:
        with self._lock:
            self._integration_requests += 1

    def record_success(self, processing_time_s: float = 0.0) -> None:
        with self._lock:
            self._successful += 1
            self._total_processing_s += max(0.0, processing_time_s)
            self._total_response_s   += max(0.0, processing_time_s)

    def record_failure(self, processing_time_s: float = 0.0) -> None:
        with self._lock:
            self._failed += 1
            self._total_response_s += max(0.0, processing_time_s)

    def record_snapshot_publication(self) -> None:
        with self._lock:
            self._snapshot_publications += 1

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def integration_requests(self) -> int:
        with self._lock:
            return self._integration_requests

    @property
    def successful_integrations(self) -> int:
        with self._lock:
            return self._successful

    @property
    def failed_integrations(self) -> int:
        with self._lock:
            return self._failed

    @property
    def snapshot_publications(self) -> int:
        with self._lock:
            return self._snapshot_publications

    @property
    def average_processing_time_s(self) -> float:
        with self._lock:
            return (
                self._total_processing_s / self._successful
                if self._successful > 0
                else 0.0
            )

    @property
    def average_response_time_s(self) -> float:
        with self._lock:
            total = self._successful + self._failed
            return self._total_response_s / total if total > 0 else 0.0

    @property
    def platform_availability(self) -> float:
        """Fraction of completed integrations that succeeded [0.0–1.0]."""
        with self._lock:
            total = self._successful + self._failed
            return self._successful / total if total > 0 else 1.0

    # ------------------------------------------------------------------
    # Snapshot / reset
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return a point-in-time copy of all metrics as a plain dict."""
        with self._lock:
            return {
                "integration_requests":      self._integration_requests,
                "successful_integrations":   self._successful,
                "failed_integrations":       self._failed,
                "snapshot_publications":     self._snapshot_publications,
                "average_processing_time_s": (
                    self._total_processing_s / self._successful
                    if self._successful > 0 else 0.0
                ),
                "average_response_time_s": (
                    self._total_response_s / (self._successful + self._failed)
                    if (self._successful + self._failed) > 0 else 0.0
                ),
                "platform_availability": (
                    self._successful / (self._successful + self._failed)
                    if (self._successful + self._failed) > 0 else 1.0
                ),
                "uptime_s": time.time() - self._started_at,
            }

    def reset(self) -> None:
        """Reset all counters to zero (test / maintenance use only)."""
        with self._lock:
            self._integration_requests  = 0
            self._successful            = 0
            self._failed                = 0
            self._snapshot_publications = 0
            self._total_processing_s    = 0.0
            self._total_response_s      = 0.0
            self._started_at            = time.time()
