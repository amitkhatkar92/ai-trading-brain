"""iios/execution/gateway/integration/gateway_integration_health.py
==================================================
GatewayIntegrationHealthMonitor — checks and reports health of
all five gateway components.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Tuple

from iios.investment.workflow.engine_lifecycle import EngineState

from .constants import ComponentHealth, ComponentType

if TYPE_CHECKING:
    from .gateway_component_registry import GatewayComponentRegistry


@dataclass(frozen=True)
class ComponentHealthRecord:
    """Immutable health record for a single gateway component."""

    component_type: ComponentType
    component_id:   str
    health:         ComponentHealth
    message:        str
    last_checked_at: float = field(default_factory=time.time, compare=False)

    def to_dict(self):
        return {
            "component_type":  self.component_type.value,
            "component_id":    self.component_id,
            "health":          self.health.value,
            "message":         self.message,
            "last_checked_at": self.last_checked_at,
        }


@dataclass(frozen=True)
class IntegrationHealthReport:
    """
    Immutable report of the health of the full integration subsystem.

    Returned by GatewayIntegrationHealthMonitor.check().
    """

    overall_health: ComponentHealth
    components:     Tuple[ComponentHealthRecord, ...]
    created_at:     float = field(default_factory=time.time, compare=False)

    @property
    def is_healthy(self) -> bool:
        return self.overall_health == ComponentHealth.HEALTHY

    @property
    def unhealthy_components(self) -> Tuple[ComponentHealthRecord, ...]:
        return tuple(
            c for c in self.components
            if c.health != ComponentHealth.HEALTHY
        )

    @property
    def component_health_map(self) -> Dict[str, str]:
        return {c.component_type.value: c.health.value for c in self.components}

    def to_dict(self):
        return {
            "overall_health": self.overall_health.value,
            "is_healthy":     self.is_healthy,
            "components":     [c.to_dict() for c in self.components],
            "created_at":     self.created_at,
        }


class GatewayIntegrationHealthMonitor:
    """
    Checks each registered component and produces an IntegrationHealthReport.

    Stateless: every call to check() re-evaluates current state.
    """

    def check(
        self, registry: "GatewayComponentRegistry"
    ) -> IntegrationHealthReport:
        records: List[ComponentHealthRecord] = []

        records.append(self._check_lifecycle(registry))
        records.append(self._check_engine(registry))
        records.append(self._check_routing_engine(registry))
        records.append(self._check_broker_manager(registry))
        records.append(self._check_snapshot_store(registry))

        overall = self._aggregate(records)
        return IntegrationHealthReport(
            overall_health=overall,
            components=tuple(records),
        )

    # ── Per-component checks ──────────────────────────────────────────────────

    def _check_lifecycle(
        self, registry: "GatewayComponentRegistry"
    ) -> ComponentHealthRecord:
        try:
            lc = registry.lifecycle
            if lc is None:
                return self._offline(ComponentType.LIFECYCLE, "not registered")
            if lc.lifecycle_state() == EngineState.RUNNING:
                return self._healthy(ComponentType.LIFECYCLE, lc.SYSTEM_ID)
            return self._degraded(
                ComponentType.LIFECYCLE,
                lc.SYSTEM_ID,
                f"state={lc.lifecycle_state().value}",
            )
        except Exception as exc:
            return self._offline(ComponentType.LIFECYCLE, str(exc))

    def _check_engine(
        self, registry: "GatewayComponentRegistry"
    ) -> ComponentHealthRecord:
        try:
            eng = registry.engine
            if eng is None:
                return self._offline(ComponentType.ENGINE, "not registered")
            if eng.lifecycle_state() == EngineState.RUNNING:
                return self._healthy(ComponentType.ENGINE, eng.SYSTEM_ID)
            return self._degraded(
                ComponentType.ENGINE,
                eng.SYSTEM_ID,
                f"state={eng.lifecycle_state().value}",
            )
        except Exception as exc:
            return self._offline(ComponentType.ENGINE, str(exc))

    def _check_routing_engine(
        self, registry: "GatewayComponentRegistry"
    ) -> ComponentHealthRecord:
        try:
            re = registry.routing_engine
            if re is None:
                return self._offline(ComponentType.ROUTING_ENGINE, "not registered")
            if re.lifecycle_state() == EngineState.RUNNING:
                return self._healthy(ComponentType.ROUTING_ENGINE, re.SYSTEM_ID)
            return self._degraded(
                ComponentType.ROUTING_ENGINE,
                re.SYSTEM_ID,
                f"state={re.lifecycle_state().value}",
            )
        except Exception as exc:
            return self._offline(ComponentType.ROUTING_ENGINE, str(exc))

    def _check_broker_manager(
        self, registry: "GatewayComponentRegistry"
    ) -> ComponentHealthRecord:
        try:
            bm = registry.broker_manager
            if bm is None:
                return self._offline(ComponentType.BROKER_LAYER, "not registered")
            if bm.lifecycle_state() == EngineState.RUNNING:
                return self._healthy(ComponentType.BROKER_LAYER, bm.SYSTEM_ID)
            return self._degraded(
                ComponentType.BROKER_LAYER,
                bm.SYSTEM_ID,
                f"state={bm.lifecycle_state().value}",
            )
        except Exception as exc:
            return self._offline(ComponentType.BROKER_LAYER, str(exc))

    def _check_snapshot_store(
        self, registry: "GatewayComponentRegistry"
    ) -> ComponentHealthRecord:
        try:
            ss = registry.snapshot_store
            if ss is None:
                return self._offline(ComponentType.SNAPSHOT_STORE, "not registered")
            if ss.lifecycle_state() == EngineState.RUNNING:
                return self._healthy(ComponentType.SNAPSHOT_STORE, ss.SYSTEM_ID)
            return self._degraded(
                ComponentType.SNAPSHOT_STORE,
                ss.SYSTEM_ID,
                f"state={ss.lifecycle_state().value}",
            )
        except Exception as exc:
            return self._offline(ComponentType.SNAPSHOT_STORE, str(exc))

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _healthy(ct: ComponentType, cid: str) -> ComponentHealthRecord:
        return ComponentHealthRecord(
            component_type=ct,
            component_id=cid,
            health=ComponentHealth.HEALTHY,
            message="Running.",
        )

    @staticmethod
    def _degraded(ct: ComponentType, cid: str, detail: str) -> ComponentHealthRecord:
        return ComponentHealthRecord(
            component_type=ct,
            component_id=cid,
            health=ComponentHealth.DEGRADED,
            message=f"Degraded: {detail}",
        )

    @staticmethod
    def _offline(ct: ComponentType, detail: str) -> ComponentHealthRecord:
        return ComponentHealthRecord(
            component_type=ct,
            component_id="unknown",
            health=ComponentHealth.OFFLINE,
            message=f"Offline: {detail}",
        )

    @staticmethod
    def _aggregate(records: List[ComponentHealthRecord]) -> ComponentHealth:
        healths = {r.health for r in records}
        if ComponentHealth.OFFLINE in healths:
            return ComponentHealth.OFFLINE
        if ComponentHealth.DEGRADED in healths:
            return ComponentHealth.DEGRADED
        if all(r.health == ComponentHealth.HEALTHY for r in records):
            return ComponentHealth.HEALTHY
        return ComponentHealth.UNKNOWN
