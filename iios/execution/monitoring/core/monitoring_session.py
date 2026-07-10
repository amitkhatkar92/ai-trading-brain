"""iios/execution/monitoring/core/monitoring_session.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.monitoring.monitoring_constants import MonitoringStatus


@dataclass
class MonitoringSession:
    """Represents one operational session of the monitoring engine."""

    session_id:     str              = field(default_factory=lambda: str(uuid.uuid4()))
    status:         MonitoringStatus = MonitoringStatus.INITIALIZING
    started_at:     float            = field(default_factory=time.time)
    stopped_at:     float | None     = None
    events_total:   int              = 0
    fills_total:    int              = 0
    alerts_total:   int              = 0
    recon_runs:     int              = 0
    metadata:       dict[str, Any]   = field(default_factory=dict)

    def uptime_sec(self) -> float:
        end = self.stopped_at if self.stopped_at else time.time()
        return max(0.0, end - self.started_at)

    def stop(self) -> None:
        self.status     = MonitoringStatus.STOPPED
        self.stopped_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id":   self.session_id,
            "status":       self.status.value,
            "started_at":   self.started_at,
            "stopped_at":   self.stopped_at,
            "uptime_sec":   round(self.uptime_sec(), 1),
            "events_total": self.events_total,
            "fills_total":  self.fills_total,
            "alerts_total": self.alerts_total,
            "recon_runs":   self.recon_runs,
            "metadata":     self.metadata,
        }
