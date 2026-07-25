"""
workflow_gateway_health.py — iios.workflow.gateway
---------------------------------------------------
WorkflowGatewayHealth + WorkflowHealthSummary —
gateway health monitoring and reporting.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import ComponentStatus, GatewayHealthStatus, GatewayState


@dataclass(frozen=True)
class WorkflowHealthSummary:
    """
    Immutable point-in-time health summary for the Enterprise Workflow Gateway.
    """
    overall_status:    GatewayHealthStatus
    gateway_id:        str
    gateway_state:     GatewayState
    component_health:  Dict[str, str]     # component_name → ComponentStatus.value
    uptime_seconds:    float
    active_requests:   int
    captured_at:       str
    details:           Dict[str, Any]

    @property
    def is_healthy(self) -> bool:
        return self.overall_status == GatewayHealthStatus.HEALTHY

    @property
    def is_degraded(self) -> bool:
        return self.overall_status == GatewayHealthStatus.DEGRADED

    @property
    def is_unhealthy(self) -> bool:
        return self.overall_status == GatewayHealthStatus.UNHEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status":   self.overall_status.value,
            "gateway_id":       self.gateway_id,
            "gateway_state":    self.gateway_state.value,
            "component_health": dict(self.component_health),
            "uptime_seconds":   self.uptime_seconds,
            "active_requests":  self.active_requests,
            "captured_at":      self.captured_at,
            "is_healthy":       self.is_healthy,
            "is_degraded":      self.is_degraded,
            "is_unhealthy":     self.is_unhealthy,
        }


class WorkflowGatewayHealth:
    """
    Builds WorkflowHealthSummary from live gateway and component state.

    Stateless and thread-safe.
    """

    def report(
        self,
        gateway_id:        str,
        gateway_state:     GatewayState,
        component_statuses: Dict[str, ComponentStatus],
        started_at:        float,          # monotonic timestamp
        active_requests:   int            = 0,
        details:           Optional[Dict[str, Any]] = None,
    ) -> WorkflowHealthSummary:
        overall   = self._compute_overall(gateway_state, component_statuses)
        comp_dict = {k: v.value for k, v in component_statuses.items()}
        return WorkflowHealthSummary(
            overall_status   = overall,
            gateway_id       = gateway_id,
            gateway_state    = gateway_state,
            component_health = comp_dict,
            uptime_seconds   = round(time.monotonic() - started_at, 3),
            active_requests  = active_requests,
            captured_at      = datetime.now(tz=timezone.utc).isoformat(),
            details          = dict(details or {}),
        )

    def _compute_overall(
        self,
        state:     GatewayState,
        components: Dict[str, ComponentStatus],
    ) -> GatewayHealthStatus:
        if state in (GatewayState.STOPPED, GatewayState.FAILED):
            return GatewayHealthStatus.UNHEALTHY
        if state != GatewayState.RUNNING:
            return GatewayHealthStatus.DEGRADED

        unavailable = sum(
            1 for s in components.values()
            if s == ComponentStatus.UNAVAILABLE
        )
        degraded = sum(
            1 for s in components.values()
            if s == ComponentStatus.DEGRADED
        )

        if unavailable > 0:
            return GatewayHealthStatus.UNHEALTHY
        if degraded > 0:
            return GatewayHealthStatus.DEGRADED
        return GatewayHealthStatus.HEALTHY
