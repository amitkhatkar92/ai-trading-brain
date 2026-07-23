"""
supervisor_events.py — iios.supervisor.lifecycle
-------------------------------------------------
Event value objects and factory functions for the supervisor lifecycle.

All event objects are immutable frozen dataclasses.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    SupervisorEventType,
    SupervisorState,
)


# ---------------------------------------------------------------------------
# Core event value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SupervisorEvent:
    """
    Immutable supervisor lifecycle event.

    Fields
    ------
    event_id :          Unique identifier for this event.
    event_type :        One of the :class:`SupervisorEventType` values.
    session_id :        Supervisor session that produced the event.
    supervisor_id :     Supervised entity identifier.
    workflow_id :       Workflow routing context.
    state :             Session state at the time of the event.
    source :            Identifier of the component that emitted the event.
    payload :           Free-form event payload.
    occurred_at :       Wall-clock time of event occurrence.
    framework_version : Framework version string.
    """
    event_id:          str
    event_type:        SupervisorEventType
    session_id:        str
    supervisor_id:     str
    workflow_id:       str            = ""
    state:             SupervisorState = SupervisorState.CREATED
    source:            str            = LIFECYCLE_SYSTEM_ID
    payload:           Dict[str, Any] = field(default_factory=dict)
    occurred_at:       float          = field(default_factory=time.time)
    framework_version: str            = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "session_id":        self.session_id,
            "supervisor_id":     self.supervisor_id,
            "workflow_id":       self.workflow_id,
            "state":             self.state.value,
            "source":            self.source,
            "payload":           dict(self.payload),
            "occurred_at":       self.occurred_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal factory helper
# ---------------------------------------------------------------------------

def _make_event(
    event_type:    SupervisorEventType,
    session_id:    str,
    supervisor_id: str,
    workflow_id:   str,
    state:         SupervisorState,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> SupervisorEvent:
    return SupervisorEvent(
        event_id      = str(uuid.uuid4()),
        event_type    = event_type,
        session_id    = session_id,
        supervisor_id = supervisor_id,
        workflow_id   = workflow_id,
        state         = state,
        source        = source,
        payload       = payload or {},
    )


# ---------------------------------------------------------------------------
# Public factory functions — one per event type (10 total)
# ---------------------------------------------------------------------------

def make_supervisor_created(
    session_id:    str,
    supervisor_id: str,
    workflow_id:   str = "",
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> SupervisorEvent:
    """Emitted when a new supervisor session is created (CREATED state)."""
    return _make_event(
        SupervisorEventType.SUPERVISOR_CREATED,
        session_id, supervisor_id, workflow_id,
        SupervisorState.CREATED,
        source=source, payload=payload,
    )


def make_supervisor_initialized(
    session_id:    str,
    supervisor_id: str,
    workflow_id:   str = "",
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> SupervisorEvent:
    """Emitted when a supervisor session enters INITIALIZING."""
    return _make_event(
        SupervisorEventType.SUPERVISOR_INITIALIZED,
        session_id, supervisor_id, workflow_id,
        SupervisorState.INITIALIZING,
        source=source, payload=payload,
    )


def make_supervisor_validated(
    session_id:    str,
    supervisor_id: str,
    workflow_id:   str = "",
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> SupervisorEvent:
    """Emitted when a supervisor session enters VALIDATING."""
    return _make_event(
        SupervisorEventType.SUPERVISOR_VALIDATED,
        session_id, supervisor_id, workflow_id,
        SupervisorState.VALIDATING,
        source=source, payload=payload,
    )


def make_supervisor_started(
    session_id:    str,
    supervisor_id: str,
    workflow_id:   str = "",
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> SupervisorEvent:
    """Emitted when a supervisor session enters SUPERVISING."""
    return _make_event(
        SupervisorEventType.SUPERVISOR_STARTED,
        session_id, supervisor_id, workflow_id,
        SupervisorState.SUPERVISING,
        source=source, payload=payload,
    )


def make_supervisor_monitoring_started(
    session_id:    str,
    supervisor_id: str,
    workflow_id:   str = "",
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> SupervisorEvent:
    """Emitted when a supervisor session enters MONITORING."""
    return _make_event(
        SupervisorEventType.SUPERVISOR_MONITORING_STARTED,
        session_id, supervisor_id, workflow_id,
        SupervisorState.MONITORING,
        source=source, payload=payload,
    )


def make_supervisor_paused(
    session_id:    str,
    supervisor_id: str,
    workflow_id:   str = "",
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> SupervisorEvent:
    """Emitted when a supervisor session enters PAUSED."""
    return _make_event(
        SupervisorEventType.SUPERVISOR_PAUSED,
        session_id, supervisor_id, workflow_id,
        SupervisorState.PAUSED,
        source=source, payload=payload,
    )


def make_supervisor_resumed(
    session_id:    str,
    supervisor_id: str,
    workflow_id:   str = "",
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> SupervisorEvent:
    """Emitted when a supervisor session enters RESUMING."""
    return _make_event(
        SupervisorEventType.SUPERVISOR_RESUMED,
        session_id, supervisor_id, workflow_id,
        SupervisorState.RESUMING,
        source=source, payload=payload,
    )


def make_supervisor_completed(
    session_id:    str,
    supervisor_id: str,
    workflow_id:   str = "",
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> SupervisorEvent:
    """Emitted when a supervisor session enters COMPLETED."""
    return _make_event(
        SupervisorEventType.SUPERVISOR_COMPLETED,
        session_id, supervisor_id, workflow_id,
        SupervisorState.COMPLETED,
        source=source, payload=payload,
    )


def make_supervisor_failed(
    session_id:    str,
    supervisor_id: str,
    workflow_id:   str = "",
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> SupervisorEvent:
    """Emitted when a supervisor session enters FAILED."""
    return _make_event(
        SupervisorEventType.SUPERVISOR_FAILED,
        session_id, supervisor_id, workflow_id,
        SupervisorState.FAILED,
        source=source, payload=payload,
    )


def make_supervisor_archived(
    session_id:    str,
    supervisor_id: str,
    workflow_id:   str = "",
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> SupervisorEvent:
    """Emitted when a supervisor session enters ARCHIVED."""
    return _make_event(
        SupervisorEventType.SUPERVISOR_ARCHIVED,
        session_id, supervisor_id, workflow_id,
        SupervisorState.ARCHIVED,
        source=source, payload=payload,
    )
