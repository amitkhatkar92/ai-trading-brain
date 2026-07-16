"""iios/execution/positions/snapshot/position_snapshot_events.py
==================================================
SnapshotEvent — immutable domain event emitted when the snapshot
subsystem performs a notable operation.

6 factory functions, one per SnapshotEventType.

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import ACTOR_SNAPSHOT, VERSION, SnapshotEventType, SnapshotStatus


@dataclass(frozen=True)
class SnapshotEvent:
    """Immutable record of a single snapshot subsystem event."""

    event_id:        str
    event_type:      SnapshotEventType
    snapshot_id:     str
    snapshot_version: int
    snapshot_status: str
    position_id:     str
    portfolio_id:    str
    strategy_id:     str
    instrument:      str
    occurred_at:     float
    emitted_by:      str
    correlation_id:  str
    version:         str = VERSION
    metadata:        Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":        self.event_id,
            "event_type":      self.event_type.value,
            "snapshot_id":     self.snapshot_id,
            "snapshot_version": self.snapshot_version,
            "snapshot_status": self.snapshot_status,
            "position_id":     self.position_id,
            "portfolio_id":    self.portfolio_id,
            "strategy_id":     self.strategy_id,
            "instrument":      self.instrument,
            "occurred_at":     self.occurred_at,
            "emitted_by":      self.emitted_by,
            "correlation_id":  self.correlation_id,
            "version":         self.version,
        }


# ── Internal factory ─────────────────────────────────────────────────────────

def _make_event(
    event_type:       SnapshotEventType,
    snapshot_id:      str,
    snapshot_version: int,
    snapshot_status:  str,
    position_id:      str,
    *,
    portfolio_id:  str = "",
    strategy_id:   str = "",
    instrument:    str = "",
    correlation_id: str = "",
    emitted_by:    str = ACTOR_SNAPSHOT,
    metadata:      Optional[Dict[str, Any]] = None,
) -> SnapshotEvent:
    return SnapshotEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        snapshot_id=snapshot_id,
        snapshot_version=snapshot_version,
        snapshot_status=snapshot_status,
        position_id=position_id,
        portfolio_id=portfolio_id,
        strategy_id=strategy_id,
        instrument=instrument,
        occurred_at=time.time(),
        emitted_by=emitted_by,
        correlation_id=correlation_id,
        metadata=metadata or {},
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_snapshot_created_event(
    snapshot_id:      str,
    snapshot_version: int,
    position_id:      str,
    **kwargs: Any,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_CREATED,
        snapshot_id, snapshot_version,
        SnapshotStatus.DRAFT.value,
        position_id, **kwargs,
    )


def make_snapshot_validated_event(
    snapshot_id:      str,
    snapshot_version: int,
    position_id:      str,
    validation_passed: bool = True,
    **kwargs: Any,
) -> SnapshotEvent:
    status = SnapshotStatus.VALID.value if validation_passed else SnapshotStatus.INVALID.value
    return _make_event(
        SnapshotEventType.SNAPSHOT_VALIDATED,
        snapshot_id, snapshot_version,
        status,
        position_id, **kwargs,
    )


def make_snapshot_published_event(
    snapshot_id:      str,
    snapshot_version: int,
    position_id:      str,
    **kwargs: Any,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_PUBLISHED,
        snapshot_id, snapshot_version,
        SnapshotStatus.PUBLISHED.value,
        position_id, **kwargs,
    )


def make_snapshot_archived_event(
    snapshot_id:      str,
    snapshot_version: int,
    position_id:      str,
    **kwargs: Any,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_ARCHIVED,
        snapshot_id, snapshot_version,
        SnapshotStatus.ARCHIVED.value,
        position_id, **kwargs,
    )


def make_snapshot_retrieved_event(
    snapshot_id:      str,
    snapshot_version: int,
    position_id:      str,
    **kwargs: Any,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_RETRIEVED,
        snapshot_id, snapshot_version,
        SnapshotStatus.PUBLISHED.value,
        position_id, **kwargs,
    )


def make_snapshot_cached_event(
    snapshot_id:      str,
    snapshot_version: int,
    position_id:      str,
    **kwargs: Any,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_CACHED,
        snapshot_id, snapshot_version,
        SnapshotStatus.VALID.value,
        position_id, **kwargs,
    )
