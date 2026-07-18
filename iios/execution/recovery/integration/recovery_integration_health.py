"""
iios/execution/recovery/integration/recovery_integration_health.py
==================================================================
IntegrationHealthMonitor — checks health of all wired components and
produces a ComponentHealthReport.

C7 Execution Recovery & Resilience — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING

from .constants import (
    COMP_ENGINE, COMP_FAILOVER, COMP_POLICY, COMP_SNAPSHOT,
    IntegrationHealth,
    VERSION,
)

if TYPE_CHECKING:
    from .recovery_component_registry import RecoveryComponentRegistry


@dataclass(frozen=True)
class ComponentHealthReport:
    """
    Immutable health report for all wired components and the integration
    subsystem as a whole.
    """

    report_id:       str
    captured_at:     float
    engine_health:   str     # ComponentStatus value
    policy_health:   str
    failover_health: str
    snapshot_health: str
    overall:         IntegrationHealth
    version:         str = VERSION

    @property
    def is_healthy(self) -> bool:
        return self.overall == IntegrationHealth.HEALTHY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id":       self.report_id,
            "captured_at":     self.captured_at,
            "engine_health":   self.engine_health,
            "policy_health":   self.policy_health,
            "failover_health": self.failover_health,
            "snapshot_health": self.snapshot_health,
            "overall":         self.overall.value,
            "is_healthy":      self.is_healthy,
        }


class IntegrationHealthMonitor:
    """Checks health of all wired components."""

    def check_health(
        self, components: "RecoveryComponentRegistry"
    ) -> ComponentHealthReport:
        """Produce a ComponentHealthReport from the current component states."""
        engine_h   = self._check(components.engine)
        policy_h   = self._check(components.policy_engine)
        failover_h = self._check(components.failover_engine)
        snapshot_h = self._check(components.snapshot_store)

        overall = self._derive_overall(engine_h, policy_h, failover_h, snapshot_h)

        return ComponentHealthReport(
            report_id       = str(uuid.uuid4()),
            captured_at     = time.time(),
            engine_health   = engine_h,
            policy_health   = policy_h,
            failover_health = failover_h,
            snapshot_health = snapshot_h,
            overall         = overall,
        )

    def _check(self, component: Optional[Any]) -> str:
        """Return "running" if the component is alive, else "stopped"."""
        if component is None:
            return "stopped"
        try:
            state = component.lifecycle_state()
            if str(state).lower() in ("running", "enginestate.running"):
                return "running"
            return "stopped"
        except Exception:
            return "error"

    def _derive_overall(self, *component_healths: str) -> IntegrationHealth:
        running = sum(1 for h in component_healths if h == "running")
        total   = len(component_healths)
        if running == total:
            return IntegrationHealth.HEALTHY
        if running >= total // 2:
            return IntegrationHealth.DEGRADED
        return IntegrationHealth.UNHEALTHY
