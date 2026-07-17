"""iios/execution/risk/integration/execution_risk_health.py
==================================================
Health data objects for the Execution Risk Integration subsystem.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from iios.investment.workflow.engine_lifecycle import EngineState


@dataclass(frozen=True)
class ComponentHealth:
    """Point-in-time health of a single integration subsystem component."""

    component_type: str
    is_healthy:     bool
    is_running:     bool
    state:          str     # EngineState value
    last_checked:   float
    error:          Optional[str]
    metadata:       Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_type": self.component_type,
            "is_healthy":     self.is_healthy,
            "is_running":     self.is_running,
            "state":          self.state,
            "last_checked":   self.last_checked,
            "error":          self.error,
        }


@dataclass(frozen=True)
class SubsystemHealth:
    """
    Aggregated health of the Execution Risk Integration subsystem.

    overall_healthy is True only when ALL required components are healthy.
    """

    overall_healthy:  bool
    all_running:      bool
    component_health: Dict[str, ComponentHealth]  # component_type → ComponentHealth
    checked_at:       float
    subsystem_state:  str    # EngineState value
    metadata:         Dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def unhealthy_components(self) -> Dict[str, ComponentHealth]:
        return {k: v for k, v in self.component_health.items() if not v.is_healthy}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_healthy":    self.overall_healthy,
            "all_running":        self.all_running,
            "subsystem_state":    self.subsystem_state,
            "checked_at":         self.checked_at,
            "component_health":   {k: v.to_dict() for k, v in self.component_health.items()},
            "unhealthy_count":    len(self.unhealthy_components),
        }


# ── Factory helpers ───────────────────────────────────────────────────────────

def check_component_health(component: Any, component_type: str) -> ComponentHealth:
    """
    Inspect a LifecycleAwareMixin component and return a ComponentHealth.

    Uses getattr() throughout — safe if component is not lifecycle-aware.
    """
    try:
        state_obj  = None
        if hasattr(component, "lifecycle_state"):
            state_obj = component.lifecycle_state()
        state_val  = getattr(state_obj, "value", str(state_obj)) if state_obj else "unknown"
        is_running = (state_val == EngineState.RUNNING.value)
        is_healthy = is_running
        error      = None if is_running else f"Component state: {state_val}"
    except Exception as exc:
        state_val  = "unknown"
        is_running = False
        is_healthy = False
        error      = str(exc)

    return ComponentHealth(
        component_type=component_type,
        is_healthy=is_healthy,
        is_running=is_running,
        state=state_val,
        last_checked=time.time(),
        error=error,
    )


def make_subsystem_health(
    components:      Dict[str, Any],     # component_type_str → component
    subsystem_state: str,
) -> SubsystemHealth:
    """Build a SubsystemHealth by checking all provided components."""
    component_health: Dict[str, ComponentHealth] = {}
    for ctype, comp in components.items():
        component_health[ctype] = check_component_health(comp, ctype)

    all_running     = all(h.is_running for h in component_health.values())
    overall_healthy = all(h.is_healthy for h in component_health.values())

    return SubsystemHealth(
        overall_healthy=overall_healthy,
        all_running=all_running,
        component_health=component_health,
        checked_at=time.time(),
        subsystem_state=subsystem_state,
    )
