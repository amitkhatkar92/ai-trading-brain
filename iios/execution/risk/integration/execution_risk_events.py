"""iios/execution/risk/integration/execution_risk_events.py
==================================================
IntegrationEvent and factory functions for integration subsystem events.

C6 Execution Intelligence — Phase 4, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import INTEGRATION_SYSTEM_ID, VERSION, IntegrationEventType


@dataclass(frozen=True)
class IntegrationEvent:
    """
    Immutable record of a single integration subsystem event.

    Published on the internal event bus.  External subsystems that need
    audit trails or real-time monitoring subscribe to these events.
    """

    event_id:     str
    event_type:   IntegrationEventType
    subsystem_id: str
    actor:        str
    occurred_at:  float
    version:      str
    metadata:     Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":     self.event_id,
            "event_type":   self.event_type.value,
            "subsystem_id": self.subsystem_id,
            "actor":        self.actor,
            "occurred_at":  self.occurred_at,
            "version":      self.version,
            "metadata":     dict(self.metadata),
        }


# ── Factory helpers ───────────────────────────────────────────────────────────

def _make_event(
    event_type: IntegrationEventType,
    actor:      str,
    **metadata,
) -> IntegrationEvent:
    return IntegrationEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        subsystem_id=INTEGRATION_SYSTEM_ID,
        actor=actor,
        occurred_at=time.time(),
        version=VERSION,
        metadata=metadata,
    )


def make_subsystem_initialized_event(actor: str = "engine", **metadata) -> IntegrationEvent:
    return _make_event(IntegrationEventType.SUBSYSTEM_INITIALIZED, actor, **metadata)


def make_subsystem_started_event(actor: str = "engine", **metadata) -> IntegrationEvent:
    return _make_event(IntegrationEventType.SUBSYSTEM_STARTED, actor, **metadata)


def make_evaluation_requested_event(
    request_id:  str = "",
    execution_id: str = "",
    actor:       str = "engine",
    **metadata,
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.EVALUATION_REQUESTED, actor,
        request_id=request_id, execution_id=execution_id, **metadata,
    )


def make_evaluation_completed_event(
    request_id:   str = "",
    response_id:  str = "",
    execution_id: str = "",
    approved:     bool = False,
    elapsed_ms:   float = 0.0,
    actor:        str = "engine",
    **metadata,
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.EVALUATION_COMPLETED, actor,
        request_id=request_id, response_id=response_id,
        execution_id=execution_id, approved=approved,
        elapsed_ms=elapsed_ms, **metadata,
    )


def make_snapshot_published_event(
    snapshot_id: str = "",
    risk_id:     str = "",
    actor:       str = "engine",
    **metadata,
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.SNAPSHOT_PUBLISHED, actor,
        snapshot_id=snapshot_id, risk_id=risk_id, **metadata,
    )


def make_validation_completed_event(
    request_id: str = "",
    is_valid:   bool = True,
    actor:      str = "validator",
    **metadata,
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.VALIDATION_COMPLETED, actor,
        request_id=request_id, is_valid=is_valid, **metadata,
    )


def make_health_updated_event(
    overall_healthy: bool = True,
    actor:           str = "health",
    **metadata,
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.HEALTH_UPDATED, actor,
        overall_healthy=overall_healthy, **metadata,
    )


def make_subsystem_stopped_event(actor: str = "engine", **metadata) -> IntegrationEvent:
    return _make_event(IntegrationEventType.SUBSYSTEM_STOPPED, actor, **metadata)
