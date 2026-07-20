"""
decision_status.py — iios.decision.engine
===========================================
Operational status snapshot for the Decision Engine.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import EngineOperationalStatus, VERSION


@dataclass(frozen=True)
class DecisionEngineStatus:
    """
    Immutable snapshot of the engine's current operational status.

    Fields
    ------
    operational :       :class:`EngineOperationalStatus` of the engine.
    active_sessions :   Number of active decision sessions.
    active_pipelines :  Number of active processing pipelines.
    queued_requests :   Number of requests queued for processing.
    completed_total :   Total completed pipelines since startup.
    failed_total :      Total failed pipelines since startup.
    uptime_s :          Seconds since the engine was last started.
    message :           Human-readable status message.
    captured_at :       Wall-clock snapshot time.
    framework_version : Framework version.
    """
    operational:       EngineOperationalStatus
    active_sessions:   int
    active_pipelines:  int
    queued_requests:   int
    completed_total:   int
    failed_total:      int
    uptime_s:          float
    message:           str   = ""
    captured_at:       float = field(default_factory=time.time)
    framework_version: str   = VERSION

    @property
    def is_running(self) -> bool:
        return self.operational == EngineOperationalStatus.RUNNING

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operational":      self.operational.value,
            "active_sessions":  self.active_sessions,
            "active_pipelines": self.active_pipelines,
            "queued_requests":  self.queued_requests,
            "completed_total":  self.completed_total,
            "failed_total":     self.failed_total,
            "uptime_s":         self.uptime_s,
            "message":          self.message,
            "captured_at":      self.captured_at,
            "framework_version": self.framework_version,
        }


def build_engine_status(
    operational:      EngineOperationalStatus,
    *,
    active_sessions:  int   = 0,
    active_pipelines: int   = 0,
    queued_requests:  int   = 0,
    completed_total:  int   = 0,
    failed_total:     int   = 0,
    started_at:       float = 0.0,
    message:          str   = "",
) -> DecisionEngineStatus:
    """
    Build a :class:`DecisionEngineStatus` snapshot from engine metrics.
    """
    uptime = (time.time() - started_at) if started_at else 0.0
    return DecisionEngineStatus(
        operational      = operational,
        active_sessions  = active_sessions,
        active_pipelines = active_pipelines,
        queued_requests  = queued_requests,
        completed_total  = completed_total,
        failed_total     = failed_total,
        uptime_s         = uptime,
        message          = message,
    )
