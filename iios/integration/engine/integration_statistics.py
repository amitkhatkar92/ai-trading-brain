"""
integration_statistics.py — iios.integration.engine
-----------------------------------------------------
9-counter rolling statistics for the Integration Engine.

Statistics:
  1. integration_sessions        — total sessions processed
  2. connectors_loaded           — connectors resolved in requests
  3. adapters_loaded             — adapters resolved in requests
  4. messages_routed             — messages routed through engine
  5. api_requests                — total API request dispatches
  6. events_processed            — lifecycle events emitted
  7. average_response_time_ms    — avg wall-clock time per request
  8. average_processing_time_ms  — avg pipeline processing time
  9. integration_availability    — rolling availability ratio (0.0–1.0)

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class IntegrationEngineStatisticsReport:
    integration_sessions:       int
    connectors_loaded:          int
    adapters_loaded:            int
    messages_routed:            int
    api_requests:               int
    events_processed:           int
    average_response_time_ms:   float
    average_processing_time_ms: float
    integration_availability:   float
    captured_at:                str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_sessions":       self.integration_sessions,
            "connectors_loaded":          self.connectors_loaded,
            "adapters_loaded":            self.adapters_loaded,
            "messages_routed":            self.messages_routed,
            "api_requests":               self.api_requests,
            "events_processed":           self.events_processed,
            "average_response_time_ms":   self.average_response_time_ms,
            "average_processing_time_ms": self.average_processing_time_ms,
            "integration_availability":   self.integration_availability,
            "captured_at":                self.captured_at,
        }


class IntegrationEngineStatistics:
    """Thread-safe rolling statistics for the Integration Engine."""

    def __init__(self) -> None:
        self._lock                      = threading.Lock()
        self._sessions                  = 0
        self._connectors_loaded         = 0
        self._adapters_loaded           = 0
        self._messages_routed           = 0
        self._api_requests              = 0
        self._events_processed          = 0
        self._total_response_ms         = 0.0
        self._response_count            = 0
        self._total_processing_ms       = 0.0
        self._processing_count          = 0
        self._availability_ticks        = 0
        self._availability_ok           = 0

    # ----------------------------------------------------------------
    # Increment
    # ----------------------------------------------------------------

    def record_session(self) -> None:
        with self._lock:
            self._sessions += 1

    def record_connector_loaded(self) -> None:
        with self._lock:
            self._connectors_loaded += 1

    def record_adapter_loaded(self) -> None:
        with self._lock:
            self._adapters_loaded += 1

    def record_message_routed(self) -> None:
        with self._lock:
            self._messages_routed += 1

    def record_api_request(self) -> None:
        with self._lock:
            self._api_requests += 1

    def record_event_processed(self) -> None:
        with self._lock:
            self._events_processed += 1

    def record_response_time(self, ms: float) -> None:
        with self._lock:
            self._total_response_ms += ms
            self._response_count    += 1

    def record_processing_time(self, ms: float) -> None:
        with self._lock:
            self._total_processing_ms += ms
            self._processing_count    += 1

    def record_availability_tick(self, available: bool) -> None:
        with self._lock:
            self._availability_ticks += 1
            if available:
                self._availability_ok += 1

    # ----------------------------------------------------------------
    # Report
    # ----------------------------------------------------------------

    def report(self) -> IntegrationEngineStatisticsReport:
        with self._lock:
            avg_response   = (
                self._total_response_ms / self._response_count
                if self._response_count > 0 else 0.0
            )
            avg_processing = (
                self._total_processing_ms / self._processing_count
                if self._processing_count > 0 else 0.0
            )
            availability = (
                self._availability_ok / self._availability_ticks
                if self._availability_ticks > 0 else 1.0
            )
            return IntegrationEngineStatisticsReport(
                integration_sessions       = self._sessions,
                connectors_loaded          = self._connectors_loaded,
                adapters_loaded            = self._adapters_loaded,
                messages_routed            = self._messages_routed,
                api_requests               = self._api_requests,
                events_processed           = self._events_processed,
                average_response_time_ms   = round(avg_response, 3),
                average_processing_time_ms = round(avg_processing, 3),
                integration_availability   = round(availability, 6),
                captured_at                = datetime.now(tz=timezone.utc).isoformat(),
            )

    def reset(self) -> None:
        with self._lock:
            self._sessions                = 0
            self._connectors_loaded       = 0
            self._adapters_loaded         = 0
            self._messages_routed         = 0
            self._api_requests            = 0
            self._events_processed        = 0
            self._total_response_ms       = 0.0
            self._response_count          = 0
            self._total_processing_ms     = 0.0
            self._processing_count        = 0
            self._availability_ticks      = 0
            self._availability_ok         = 0
