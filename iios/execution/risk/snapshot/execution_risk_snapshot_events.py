"""iios/execution/risk/snapshot/execution_risk_snapshot_events.py
==================================================
SnapshotEvent and factory functions for snapshot lifecycle events.

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict

from .constants import SNAPSHOT_VERSION, SnapshotEventType


@dataclass(frozen=True)
class SnapshotEvent:
    """
    Immutable record of a single snapshot lifecycle transition.

    Published on the internal event bus.  Downstream systems that need
    to react to snapshot lifecycle changes (e.g. audit log, metrics,
    compliance stream) subscribe to these events.
    """

    event_id:     str
    event_type:   SnapshotEventType
    snapshot_id:  str
    risk_id:      str
    evaluation_id: str
    actor:        str
    occurred_at:  float
    version:      str
    metadata:     Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":      self.event_id,
            "event_type":    self.event_type.value,
            "snapshot_id":   self.snapshot_id,
            "risk_id":       self.risk_id,
            "evaluation_id": self.evaluation_id,
            "actor":         self.actor,
            "occurred_at":   self.occurred_at,
            "version":       self.version,
            "metadata":      dict(self.metadata),
        }


# ── Factory functions ─────────────────────────────────────────────────────────

def _make_event(
    event_type:    SnapshotEventType,
    snapshot_id:   str,
    risk_id:       str,
    evaluation_id: str,
    actor:         str,
    **metadata,
) -> SnapshotEvent:
    return SnapshotEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        snapshot_id=snapshot_id,
        risk_id=risk_id,
        evaluation_id=evaluation_id,
        actor=actor,
        occurred_at=time.time(),
        version=SNAPSHOT_VERSION,
        metadata=metadata,
    )


def make_snapshot_created_event(
    snapshot_id:   str,
    risk_id:       str,
    evaluation_id: str = "",
    actor:         str = "registry",
    **metadata,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_CREATED,
        snapshot_id, risk_id, evaluation_id, actor, **metadata,
    )


def make_snapshot_validated_event(
    snapshot_id:   str,
    risk_id:       str,
    evaluation_id: str = "",
    actor:         str = "validator",
    **metadata,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_VALIDATED,
        snapshot_id, risk_id, evaluation_id, actor, **metadata,
    )


def make_snapshot_published_event(
    snapshot_id:   str,
    risk_id:       str,
    evaluation_id: str = "",
    actor:         str = "registry",
    **metadata,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_PUBLISHED,
        snapshot_id, risk_id, evaluation_id, actor, **metadata,
    )


def make_snapshot_archived_event(
    snapshot_id:   str,
    risk_id:       str,
    evaluation_id: str = "",
    actor:         str = "registry",
    **metadata,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_ARCHIVED,
        snapshot_id, risk_id, evaluation_id, actor, **metadata,
    )


def make_snapshot_retrieved_event(
    snapshot_id:   str,
    risk_id:       str,
    evaluation_id: str = "",
    actor:         str = "registry",
    **metadata,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_RETRIEVED,
        snapshot_id, risk_id, evaluation_id, actor, **metadata,
    )


def make_snapshot_cached_event(
    snapshot_id:   str,
    risk_id:       str,
    evaluation_id: str = "",
    actor:         str = "cache",
    **metadata,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_CACHED,
        snapshot_id, risk_id, evaluation_id, actor, **metadata,
    )
