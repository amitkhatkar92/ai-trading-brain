"""
portfolio_status.py — iios.portfolio.engine
============================================
Point-in-time status snapshot for the Portfolio Engine.

C10 Portfolio Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION, EngineState


@dataclass(frozen=True)
class PortfolioEngineStatus:
    """
    Immutable point-in-time status snapshot of the Portfolio Engine.

    Fields
    ------
    engine_state :         Current processing state.
    lifecycle_state :      LifecycleAwareMixin state (e.g. "running").
    active_pipelines :     Number of in-flight pipelines.
    completed_pipelines :  Total completed pipelines (bounded window).
    failed_pipelines :     Total failed pipelines (bounded window).
    pending_requests :     Requests queued in the scheduler.
    is_healthy :           True iff all subsystems are available.
    statistics_snapshot :  Copy of current statistics.
    uptime_s :             Engine uptime in seconds.
    captured_at :          Wall-clock capture time.
    framework_version :    Framework version string.
    """
    engine_state:          EngineState
    lifecycle_state:       str
    active_pipelines:      int
    completed_pipelines:   int
    failed_pipelines:      int
    pending_requests:      int
    is_healthy:            bool
    statistics_snapshot:   Dict[str, Any]   = field(default_factory=dict)
    uptime_s:              float            = 0.0
    captured_at:           float            = field(default_factory=time.time)
    framework_version:     str              = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_state":        self.engine_state.value,
            "lifecycle_state":     self.lifecycle_state,
            "active_pipelines":    self.active_pipelines,
            "completed_pipelines": self.completed_pipelines,
            "failed_pipelines":    self.failed_pipelines,
            "pending_requests":    self.pending_requests,
            "is_healthy":          self.is_healthy,
            "uptime_s":            self.uptime_s,
            "captured_at":         self.captured_at,
        }
