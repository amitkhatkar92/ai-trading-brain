"""
decision_events.py — iios.decision.engine
===========================================
Event value objects and eight factory functions for the Decision Engine.

C9 Decision Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    ENGINE_SYSTEM_ID,
    VERSION,
    DecisionEngineEventType,
)


@dataclass(frozen=True)
class DecisionEngineEvent:
    """
    Immutable decision engine lifecycle event.

    Fields
    ------
    event_id :         Unique identifier.
    event_type :       One of the eight :class:`DecisionEngineEventType` values.
    session_id :       Lifecycle session identifier.
    request_id :       Source request identifier.
    decision_id :      Decision identifier.
    pipeline_id :      Processing pipeline identifier.
    source :           Component that emitted the event.
    payload :          Free-form payload.
    occurred_at :      Wall-clock time.
    framework_version: Framework version.
    """
    event_id:          str
    event_type:        DecisionEngineEventType
    session_id:        str
    request_id:        str
    decision_id:       str
    pipeline_id:       str                  = ""
    source:            str                  = ENGINE_SYSTEM_ID
    payload:           Dict[str, Any]       = field(default_factory=dict)
    occurred_at:       float                = field(default_factory=time.time)
    framework_version: str                  = VERSION


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------
def _make_event(
    event_type:  DecisionEngineEventType,
    session_id:  str,
    request_id:  str,
    decision_id: str,
    pipeline_id: str = "",
    *,
    source:  str = ENGINE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEngineEvent:
    return DecisionEngineEvent(
        event_id    = str(uuid.uuid4()),
        event_type  = event_type,
        session_id  = session_id,
        request_id  = request_id,
        decision_id = decision_id,
        pipeline_id = pipeline_id,
        source      = source,
        payload     = dict(payload or {}),
    )


# ---------------------------------------------------------------------------
# Public factory functions — one per event type
# ---------------------------------------------------------------------------
def make_decision_engine_initialized(
    session_id:  str,
    request_id:  str,
    decision_id: str,
    pipeline_id: str = "",
    *,
    source:  str = ENGINE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEngineEvent:
    """Create a DECISION_INITIALIZED event."""
    return _make_event(
        DecisionEngineEventType.DECISION_INITIALIZED,
        session_id, request_id, decision_id, pipeline_id,
        source=source, payload=payload,
    )


def make_decision_engine_started(
    session_id:  str,
    request_id:  str,
    decision_id: str,
    pipeline_id: str = "",
    *,
    source:  str = ENGINE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEngineEvent:
    """Create a DECISION_STARTED event."""
    return _make_event(
        DecisionEngineEventType.DECISION_STARTED,
        session_id, request_id, decision_id, pipeline_id,
        source=source, payload=payload,
    )


def make_decision_engine_collected(
    session_id:  str,
    request_id:  str,
    decision_id: str,
    pipeline_id: str = "",
    *,
    collection_time_s: float = 0.0,
    input_count:       int   = 0,
    source:  str = ENGINE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEngineEvent:
    """Create a DECISION_COLLECTED event."""
    p = dict(payload or {})
    p.setdefault("collection_time_s", collection_time_s)
    p.setdefault("input_count",       input_count)
    return _make_event(
        DecisionEngineEventType.DECISION_COLLECTED,
        session_id, request_id, decision_id, pipeline_id,
        source=source, payload=p,
    )


def make_decision_engine_dispatched(
    session_id:  str,
    request_id:  str,
    decision_id: str,
    pipeline_id: str = "",
    *,
    dispatch_time_s: float = 0.0,
    source:  str = ENGINE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEngineEvent:
    """Create a DECISION_DISPATCHED event."""
    p = dict(payload or {})
    p.setdefault("dispatch_time_s", dispatch_time_s)
    return _make_event(
        DecisionEngineEventType.DECISION_DISPATCHED,
        session_id, request_id, decision_id, pipeline_id,
        source=source, payload=p,
    )


def make_decision_engine_completed(
    session_id:  str,
    request_id:  str,
    decision_id: str,
    pipeline_id: str = "",
    *,
    total_time_s: float = 0.0,
    source:  str = ENGINE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEngineEvent:
    """Create a DECISION_COMPLETED event."""
    p = dict(payload or {})
    p.setdefault("total_time_s", total_time_s)
    return _make_event(
        DecisionEngineEventType.DECISION_COMPLETED,
        session_id, request_id, decision_id, pipeline_id,
        source=source, payload=p,
    )


def make_decision_engine_published(
    session_id:  str,
    request_id:  str,
    decision_id: str,
    pipeline_id: str = "",
    *,
    snapshot_id: str = "",
    source:  str = ENGINE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEngineEvent:
    """Create a DECISION_PUBLISHED event."""
    p = dict(payload or {})
    p.setdefault("snapshot_id", snapshot_id)
    return _make_event(
        DecisionEngineEventType.DECISION_PUBLISHED,
        session_id, request_id, decision_id, pipeline_id,
        source=source, payload=p,
    )


def make_decision_engine_failed(
    session_id:  str,
    request_id:  str,
    decision_id: str,
    pipeline_id: str = "",
    *,
    reason:  str = "",
    source:  str = ENGINE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEngineEvent:
    """Create a DECISION_FAILED event."""
    p = dict(payload or {})
    p.setdefault("reason", reason)
    return _make_event(
        DecisionEngineEventType.DECISION_FAILED,
        session_id, request_id, decision_id, pipeline_id,
        source=source, payload=p,
    )


def make_decision_engine_stopped(
    session_id:  str,
    request_id:  str,
    decision_id: str,
    pipeline_id: str = "",
    *,
    reason:  str = "",
    source:  str = ENGINE_SYSTEM_ID,
    payload: Optional[Dict[str, Any]] = None,
) -> DecisionEngineEvent:
    """Create a DECISION_STOPPED event."""
    p = dict(payload or {})
    p.setdefault("reason", reason)
    return _make_event(
        DecisionEngineEventType.DECISION_STOPPED,
        session_id, request_id, decision_id, pipeline_id,
        source=source, payload=p,
    )
