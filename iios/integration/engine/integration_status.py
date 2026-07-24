"""
integration_status.py — iios.integration.engine
-------------------------------------------------
Engine status snapshot — captures current operational state.

C15 Enterprise Integration & Connectivity — Phase 1, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import IntegrationEngineState


@dataclass(frozen=True)
class IntegrationEngineStatus:
    """Point-in-time operational status for the Integration Engine."""
    engine_id:       str
    state:           IntegrationEngineState
    uptime_seconds:  float
    active_sessions: int
    queue_size:      int
    connector_count: int
    adapter_count:   int
    protocol_count:  int
    captured_at:     str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id":       self.engine_id,
            "state":           self.state.value,
            "uptime_seconds":  self.uptime_seconds,
            "active_sessions": self.active_sessions,
            "queue_size":      self.queue_size,
            "connector_count": self.connector_count,
            "adapter_count":   self.adapter_count,
            "protocol_count":  self.protocol_count,
            "captured_at":     self.captured_at,
        }


class IntegrationEngineStatusTracker:
    """Captures IntegrationEngineStatus from live engine components."""

    def capture(
        self,
        engine_id:       str,
        state:           IntegrationEngineState,
        active_sessions: int,
        queue_size:      int,
        connector_count: int,
        adapter_count:   int,
        protocol_count:  int,
        started_at:      float,   # monotonic timestamp
    ) -> IntegrationEngineStatus:
        return IntegrationEngineStatus(
            engine_id       = engine_id,
            state           = state,
            uptime_seconds  = round(time.monotonic() - started_at, 3),
            active_sessions = active_sessions,
            queue_size      = queue_size,
            connector_count = connector_count,
            adapter_count   = adapter_count,
            protocol_count  = protocol_count,
            captured_at     = datetime.now(tz=timezone.utc).isoformat(),
        )
