"""
risk_integration_status.py — iios.risk.integration
====================================================
Immutable status value object for the Risk Integration Engine.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import dataclasses
import time
from typing import Any, Dict

from .constants import HealthStatus, VERSION


@dataclasses.dataclass(frozen=True)
class RiskIntegrationStatus:
    """Snapshot of the Risk Integration Engine state at a point in time."""
    engine_id:           str
    state:               str
    health_status:       HealthStatus
    is_running:          bool
    requests_total:      int
    requests_completed:  int
    requests_failed:     int
    snapshots_published: int
    components_available: int
    components_total:    int
    uptime_s:            float
    started_at:          float
    framework_version:   str   = VERSION
    reported_at:         float = dataclasses.field(default_factory=time.time)

    @property
    def success_rate(self) -> float:
        total = self.requests_completed + self.requests_failed
        return self.requests_completed / total if total > 0 else 0.0

    @property
    def error_rate(self) -> float:
        total = self.requests_completed + self.requests_failed
        return self.requests_failed / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id":            self.engine_id,
            "state":                self.state,
            "health_status":        self.health_status.value,
            "is_running":           self.is_running,
            "requests_total":       self.requests_total,
            "requests_completed":   self.requests_completed,
            "requests_failed":      self.requests_failed,
            "snapshots_published":  self.snapshots_published,
            "components_available": self.components_available,
            "components_total":     self.components_total,
            "uptime_s":             self.uptime_s,
            "success_rate":         self.success_rate,
            "error_rate":           self.error_rate,
            "framework_version":    self.framework_version,
            "reported_at":          self.reported_at,
        }
