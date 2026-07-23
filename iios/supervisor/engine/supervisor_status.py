"""
supervisor_status.py — iios.supervisor.engine
----------------------------------------------
Immutable supervisor engine status value object.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .constants import (
    VERSION,
    EngineState,
)


@dataclass(frozen=True)
class SupervisorEngineStatus:
    """
    Point-in-time snapshot of the supervisor engine's operational status.

    Fields
    ------
    engine_state :         Current engine state.
    engine_lifecycle :     Lifecycle state string (e.g. "running").
    active_pipelines :     Number of currently active pipelines.
    archived_pipelines :   Total pipelines archived since start.
    scheduler_queue_depth: Requests waiting in the scheduler.
    active_sessions :      Number of live supervisor sessions.
    total_requests :       Cumulative requests submitted.
    total_responses :      Cumulative responses returned.
    health :               Overall health classification.
    issues :               Active health issue descriptions.
    captured_at :          Wall-clock capture time.
    framework_version :    Framework version string.
    """
    engine_state:          EngineState
    engine_lifecycle:      str
    active_pipelines:      int
    archived_pipelines:    int
    scheduler_queue_depth: int
    active_sessions:       int
    total_requests:        int
    total_responses:       int
    health:                str
    issues:                List[str]       = field(default_factory=list)
    captured_at:           float           = field(default_factory=time.time)
    framework_version:     str             = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_state":          self.engine_state.value,
            "engine_lifecycle":      self.engine_lifecycle,
            "active_pipelines":      self.active_pipelines,
            "archived_pipelines":    self.archived_pipelines,
            "scheduler_queue_depth": self.scheduler_queue_depth,
            "active_sessions":       self.active_sessions,
            "total_requests":        self.total_requests,
            "total_responses":       self.total_responses,
            "health":                self.health,
            "issues":                list(self.issues),
            "captured_at":           self.captured_at,
            "framework_version":     self.framework_version,
        }
