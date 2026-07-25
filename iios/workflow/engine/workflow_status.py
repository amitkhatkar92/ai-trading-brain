"""
workflow_status.py — iios.workflow.engine
------------------------------------------
Engine status snapshot — captures current operational state.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import WorkflowEngineState


@dataclass(frozen=True)
class WorkflowEngineStatus:
    """Point-in-time operational status for the Workflow Engine."""
    engine_id:       str
    state:           WorkflowEngineState
    uptime_seconds:  float
    active_requests: int
    queue_size:      int
    sessions_active: int
    captured_at:     str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id":       self.engine_id,
            "state":           self.state.value,
            "uptime_seconds":  self.uptime_seconds,
            "active_requests": self.active_requests,
            "queue_size":      self.queue_size,
            "sessions_active": self.sessions_active,
            "captured_at":     self.captured_at,
        }


class WorkflowEngineStatusTracker:
    """Captures WorkflowEngineStatus from live engine components."""

    def capture(
        self,
        engine_id:       str,
        state:           WorkflowEngineState,
        active_requests: int,
        queue_size:      int,
        sessions_active: int,
        started_at:      float,   # monotonic timestamp
    ) -> WorkflowEngineStatus:
        return WorkflowEngineStatus(
            engine_id       = engine_id,
            state           = state,
            uptime_seconds  = round(time.monotonic() - started_at, 3),
            active_requests = active_requests,
            queue_size      = queue_size,
            sessions_active = sessions_active,
            captured_at     = datetime.now(tz=timezone.utc).isoformat(),
        )
