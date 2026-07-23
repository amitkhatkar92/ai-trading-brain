"""
market_integration_status.py — iios.market.integration
========================================================
Immutable integration engine status snapshot.

C12 Market Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import VERSION, INTEGRATION_SYSTEM_ID


@dataclass(frozen=True)
class MarketIntegrationStatus:
    """
    Immutable point-in-time status of the Market Integration engine.

    Captured via
    :meth:`~.market_integration_engine.MarketIntegrationEngine.status`.

    Fields
    ------
    engine_id :            Engine system identifier.
    lifecycle_state :      LifecycleAwareMixin state ("running" / "stopped" …).
    request_count :        Total requests processed since engine start.
    success_count :        Total successful requests.
    failure_count :        Total failed requests.
    rejection_count :      Total rejected requests.
    snapshot_publications : Total MarketSnapshots published.
    subsystem_states :     Dict of subsystem_name → lifecycle_state string.
    health :               Aggregate health report.
    statistics :           Full statistics snapshot.
    started_at :           Engine start time (0.0 if not started).
    captured_at :          Wall-clock time of this status snapshot.
    framework_version :    Framework version string.
    """
    engine_id:              str
    lifecycle_state:        str
    request_count:          int
    success_count:          int
    failure_count:          int
    rejection_count:        int
    snapshot_publications:  int
    subsystem_states:       Dict[str, str]
    health:                 Dict[str, Any]
    statistics:             Dict[str, Any]
    started_at:             float
    captured_at:            float
    framework_version:      str

    @property
    def is_running(self) -> bool:
        return self.lifecycle_state == "running"

    @property
    def overall_health(self) -> str:
        return self.health.get("overall", "unknown")

    @property
    def availability_rate(self) -> float:
        total = self.request_count
        if total == 0:
            return 1.0
        return round(self.success_count / total, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id":             self.engine_id,
            "lifecycle_state":       self.lifecycle_state,
            "request_count":         self.request_count,
            "success_count":         self.success_count,
            "failure_count":         self.failure_count,
            "rejection_count":       self.rejection_count,
            "snapshot_publications": self.snapshot_publications,
            "availability_rate":     self.availability_rate,
            "overall_health":        self.overall_health,
            "subsystem_states":      dict(self.subsystem_states),
            "started_at":            self.started_at,
            "captured_at":           self.captured_at,
            "framework_version":     self.framework_version,
        }
