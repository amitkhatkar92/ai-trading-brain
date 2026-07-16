"""iios/execution/positions/integration/position_integration_events.py
==================================================
IntegrationEvent and factory functions for the Position Integration
subsystem events.

Events: SubsystemInitialized, SubsystemStarted, SubsystemStopped,
        SnapshotPublished, ValidationCompleted,
        ComponentRegistered, ComponentFailed

C6 Execution Intelligence — Phase 3, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    ACTOR_INTEGRATION,
    ACTOR_SYSTEM,
    IntegrationEventType,
    VERSION,
)


@dataclass(frozen=True)
class IntegrationEvent:
    """
    Immutable domain event emitted by the Position Integration subsystem.

    Attributes
    ----------
    event_id
        UUID for this event.
    event_type
        :class:`IntegrationEventType` value string.
    component
        Component that produced the event (or ``""`` for subsystem-level events).
    occurred_at
        Unix timestamp.
    emitted_by
        Actor that triggered the event.
    correlation_id
        Optional external correlation ID.
    version
        Module version at emission time.
    metadata
        Arbitrary extra key-value pairs.
    """

    event_id:       str
    event_type:     IntegrationEventType
    component:      str
    occurred_at:    float
    emitted_by:     str
    correlation_id: str = ""
    version:        str = VERSION
    metadata:       Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":       self.event_id,
            "event_type":     self.event_type.value,
            "component":      self.component,
            "occurred_at":    self.occurred_at,
            "emitted_by":     self.emitted_by,
            "correlation_id": self.correlation_id,
            "version":        self.version,
            "metadata":       dict(self.metadata),
        }


# ── Factory functions ─────────────────────────────────────────────────────────

def _make(
    event_type:     IntegrationEventType,
    *,
    component:      str = "",
    emitted_by:     str = ACTOR_SYSTEM,
    correlation_id: str = "",
    metadata:       Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    return IntegrationEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        component=component,
        occurred_at=time.time(),
        emitted_by=emitted_by,
        correlation_id=correlation_id,
        metadata=metadata or {},
    )


def make_subsystem_initialized_event(
    *,
    emitted_by:     str = ACTOR_SYSTEM,
    correlation_id: str = "",
) -> IntegrationEvent:
    return _make(
        IntegrationEventType.SUBSYSTEM_INITIALIZED,
        emitted_by=emitted_by,
        correlation_id=correlation_id,
    )


def make_subsystem_started_event(
    *,
    emitted_by:     str = ACTOR_SYSTEM,
    correlation_id: str = "",
) -> IntegrationEvent:
    return _make(
        IntegrationEventType.SUBSYSTEM_STARTED,
        emitted_by=emitted_by,
        correlation_id=correlation_id,
    )


def make_subsystem_stopped_event(
    *,
    emitted_by:     str = ACTOR_SYSTEM,
    correlation_id: str = "",
) -> IntegrationEvent:
    return _make(
        IntegrationEventType.SUBSYSTEM_STOPPED,
        emitted_by=emitted_by,
        correlation_id=correlation_id,
    )


def make_snapshot_published_event(
    position_id:    str,
    *,
    emitted_by:     str = ACTOR_INTEGRATION,
    correlation_id: str = "",
) -> IntegrationEvent:
    return _make(
        IntegrationEventType.SNAPSHOT_PUBLISHED,
        emitted_by=emitted_by,
        correlation_id=correlation_id,
        metadata={"position_id": position_id},
    )


def make_validation_completed_event(
    is_valid:       bool,
    *,
    emitted_by:     str = ACTOR_INTEGRATION,
    correlation_id: str = "",
) -> IntegrationEvent:
    return _make(
        IntegrationEventType.VALIDATION_COMPLETED,
        emitted_by=emitted_by,
        correlation_id=correlation_id,
        metadata={"is_valid": is_valid},
    )


def make_component_registered_event(
    component_name: str,
    *,
    emitted_by:     str = ACTOR_SYSTEM,
    correlation_id: str = "",
) -> IntegrationEvent:
    return _make(
        IntegrationEventType.COMPONENT_REGISTERED,
        component=component_name,
        emitted_by=emitted_by,
        correlation_id=correlation_id,
    )


def make_component_failed_event(
    component_name: str,
    *,
    reason:         str = "",
    emitted_by:     str = ACTOR_SYSTEM,
    correlation_id: str = "",
) -> IntegrationEvent:
    return _make(
        IntegrationEventType.COMPONENT_FAILED,
        component=component_name,
        emitted_by=emitted_by,
        correlation_id=correlation_id,
        metadata={"reason": reason},
    )
