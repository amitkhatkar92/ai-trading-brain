"""
risk_integration_health.py — iios.risk.integration
====================================================
Health reporter for the Risk Integration layer.

C11 Risk Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import ComponentStatus, HealthStatus, VERSION
from .risk_component_registry import RiskComponentRegistry


@dataclass(frozen=True)
class RiskIntegrationHealthReport:
    """Immutable health report snapshot."""
    engine_id:          str
    health_status:      HealthStatus
    component_statuses: Dict[str, str]
    is_running:         bool
    uptime_s:           float
    requests_processed: int
    requests_failed:    int
    error_rate:         float
    framework_version:  str   = VERSION
    reported_at:        float = field(default_factory=time.time)

    @property
    def is_healthy(self) -> bool:
        return self.health_status == HealthStatus.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine_id":          self.engine_id,
            "health_status":      self.health_status.value,
            "component_statuses": self.component_statuses,
            "is_running":         self.is_running,
            "uptime_s":           self.uptime_s,
            "requests_processed": self.requests_processed,
            "requests_failed":    self.requests_failed,
            "error_rate":         self.error_rate,
            "framework_version":  self.framework_version,
            "reported_at":        self.reported_at,
        }


class RiskIntegrationHealth:
    """
    Health reporter for the Risk Integration Engine.

    Aggregates component statuses into a single
    :class:`RiskIntegrationHealthReport`.
    """

    def __init__(self, engine_id: str) -> None:
        self._engine_id = engine_id

    def report(
        self,
        *,
        component_registry: Optional[RiskComponentRegistry] = None,
        is_running:         bool      = False,
        started_at:         float     = 0.0,
        requests_processed: int       = 0,
        requests_failed:    int       = 0,
    ) -> RiskIntegrationHealthReport:
        """Build and return an immutable health report."""
        now     = time.time()
        uptime  = round(now - started_at, 2) if started_at > 0 and is_running else 0.0
        total   = requests_processed + requests_failed
        err_rate = requests_failed / total if total > 0 else 0.0

        component_statuses: Dict[str, str] = {}
        if component_registry is not None:
            component_statuses = component_registry.health_summary()

        # Determine overall health
        unavailable_count = sum(
            1 for v in component_statuses.values()
            if v == ComponentStatus.UNAVAILABLE.value
        )
        degraded_count = sum(
            1 for v in component_statuses.values()
            if v == ComponentStatus.DEGRADED.value
        )

        if not is_running:
            health = HealthStatus.UNHEALTHY
        elif unavailable_count > 0:
            health = HealthStatus.UNHEALTHY
        elif degraded_count > 0 or err_rate > 0.1:
            health = HealthStatus.DEGRADED
        else:
            health = HealthStatus.HEALTHY

        return RiskIntegrationHealthReport(
            engine_id          = self._engine_id,
            health_status      = health,
            component_statuses = component_statuses,
            is_running         = is_running,
            uptime_s           = uptime,
            requests_processed = requests_processed,
            requests_failed    = requests_failed,
            error_rate         = round(err_rate, 4),
        )
