"""
supervisor_events.py — iios.supervisor.engine
----------------------------------------------
Supervisor engine event value objects and factory functions.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    VERSION,
    ACTOR_ENGINE,
    ACTOR_SCHEDULER,
    ACTOR_DISPATCHER,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    EngineState,
    SupervisorEngineEventType,
    SupervisorWorkflowType,
)


# ---------------------------------------------------------------------------
# Event value object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SupervisorEngineEvent:
    """
    Immutable record of a supervisor engine lifecycle event.

    Fields
    ------
    event_id :         Unique event identifier.
    event_type :       Classification of this event.
    supervision_id :   Supervision run this event belongs to.
    subsystem_id :     Target subsystem identifier (may be empty).
    session_id :       Lifecycle session identifier (may be empty).
    pipeline_id :      Pipeline identifier (may be empty).
    engine_state :     Engine state at the time of the event.
    actor :            Component that triggered the event.
    payload :          Optional supplementary data.
    occurred_at :      Wall-clock time of the event.
    framework_version: Framework version string.
    """
    event_id:          str
    event_type:        SupervisorEngineEventType
    supervision_id:    str
    engine_state:      EngineState
    actor:             str
    subsystem_id:      str              = ""
    session_id:        str              = ""
    pipeline_id:       str              = ""
    payload:           Dict[str, Any]   = field(default_factory=dict)
    occurred_at:       float            = field(default_factory=time.time)
    framework_version: str              = VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "supervision_id":    self.supervision_id,
            "subsystem_id":      self.subsystem_id,
            "session_id":        self.session_id,
            "pipeline_id":       self.pipeline_id,
            "engine_state":      self.engine_state.value,
            "actor":             self.actor,
            "occurred_at":       self.occurred_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Convenience builder
# ---------------------------------------------------------------------------

def _make_event(
    event_type:     SupervisorEngineEventType,
    supervision_id: str,
    engine_state:   EngineState,
    actor:          str,
    *,
    subsystem_id: str              = "",
    session_id:   str              = "",
    pipeline_id:  str              = "",
    payload:      Optional[Dict[str, Any]] = None,
) -> SupervisorEngineEvent:
    return SupervisorEngineEvent(
        event_id       = str(uuid.uuid4()),
        event_type     = event_type,
        supervision_id = supervision_id,
        engine_state   = engine_state,
        actor          = actor,
        subsystem_id   = subsystem_id,
        session_id     = session_id,
        pipeline_id    = pipeline_id,
        payload        = dict(payload or {}),
    )


# ---------------------------------------------------------------------------
# Factory functions — one per SupervisorEngineEventType
# ---------------------------------------------------------------------------

def make_supervisor_engine_initialized(
    supervision_id: str,
    *,
    session_id: str = "",
    payload:    Optional[Dict[str, Any]] = None,
) -> SupervisorEngineEvent:
    return _make_event(
        SupervisorEngineEventType.SUPERVISOR_INITIALIZED,
        supervision_id, EngineState.INITIALIZING, ACTOR_ENGINE,
        session_id=session_id, payload=payload,
    )


def make_supervisor_engine_started(
    supervision_id: str,
    *,
    session_id:  str = "",
    pipeline_id: str = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> SupervisorEngineEvent:
    return _make_event(
        SupervisorEngineEventType.SUPERVISOR_STARTED,
        supervision_id, EngineState.DISCOVERING, ACTOR_ENGINE,
        session_id=session_id, pipeline_id=pipeline_id, payload=payload,
    )


def make_supervisor_engine_collected(
    supervision_id: str,
    *,
    session_id:  str = "",
    pipeline_id: str = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> SupervisorEngineEvent:
    return _make_event(
        SupervisorEngineEventType.SUPERVISOR_COLLECTED,
        supervision_id, EngineState.COLLECTING, ACTOR_ENGINE,
        session_id=session_id, pipeline_id=pipeline_id, payload=payload,
    )


def make_supervisor_engine_validated(
    supervision_id: str,
    *,
    session_id:  str = "",
    pipeline_id: str = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> SupervisorEngineEvent:
    return _make_event(
        SupervisorEngineEventType.SUPERVISOR_VALIDATED,
        supervision_id, EngineState.VALIDATING, ACTOR_ENGINE,
        session_id=session_id, pipeline_id=pipeline_id, payload=payload,
    )


def make_supervisor_engine_dispatched(
    supervision_id: str,
    *,
    session_id:  str = "",
    pipeline_id: str = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> SupervisorEngineEvent:
    return _make_event(
        SupervisorEngineEventType.SUPERVISOR_DISPATCHED,
        supervision_id, EngineState.DISPATCHING, ACTOR_DISPATCHER,
        session_id=session_id, pipeline_id=pipeline_id, payload=payload,
    )


def make_supervisor_engine_monitoring_started(
    supervision_id: str,
    *,
    session_id:  str = "",
    pipeline_id: str = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> SupervisorEngineEvent:
    return _make_event(
        SupervisorEngineEventType.SUPERVISOR_MONITORING_STARTED,
        supervision_id, EngineState.MONITORING, ACTOR_ENGINE,
        session_id=session_id, pipeline_id=pipeline_id, payload=payload,
    )


def make_supervisor_engine_published(
    supervision_id: str,
    *,
    session_id:  str = "",
    pipeline_id: str = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> SupervisorEngineEvent:
    return _make_event(
        SupervisorEngineEventType.SUPERVISOR_PUBLISHED,
        supervision_id, EngineState.PUBLISHING, ACTOR_ENGINE,
        session_id=session_id, pipeline_id=pipeline_id, payload=payload,
    )


def make_supervisor_engine_completed(
    supervision_id: str,
    *,
    session_id:  str = "",
    pipeline_id: str = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> SupervisorEngineEvent:
    return _make_event(
        SupervisorEngineEventType.SUPERVISOR_COMPLETED,
        supervision_id, EngineState.COMPLETED, ACTOR_ENGINE,
        session_id=session_id, pipeline_id=pipeline_id, payload=payload,
    )


def make_supervisor_engine_failed(
    supervision_id: str,
    *,
    session_id:  str = "",
    pipeline_id: str = "",
    error:       str = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> SupervisorEngineEvent:
    merged = dict(payload or {})
    if error:
        merged["error"] = error
    return _make_event(
        SupervisorEngineEventType.SUPERVISOR_FAILED,
        supervision_id, EngineState.FAILED, ACTOR_ENGINE,
        session_id=session_id, pipeline_id=pipeline_id, payload=merged,
    )


def make_supervisor_engine_stopped(
    supervision_id: str,
    *,
    session_id:  str = "",
    pipeline_id: str = "",
    payload:     Optional[Dict[str, Any]] = None,
) -> SupervisorEngineEvent:
    return _make_event(
        SupervisorEngineEventType.SUPERVISOR_STOPPED,
        supervision_id, EngineState.STOPPED, ACTOR_SYSTEM,
        session_id=session_id, pipeline_id=pipeline_id, payload=payload,
    )
