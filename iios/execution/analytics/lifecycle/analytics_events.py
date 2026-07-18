"""
iios/execution/analytics/lifecycle/analytics_events.py
======================================================
AnalyticsEvent — immutable domain events emitted by AnalyticsLifecycle.

C8 Execution Analytics & Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from .constants import (
    ACTOR_LIFECYCLE,
    VERSION,
    AnalyticsEventType,
    AnalyticsState,
)


@dataclass(frozen=True)
class AnalyticsEvent:
    """
    Immutable domain event emitted on every analytics lifecycle transition.

    Fields
    ------
    event_id:    Globally unique event ID.
    event_type:  Classification of this event.
    session_id:  Owning analytics session.
    actor:       Component that triggered the event.
    occurred_at: Wall-time of the event.
    version:     Framework version.
    reason:      Optional human-readable context.
    metadata:    Optional supplementary data.
    """

    event_id:    str
    event_type:  AnalyticsEventType
    session_id:  str
    actor:       str
    occurred_at: float
    version:     str
    reason:      Optional[str]  = None
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
            "metadata":    dict(self.metadata),
        }


# ── Internal factory helper ───────────────────────────────────────────────────

def _make_event(
    event_type: AnalyticsEventType,
    session_id: str,
    *,
    actor:    str            = ACTOR_LIFECYCLE,
    reason:   Optional[str]  = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AnalyticsEvent:
    return AnalyticsEvent(
        event_id    = str(uuid.uuid4()),
        event_type  = event_type,
        session_id  = session_id,
        actor       = actor,
        occurred_at = time.time(),
        version     = VERSION,
        reason      = reason,
        metadata    = metadata or {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_analytics_created(
    session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: Optional[str] = None
) -> AnalyticsEvent:
    return _make_event(AnalyticsEventType.ANALYTICS_CREATED, session_id, actor=actor, reason=reason)


def make_analytics_initialized(
    session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: Optional[str] = None
) -> AnalyticsEvent:
    return _make_event(AnalyticsEventType.ANALYTICS_INITIALIZED, session_id, actor=actor, reason=reason)


def make_analytics_started(
    session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: Optional[str] = None
) -> AnalyticsEvent:
    return _make_event(AnalyticsEventType.ANALYTICS_STARTED, session_id, actor=actor, reason=reason)


def make_analytics_paused(
    session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: Optional[str] = None
) -> AnalyticsEvent:
    return _make_event(AnalyticsEventType.ANALYTICS_PAUSED, session_id, actor=actor, reason=reason)


def make_analytics_resumed(
    session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: Optional[str] = None
) -> AnalyticsEvent:
    return _make_event(AnalyticsEventType.ANALYTICS_RESUMED, session_id, actor=actor, reason=reason)


def make_analytics_completed(
    session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: Optional[str] = None
) -> AnalyticsEvent:
    return _make_event(AnalyticsEventType.ANALYTICS_COMPLETED, session_id, actor=actor, reason=reason)


def make_analytics_failed(
    session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: Optional[str] = None
) -> AnalyticsEvent:
    return _make_event(AnalyticsEventType.ANALYTICS_FAILED, session_id, actor=actor, reason=reason)


def make_analytics_archived(
    session_id: str, *, actor: str = ACTOR_LIFECYCLE, reason: Optional[str] = None
) -> AnalyticsEvent:
    return _make_event(AnalyticsEventType.ANALYTICS_ARCHIVED, session_id, actor=actor, reason=reason)


# ── State → event factory mapping ────────────────────────────────────────────

_STATE_EVENT_FACTORY: Dict[AnalyticsState, Callable[[str], AnalyticsEvent]] = {
    AnalyticsState.INITIALIZING: make_analytics_initialized,
    AnalyticsState.COLLECTING:   make_analytics_started,
    AnalyticsState.ACTIVE:       make_analytics_started,
    AnalyticsState.PAUSED:       make_analytics_paused,
    AnalyticsState.RESUMING:     make_analytics_resumed,
    AnalyticsState.COMPLETED:    make_analytics_completed,
    AnalyticsState.FAILED:       make_analytics_failed,
    AnalyticsState.ARCHIVED:     make_analytics_archived,
}
