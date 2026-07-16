"""iios/execution/oms/integration/oms_component_status.py
==================================================
ComponentStatus — lifecycle status of one registered OMS component.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.integration.constants import ComponentType, OMSState


@dataclass(frozen=True)
class ComponentStatus:
    """
    Immutable status snapshot of one registered OMS component.

    Produced on demand by OMSComponentRegistry.status_all() and
    embedded in OMSSnapshot.
    """
    component_type:  ComponentType = ComponentType.ORDER_MANAGER
    component_id:    str           = ""
    lifecycle_state: str           = "unknown"   # raw string from EngineState.value
    is_running:      bool          = False
    checked_at:      float         = field(default_factory=time.time)
    metadata:        dict[str, Any] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.is_running

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_type":  self.component_type.value,
            "component_id":    self.component_id,
            "lifecycle_state": self.lifecycle_state,
            "is_running":      self.is_running,
            "is_healthy":      self.is_healthy,
            "checked_at":      self.checked_at,
        }
