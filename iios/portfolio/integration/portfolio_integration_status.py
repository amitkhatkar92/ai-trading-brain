"""
portfolio_integration_status.py — iios.portfolio.integration
=============================================================
Immutable status value objects for the Portfolio Integration subsystem.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict

from .constants import VERSION, INTEGRATION_SYSTEM_ID, IntegrationHealth


@dataclass(frozen=True)
class IntegrationComponentStatus:
    """
    Immutable status snapshot for a single integration component.

    Fields
    ------
    component_type : Component classification (lifecycle/engine/policy/…).
    is_running :     Whether the component is currently operational.
    health :         Component health (healthy/degraded/critical/unknown).
    started_at :     Wall-clock time when the component last started (0 = not started).
    last_event :     Description of the most recent lifecycle event.
    metadata :       Supplementary metadata dict.
    """
    component_type: str
    is_running:     bool
    health:         str
    started_at:     float
    last_event:     str
    metadata:       Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_type": self.component_type,
            "is_running":     self.is_running,
            "health":         self.health,
            "started_at":     self.started_at,
            "last_event":     self.last_event,
            "metadata":       dict(self.metadata),
        }

    @classmethod
    def unknown(cls, component_type: str) -> "IntegrationComponentStatus":
        return cls(
            component_type = component_type,
            is_running     = False,
            health         = IntegrationHealth.UNKNOWN.value,
            started_at     = 0.0,
            last_event     = "",
            metadata       = {},
        )

    @classmethod
    def running(cls, component_type: str, started_at: float = 0.0) -> "IntegrationComponentStatus":
        return cls(
            component_type = component_type,
            is_running     = True,
            health         = IntegrationHealth.HEALTHY.value,
            started_at     = started_at or time.time(),
            last_event     = "started",
            metadata       = {},
        )


@dataclass(frozen=True)
class PortfolioIntegrationStatus:
    """
    Immutable top-level status snapshot of the Portfolio Integration Engine.

    Aggregates the status of all five integrated components and reports
    the overall system health.

    Fields
    ------
    integration_id :     Integration engine identifier.
    state :              Current integration engine state.
    lifecycle_status :   Status of the Portfolio Lifecycle component.
    engine_status :      Status of the Portfolio Engine component.
    policy_status :      Status of the Portfolio Policy Framework component.
    optimization_status: Status of the Portfolio Optimization Framework.
    snapshot_status :    Status of the Portfolio Snapshot component.
    overall_health :     Aggregated health across all components.
    statistics :         Current statistics snapshot.
    started_at :         Wall-clock time the integration engine last started.
    captured_at :        Wall-clock time this status was captured.
    framework_version :  Framework version string.
    """
    integration_id:      str
    state:               str
    lifecycle_status:    IntegrationComponentStatus
    engine_status:       IntegrationComponentStatus
    policy_status:       IntegrationComponentStatus
    optimization_status: IntegrationComponentStatus
    snapshot_status:     IntegrationComponentStatus
    overall_health:      str
    statistics:          Dict[str, Any]
    started_at:          float
    captured_at:         float
    framework_version:   str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integration_id":      self.integration_id,
            "state":               self.state,
            "lifecycle_status":    self.lifecycle_status.to_dict(),
            "engine_status":       self.engine_status.to_dict(),
            "policy_status":       self.policy_status.to_dict(),
            "optimization_status": self.optimization_status.to_dict(),
            "snapshot_status":     self.snapshot_status.to_dict(),
            "overall_health":      self.overall_health,
            "statistics":          dict(self.statistics),
            "started_at":          self.started_at,
            "captured_at":         self.captured_at,
            "framework_version":   self.framework_version,
        }
