"""
iios/execution/analytics/snapshot/analytics_snapshot_events.py
===============================================================
AnalyticsSnapshotEvent — immutable domain events for the snapshot
lifecycle.

Six factory functions cover the full snapshot lifecycle.

C8 Execution Analytics & Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    ACTOR_BUILDER,
    ACTOR_STORE,
    ACTOR_SYSTEM,
    SNAPSHOT_ENGINE_ID,
    SnapshotEventType,
)


@dataclass(frozen=True)
class AnalyticsSnapshotEvent:
    """Immutable domain event for the snapshot lifecycle."""

    event_id:    str
    event_type:  SnapshotEventType
    snapshot_id: str
    actor:       str
    system_id:   str
    payload:     Dict[str, Any] = field(default_factory=dict)
    occurred_at: float          = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "snapshot_id": self.snapshot_id,
            "actor":       self.actor,
            "system_id":   self.system_id,
            "payload":     dict(self.payload),
            "occurred_at": self.occurred_at,
        }


# ── Factory functions ─────────────────────────────────────────────────────────

def _make(
    event_type:  SnapshotEventType,
    snapshot_id: str,
    actor:       str,
    payload:     Dict[str, Any],
) -> AnalyticsSnapshotEvent:
    return AnalyticsSnapshotEvent(
        event_id    = str(uuid.uuid4()),
        event_type  = event_type,
        snapshot_id = snapshot_id,
        actor       = actor,
        system_id   = SNAPSHOT_ENGINE_ID,
        payload     = payload,
    )


def make_snapshot_created_event(
    snapshot_id:          str,
    analytics_session_id: str,
    actor:                str                      = ACTOR_BUILDER,
    payload:              Optional[Dict[str, Any]] = None,
) -> AnalyticsSnapshotEvent:
    return _make(
        SnapshotEventType.SNAPSHOT_CREATED,
        snapshot_id, actor,
        {**(payload or {}), "analytics_session_id": analytics_session_id},
    )


def make_snapshot_validated_event(
    snapshot_id: str,
    actor:       str = ACTOR_BUILDER,
) -> AnalyticsSnapshotEvent:
    return _make(
        SnapshotEventType.SNAPSHOT_VALIDATED,
        snapshot_id, actor, {},
    )


def make_snapshot_published_event(
    snapshot_id: str,
    actor:       str = ACTOR_STORE,
) -> AnalyticsSnapshotEvent:
    return _make(
        SnapshotEventType.SNAPSHOT_PUBLISHED,
        snapshot_id, actor, {},
    )


def make_snapshot_archived_event(
    snapshot_id: str,
    reason:      str = "",
    actor:       str = ACTOR_STORE,
) -> AnalyticsSnapshotEvent:
    return _make(
        SnapshotEventType.SNAPSHOT_ARCHIVED,
        snapshot_id, actor,
        {"reason": reason},
    )


def make_snapshot_retrieved_event(
    snapshot_id: str,
    requester:   str = ACTOR_SYSTEM,
) -> AnalyticsSnapshotEvent:
    return _make(
        SnapshotEventType.SNAPSHOT_RETRIEVED,
        snapshot_id, requester, {},
    )


def make_snapshot_cached_event(
    snapshot_id: str,
    actor:       str = ACTOR_STORE,
) -> AnalyticsSnapshotEvent:
    return _make(
        SnapshotEventType.SNAPSHOT_CACHED,
        snapshot_id, actor, {},
    )
