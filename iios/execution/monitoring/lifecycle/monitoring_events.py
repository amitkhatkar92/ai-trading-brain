"""iios/execution/monitoring/lifecycle/monitoring_events.py
==================================================
MonitoringEvent — domain events emitted by the monitoring lifecycle.

C6 Execution Intelligence — Phase 6, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import ACTOR_LIFECYCLE, MonitoringEventType, VERSION


@dataclass(frozen=True)
class MonitoringEvent:
    """Immutable domain event emitted on a monitoring lifecycle transition."""

    event_id:    str
    event_type:  MonitoringEventType
    session_id:  str
    actor:       str
    occurred_at: float
    version:     str
    reason:      str = ""
    metadata:    Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "session_id":  self.session_id,
            "actor":       self.actor,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "reason":      self.reason,
        }


# ── Factory helpers ───────────────────────────────────────────────────────────

def _make_event(
    event_type: MonitoringEventType,
    session_id: str,
    *,
    actor:    str = ACTOR_LIFECYCLE,
    reason:   str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> MonitoringEvent:
    return MonitoringEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        session_id=session_id,
        actor=actor,
        occurred_at=time.time(),
        version=VERSION,
        reason=reason,
        metadata=metadata or {},
    )


def make_monitoring_created(session_id: str, **kw) -> MonitoringEvent:
    return _make_event(MonitoringEventType.MONITORING_CREATED, session_id, **kw)


def make_monitoring_initialized(session_id: str, **kw) -> MonitoringEvent:
    return _make_event(MonitoringEventType.MONITORING_INITIALIZED, session_id, **kw)


def make_monitoring_started(session_id: str, **kw) -> MonitoringEvent:
    return _make_event(MonitoringEventType.MONITORING_STARTED, session_id, **kw)


def make_monitoring_paused(session_id: str, **kw) -> MonitoringEvent:
    return _make_event(MonitoringEventType.MONITORING_PAUSED, session_id, **kw)


def make_monitoring_resumed(session_id: str, **kw) -> MonitoringEvent:
    return _make_event(MonitoringEventType.MONITORING_RESUMED, session_id, **kw)


def make_monitoring_stopped(session_id: str, **kw) -> MonitoringEvent:
    return _make_event(MonitoringEventType.MONITORING_STOPPED, session_id, **kw)


def make_monitoring_failed(session_id: str, **kw) -> MonitoringEvent:
    return _make_event(MonitoringEventType.MONITORING_FAILED, session_id, **kw)


def make_monitoring_archived(session_id: str, **kw) -> MonitoringEvent:
    return _make_event(MonitoringEventType.MONITORING_ARCHIVED, session_id, **kw)


# ── State → event factory map ─────────────────────────────────────────────────

from .constants import MonitoringState  # noqa: E402

_STATE_EVENT_FACTORY = {
    MonitoringState.INITIALIZING: make_monitoring_initialized,
    MonitoringState.ACTIVE:       make_monitoring_started,
    MonitoringState.PAUSED:       make_monitoring_paused,
    MonitoringState.RESUMING:     make_monitoring_resumed,
    MonitoringState.STOPPED:      make_monitoring_stopped,
    MonitoringState.FAILED:       make_monitoring_failed,
    MonitoringState.ARCHIVED:     make_monitoring_archived,
}
