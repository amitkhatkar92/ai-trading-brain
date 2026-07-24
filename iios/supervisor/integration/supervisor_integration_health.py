"""
supervisor_integration_health.py — iios.supervisor.integration
--------------------------------------------------------------
Health assessment for the AI Supervisor Integration layer.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

from typing import Any, Dict

from .constants import IntegrationHealthStatus


class SupervisorIntegrationHealth:
    """
    Health assessor for the AI Supervisor Integration layer.

    Examines the integration engine's lifecycle state and the registered
    M1-M5 component states to produce a unified health report.
    """

    # ------------------------------------------------------------------
    # Primary assessment
    # ------------------------------------------------------------------

    def assess(
        self,
        engine:             Any,  # SupervisorIntegrationEngine (duck-typed)
        component_registry: Any,  # SupervisorComponentRegistry (duck-typed)
        statistics:         Any,  # SupervisorIntegrationStatistics (duck-typed)
    ) -> Dict[str, Any]:
        """
        Return a plain-dict health report.

        Parameters
        ----------
        engine :             The running integration engine (for lifecycle_state).
        component_registry : Component registry (for component liveness).
        statistics :         Statistics accumulator (for availability metrics).
        """
        lifecycle_state = "unknown"
        lc = getattr(engine, "lifecycle_state", None)
        if callable(lc):
            state_obj = lc()
            lifecycle_state = getattr(state_obj, "value", str(state_obj))

        # --- component health ---
        component_health: Dict[str, str] = {}
        if component_registry is not None:
            for name, comp in (component_registry.all_components() or {}).items():
                comp_lc = getattr(comp, "lifecycle_state", None)
                if callable(comp_lc):
                    s = comp_lc()
                    component_health[name] = getattr(s, "value", str(s))
                else:
                    component_health[name] = "unknown"

        # --- availability ---
        availability = 1.0
        if statistics is not None:
            fn = getattr(statistics, "platform_availability", None)
            if fn is not None:
                raw = fn() if callable(fn) else fn
                try:
                    availability = float(raw)
                except (TypeError, ValueError):
                    availability = 1.0

        # --- overall status ---
        status = self._compute_status(lifecycle_state, component_health, availability)

        return {
            "status":            status.value,
            "is_healthy":        status == IntegrationHealthStatus.HEALTHY,
            "lifecycle_state":   lifecycle_state,
            "component_health":  component_health,
            "platform_availability": availability,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _compute_status(
        self,
        lifecycle_state:  str,
        component_health: Dict[str, str],
        availability:     float,
    ) -> IntegrationHealthStatus:
        if lifecycle_state != "running":
            return IntegrationHealthStatus.UNKNOWN
        non_running = [
            v for v in component_health.values() if v not in ("running", "unknown")
        ]
        if len(non_running) >= len(component_health) and component_health:
            return IntegrationHealthStatus.CRITICAL
        if non_running or availability < 0.90:
            return IntegrationHealthStatus.DEGRADED
        return IntegrationHealthStatus.HEALTHY
