"""
decision_integration_events.py — iios.decision.integration
============================================================
Integration-layer event value objects and factory functions.

C9 Decision Intelligence — Phase 1, Module 6
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from .constants import IntegrationEventType, VERSION


# ---------------------------------------------------------------------------
# Event value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DecisionIntegrationEvent:
    """
    Immutable event emitted by :class:`DecisionIntegrationEngine`.

    Fields
    ------
    event_id :           Unique event identifier.
    event_type :         :class:`IntegrationEventType` value.
    request_id :         Originating request ID (empty when system-level).
    decision_id :        Decision ID (empty when system-level).
    session_id :         Lifecycle session ID (empty when system-level).
    snapshot_id :        M5 snapshot ID (empty when not applicable).
    source :             Actor that emitted the event.
    payload :            Arbitrary event payload.
    occurred_at :        UTC timestamp.
    framework_version :  Framework version.
    """

    event_id:          str
    event_type:        IntegrationEventType
    request_id:        str              = ""
    decision_id:       str              = ""
    session_id:        str              = ""
    snapshot_id:       str              = ""
    source:            str              = ""
    payload:           Dict[str, Any]   = field(default_factory=dict)
    occurred_at:       datetime         = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version: str              = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "request_id":        self.request_id,
            "decision_id":       self.decision_id,
            "session_id":        self.session_id,
            "snapshot_id":       self.snapshot_id,
            "source":            self.source,
            "payload":           dict(self.payload),
            "occurred_at":       self.occurred_at.isoformat(),
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

def _make(
    event_type:  IntegrationEventType,
    request_id:  str = "",
    decision_id: str = "",
    session_id:  str = "",
    snapshot_id: str = "",
    source:      str = "integration_engine",
    payload:     Optional[Dict[str, Any]] = None,
) -> DecisionIntegrationEvent:
    return DecisionIntegrationEvent(
        event_id    = str(uuid.uuid4()),
        event_type  = event_type,
        request_id  = request_id,
        decision_id = decision_id,
        session_id  = session_id,
        snapshot_id = snapshot_id,
        source      = source,
        payload     = payload or {},
    )


def make_integration_initialized(source: str = "system") -> DecisionIntegrationEvent:
    """Emitted once when the integration engine finishes initializing."""
    return _make(IntegrationEventType.INITIALIZED, source=source)


def make_integration_started(source: str = "system") -> DecisionIntegrationEvent:
    """Emitted when the integration engine starts."""
    return _make(IntegrationEventType.STARTED, source=source)


def make_integration_stopped(source: str = "system") -> DecisionIntegrationEvent:
    """Emitted when the integration engine stops."""
    return _make(IntegrationEventType.STOPPED, source=source)


def make_integration_restarted(source: str = "system") -> DecisionIntegrationEvent:
    """Emitted when the integration engine is restarted."""
    return _make(IntegrationEventType.RESTARTED, source=source)


def make_request_submitted(
    request_id:  str,
    decision_id: str,
    *,
    scope:    str = "",
    priority: str = "",
    source:   str = "integration_engine",
) -> DecisionIntegrationEvent:
    """Emitted when a new integration request is accepted."""
    return _make(
        IntegrationEventType.REQUEST_SUBMITTED,
        request_id  = request_id,
        decision_id = decision_id,
        source      = source,
        payload     = {"scope": scope, "priority": priority},
    )


def make_request_completed(
    request_id:  str,
    decision_id: str,
    session_id:  str,
    *,
    status:          str   = "",
    total_time_s:    float = 0.0,
    snapshot_id:     str   = "",
    source:          str   = "integration_engine",
) -> DecisionIntegrationEvent:
    """Emitted when an integration request completes successfully or partially."""
    return _make(
        IntegrationEventType.REQUEST_COMPLETED,
        request_id  = request_id,
        decision_id = decision_id,
        session_id  = session_id,
        snapshot_id = snapshot_id,
        source      = source,
        payload     = {
            "status":       status,
            "total_time_s": total_time_s,
        },
    )


def make_request_failed(
    request_id:  str,
    decision_id: str,
    session_id:  str,
    *,
    error_message: str  = "",
    error_code:    str  = "",
    source:        str  = "integration_engine",
) -> DecisionIntegrationEvent:
    """Emitted when an integration request fails."""
    return _make(
        IntegrationEventType.REQUEST_FAILED,
        request_id  = request_id,
        decision_id = decision_id,
        session_id  = session_id,
        source      = source,
        payload     = {
            "error_message": error_message,
            "error_code":    error_code,
        },
    )


def make_snapshot_published(
    request_id:  str,
    decision_id: str,
    session_id:  str,
    snapshot_id: str,
    *,
    decision_status: str   = "",
    decision_score:  float = 0.0,
    source:          str   = "integration_engine",
) -> DecisionIntegrationEvent:
    """Emitted when an M5 snapshot is published."""
    return _make(
        IntegrationEventType.SNAPSHOT_PUBLISHED,
        request_id  = request_id,
        decision_id = decision_id,
        session_id  = session_id,
        snapshot_id = snapshot_id,
        source      = source,
        payload     = {
            "decision_status": decision_status,
            "decision_score":  decision_score,
        },
    )


def make_health_changed(
    *,
    previous_health: str = "",
    current_health:  str = "",
    source:          str = "health_monitor",
) -> DecisionIntegrationEvent:
    """Emitted when the overall health changes."""
    return _make(
        IntegrationEventType.HEALTH_CHANGED,
        source  = source,
        payload = {
            "previous_health": previous_health,
            "current_health":  current_health,
        },
    )
