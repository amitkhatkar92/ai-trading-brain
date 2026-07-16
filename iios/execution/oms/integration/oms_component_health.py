"""iios/execution/oms/integration/oms_component_health.py
==================================================
ComponentHealth — health check result for one OMS component.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.integration.constants import ComponentType


@dataclass(frozen=True)
class ComponentHealth:
    """
    Immutable health check result for a single OMS component.

    Aggregated by OMSComponentRegistry.health_all() and
    embedded in OMSSnapshot.
    """
    component_type: ComponentType = ComponentType.ORDER_MANAGER
    component_id:   str           = ""
    is_healthy:     bool          = True
    latency_ms:     float         = 0.0
    message:        str           = ""
    checked_at:     float         = field(default_factory=time.time)
    metadata:       dict[str, Any] = field(default_factory=dict)

    @property
    def is_degraded(self) -> bool:
        return not self.is_healthy

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_type": self.component_type.value,
            "component_id":   self.component_id,
            "is_healthy":     self.is_healthy,
            "latency_ms":     round(self.latency_ms, 3),
            "message":        self.message,
            "checked_at":     self.checked_at,
        }
