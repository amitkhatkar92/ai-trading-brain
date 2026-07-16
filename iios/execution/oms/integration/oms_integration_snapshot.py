"""iios/execution/oms/integration/oms_integration_snapshot.py
==================================================
OMSSnapshot — immutable point-in-time view of the full OMS system.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.integration.constants import OMSState, VERSION
from iios.execution.oms.integration.oms_component_health import ComponentHealth
from iios.execution.oms.integration.oms_component_status import ComponentStatus
from iios.execution.oms.integration.oms_integration_statistics import IntegrationStatistics


@dataclass(frozen=True)
class OMSSnapshot:
    """
    Immutable, comprehensive snapshot of all OMS subsystems.

    Contains:
    - Per-component status and health
    - Aggregated statistics
    - Raw component snapshots (as dicts or typed objects)
    - OMS-level metadata

    Component snapshot fields accept Any to avoid tight coupling to
    internal component snapshot types.
    """
    snapshot_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    oms_state:            OMSState    = OMSState.RUNNING
    version:              str         = VERSION

    # Component snapshots — produced by each facade's .snapshot() method
    manager_snapshot:     Any   = None   # OrderManagerSnapshot
    book_snapshot:        Any   = None   # OrderBookSnapshot
    router_snapshot:      Any   = None   # dict from OrderRouter.snapshot()
    queue_snapshot:       Any   = None   # QueueSnapshot
    persistence_snapshot: Any   = None   # StorageSnapshot

    # Health and status
    component_health:     tuple[ComponentHealth, ...] = field(default_factory=tuple)
    component_status:     tuple[ComponentStatus, ...] = field(default_factory=tuple)

    # Aggregated statistics
    statistics:           IntegrationStatistics = field(
        default_factory=IntegrationStatistics
    )

    # Meta
    is_degraded:          bool  = False
    degraded_components:  tuple[str, ...] = field(default_factory=tuple)
    taken_at:             float = field(default_factory=time.time)
    metadata:             dict[str, Any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.oms_state == OMSState.RUNNING and not self.is_degraded

    @property
    def healthy_component_count(self) -> int:
        return sum(1 for h in self.component_health if h.is_healthy)

    @property
    def unhealthy_component_count(self) -> int:
        return sum(1 for h in self.component_health if h.is_degraded)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id":             self.snapshot_id,
            "oms_state":               self.oms_state.value,
            "version":                 self.version,
            "is_healthy":              self.is_healthy,
            "is_degraded":             self.is_degraded,
            "degraded_components":     list(self.degraded_components),
            "healthy_component_count": self.healthy_component_count,
            "statistics":              self.statistics.to_dict(),
            "component_health":        [h.to_dict() for h in self.component_health],
            "component_status":        [s.to_dict() for s in self.component_status],
            "taken_at":                self.taken_at,
        }
