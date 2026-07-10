"""iios/execution/monitoring/core/execution_snapshot.py

Point-in-time summary snapshot of execution engine state.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import MonitoringStatus


@dataclass
class ExecutionSnapshot:
    """Captures a consistent point-in-time view of the monitoring engine state."""

    snapshot_id:          str            = field(default_factory=lambda: str(uuid.uuid4()))
    monitoring_status:    MonitoringStatus = MonitoringStatus.ACTIVE
    active_executions:    int            = 0
    completed_executions: int            = 0
    failed_executions:    int            = 0
    total_fills:          int            = 0
    active_alerts:        int            = 0
    last_reconciliation:  float | None   = None
    last_audit_event:     float | None   = None
    uptime_sec:           float          = 0.0
    captured_at:          float          = field(default_factory=time.time)
    metadata:             dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":           self.snapshot_id,
            "monitoring_status":     self.monitoring_status.value,
            "active_executions":     self.active_executions,
            "completed_executions":  self.completed_executions,
            "failed_executions":     self.failed_executions,
            "total_fills":           self.total_fills,
            "active_alerts":         self.active_alerts,
            "last_reconciliation":   self.last_reconciliation,
            "last_audit_event":      self.last_audit_event,
            "uptime_sec":            round(self.uptime_sec, 1),
            "captured_at":           self.captured_at,
            "metadata":              self.metadata,
        }
