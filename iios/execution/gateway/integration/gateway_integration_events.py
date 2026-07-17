"""iios/execution/gateway/integration/gateway_integration_events.py
==================================================
IntegrationEvent — domain events emitted by the
Gateway Integration Layer.

C6 Execution Intelligence — Phase 5, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    ACTOR_INTEGRATION_SYSTEM,
    IntegrationEventType,
    VERSION,
)


@dataclass(frozen=True)
class IntegrationEvent:
    """
    Immutable domain event emitted by the integration layer.

    Appended to GatewayIntegrationHistory and fired to all
    registered event listeners.
    """

    event_id:       str
    event_type:     IntegrationEventType
    integration_id: str
    actor:          str
    occurred_at:    float
    version:        str

    # Optional correlation
    request_id:  Optional[str] = None

    # Arbitrary context
    metadata: Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":       self.event_id,
            "event_type":     self.event_type.value,
            "integration_id": self.integration_id,
            "actor":          self.actor,
            "occurred_at":    self.occurred_at,
            "version":        self.version,
            "request_id":     self.request_id,
        }


# ── Factory functions ─────────────────────────────────────────────────────────

def _make_event(
    event_type:     IntegrationEventType,
    integration_id: str,
    *,
    request_id: Optional[str] = None,
    actor:      str = ACTOR_INTEGRATION_SYSTEM,
    metadata:   Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    return IntegrationEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        integration_id=integration_id,
        actor=actor,
        occurred_at=time.time(),
        version=VERSION,
        request_id=request_id,
        metadata=metadata or {},
    )


def make_subsystem_initialized_event(
    integration_id: str, **kwargs: Any
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.SUBSYSTEM_INITIALIZED, integration_id, **kwargs
    )


def make_subsystem_started_event(
    integration_id: str, **kwargs: Any
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.SUBSYSTEM_STARTED, integration_id, **kwargs
    )


def make_subsystem_stopped_event(
    integration_id: str, **kwargs: Any
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.SUBSYSTEM_STOPPED, integration_id, **kwargs
    )


def make_request_received_event(
    integration_id: str, request_id: str, **kwargs: Any
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.GATEWAY_REQUEST_RECEIVED,
        integration_id,
        request_id=request_id,
        **kwargs,
    )


def make_request_validated_event(
    integration_id: str, request_id: str, **kwargs: Any
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.GATEWAY_REQUEST_VALIDATED,
        integration_id,
        request_id=request_id,
        **kwargs,
    )


def make_request_routed_event(
    integration_id: str, request_id: str, **kwargs: Any
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.GATEWAY_REQUEST_ROUTED,
        integration_id,
        request_id=request_id,
        **kwargs,
    )


def make_request_completed_event(
    integration_id: str, request_id: str, **kwargs: Any
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.GATEWAY_REQUEST_COMPLETED,
        integration_id,
        request_id=request_id,
        **kwargs,
    )


def make_request_failed_event(
    integration_id: str, request_id: str, **kwargs: Any
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.GATEWAY_REQUEST_FAILED,
        integration_id,
        request_id=request_id,
        **kwargs,
    )


def make_snapshot_published_event(
    integration_id: str,
    *,
    request_id: Optional[str] = None,
    **kwargs: Any,
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.SNAPSHOT_PUBLISHED,
        integration_id,
        request_id=request_id,
        **kwargs,
    )


def make_health_updated_event(
    integration_id: str, **kwargs: Any
) -> IntegrationEvent:
    return _make_event(
        IntegrationEventType.HEALTH_UPDATED, integration_id, **kwargs
    )
