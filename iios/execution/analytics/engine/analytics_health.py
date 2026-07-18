"""
iios/execution/analytics/engine/analytics_health.py
====================================================
AnalyticsEngineHealth — point-in-time health assessment of the Execution
Analytics Engine.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import VERSION, EngineHealthStatus


@dataclass
class AnalyticsEngineHealth:
    """
    Mutable health record for the Execution Analytics Engine.

    Aggregates health signals from all engine sub-components.

    Fields
    ------
    status:               Overall health status.
    components:           Per-component health (component_name → status).
    warnings:             Active warning messages.
    errors:               Active error messages.
    scheduler_queue_depth: Current scheduler queue depth.
    active_requests:      Number of in-flight requests.
    last_success_at:      Wall-time of last successful analytics cycle.
    uptime_seconds:       Engine uptime in seconds.
    assessed_at:          Wall-time of this health assessment.
    framework_version:    Framework version.
    """

    status:                EngineHealthStatus        = EngineHealthStatus.UNKNOWN
    components:            Dict[str, str]            = field(default_factory=dict)
    warnings:              List[str]                 = field(default_factory=list)
    errors:                List[str]                 = field(default_factory=list)
    scheduler_queue_depth: int                       = 0
    active_requests:       int                       = 0
    last_success_at:       Optional[float]           = None
    uptime_seconds:        float                     = 0.0
    assessed_at:           float                     = field(default_factory=time.time)
    framework_version:     str                       = VERSION

    @property
    def is_healthy(self) -> bool:
        return self.status == EngineHealthStatus.HEALTHY

    @property
    def is_degraded(self) -> bool:
        return self.status == EngineHealthStatus.DEGRADED

    @property
    def is_unhealthy(self) -> bool:
        return self.status == EngineHealthStatus.UNHEALTHY

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)
        if self.status == EngineHealthStatus.HEALTHY:
            self.status = EngineHealthStatus.DEGRADED

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.status = EngineHealthStatus.UNHEALTHY

    def set_component(self, name: str, status: EngineHealthStatus) -> None:
        self.components[name] = status.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status":                self.status.value,
            "components":            dict(self.components),
            "warnings":              list(self.warnings),
            "errors":                list(self.errors),
            "scheduler_queue_depth": self.scheduler_queue_depth,
            "active_requests":       self.active_requests,
            "last_success_at":       self.last_success_at,
            "uptime_seconds":        round(self.uptime_seconds, 1),
            "assessed_at":           self.assessed_at,
            "framework_version":     self.framework_version,
        }


def assess_engine_health(
    *,
    scheduler_queue_depth: int          = 0,
    active_requests:       int          = 0,
    last_success_at:       Optional[float] = None,
    uptime_seconds:        float        = 0.0,
    scheduler_running:     bool         = True,
    dispatcher_running:    bool         = True,
    session_mgr_running:   bool         = True,
    registry_running:      bool         = True,
    max_queue_threshold:   int          = 800,
) -> AnalyticsEngineHealth:
    """
    Evaluate engine health from current operational metrics.

    Returns an AnalyticsEngineHealth with status set appropriately.
    """
    health = AnalyticsEngineHealth(
        status                = EngineHealthStatus.HEALTHY,
        scheduler_queue_depth = scheduler_queue_depth,
        active_requests       = active_requests,
        last_success_at       = last_success_at,
        uptime_seconds        = uptime_seconds,
    )

    # Component status
    health.set_component(
        "scheduler",
        EngineHealthStatus.HEALTHY if scheduler_running else EngineHealthStatus.UNHEALTHY,
    )
    health.set_component(
        "dispatcher",
        EngineHealthStatus.HEALTHY if dispatcher_running else EngineHealthStatus.UNHEALTHY,
    )
    health.set_component(
        "session_manager",
        EngineHealthStatus.HEALTHY if session_mgr_running else EngineHealthStatus.UNHEALTHY,
    )
    health.set_component(
        "registry",
        EngineHealthStatus.HEALTHY if registry_running else EngineHealthStatus.UNHEALTHY,
    )

    # Raise errors for non-running components
    for component, running in [
        ("scheduler",      scheduler_running),
        ("dispatcher",     dispatcher_running),
        ("session_manager",session_mgr_running),
        ("registry",       registry_running),
    ]:
        if not running:
            health.add_error(f"{component} is not running")

    # Warn on high queue depth
    if scheduler_queue_depth > max_queue_threshold:
        health.add_warning(
            f"Scheduler queue depth is high: {scheduler_queue_depth} "
            f"(threshold: {max_queue_threshold})"
        )

    return health
