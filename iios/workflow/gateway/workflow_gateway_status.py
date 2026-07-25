"""
workflow_gateway_status.py — iios.workflow.gateway
---------------------------------------------------
WorkflowGatewayStatus + WorkflowStatus —
gateway operational status capture.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import GatewayState


@dataclass(frozen=True)
class WorkflowStatus:
    """Immutable point-in-time operational status of the gateway."""
    gateway_id:         str
    gateway_state:      GatewayState
    active_workflows:   int
    pending_workflows:  int
    total_processed:    int
    uptime_seconds:     float
    captured_at:        str
    metadata:           Dict[str, Any]

    @property
    def is_operational(self) -> bool:
        return self.gateway_state == GatewayState.RUNNING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gateway_id":        self.gateway_id,
            "gateway_state":     self.gateway_state.value,
            "active_workflows":  self.active_workflows,
            "pending_workflows": self.pending_workflows,
            "total_processed":   self.total_processed,
            "uptime_seconds":    self.uptime_seconds,
            "captured_at":       self.captured_at,
            "is_operational":    self.is_operational,
            "metadata":          dict(self.metadata),
        }


class WorkflowGatewayStatus:
    """
    Captures WorkflowStatus from live gateway state.

    Stateless and thread-safe.
    """

    def capture(
        self,
        gateway_id:        str,
        gateway_state:     GatewayState,
        active_workflows:  int,
        pending_workflows: int,
        total_processed:   int,
        started_at:        float,   # monotonic timestamp
        metadata:          Optional[Dict[str, Any]] = None,
    ) -> WorkflowStatus:
        return WorkflowStatus(
            gateway_id        = gateway_id,
            gateway_state     = gateway_state,
            active_workflows  = active_workflows,
            pending_workflows = pending_workflows,
            total_processed   = total_processed,
            uptime_seconds    = round(time.monotonic() - started_at, 3),
            captured_at       = datetime.now(tz=timezone.utc).isoformat(),
            metadata          = dict(metadata or {}),
        )
