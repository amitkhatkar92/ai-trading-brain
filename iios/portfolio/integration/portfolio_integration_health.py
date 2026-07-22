"""
portfolio_integration_health.py — iios.portfolio.integration
=============================================================
PortfolioIntegrationHealth — monitors health of all five integrated
subsystems and reports aggregate portfolio health.

C10 Portfolio Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, TYPE_CHECKING

from .constants import (
    INTEGRATION_SYSTEM_ID,
    VERSION,
    ComponentType,
    IntegrationHealth,
)
from .portfolio_integration_status import IntegrationComponentStatus

if TYPE_CHECKING:
    from .portfolio_component_registry import PortfolioComponentRegistry


class PortfolioIntegrationHealth:
    """
    Inspects and aggregates the health of all five integration components.

    Health checks are pull-based: each method interrogates the component's
    own health() / statistics() APIs and maps the result to
    IntegrationHealth enum values.
    """

    # ------------------------------------------------------------------
    # Component health checks
    # ------------------------------------------------------------------

    def check_lifecycle(
        self, component_registry: "PortfolioComponentRegistry"
    ) -> IntegrationComponentStatus:
        lc = component_registry.get_lifecycle()
        if lc is None:
            return IntegrationComponentStatus.unknown(ComponentType.LIFECYCLE.value)
        try:
            is_running = lc.lifecycle_state().value == "running"
            h = lc.health() if hasattr(lc, "health") else {}
            health = _map_health(h.get("is_healthy", is_running))
            return IntegrationComponentStatus(
                component_type = ComponentType.LIFECYCLE.value,
                is_running     = is_running,
                health         = health,
                started_at     = h.get("started_at", 0.0),
                last_event     = "running" if is_running else "stopped",
                metadata       = {},
            )
        except Exception as exc:
            return IntegrationComponentStatus(
                component_type = ComponentType.LIFECYCLE.value,
                is_running     = False,
                health         = IntegrationHealth.CRITICAL.value,
                started_at     = 0.0,
                last_event     = f"health check error: {exc}",
                metadata       = {},
            )

    def check_engine(
        self, component_registry: "PortfolioComponentRegistry"
    ) -> IntegrationComponentStatus:
        eng = component_registry.get_engine()
        if eng is None:
            return IntegrationComponentStatus.unknown(ComponentType.ENGINE.value)
        try:
            is_running = eng.lifecycle_state().value == "running"
            h = eng.health() if hasattr(eng, "health") else {}
            health = _map_health(h.get("is_healthy", is_running))
            return IntegrationComponentStatus(
                component_type = ComponentType.ENGINE.value,
                is_running     = is_running,
                health         = health,
                started_at     = h.get("started_at", 0.0),
                last_event     = "running" if is_running else "stopped",
                metadata       = {},
            )
        except Exception as exc:
            return IntegrationComponentStatus(
                component_type = ComponentType.ENGINE.value,
                is_running     = False,
                health         = IntegrationHealth.CRITICAL.value,
                started_at     = 0.0,
                last_event     = f"health check error: {exc}",
                metadata       = {},
            )

    def check_policy(
        self, component_registry: "PortfolioComponentRegistry"
    ) -> IntegrationComponentStatus:
        pol = component_registry.get_policy()
        if pol is None:
            return IntegrationComponentStatus.unknown(ComponentType.POLICY.value)
        try:
            is_running = pol.lifecycle_state().value == "running"
            h = pol.health() if hasattr(pol, "health") else {}
            health = _map_health(h.get("is_healthy", is_running))
            return IntegrationComponentStatus(
                component_type = ComponentType.POLICY.value,
                is_running     = is_running,
                health         = health,
                started_at     = h.get("started_at", 0.0),
                last_event     = "running" if is_running else "stopped",
                metadata       = {},
            )
        except Exception as exc:
            return IntegrationComponentStatus(
                component_type = ComponentType.POLICY.value,
                is_running     = False,
                health         = IntegrationHealth.CRITICAL.value,
                started_at     = 0.0,
                last_event     = f"health check error: {exc}",
                metadata       = {},
            )

    def check_optimization(
        self, component_registry: "PortfolioComponentRegistry"
    ) -> IntegrationComponentStatus:
        opt = component_registry.get_optimization()
        if opt is None:
            return IntegrationComponentStatus.unknown(ComponentType.OPTIMIZATION.value)
        try:
            is_running = opt.lifecycle_state().value == "running"
            h = opt.health() if hasattr(opt, "health") else {}
            health = _map_health(h.get("is_healthy", is_running))
            return IntegrationComponentStatus(
                component_type = ComponentType.OPTIMIZATION.value,
                is_running     = is_running,
                health         = health,
                started_at     = h.get("started_at", 0.0),
                last_event     = "running" if is_running else "stopped",
                metadata       = {},
            )
        except Exception as exc:
            return IntegrationComponentStatus(
                component_type = ComponentType.OPTIMIZATION.value,
                is_running     = False,
                health         = IntegrationHealth.CRITICAL.value,
                started_at     = 0.0,
                last_event     = f"health check error: {exc}",
                metadata       = {},
            )

    def check_snapshot(
        self, component_registry: "PortfolioComponentRegistry"
    ) -> IntegrationComponentStatus:
        snap = component_registry.get_snapshot_registry()
        if snap is None:
            return IntegrationComponentStatus.unknown(ComponentType.SNAPSHOT.value)
        try:
            count = snap.count()
            return IntegrationComponentStatus(
                component_type = ComponentType.SNAPSHOT.value,
                is_running     = True,
                health         = IntegrationHealth.HEALTHY.value,
                started_at     = 0.0,
                last_event     = f"snapshot_count={count}",
                metadata       = {"snapshot_count": count},
            )
        except Exception as exc:
            return IntegrationComponentStatus(
                component_type = ComponentType.SNAPSHOT.value,
                is_running     = False,
                health         = IntegrationHealth.CRITICAL.value,
                started_at     = 0.0,
                last_event     = f"health check error: {exc}",
                metadata       = {},
            )

    # ------------------------------------------------------------------
    # Overall health
    # ------------------------------------------------------------------

    def overall_health(self, statuses: list) -> str:
        """
        Aggregate component statuses into a single health value.

        Rules:
        - Any CRITICAL → CRITICAL
        - Any DEGRADED → DEGRADED
        - All HEALTHY → HEALTHY
        - All UNKNOWN → UNKNOWN
        - Mix of HEALTHY + UNKNOWN → DEGRADED
        """
        health_vals = {s.health for s in statuses}
        if IntegrationHealth.CRITICAL.value in health_vals:
            return IntegrationHealth.CRITICAL.value
        if IntegrationHealth.DEGRADED.value in health_vals:
            return IntegrationHealth.DEGRADED.value
        if all(h == IntegrationHealth.UNKNOWN.value for h in health_vals):
            return IntegrationHealth.UNKNOWN.value
        if all(h == IntegrationHealth.HEALTHY.value for h in health_vals):
            return IntegrationHealth.HEALTHY.value
        # Mix of healthy + unknown
        return IntegrationHealth.DEGRADED.value

    def report(
        self, component_registry: "PortfolioComponentRegistry"
    ) -> Dict[str, Any]:
        """Return a full health report dict."""
        lc    = self.check_lifecycle(component_registry)
        eng   = self.check_engine(component_registry)
        pol   = self.check_policy(component_registry)
        opt   = self.check_optimization(component_registry)
        snap  = self.check_snapshot(component_registry)
        overall = self.overall_health([lc, eng, pol, opt, snap])
        return {
            "overall":      overall,
            "lifecycle":    lc.to_dict(),
            "engine":       eng.to_dict(),
            "policy":       pol.to_dict(),
            "optimization": opt.to_dict(),
            "snapshot":     snap.to_dict(),
            "captured_at":  time.time(),
            "framework_version": VERSION,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_health(flag: Any) -> str:
    if flag is True:
        return IntegrationHealth.HEALTHY.value
    if flag is False:
        return IntegrationHealth.DEGRADED.value
    return IntegrationHealth.UNKNOWN.value
