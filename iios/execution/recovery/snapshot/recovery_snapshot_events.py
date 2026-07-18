"""
iios/execution/recovery/snapshot/recovery_snapshot_events.py
============================================================
SnapshotEvent — immutable event emitted by the Snapshot subsystem.

Six event types defined in SnapshotEventType.

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import ACTOR_SYSTEM, VERSION, SnapshotEventType


@dataclass(frozen=True)
class SnapshotEvent:
    """Immutable event emitted by the Snapshot subsystem."""

    event_id:            str
    event_type:          SnapshotEventType
    snapshot_id:         str
    recovery_session_id: str
    occurred_at:         float
    version:             str
    actor:               str
    reason:              str
    metadata:            Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":            self.event_id,
            "event_type":          self.event_type.value,
            "snapshot_id":         self.snapshot_id,
            "recovery_session_id": self.recovery_session_id,
            "occurred_at":         self.occurred_at,
            "version":             self.version,
            "actor":               self.actor,
            "reason":              self.reason,
            "metadata":            dict(self.metadata),
        }


# ── Private factory ───────────────────────────────────────────────────────────

def _make_event(
    event_type:          SnapshotEventType,
    snapshot_id:         str,
    recovery_session_id: str,
    *,
    actor:               str = ACTOR_SYSTEM,
    reason:              str = "",
    metadata:            Optional[Dict[str, Any]] = None,
) -> SnapshotEvent:
    return SnapshotEvent(
        event_id            = str(uuid.uuid4()),
        event_type          = event_type,
        snapshot_id         = snapshot_id,
        recovery_session_id = recovery_session_id,
        occurred_at         = time.time(),
        version             = VERSION,
        actor               = actor,
        reason              = reason,
        metadata            = dict(metadata) if metadata else {},
    )


# ── Public factories ──────────────────────────────────────────────────────────

def make_snapshot_created(
    snapshot_id: str, recovery_session_id: str, *, actor: str = ACTOR_SYSTEM, **kwargs
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_CREATED, snapshot_id, recovery_session_id,
        actor=actor, **kwargs,
    )


def make_snapshot_validated(
    snapshot_id: str, recovery_session_id: str, *, actor: str = ACTOR_SYSTEM, **kwargs
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_VALIDATED, snapshot_id, recovery_session_id,
        actor=actor, **kwargs,
    )


def make_snapshot_published(
    snapshot_id: str, recovery_session_id: str, *, actor: str = ACTOR_SYSTEM, **kwargs
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_PUBLISHED, snapshot_id, recovery_session_id,
        actor=actor, **kwargs,
    )


def make_snapshot_archived(
    snapshot_id: str, recovery_session_id: str, *, actor: str = ACTOR_SYSTEM, **kwargs
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_ARCHIVED, snapshot_id, recovery_session_id,
        actor=actor, **kwargs,
    )


def make_snapshot_retrieved(
    snapshot_id: str, recovery_session_id: str, *, actor: str = ACTOR_SYSTEM, **kwargs
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_RETRIEVED, snapshot_id, recovery_session_id,
        actor=actor, **kwargs,
    )


def make_snapshot_cached(
    snapshot_id: str, recovery_session_id: str, *, actor: str = ACTOR_SYSTEM, **kwargs
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_CACHED, snapshot_id, recovery_session_id,
        actor=actor, **kwargs,
    )
