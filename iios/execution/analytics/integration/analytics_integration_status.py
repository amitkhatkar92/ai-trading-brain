"""
analytics_integration_status.py — iios.execution.analytics.integration
=======================================================================
Immutable status snapshot for the Execution Analytics Integration subsystem.

Provides :class:`AnalyticsIntegrationStatus` and :func:`build_integration_status`.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import (
    INTEGRATION_SYSTEM_ID,
    INTEGRATION_VERSION,
    ComponentType,
    IntegrationStatus,
)
from .analytics_integration_health import AnalyticsIntegrationHealth


@dataclass(frozen=True)
class AnalyticsIntegrationStatus:
    """
    Point-in-time status snapshot of the analytics integration subsystem.

    Intended to be returned by :meth:`ExecutionAnalyticsIntegration.status`.

    Fields
    ------
    integration_id :     System identifier of the integration engine.
    status :             Current :class:`IntegrationStatus`.
    health :             Current :class:`AnalyticsIntegrationHealth`.
    is_running :         ``True`` when subsystem lifecycle is active.
    is_operational :     ``True`` when subsystem can accept requests.
    active_requests :    Number of concurrently in-flight analytics requests.
    total_requests :     Cumulative requests received since last start.
    total_snapshots :    Cumulative snapshots published since last start.
    component_states :   Mapping of component-name → running/stopped string.
    uptime_seconds :     Elapsed seconds since subsystem was started.
    snapshot_at :        Unix timestamp of this status snapshot.
    metadata :           Optional supplementary metadata.
    framework_version :  Framework version string.
    """
    integration_id:   str
    status:           IntegrationStatus
    health:           AnalyticsIntegrationHealth
    is_running:       bool
    is_operational:   bool
    active_requests:  int
    total_requests:   int
    total_snapshots:  int
    component_states: Dict[str, str]        = field(default_factory=dict)
    uptime_seconds:   float                 = 0.0
    snapshot_at:      float                 = field(default_factory=time.time)
    metadata:         Dict[str, Any]        = field(default_factory=dict)
    framework_version: str                  = INTEGRATION_VERSION


def build_integration_status(
    *,
    health: AnalyticsIntegrationHealth,
    is_running: bool,
    active_requests: int,
    total_requests: int,
    total_snapshots: int,
    started_at: float | None,
    component_running_map: Dict[ComponentType, bool],
    metadata: Dict[str, Any] | None = None,
) -> AnalyticsIntegrationStatus:
    """
    Construct an :class:`AnalyticsIntegrationStatus` from runtime state.

    Parameters
    ----------
    health :                Current :class:`AnalyticsIntegrationHealth`.
    is_running :            Whether the subsystem lifecycle is active.
    active_requests :       Current in-flight request count.
    total_requests :        Cumulative requests received.
    total_snapshots :       Cumulative snapshots published.
    started_at :            Unix timestamp of last start; ``None`` if not started.
    component_running_map : Dict of ``ComponentType`` → ``bool`` running flags.
    metadata :              Optional supplementary metadata.
    """
    now = time.time()

    # Derive overall status
    if not is_running:
        status = IntegrationStatus.STOPPED
    elif health.is_critical:
        status = IntegrationStatus.ERROR
    elif health.is_degraded:
        status = IntegrationStatus.DEGRADED
    else:
        status = IntegrationStatus.RUNNING

    component_states: Dict[str, str] = {
        ct.value: ("running" if running else "stopped")
        for ct, running in component_running_map.items()
    }

    uptime = (now - started_at) if (is_running and started_at is not None) else 0.0

    return AnalyticsIntegrationStatus(
        integration_id   = INTEGRATION_SYSTEM_ID,
        status           = status,
        health           = health,
        is_running       = is_running,
        is_operational   = health.is_operational,
        active_requests  = active_requests,
        total_requests   = total_requests,
        total_snapshots  = total_snapshots,
        component_states = component_states,
        uptime_seconds   = uptime,
        snapshot_at      = now,
        metadata         = metadata or {},
    )
