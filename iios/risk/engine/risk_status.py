"""
risk_status.py — iios.risk.engine
====================================
Immutable engine-level status snapshot.

C11 Risk Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION, EngineState, ENGINE_SYSTEM_ID


@dataclass(frozen=True)
class RiskEngineStatus:
    """
    Immutable point-in-time status of the Risk Engine.

    Captured via :meth:`RiskEngine.status()`.

    Fields
    ------
    engine_id :         Engine system identifier.
    state :             Lifecycle state of the engine itself (running/stopped).
    engine_state :      Current processing state.
    session_count :     Number of active lifecycle sessions.
    pipeline_count :    Number of active pipelines.
    health :            Health report dict from RiskEngineHealth.
    statistics :        Statistics snapshot dict.
    started_at :        Wall-clock engine start time (0.0 if not started).
    captured_at :       Wall-clock time of this snapshot.
    framework_version : Framework version string.
    """
    engine_id:         str
    state:             str                  # lifecycle state ("running", "stopped", …)
    engine_state:      EngineState
    session_count:     int
    pipeline_count:    int
    health:            Dict[str, Any]       = field(default_factory=dict)
    statistics:        Dict[str, Any]       = field(default_factory=dict)
    started_at:        float                = 0.0
    captured_at:       float               = field(default_factory=time.time)
    framework_version: str                  = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id":         self.engine_id,
            "state":             self.state,
            "engine_state":      self.engine_state.value,
            "session_count":     self.session_count,
            "pipeline_count":    self.pipeline_count,
            "health_overall":    self.health.get("overall", "unknown"),
            "started_at":        self.started_at,
            "captured_at":       self.captured_at,
            "framework_version": self.framework_version,
        }
