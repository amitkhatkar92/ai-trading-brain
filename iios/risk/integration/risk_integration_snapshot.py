"""
risk_integration_snapshot.py — iios.risk.integration
======================================================
Lightweight immutable snapshot of the Risk Integration Engine state.

NOT the same as RiskSnapshot (M5) — this is a diagnostic snapshot
of the integration layer itself.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import HealthStatus, VERSION


@dataclass(frozen=True)
class RiskIntegrationSnapshot:
    """
    Immutable point-in-time snapshot of the Risk Integration Engine.

    Used for diagnostics, monitoring, and status reporting.
    This is distinct from :class:`~iios.risk.snapshot.RiskSnapshot` (M5),
    which represents the published Risk Intelligence output.
    """
    snapshot_id:         str
    engine_id:           str
    state:               str
    health_status:       HealthStatus
    is_running:          bool
    requests_received:   int
    requests_completed:  int
    requests_failed:     int
    snapshots_published: int
    components:          Dict[str, str]   # component_key → status
    uptime_s:            float
    avg_processing_s:    float
    framework_version:   str   = VERSION
    captured_at:         float = field(default_factory=time.time)

    @classmethod
    def capture(
        cls,
        engine_id:           str,
        state:               str,
        health_status:       HealthStatus,
        is_running:          bool,
        requests_received:   int,
        requests_completed:  int,
        requests_failed:     int,
        snapshots_published: int,
        components:          Dict[str, str],
        uptime_s:            float,
        avg_processing_s:    float,
    ) -> "RiskIntegrationSnapshot":
        return cls(
            snapshot_id         = str(uuid.uuid4()),
            engine_id           = engine_id,
            state               = state,
            health_status       = health_status,
            is_running          = is_running,
            requests_received   = requests_received,
            requests_completed  = requests_completed,
            requests_failed     = requests_failed,
            snapshots_published = snapshots_published,
            components          = dict(components),
            uptime_s            = uptime_s,
            avg_processing_s    = avg_processing_s,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id":        self.snapshot_id,
            "engine_id":          self.engine_id,
            "state":              self.state,
            "health_status":      self.health_status.value,
            "is_running":         self.is_running,
            "requests_received":  self.requests_received,
            "requests_completed": self.requests_completed,
            "requests_failed":    self.requests_failed,
            "snapshots_published": self.snapshots_published,
            "components":         self.components,
            "uptime_s":           self.uptime_s,
            "avg_processing_s":   self.avg_processing_s,
            "framework_version":  self.framework_version,
            "captured_at":        self.captured_at,
        }
