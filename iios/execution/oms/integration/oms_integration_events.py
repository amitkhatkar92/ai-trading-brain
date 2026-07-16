"""iios/execution/oms/integration/oms_integration_events.py
==================================================
OMSEvent and factory functions for all OMS Integration domain events.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.oms.integration.constants import (
    ComponentType,
    IntegrationEventType,
    OMSState,
)


@dataclass(frozen=True)
class OMSEvent:
    """
    Immutable domain event emitted by the OMS Integration layer.

    Events are append-only and represent significant state changes.
    """
    event_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:     IntegrationEventType = IntegrationEventType.OMS_STARTED
    oms_state:      OMSState = OMSState.RUNNING
    component_type: ComponentType | None = None
    succeeded:      bool  = True
    detail:         str   = ""
    occurred_at:    float = field(default_factory=time.time)
    metadata:       dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":       self.event_id,
            "event_type":     self.event_type.value,
            "oms_state":      self.oms_state.value,
            "component_type": self.component_type.value if self.component_type else None,
            "succeeded":      self.succeeded,
            "detail":         self.detail,
            "occurred_at":    self.occurred_at,
        }


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

def make_oms_initialized(version: str = "1.0.0") -> OMSEvent:
    return OMSEvent(
        event_type  = IntegrationEventType.OMS_INITIALIZED,
        oms_state   = OMSState.RUNNING,
        detail      = f"OMS initialized (version={version})",
    )


def make_oms_started() -> OMSEvent:
    return OMSEvent(
        event_type = IntegrationEventType.OMS_STARTED,
        oms_state  = OMSState.RUNNING,
        detail     = "OMS Integration Engine started",
    )


def make_oms_stopped() -> OMSEvent:
    return OMSEvent(
        event_type = IntegrationEventType.OMS_STOPPED,
        oms_state  = OMSState.STOPPED,
        detail     = "OMS Integration Engine stopped",
    )


def make_oms_validated(is_valid: bool, detail: str = "") -> OMSEvent:
    return OMSEvent(
        event_type = IntegrationEventType.OMS_VALIDATED,
        oms_state  = OMSState.RUNNING,
        succeeded  = is_valid,
        detail     = detail or ("Validation passed" if is_valid else "Validation failed"),
    )


def make_snapshot_published(snapshot_id: str) -> OMSEvent:
    return OMSEvent(
        event_type = IntegrationEventType.SNAPSHOT_PUBLISHED,
        oms_state  = OMSState.RUNNING,
        detail     = f"Snapshot {snapshot_id} published",
    )


def make_component_registered(component_type: ComponentType) -> OMSEvent:
    return OMSEvent(
        event_type     = IntegrationEventType.COMPONENT_REGISTERED,
        oms_state      = OMSState.INITIALIZING,
        component_type = component_type,
        detail         = f"Component {component_type.value} registered",
    )


def make_component_failed(
    component_type: ComponentType,
    reason:         str = "",
) -> OMSEvent:
    return OMSEvent(
        event_type     = IntegrationEventType.COMPONENT_FAILED,
        oms_state      = OMSState.DEGRADED,
        component_type = component_type,
        succeeded      = False,
        detail         = f"Component {component_type.value} failed: {reason}",
    )
