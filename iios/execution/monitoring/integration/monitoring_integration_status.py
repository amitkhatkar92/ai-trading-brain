"""iios/execution/monitoring/integration/monitoring_integration_status.py
==================================================
IntegrationStatusRecord — immutable point-in-time status of the
integration subsystem.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import IntegrationState, HealthStatus, VERSION
from .monitoring_integration_health import IntegrationHealth


@dataclass(frozen=True)
class IntegrationStatusRecord:
    """
    Immutable snapshot of the integration subsystem status.

    Fields
    ------
    state:              Current IntegrationState.
    health:             Aggregated IntegrationHealth.
    active_sessions:    Number of active monitoring sessions.
    total_requests:     Cumulative request count.
    total_errors:       Cumulative error count.
    uptime_seconds:     Seconds since last start, or 0.0.
    started_at:         Wall-time of last start, or None.
    checked_at:         Wall-time this status was captured.
    framework_version:  Version for compatibility checks.
    """

    state:             IntegrationState
    health:            IntegrationHealth
    active_sessions:   int               = 0
    total_requests:    int               = 0
    total_errors:      int               = 0
    uptime_seconds:    float             = 0.0
    started_at:        Optional[float]   = None
    checked_at:        float             = field(default_factory=time.time, compare=False)
    framework_version: str               = VERSION

    @property
    def is_running(self) -> bool:
        from .constants import RUNNING_INTEGRATION_STATES
        return self.state in RUNNING_INTEGRATION_STATES

    @property
    def is_healthy(self) -> bool:
        return self.health.is_healthy

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state":             self.state.value,
            "health":            self.health.to_dict(),
            "active_sessions":   self.active_sessions,
            "total_requests":    self.total_requests,
            "total_errors":      self.total_errors,
            "uptime_seconds":    self.uptime_seconds,
            "started_at":        self.started_at,
            "checked_at":        self.checked_at,
            "framework_version": self.framework_version,
        }
