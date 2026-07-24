"""
supervisor_integration_events.py — iios.supervisor.integration
---------------------------------------------------------------
Domain event value object and 8 factory functions for the integration layer.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import IntegrationEventType, VERSION


@dataclass(frozen=True)
class SupervisorIntegrationEvent:
    """
    Immutable domain event emitted by the AI Supervisor Integration layer.

    Fields
    ------
    event_id :        Unique event identifier.
    event_type :      Classification from :class:`IntegrationEventType`.
    integration_id :  Owning integration run identifier.
    request_id :      Originating request identifier (if applicable).
    payload :         Event-specific key-value payload.
    emitted_at :      Wall-clock event creation time.
    framework_version: Framework version string.
    """
    event_id:          str
    event_type:        IntegrationEventType
    integration_id:    str
    request_id:        str
    payload:           Dict[str, Any]
    emitted_at:        float = field(default_factory=time.time)
    framework_version: str   = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":         self.event_id,
            "event_type":       self.event_type.value,
            "integration_id":   self.integration_id,
            "request_id":       self.request_id,
            "payload":          self.payload,
            "emitted_at":       self.emitted_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal builder
# ---------------------------------------------------------------------------


def _make_event(
    event_type:     IntegrationEventType,
    integration_id: str,
    request_id:     str     = "",
    payload:        Optional[Dict[str, Any]] = None,
    *,
    event_id: Optional[str] = None,
) -> SupervisorIntegrationEvent:
    return SupervisorIntegrationEvent(
        event_id       = event_id or str(uuid.uuid4()),
        event_type     = event_type,
        integration_id = integration_id,
        request_id     = request_id,
        payload        = payload or {},
    )


# ---------------------------------------------------------------------------
# Public factory functions (one per IntegrationEventType)
# ---------------------------------------------------------------------------


def make_integration_initialized_event(
    integration_id: str,
    *,
    version: str = VERSION,
    event_id: Optional[str] = None,
) -> SupervisorIntegrationEvent:
    """Emitted once when the integration engine finishes initialising."""
    return _make_event(
        IntegrationEventType.INTEGRATION_INITIALIZED,
        integration_id,
        payload={"version": version},
        event_id=event_id,
    )


def make_integration_started_event(
    integration_id: str,
    request_id:     str,
    *,
    mode:     str               = "full",
    event_id: Optional[str]    = None,
    payload:  Optional[Dict[str, Any]] = None,
) -> SupervisorIntegrationEvent:
    """Emitted at the start of each integration workflow execution."""
    p = {"mode": mode}
    if payload:
        p.update(payload)
    return _make_event(
        IntegrationEventType.INTEGRATION_STARTED,
        integration_id,
        request_id,
        payload=p,
        event_id=event_id,
    )


def make_integration_validated_event(
    integration_id: str,
    request_id:     str,
    *,
    is_valid: bool             = True,
    event_id: Optional[str]   = None,
) -> SupervisorIntegrationEvent:
    """Emitted after the request passes (or fails) validation."""
    return _make_event(
        IntegrationEventType.INTEGRATION_VALIDATED,
        integration_id,
        request_id,
        payload={"is_valid": is_valid},
        event_id=event_id,
    )


def make_integration_executed_event(
    integration_id: str,
    request_id:     str,
    *,
    phase:    str              = "",
    elapsed_s: float           = 0.0,
    event_id: Optional[str]   = None,
) -> SupervisorIntegrationEvent:
    """Emitted after each workflow phase completes execution."""
    return _make_event(
        IntegrationEventType.INTEGRATION_EXECUTED,
        integration_id,
        request_id,
        payload={"phase": phase, "elapsed_s": elapsed_s},
        event_id=event_id,
    )


def make_snapshot_published_event(
    integration_id: str,
    request_id:     str,
    *,
    snapshot_id: str           = "",
    event_id: Optional[str]   = None,
) -> SupervisorIntegrationEvent:
    """Emitted when the M5 supervisor snapshot is successfully published."""
    return _make_event(
        IntegrationEventType.SNAPSHOT_PUBLISHED,
        integration_id,
        request_id,
        payload={"snapshot_id": snapshot_id},
        event_id=event_id,
    )


def make_integration_completed_event(
    integration_id: str,
    request_id:     str,
    *,
    processing_time_s: float   = 0.0,
    event_id: Optional[str]   = None,
) -> SupervisorIntegrationEvent:
    """Emitted when the integration workflow completes successfully."""
    return _make_event(
        IntegrationEventType.INTEGRATION_COMPLETED,
        integration_id,
        request_id,
        payload={"processing_time_s": processing_time_s},
        event_id=event_id,
    )


def make_integration_failed_event(
    integration_id: str,
    request_id:     str,
    *,
    error:    str              = "",
    event_id: Optional[str]   = None,
) -> SupervisorIntegrationEvent:
    """Emitted when the integration workflow encounters a terminal error."""
    return _make_event(
        IntegrationEventType.INTEGRATION_FAILED,
        integration_id,
        request_id,
        payload={"error": error},
        event_id=event_id,
    )


def make_integration_stopped_event(
    integration_id: str,
    *,
    event_id: Optional[str] = None,
) -> SupervisorIntegrationEvent:
    """Emitted when the integration engine stops."""
    return _make_event(
        IntegrationEventType.INTEGRATION_STOPPED,
        integration_id,
        event_id=event_id,
    )
