"""
decision_events.py — iios.decision.lifecycle
=============================================
Event value objects and eight factory functions for the decision lifecycle.

All event objects are immutable frozen dataclasses.

C9 Decision Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    LIFECYCLE_SYSTEM_ID,
    VERSION,
    DecisionEventType,
    DecisionState,
)


# ---------------------------------------------------------------------------
# Core event value object
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DecisionEvent:
    """
    Immutable decision lifecycle event.

    Fields
    ------
    event_id :          Unique identifier for this event.
    event_type :        One of the eight :class:`DecisionEventType` values.
    session_id :        Decision session that produced the event.
    decision_id :       Decision identifier.
    state :             Session state at the time of the event.
    source :            Identifier of the component that emitted the event.
    payload :           Free-form event payload.
    occurred_at :       Wall-clock time of event occurrence.
    framework_version : Framework version string.
    """
    event_id:          str
    event_type:        DecisionEventType
    session_id:        str
    decision_id:       str
    state:             DecisionState
    source:            str              = LIFECYCLE_SYSTEM_ID
    payload:           Dict[str, Any]   = field(default_factory=dict)
    occurred_at:       float            = field(default_factory=time.time)
    framework_version: str              = VERSION


# ---------------------------------------------------------------------------
# Internal factory helper
# ---------------------------------------------------------------------------
def _make_event(
    event_type:  DecisionEventType,
    session_id:  str,
    decision_id: str,
    state:       DecisionState,
    *,
    source:      str = LIFECYCLE_SYSTEM_ID,
    payload:     Optional[Dict[str, Any]] = None,
) -> DecisionEvent:
    return DecisionEvent(
        event_id    = str(uuid.uuid4()),
        event_type  = event_type,
        session_id  = session_id,
        decision_id = decision_id,
        state       = state,
        source      = source,
        payload     = payload or {},
    )


# ---------------------------------------------------------------------------
# Public factory functions — one per event type
# ---------------------------------------------------------------------------
def make_decision_created(
    session_id:  str,
    decision_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEvent:
    """Create a DECISION_CREATED event."""
    return _make_event(
        DecisionEventType.DECISION_CREATED,
        session_id, decision_id,
        DecisionState.CREATED,
        source=source, payload=payload,
    )


def make_decision_initialized(
    session_id:  str,
    decision_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEvent:
    """Create a DECISION_INITIALIZED event."""
    return _make_event(
        DecisionEventType.DECISION_INITIALIZED,
        session_id, decision_id,
        DecisionState.INITIALIZING,
        source=source, payload=payload,
    )


def make_decision_started(
    session_id:  str,
    decision_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEvent:
    """Create a DECISION_STARTED event (session became ACTIVE)."""
    return _make_event(
        DecisionEventType.DECISION_STARTED,
        session_id, decision_id,
        DecisionState.ACTIVE,
        source=source, payload=payload,
    )


def make_decision_paused(
    session_id:  str,
    decision_id: str,
    *,
    reason:  str = "",
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEvent:
    """Create a DECISION_PAUSED event."""
    p: Dict[str, Any] = {"reason": reason}
    if payload:
        p.update(payload)
    return _make_event(
        DecisionEventType.DECISION_PAUSED,
        session_id, decision_id,
        DecisionState.PAUSED,
        source=source, payload=p,
    )


def make_decision_resumed(
    session_id:  str,
    decision_id: str,
    *,
    resumed_to: DecisionState = DecisionState.COLLECTING,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEvent:
    """Create a DECISION_RESUMED event."""
    p: Dict[str, Any] = {"resumed_to": resumed_to.value}
    if payload:
        p.update(payload)
    return _make_event(
        DecisionEventType.DECISION_RESUMED,
        session_id, decision_id,
        resumed_to,
        source=source, payload=p,
    )


def make_decision_completed(
    session_id:  str,
    decision_id: str,
    *,
    duration_s:  Optional[float] = None,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEvent:
    """Create a DECISION_COMPLETED event."""
    p: Dict[str, Any] = {}
    if duration_s is not None:
        p["duration_s"] = duration_s
    if payload:
        p.update(payload)
    return _make_event(
        DecisionEventType.DECISION_COMPLETED,
        session_id, decision_id,
        DecisionState.COMPLETED,
        source=source, payload=p,
    )


def make_decision_failed(
    session_id:  str,
    decision_id: str,
    *,
    reason:  str = "",
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEvent:
    """Create a DECISION_FAILED event."""
    p: Dict[str, Any] = {"reason": reason}
    if payload:
        p.update(payload)
    return _make_event(
        DecisionEventType.DECISION_FAILED,
        session_id, decision_id,
        DecisionState.FAILED,
        source=source, payload=p,
    )


def make_decision_archived(
    session_id:  str,
    decision_id: str,
    *,
    source:  str = LIFECYCLE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEvent:
    """Create a DECISION_ARCHIVED event."""
    return _make_event(
        DecisionEventType.DECISION_ARCHIVED,
        session_id, decision_id,
        DecisionState.ARCHIVED,
        source=source, payload=payload,
    )
