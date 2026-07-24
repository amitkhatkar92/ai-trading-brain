"""
integration_health.py — iios.integration.engine
-------------------------------------------------
Engine health monitoring — builds health reports from live engine state.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import IntegrationEngineState


@dataclass(frozen=True)
class EngineHealthReport:
    """Point-in-time health snapshot for the Integration Engine."""
    status:           str   # "healthy" | "degraded" | "unhealthy"
    engine_state:     str
    active_sessions:  int
    connector_count:  int
    adapter_count:    int
    protocol_count:   int
    queue_size:       int
    uptime_seconds:   float
    captured_at:      str
    details:          Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":          self.status,
            "engine_state":    self.engine_state,
            "active_sessions": self.active_sessions,
            "connector_count": self.connector_count,
            "adapter_count":   self.adapter_count,
            "protocol_count":  self.protocol_count,
            "queue_size":      self.queue_size,
            "uptime_seconds":  self.uptime_seconds,
            "captured_at":     self.captured_at,
            "details":         self.details,
        }


class IntegrationEngineHealth:
    """Builds EngineHealthReport from live engine components."""

    def report(
        self,
        engine_state:    IntegrationEngineState,
        connector_count: int,
        adapter_count:   int,
        protocol_count:  int,
        active_sessions: int,
        queue_size:      int,
        started_at:      float,   # monotonic timestamp
        details:         Dict[str, Any] = None,
    ) -> EngineHealthReport:
        uptime = time.monotonic() - started_at
        status = self._compute_status(engine_state, connector_count, adapter_count)
        return EngineHealthReport(
            status          = status,
            engine_state    = engine_state.value,
            active_sessions = active_sessions,
            connector_count = connector_count,
            adapter_count   = adapter_count,
            protocol_count  = protocol_count,
            queue_size      = queue_size,
            uptime_seconds  = round(uptime, 3),
            captured_at     = datetime.now(tz=timezone.utc).isoformat(),
            details         = dict(details or {}),
        )

    def _compute_status(
        self,
        state:           IntegrationEngineState,
        connector_count: int,
        adapter_count:   int,
    ) -> str:
        if state == IntegrationEngineState.STOPPED:
            return "unhealthy"
        if state == IntegrationEngineState.FAILED:
            return "unhealthy"
        if connector_count == 0 or adapter_count == 0:
            return "degraded"
        return "healthy"
