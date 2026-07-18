"""iios/execution/monitoring/integration/monitoring_integration_health.py
==================================================
Health check DTOs for the integration subsystem.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constants import ComponentType, HealthStatus, VERSION


@dataclass(frozen=True)
class ComponentHealth:
    """
    Immutable health status for a single sub-component.

    Fields
    ------
    component_type:    Type of sub-component.
    component_name:    Human-readable name.
    status:            Current health status.
    is_running:        Whether the component is currently running.
    error:             Optional description of any problem.
    last_checked_at:   Wall-time of the last check.
    framework_version: Version for compatibility.
    """

    component_type:    ComponentType
    component_name:    str
    status:            HealthStatus
    is_running:        bool
    error:             Optional[str] = None
    last_checked_at:   float         = field(default_factory=time.time, compare=False)
    framework_version: str           = VERSION

    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY

    @property
    def is_unhealthy(self) -> bool:
        return self.status in (HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_type":    self.component_type.value,
            "component_name":    self.component_name,
            "status":            self.status.value,
            "is_running":        self.is_running,
            "error":             self.error,
            "last_checked_at":   self.last_checked_at,
            "framework_version": self.framework_version,
        }


@dataclass(frozen=True)
class IntegrationHealth:
    """
    Immutable combined health snapshot for the entire integration subsystem.

    Fields
    ------
    overall_status:         Worst-case health across all components.
    component_health:       List of individual ComponentHealth records.
    is_fully_operational:   True only when all components are HEALTHY.
    degraded_components:    Names of components that are degraded/unhealthy.
    checked_at:             Wall-time of this health check.
    framework_version:      Version for compatibility.
    """

    overall_status:         HealthStatus
    component_health:       List[ComponentHealth]
    is_fully_operational:   bool
    degraded_components:    List[str]
    checked_at:             float         = field(default_factory=time.time, compare=False)
    framework_version:      str           = VERSION

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == HealthStatus.HEALTHY

    @property
    def has_unhealthy_components(self) -> bool:
        return bool(self.degraded_components)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status":       self.overall_status.value,
            "component_health":     [c.to_dict() for c in self.component_health],
            "is_fully_operational": self.is_fully_operational,
            "degraded_components":  list(self.degraded_components),
            "checked_at":           self.checked_at,
            "framework_version":    self.framework_version,
        }


def make_component_health(
    component_type: ComponentType,
    component_name: str,
    *,
    is_running: bool,
    error:      Optional[str] = None,
) -> ComponentHealth:
    """Build a ``ComponentHealth`` from a liveness check."""
    if error:
        status = HealthStatus.UNHEALTHY
    elif not is_running:
        status = HealthStatus.DEGRADED
    else:
        status = HealthStatus.HEALTHY
    return ComponentHealth(
        component_type = component_type,
        component_name = component_name,
        status         = status,
        is_running     = is_running,
        error          = error,
    )


def compute_integration_health(
    component_statuses: List[ComponentHealth],
) -> IntegrationHealth:
    """
    Aggregate individual component health into an overall IntegrationHealth.

    Rules:
    - All HEALTHY → overall HEALTHY
    - Any DEGRADED (none UNHEALTHY/UNKNOWN) → overall DEGRADED
    - Any UNHEALTHY or UNKNOWN → overall UNHEALTHY
    """
    from .constants import UNHEALTHY_COMPONENT_STATUSES

    degraded = [c.component_name for c in component_statuses if not c.is_healthy]
    has_unhealthy = any(c.status in UNHEALTHY_COMPONENT_STATUSES for c in component_statuses)
    all_healthy   = all(c.is_healthy for c in component_statuses)

    if all_healthy:
        overall = HealthStatus.HEALTHY
    elif has_unhealthy:
        overall = HealthStatus.UNHEALTHY
    else:
        overall = HealthStatus.DEGRADED

    return IntegrationHealth(
        overall_status       = overall,
        component_health     = list(component_statuses),
        is_fully_operational = all_healthy,
        degraded_components  = degraded,
    )
