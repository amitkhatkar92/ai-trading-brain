"""
decision_integration_health.py — iios.decision.integration
============================================================
Health monitoring for the Decision Integration subsystem.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from .constants import (
    ComponentHealth,
    ComponentType,
    OverallHealth,
    VERSION,
)


# ---------------------------------------------------------------------------
# Per-component health record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComponentHealthRecord:
    """Immutable health reading for a single component."""
    component_type: ComponentType
    health:         ComponentHealth
    is_available:   bool
    is_ready:       bool
    detail:         str  = ""
    checked_at:     datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> Dict:
        return {
            "component_type": self.component_type.value,
            "health":         self.health.value,
            "is_available":   self.is_available,
            "is_ready":       self.is_ready,
            "detail":         self.detail,
            "checked_at":     self.checked_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Aggregate health report
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionIntegrationHealth:
    """
    Aggregate health of the entire Decision Integration subsystem.

    Fields
    ------
    overall :          Aggregate health level.
    components :       Per-component health records keyed by component type.
    is_available :     True when the integration engine is running.
    is_degraded :      True when at least one optional component is unhealthy.
    detail :           Human-readable summary.
    checked_at :       UTC timestamp of the health check.
    framework_version: Framework version.
    """
    overall:           OverallHealth
    components:        Dict[str, ComponentHealthRecord]
    is_available:      bool
    is_degraded:       bool
    detail:            str      = ""
    checked_at:        datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version: str      = VERSION

    def to_dict(self) -> Dict:
        return {
            "overall":           self.overall.value,
            "components":        {k: v.to_dict() for k, v in self.components.items()},
            "is_available":      self.is_available,
            "is_degraded":       self.is_degraded,
            "detail":            self.detail,
            "checked_at":        self.checked_at.isoformat(),
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Health monitor
# ---------------------------------------------------------------------------

class DecisionIntegrationHealthMonitor:
    """
    Thread-safe health monitor for the Decision Integration subsystem.

    Usage
    -----
    ::

        monitor  = DecisionIntegrationHealthMonitor()
        registry = DecisionComponentRegistry(...)
        health   = monitor.check(registry, engine_is_running=True)
    """

    def __init__(self) -> None:
        self._lock:   threading.Lock                           = threading.Lock()
        self._last:   Optional[DecisionIntegrationHealth]      = None

    # ------------------------------------------------------------------
    # Check
    # ------------------------------------------------------------------

    def check(
        self,
        component_registry,
        engine_is_running: bool = False,
    ) -> DecisionIntegrationHealth:
        """
        Run a health check against *component_registry*.

        Parameters
        ----------
        component_registry : :class:`DecisionComponentRegistry`
        engine_is_running :  Whether the integration engine itself is running.

        Returns
        -------
        DecisionIntegrationHealth
        """
        component_records: Dict[str, ComponentHealthRecord] = {}
        critical_count = 0
        degraded_count = 0

        required_types = [ComponentType.LIFECYCLE, ComponentType.SNAPSHOT]
        optional_types = [
            ComponentType.ENGINE,
            ComponentType.POLICY_FRAMEWORK,
            ComponentType.OPTIMIZATION_FRAMEWORK,
        ]

        for ct in required_types + optional_types:
            available = (
                hasattr(component_registry, "is_available")
                and component_registry.is_available(ct)
            )
            ready = (
                available
                and hasattr(component_registry, "is_ready")
                and component_registry.is_ready(ct)
            )
            if not available:
                h = ComponentHealth.UNAVAILABLE
                if ct in required_types:
                    critical_count += 1
            elif not ready:
                h = ComponentHealth.CRITICAL
                if ct in required_types:
                    critical_count += 1
                else:
                    degraded_count += 1
            else:
                h = (
                    component_registry.health(ct)
                    if hasattr(component_registry, "health")
                    else ComponentHealth.HEALTHY
                )
                if h == ComponentHealth.CRITICAL and ct in required_types:
                    critical_count += 1
                elif h in (ComponentHealth.CRITICAL, ComponentHealth.DEGRADED):
                    degraded_count += 1

            component_records[ct.value] = ComponentHealthRecord(
                component_type = ct,
                health         = h,
                is_available   = available,
                is_ready       = ready,
            )

        # Compute overall
        if not engine_is_running:
            overall = OverallHealth.UNAVAILABLE
            detail  = "Integration engine is not running"
        elif critical_count > 0:
            overall = OverallHealth.CRITICAL
            detail  = f"{critical_count} required component(s) unhealthy"
        elif degraded_count > 0:
            overall = OverallHealth.DEGRADED
            detail  = f"{degraded_count} optional component(s) degraded"
        else:
            overall = OverallHealth.HEALTHY
            detail  = "All components healthy"

        health = DecisionIntegrationHealth(
            overall      = overall,
            components   = component_records,
            is_available = engine_is_running,
            is_degraded  = degraded_count > 0,
            detail       = detail,
        )
        with self._lock:
            self._last = health
        return health

    def last(self) -> Optional[DecisionIntegrationHealth]:
        """Return the most recently computed health report."""
        with self._lock:
            return self._last
