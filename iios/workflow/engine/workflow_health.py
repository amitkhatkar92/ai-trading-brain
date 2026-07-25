"""
workflow_health.py — iios.workflow.engine
------------------------------------------
Engine health monitoring — builds health reports from live engine state.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import WorkflowEngineState


@dataclass(frozen=True)
class WorkflowEngineHealthReport:
    """Point-in-time health snapshot for the Workflow Engine."""
    status:          str   # "healthy" | "degraded" | "unhealthy"
    engine_state:    str
    active_requests: int
    queue_size:      int
    uptime_seconds:  float
    captured_at:     str
    details:         Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":          self.status,
            "engine_state":    self.engine_state,
            "active_requests": self.active_requests,
            "queue_size":      self.queue_size,
            "uptime_seconds":  self.uptime_seconds,
            "captured_at":     self.captured_at,
            "details":         self.details,
        }

    @property
    def is_healthy(self) -> bool:
        return self.status == "healthy"

    @property
    def is_degraded(self) -> bool:
        return self.status == "degraded"

    @property
    def is_unhealthy(self) -> bool:
        return self.status == "unhealthy"


class WorkflowEngineHealth:
    """Builds WorkflowEngineHealthReport from live engine components."""

    def report(
        self,
        engine_state:    WorkflowEngineState,
        active_requests: int,
        queue_size:      int,
        started_at:      float,   # monotonic timestamp
        details:         Dict[str, Any] = None,
    ) -> WorkflowEngineHealthReport:
        uptime = time.monotonic() - started_at
        status = self._compute_status(engine_state, queue_size)
        return WorkflowEngineHealthReport(
            status          = status,
            engine_state    = engine_state.value,
            active_requests = active_requests,
            queue_size      = queue_size,
            uptime_seconds  = round(uptime, 3),
            captured_at     = datetime.now(tz=timezone.utc).isoformat(),
            details         = dict(details or {}),
        )

    def _compute_status(
        self,
        state:      WorkflowEngineState,
        queue_size: int,
    ) -> str:
        if state in (WorkflowEngineState.STOPPED, WorkflowEngineState.FAILED):
            return "unhealthy"
        from .constants import DEFAULT_QUEUE_SIZE
        if queue_size >= DEFAULT_QUEUE_SIZE * 0.9:
            return "degraded"
        return "healthy"
