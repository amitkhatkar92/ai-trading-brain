"""
iios/execution/analytics/engine/analytics_status.py
====================================================
AnalyticsEngineStatus — point-in-time operational status snapshot of the
Execution Analytics Engine.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION, EngineAnalyticsState, EngineHealthStatus


@dataclass(frozen=True)
class AnalyticsEngineStatus:
    """
    Immutable point-in-time status snapshot of the Execution Analytics Engine.

    Fields
    ------
    engine_state:          Current cycle state.
    health_status:         Overall health assessment.
    is_running:            Whether the engine is started.
    active_requests:       Number of requests currently in flight.
    completed_requests:    Total requests completed since start.
    failed_requests:       Total requests failed since start.
    scheduler_queue_depth: Number of requests waiting in the scheduler.
    dispatcher_count:      Total pipelines dispatched since start.
    uptime_seconds:        Engine uptime in seconds.
    captured_at:           Wall-time of this status snapshot.
    framework_version:     Framework version.
    """

    engine_state:          EngineAnalyticsState
    health_status:         EngineHealthStatus
    is_running:            bool
    active_requests:       int              = 0
    completed_requests:    int              = 0
    failed_requests:       int              = 0
    scheduler_queue_depth: int              = 0
    dispatcher_count:      int              = 0
    uptime_seconds:        float            = 0.0
    captured_at:           float            = field(default_factory=time.time)
    framework_version:     str              = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_state":          self.engine_state.value,
            "health_status":         self.health_status.value,
            "is_running":            self.is_running,
            "active_requests":       self.active_requests,
            "completed_requests":    self.completed_requests,
            "failed_requests":       self.failed_requests,
            "scheduler_queue_depth": self.scheduler_queue_depth,
            "dispatcher_count":      self.dispatcher_count,
            "uptime_seconds":        round(self.uptime_seconds, 1),
            "captured_at":           self.captured_at,
            "framework_version":     self.framework_version,
        }
