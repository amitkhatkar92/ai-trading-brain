"""
iios/execution/analytics/engine/analytics_events.py
====================================================
EngineAnalyticsEvent — immutable domain events emitted by the Execution
Analytics Engine.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import ACTOR_ENGINE, VERSION, EngineEventType


@dataclass(frozen=True)
class EngineAnalyticsEvent:
    """
    Immutable domain event emitted by the Execution Analytics Engine on
    every workflow phase transition.

    Fields
    ------
    event_id:    Globally unique event ID.
    event_type:  Classification of this event.
    request_id:  Owning analytics request.
    actor:       Component that emitted the event.
    occurred_at: Wall-time of the event.
    version:     Framework version.
    reason:      Optional human-readable context.
    metadata:    Optional supplementary data.
    """

    event_id:    str
    event_type:  EngineEventType
    request_id:  str
    actor:       str
    occurred_at: float
    version:     str
    reason:      Optional[str]  = None
    metadata:    Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "request_id":  self.request_id,
            "actor":       self.actor,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "reason":      self.reason,
        }


# ── Internal factory helper ───────────────────────────────────────────────────

def _make_event(
    event_type: EngineEventType,
    request_id: str,
    *,
    actor:    str                      = ACTOR_ENGINE,
    reason:   Optional[str]            = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EngineAnalyticsEvent:
    return EngineAnalyticsEvent(
        event_id    = str(uuid.uuid4()),
        event_type  = event_type,
        request_id  = request_id,
        actor       = actor,
        occurred_at = time.time(),
        version     = VERSION,
        reason      = reason,
        metadata    = metadata or {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_analytics_engine_initialized(
    request_id: str,
    *,
    actor:    str             = ACTOR_ENGINE,
    reason:   Optional[str]   = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EngineAnalyticsEvent:
    return _make_event(EngineEventType.ANALYTICS_INITIALIZED, request_id,
                       actor=actor, reason=reason, metadata=metadata)


def make_analytics_engine_started(
    request_id: str,
    *,
    actor:    str             = ACTOR_ENGINE,
    reason:   Optional[str]   = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EngineAnalyticsEvent:
    return _make_event(EngineEventType.ANALYTICS_STARTED, request_id,
                       actor=actor, reason=reason, metadata=metadata)


def make_analytics_engine_collected(
    request_id: str,
    *,
    actor:    str             = ACTOR_ENGINE,
    reason:   Optional[str]   = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EngineAnalyticsEvent:
    return _make_event(EngineEventType.ANALYTICS_COLLECTED, request_id,
                       actor=actor, reason=reason, metadata=metadata)


def make_analytics_engine_dispatched(
    request_id: str,
    *,
    actor:    str             = ACTOR_ENGINE,
    reason:   Optional[str]   = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EngineAnalyticsEvent:
    return _make_event(EngineEventType.ANALYTICS_DISPATCHED, request_id,
                       actor=actor, reason=reason, metadata=metadata)


def make_analytics_engine_completed(
    request_id: str,
    *,
    actor:    str             = ACTOR_ENGINE,
    reason:   Optional[str]   = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EngineAnalyticsEvent:
    return _make_event(EngineEventType.ANALYTICS_COMPLETED, request_id,
                       actor=actor, reason=reason, metadata=metadata)


def make_analytics_engine_published(
    request_id: str,
    *,
    actor:    str             = ACTOR_ENGINE,
    reason:   Optional[str]   = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EngineAnalyticsEvent:
    return _make_event(EngineEventType.ANALYTICS_PUBLISHED, request_id,
                       actor=actor, reason=reason, metadata=metadata)


def make_analytics_engine_failed(
    request_id: str,
    *,
    actor:    str             = ACTOR_ENGINE,
    reason:   Optional[str]   = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EngineAnalyticsEvent:
    return _make_event(EngineEventType.ANALYTICS_FAILED, request_id,
                       actor=actor, reason=reason, metadata=metadata)


def make_analytics_engine_stopped(
    request_id: str,
    *,
    actor:    str             = ACTOR_ENGINE,
    reason:   Optional[str]   = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EngineAnalyticsEvent:
    return _make_event(EngineEventType.ANALYTICS_STOPPED, request_id,
                       actor=actor, reason=reason, metadata=metadata)
