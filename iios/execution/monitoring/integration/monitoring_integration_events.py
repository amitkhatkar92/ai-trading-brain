"""iios/execution/monitoring/integration/monitoring_integration_events.py
==================================================
IntegrationEvent — immutable domain event emitted by the integration
engine.

C6 Execution Intelligence — Phase 6, Module 6
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import IntegrationEventType, VERSION


@dataclass(frozen=True)
class IntegrationEvent:
    """
    Immutable domain event emitted by ExecutionMonitoringIntegrationEngine.

    Fields
    ------
    event_id:          Unique event ID.
    event_type:        Type of integration event.
    session_id:        Session this event relates to.
    actor:             Component that generated the event.
    occurred_at:       Wall-time of the event.
    version:           Framework version.
    reason:            Optional human-readable context.
    metadata:          Optional additional data.
    """

    event_id:   str
    event_type: IntegrationEventType
    session_id: str
    actor:      str
    occurred_at:float
    version:    str
    reason:     Optional[str]        = None
    metadata:   Dict[str, Any]       = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "actor":      self.actor,
            "occurred_at":self.occurred_at,
            "version":    self.version,
            "reason":     self.reason,
            "metadata":   dict(self.metadata),
        }


# ── Factory helpers ───────────────────────────────────────────────────────────

def _make_event(
    event_type: IntegrationEventType,
    session_id: str,
    *,
    actor:      str             = "iios:execution:monitoring:integration",
    reason:     Optional[str]   = None,
    metadata:   Optional[Dict[str, Any]] = None,
) -> IntegrationEvent:
    return IntegrationEvent(
        event_id   = str(uuid.uuid4()),
        event_type = event_type,
        session_id = session_id,
        actor      = actor,
        occurred_at= time.time(),
        version    = VERSION,
        reason     = reason,
        metadata   = metadata or {},
    )


def make_monitoring_initialized(session_id: str, *, actor: str = "iios:execution:monitoring:integration", reason: Optional[str] = None) -> IntegrationEvent:
    return _make_event(IntegrationEventType.MONITORING_INITIALIZED, session_id, actor=actor, reason=reason)


def make_monitoring_started(session_id: str, *, actor: str = "iios:execution:monitoring:integration", reason: Optional[str] = None) -> IntegrationEvent:
    return _make_event(IntegrationEventType.MONITORING_STARTED, session_id, actor=actor, reason=reason)


def make_monitoring_completed(session_id: str, *, actor: str = "iios:execution:monitoring:integration", reason: Optional[str] = None) -> IntegrationEvent:
    return _make_event(IntegrationEventType.MONITORING_COMPLETED, session_id, actor=actor, reason=reason)


def make_monitoring_stopped(session_id: str, *, actor: str = "iios:execution:monitoring:integration", reason: Optional[str] = None) -> IntegrationEvent:
    return _make_event(IntegrationEventType.MONITORING_STOPPED, session_id, actor=actor, reason=reason)


def make_monitoring_restarted(session_id: str, *, actor: str = "iios:execution:monitoring:integration", reason: Optional[str] = None) -> IntegrationEvent:
    return _make_event(IntegrationEventType.MONITORING_RESTARTED, session_id, actor=actor, reason=reason)


def make_monitoring_validated(session_id: str, *, actor: str = "iios:execution:monitoring:integration", reason: Optional[str] = None) -> IntegrationEvent:
    return _make_event(IntegrationEventType.MONITORING_VALIDATED, session_id, actor=actor, reason=reason)


def make_monitoring_health_changed(session_id: str, *, actor: str = "iios:execution:monitoring:integration", reason: Optional[str] = None) -> IntegrationEvent:
    return _make_event(IntegrationEventType.MONITORING_HEALTH_CHANGED, session_id, actor=actor, reason=reason)


def make_monitoring_snapshot_published(session_id: str, *, actor: str = "iios:execution:monitoring:integration", reason: Optional[str] = None) -> IntegrationEvent:
    return _make_event(IntegrationEventType.MONITORING_SNAPSHOT_PUBLISHED, session_id, actor=actor, reason=reason)
