"""
portfolio_snapshot_events.py — iios.portfolio.snapshot
=======================================================
SnapshotEvent value object and six factory functions covering the full
snapshot lifecycle.

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict

from .constants import (
    SNAPSHOT_SYSTEM_ID,
    VERSION,
    SnapshotEventType,
)


@dataclass(frozen=True)
class SnapshotEvent:
    """
    Immutable record of a single snapshot lifecycle event.

    Every SnapshotEvent carries a unique event_id, the type of event,
    the snapshot and portfolio it concerns, who emitted it, and an
    arbitrary payload dict for downstream consumers.
    """
    event_id:         str
    event_type:       str          # SnapshotEventType.value
    snapshot_id:      str
    portfolio_id:     str
    source:           str
    payload:          Dict[str, Any]
    occurred_at:      float
    framework_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":         self.event_id,
            "event_type":       self.event_type,
            "snapshot_id":      self.snapshot_id,
            "portfolio_id":     self.portfolio_id,
            "source":           self.source,
            "payload":          dict(self.payload),
            "occurred_at":      self.occurred_at,
            "framework_version": self.framework_version,
        }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _make_event(
    event_type:   SnapshotEventType,
    snapshot_id:  str,
    portfolio_id: str,
    source:       str,
    payload:      Dict[str, Any],
) -> SnapshotEvent:
    return SnapshotEvent(
        event_id          = str(uuid.uuid4()),
        event_type        = event_type.value,
        snapshot_id       = snapshot_id,
        portfolio_id      = portfolio_id,
        source            = source,
        payload           = dict(payload),
        occurred_at       = time.time(),
        framework_version = VERSION,
    )


# ---------------------------------------------------------------------------
# Six public factory functions
# ---------------------------------------------------------------------------

def make_snapshot_created(
    snapshot_id:  str,
    portfolio_id: str,
    *,
    source:       str = SNAPSHOT_SYSTEM_ID,
    payload:      Dict[str, Any] | None = None,
) -> SnapshotEvent:
    """Create a SnapshotCreated event."""
    return _make_event(
        SnapshotEventType.SNAPSHOT_CREATED,
        snapshot_id, portfolio_id, source, payload or {},
    )


def make_snapshot_validated(
    snapshot_id:  str,
    portfolio_id: str,
    *,
    source:        str = SNAPSHOT_SYSTEM_ID,
    passed_checks: int = 0,
    payload:       Dict[str, Any] | None = None,
) -> SnapshotEvent:
    """Create a SnapshotValidated event."""
    p = dict(payload or {})
    p.setdefault("passed_checks", passed_checks)
    return _make_event(
        SnapshotEventType.SNAPSHOT_VALIDATED,
        snapshot_id, portfolio_id, source, p,
    )


def make_snapshot_published(
    snapshot_id:  str,
    portfolio_id: str,
    *,
    source:       str = SNAPSHOT_SYSTEM_ID,
    publisher:    str = "",
    payload:      Dict[str, Any] | None = None,
) -> SnapshotEvent:
    """Create a SnapshotPublished event."""
    p = dict(payload or {})
    p.setdefault("publisher", publisher)
    return _make_event(
        SnapshotEventType.SNAPSHOT_PUBLISHED,
        snapshot_id, portfolio_id, source, p,
    )


def make_snapshot_archived(
    snapshot_id:  str,
    portfolio_id: str,
    *,
    source:       str = SNAPSHOT_SYSTEM_ID,
    reason:       str = "",
    payload:      Dict[str, Any] | None = None,
) -> SnapshotEvent:
    """Create a SnapshotArchived event."""
    p = dict(payload or {})
    p.setdefault("reason", reason)
    return _make_event(
        SnapshotEventType.SNAPSHOT_ARCHIVED,
        snapshot_id, portfolio_id, source, p,
    )


def make_snapshot_retrieved(
    snapshot_id:  str,
    portfolio_id: str,
    *,
    source:      str = SNAPSHOT_SYSTEM_ID,
    requester:   str = "",
    payload:     Dict[str, Any] | None = None,
) -> SnapshotEvent:
    """Create a SnapshotRetrieved event."""
    p = dict(payload or {})
    p.setdefault("requester", requester)
    return _make_event(
        SnapshotEventType.SNAPSHOT_RETRIEVED,
        snapshot_id, portfolio_id, source, p,
    )


def make_snapshot_cached(
    snapshot_id:  str,
    portfolio_id: str,
    *,
    source:       str = SNAPSHOT_SYSTEM_ID,
    cache_key:    str = "",
    payload:      Dict[str, Any] | None = None,
) -> SnapshotEvent:
    """Create a SnapshotCached event."""
    p = dict(payload or {})
    p.setdefault("cache_key", cache_key)
    return _make_event(
        SnapshotEventType.SNAPSHOT_CACHED,
        snapshot_id, portfolio_id, source, p,
    )
