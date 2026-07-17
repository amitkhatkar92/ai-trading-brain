"""iios/execution/gateway/snapshot/gateway_snapshot_events.py
==================================================
SnapshotEvent — domain event emitted by the Snapshot module —
and factory functions for each event type.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import (
    ACTOR_SNAPSHOT_STORE,
    SNAPSHOT_SYSTEM_ID,
    SnapshotEventType,
    VERSION,
)


@dataclass(frozen=True)
class SnapshotEvent:
    """
    Immutable domain event for the Gateway Snapshot module.

    Events are fired in the order they occur during publish/get/archive
    and delivered synchronously to registered listeners.
    """

    event_id:    str
    event_type:  SnapshotEventType
    snapshot_id: str
    actor:       str
    occurred_at: float
    version:     str = VERSION

    # Optional detail fields
    execution_id: Optional[str] = None
    gateway_id:   Optional[str] = None
    metadata:     Dict[str, Any] = field(default_factory=dict, compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type.value,
            "snapshot_id": self.snapshot_id,
            "actor":       self.actor,
            "occurred_at": self.occurred_at,
            "version":     self.version,
            "execution_id": self.execution_id,
            "gateway_id":  self.gateway_id,
            "metadata":    dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"SnapshotEvent("
            f"type={self.event_type.value!r}, "
            f"snapshot_id={self.snapshot_id!r}"
            f")"
        )


# ── Internal factory ──────────────────────────────────────────────────────────

def _make_event(
    event_type:   SnapshotEventType,
    snapshot_id:  str,
    *,
    actor:        str = ACTOR_SNAPSHOT_STORE,
    execution_id: Optional[str] = None,
    gateway_id:   Optional[str] = None,
    metadata:     Optional[Dict[str, Any]] = None,
) -> SnapshotEvent:
    return SnapshotEvent(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        snapshot_id=snapshot_id,
        actor=actor,
        occurred_at=time.time(),
        execution_id=execution_id,
        gateway_id=gateway_id,
        metadata=dict(metadata or {}),
    )


# ── Public factory functions ──────────────────────────────────────────────────

def make_snapshot_created_event(
    snapshot_id:  str,
    *,
    execution_id: Optional[str] = None,
    gateway_id:   Optional[str] = None,
    actor:        str = ACTOR_SNAPSHOT_STORE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_CREATED,
        snapshot_id,
        actor=actor,
        execution_id=execution_id,
        gateway_id=gateway_id,
        metadata=metadata,
    )


def make_snapshot_validated_event(
    snapshot_id:  str,
    *,
    execution_id: Optional[str] = None,
    gateway_id:   Optional[str] = None,
    actor:        str = ACTOR_SNAPSHOT_STORE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_VALIDATED,
        snapshot_id,
        actor=actor,
        execution_id=execution_id,
        gateway_id=gateway_id,
        metadata=metadata,
    )


def make_snapshot_published_event(
    snapshot_id:  str,
    *,
    execution_id: Optional[str] = None,
    gateway_id:   Optional[str] = None,
    actor:        str = ACTOR_SNAPSHOT_STORE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_PUBLISHED,
        snapshot_id,
        actor=actor,
        execution_id=execution_id,
        gateway_id=gateway_id,
        metadata=metadata,
    )


def make_snapshot_archived_event(
    snapshot_id:  str,
    *,
    execution_id: Optional[str] = None,
    gateway_id:   Optional[str] = None,
    actor:        str = ACTOR_SNAPSHOT_STORE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_ARCHIVED,
        snapshot_id,
        actor=actor,
        execution_id=execution_id,
        gateway_id=gateway_id,
        metadata=metadata,
    )


def make_snapshot_retrieved_event(
    snapshot_id:  str,
    *,
    execution_id: Optional[str] = None,
    gateway_id:   Optional[str] = None,
    actor:        str = ACTOR_SNAPSHOT_STORE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_RETRIEVED,
        snapshot_id,
        actor=actor,
        execution_id=execution_id,
        gateway_id=gateway_id,
        metadata=metadata,
    )


def make_snapshot_cached_event(
    snapshot_id:  str,
    *,
    execution_id: Optional[str] = None,
    gateway_id:   Optional[str] = None,
    actor:        str = ACTOR_SNAPSHOT_STORE,
    metadata:     Optional[Dict[str, Any]] = None,
) -> SnapshotEvent:
    return _make_event(
        SnapshotEventType.SNAPSHOT_CACHED,
        snapshot_id,
        actor=actor,
        execution_id=execution_id,
        gateway_id=gateway_id,
        metadata=metadata,
    )
