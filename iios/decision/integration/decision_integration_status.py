"""
decision_integration_status.py — iios.decision.integration
===========================================================
Service-level status reports for the Decision Integration subsystem.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .constants import IntegrationStatus, OverallHealth, VERSION


@dataclass(frozen=True)
class DecisionIntegrationStatus:
    """
    Immutable status report for the Decision Integration subsystem.

    Fields
    ------
    is_running :         True when the integration engine is running.
    overall_health :     Aggregate health level.
    in_flight_count :    Number of requests currently in flight.
    completed_count :    Total completed requests since start.
    failed_count :       Total failed requests since start.
    uptime_s :           Seconds since the engine last started.
    components_ready :   List of component type strings that are ready.
    components_missing : List of required component types that are absent.
    detail :             Human-readable status summary.
    checked_at :         UTC timestamp of this status snapshot.
    framework_version :  Framework version.
    """

    is_running:          bool
    overall_health:      OverallHealth
    in_flight_count:     int
    completed_count:     int
    failed_count:        int
    uptime_s:            float
    components_ready:    List[str]   = field(default_factory=list)
    components_missing:  List[str]   = field(default_factory=list)
    detail:              str         = ""
    checked_at:          datetime    = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version:   str         = VERSION

    def to_dict(self) -> Dict:
        return {
            "is_running":         self.is_running,
            "overall_health":     self.overall_health.value,
            "in_flight_count":    self.in_flight_count,
            "completed_count":    self.completed_count,
            "failed_count":       self.failed_count,
            "uptime_s":           self.uptime_s,
            "components_ready":   list(self.components_ready),
            "components_missing": list(self.components_missing),
            "detail":             self.detail,
            "checked_at":         self.checked_at.isoformat(),
            "framework_version":  self.framework_version,
        }


class DecisionIntegrationStatusMonitor:
    """
    Produces :class:`DecisionIntegrationStatus` snapshots.

    Usage
    -----
    ::

        monitor  = DecisionIntegrationStatusMonitor()
        registry = DecisionComponentRegistry(...)
        status   = monitor.snapshot(registry, statistics, health, is_running, uptime_s)
    """

    def __init__(self) -> None:
        self._lock: threading.Lock                            = threading.Lock()
        self._last: Optional[DecisionIntegrationStatus]       = None

    def snapshot(
        self,
        component_registry,
        statistics,
        health,
        is_running: bool,
        uptime_s:   float,
    ) -> DecisionIntegrationStatus:
        """
        Build a status snapshot from current engine state.

        Parameters
        ----------
        component_registry : :class:`DecisionComponentRegistry`
        statistics :         :class:`DecisionIntegrationStatistics`
        health :             Latest :class:`DecisionIntegrationHealth`
        is_running :         Whether the engine is running.
        uptime_s :           Seconds since engine last started.
        """
        from .constants import ComponentType

        # Component readiness
        ready_types:   List[str] = []
        missing_types: List[str] = []

        for ct in ComponentType:
            available = (
                hasattr(component_registry, "is_available")
                and component_registry.is_available(ct)
            )
            if available and hasattr(component_registry, "is_ready"):
                if component_registry.is_ready(ct):
                    ready_types.append(ct.value)
                else:
                    missing_types.append(ct.value)
            elif not available:
                missing_types.append(ct.value)

        # Statistics
        stats_snap       = statistics.snapshot() if hasattr(statistics, "snapshot") else {}
        completed_count  = stats_snap.get("requests_completed", 0)
        failed_count     = stats_snap.get("requests_failed", 0)
        in_flight        = stats_snap.get("requests_in_flight", 0)

        overall_health = (
            health.overall if health is not None else OverallHealth.UNKNOWN
        )

        if not is_running:
            detail = "Integration engine is stopped"
        elif missing_types:
            detail = f"Missing components: {missing_types}"
        else:
            detail = "Integration engine running, all components available"

        status = DecisionIntegrationStatus(
            is_running         = is_running,
            overall_health     = overall_health,
            in_flight_count    = in_flight,
            completed_count    = completed_count,
            failed_count       = failed_count,
            uptime_s           = uptime_s,
            components_ready   = ready_types,
            components_missing = missing_types,
            detail             = detail,
        )
        with self._lock:
            self._last = status
        return status

    def last(self) -> Optional[DecisionIntegrationStatus]:
        with self._lock:
            return self._last
