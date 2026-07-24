"""
supervisor_snapshot_events.py — iios.supervisor.snapshot
---------------------------------------------------------
Events emitted by the Supervisor Snapshot subsystem.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import SUPERVISOR_SNAPSHOT_SYSTEM_ID, SnapshotEventType


@dataclass(frozen=True)
class SupervisorSnapshotEvent:
    """Immutable event emitted by the Supervisor Snapshot subsystem."""
    event_id:    str
    event_type:  SnapshotEventType
    source:      str
    payload:     Dict[str, Any]
    occurred_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "source":      self.source,
            "payload":     self.payload,
            "occurred_at": self.occurred_at,
        }


# ---------------------------------------------------------------------------
# Internal factory helper
# ---------------------------------------------------------------------------

def _make(
    event_type: SnapshotEventType,
    payload:    Optional[Dict[str, Any]] = None,
    source:     str = SUPERVISOR_SNAPSHOT_SYSTEM_ID,
) -> SupervisorSnapshotEvent:
    return SupervisorSnapshotEvent(
        event_id    = str(uuid.uuid4()),
        event_type  = event_type,
        source      = source,
        payload     = payload or {},
        occurred_at = time.time(),
    )


# ---------------------------------------------------------------------------
# Public factory functions — one per event type
# ---------------------------------------------------------------------------

def make_snapshot_started_event(
    session_id:  str = "",
    workflow_id: str = "",
) -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_STARTED, {
        "session_id":  session_id,
        "workflow_id": workflow_id,
    })


def make_snapshot_built_event(
    snapshot_id: str   = "",
    size_bytes:  int   = 0,
    elapsed_s:   float = 0.0,
) -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_BUILT, {
        "snapshot_id": snapshot_id,
        "size_bytes":  size_bytes,
        "elapsed_s":   elapsed_s,
    })


def make_snapshot_validated_event(
    snapshot_id:  str  = "",
    is_valid:     bool = True,
    failed_count: int  = 0,
) -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_VALIDATED, {
        "snapshot_id":  snapshot_id,
        "is_valid":     is_valid,
        "failed_count": failed_count,
    })


def make_snapshot_published_event(
    snapshot_id:  str  = "",
    session_id:   str  = "",
    is_emergency: bool = False,
    gov_decision: str  = "",
) -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_PUBLISHED, {
        "snapshot_id":  snapshot_id,
        "session_id":   session_id,
        "is_emergency": is_emergency,
        "gov_decision": gov_decision,
    })


def make_snapshot_registered_event(
    snapshot_id: str = "",
    session_id:  str = "",
) -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_REGISTERED, {
        "snapshot_id": snapshot_id,
        "session_id":  session_id,
    })


def make_snapshot_retrieved_event(
    snapshot_id: str  = "",
    from_cache:  bool = False,
) -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_RETRIEVED, {
        "snapshot_id": snapshot_id,
        "from_cache":  from_cache,
    })


def make_snapshot_invalidated_event(
    snapshot_id: str = "",
    reason:      str = "",
) -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_INVALIDATED, {
        "snapshot_id": snapshot_id,
        "reason":      reason,
    })


def make_snapshot_cached_event(
    snapshot_id: str   = "",
    ttl_s:       float = 0.0,
) -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_CACHED, {
        "snapshot_id": snapshot_id,
        "ttl_s":       ttl_s,
    })


def make_snapshot_expired_event(snapshot_id: str = "") -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_EXPIRED, {"snapshot_id": snapshot_id})


def make_snapshot_archived_event(snapshot_id: str = "") -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.SNAPSHOT_ARCHIVED, {"snapshot_id": snapshot_id})


def make_bundle_created_event(
    bundle_id:      str = "",
    snapshot_count: int = 0,
) -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.BUNDLE_CREATED, {
        "bundle_id":      bundle_id,
        "snapshot_count": snapshot_count,
    })


def make_store_saved_event(
    snapshot_id: str = "",
    store:       str = "in_memory",
) -> SupervisorSnapshotEvent:
    return _make(SnapshotEventType.STORE_SAVED, {
        "snapshot_id": snapshot_id,
        "store":       store,
    })
