"""
decision_snapshot_events.py — iios.decision.snapshot
=====================================================
Event value objects and factory functions for the Snapshot subsystem.

Six event types:
  SnapshotCreated, SnapshotValidated, SnapshotPublished,
  SnapshotArchived, SnapshotRetrieved, SnapshotCached

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import VERSION, SnapshotEventType


@dataclass(frozen=True)
class DecisionSnapshotEvent:
    """
    Immutable event emitted during the snapshot lifecycle.

    Parameters
    ----------
    event_id :          Unique event identifier.
    event_type :        Kind of event.
    snapshot_id :       Target snapshot identifier.
    decision_id :       Decision associated with the snapshot.
    session_id :        Decision session identifier.
    source :            Component that emitted the event.
    payload :           Event-specific data.
    occurred_at :       Timestamp.
    framework_version : Version string.
    """

    event_id:          str
    event_type:        SnapshotEventType
    snapshot_id:       str
    decision_id:       str
    session_id:        str
    source:            str
    payload:           Dict[str, Any]
    occurred_at:       datetime
    framework_version: str = VERSION

    def to_dict(self) -> dict:
        return {
            "event_id":          self.event_id,
            "event_type":        self.event_type.value,
            "snapshot_id":       self.snapshot_id,
            "decision_id":       self.decision_id,
            "session_id":        self.session_id,
            "source":            self.source,
            "payload":           self.payload,
            "occurred_at":       self.occurred_at.isoformat(),
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _make_event(
    event_type:  SnapshotEventType,
    snapshot_id: str,
    decision_id: str,
    session_id:  str,
    source:      str,
    payload:     Dict[str, Any],
) -> DecisionSnapshotEvent:
    return DecisionSnapshotEvent(
        event_id    = str(uuid.uuid4()),
        event_type  = event_type,
        snapshot_id = snapshot_id,
        decision_id = decision_id,
        session_id  = session_id,
        source      = source,
        payload     = payload,
        occurred_at = datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Factory functions — one per SnapshotEventType
# ---------------------------------------------------------------------------

def make_snapshot_created(
    snapshot_id: str,
    decision_id: str,
    session_id:  str,
    source:      str,
    *,
    snapshot_version: int = 1,
    lifecycle_state:  str = "",
) -> DecisionSnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_CREATED,
        snapshot_id, decision_id, session_id, source,
        {"snapshot_version": snapshot_version, "lifecycle_state": lifecycle_state},
    )


def make_snapshot_validated(
    snapshot_id: str,
    decision_id: str,
    session_id:  str,
    source:      str,
    *,
    is_valid:      bool = True,
    failed_checks: tuple = (),
) -> DecisionSnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_VALIDATED,
        snapshot_id, decision_id, session_id, source,
        {"is_valid": is_valid, "failed_checks": list(failed_checks)},
    )


def make_snapshot_published(
    snapshot_id: str,
    decision_id: str,
    session_id:  str,
    source:      str,
    *,
    decision_status: str = "",
) -> DecisionSnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_PUBLISHED,
        snapshot_id, decision_id, session_id, source,
        {"decision_status": decision_status},
    )


def make_snapshot_archived(
    snapshot_id: str,
    decision_id: str,
    session_id:  str,
    source:      str,
    *,
    reason: str = "",
) -> DecisionSnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_ARCHIVED,
        snapshot_id, decision_id, session_id, source,
        {"reason": reason},
    )


def make_snapshot_retrieved(
    snapshot_id: str,
    decision_id: str,
    session_id:  str,
    source:      str,
    *,
    query_key: str = "",
) -> DecisionSnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_RETRIEVED,
        snapshot_id, decision_id, session_id, source,
        {"query_key": query_key},
    )


def make_snapshot_cached(
    snapshot_id: str,
    decision_id: str,
    session_id:  str,
    source:      str,
    *,
    cache_hit: bool = False,
) -> DecisionSnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_CACHED,
        snapshot_id, decision_id, session_id, source,
        {"cache_hit": cache_hit},
    )
