"""iios/execution/snapshot/execution_snapshot_events.py
==================================================
SnapshotEvent and SnapshotEventType — events emitted at each
lifecycle transition of an ExecutionSnapshot.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from iios.execution.snapshot.constants import SnapshotLifecycle, SnapshotTrigger


class SnapshotEventType(str, Enum):
    """Events emitted by the Execution Snapshot lifecycle."""
    SNAPSHOT_CREATED   = "SNAPSHOT_CREATED"
    SNAPSHOT_VALIDATED = "SNAPSHOT_VALIDATED"
    SNAPSHOT_PUBLISHED = "SNAPSHOT_PUBLISHED"
    SNAPSHOT_STORED    = "SNAPSHOT_STORED"
    SNAPSHOT_ARCHIVED  = "SNAPSHOT_ARCHIVED"
    BUNDLE_CREATED     = "BUNDLE_CREATED"
    BUNDLE_PUBLISHED   = "BUNDLE_PUBLISHED"


@dataclass(frozen=True)
class SnapshotEvent:
    """Immutable event record emitted by the snapshot lifecycle."""

    event_id:     str               = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:   SnapshotEventType = SnapshotEventType.SNAPSHOT_CREATED
    snapshot_id:  str               = ""
    execution_id: str               = ""
    workflow_id:  str               = ""
    occurred_at:  float             = field(default_factory=time.time)
    lifecycle:    Optional[SnapshotLifecycle] = None
    trigger:      Optional[SnapshotTrigger]   = None
    error_message: str              = ""
    payload:      dict[str, Any]    = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id":     self.event_id,
            "event_type":   self.event_type.value,
            "snapshot_id":  self.snapshot_id,
            "execution_id": self.execution_id,
            "workflow_id":  self.workflow_id,
            "occurred_at":  self.occurred_at,
            "lifecycle":    self.lifecycle.value if self.lifecycle else None,
            "trigger":      self.trigger.value   if self.trigger   else None,
            "error_message": self.error_message,
            "payload":      self.payload,
        }

    def __repr__(self) -> str:
        return (
            f"SnapshotEvent(type={self.event_type.value}, "
            f"snapshot={self.snapshot_id[:12]}, "
            f"execution={self.execution_id[:8] if self.execution_id else '?'})"
        )


def make_snapshot_event(
    event_type:   SnapshotEventType,
    snapshot_id:  str,
    *,
    execution_id: str = "",
    workflow_id:  str = "",
    lifecycle:    Optional[SnapshotLifecycle] = None,
    trigger:      Optional[SnapshotTrigger]   = None,
    error_message: str = "",
    payload:      dict[str, Any] | None = None,
    occurred_at:  float = 0.0,
) -> SnapshotEvent:
    """Factory function for SnapshotEvent."""
    return SnapshotEvent(
        event_type    = event_type,
        snapshot_id   = snapshot_id,
        execution_id  = execution_id,
        workflow_id   = workflow_id,
        occurred_at   = occurred_at or time.time(),
        lifecycle     = lifecycle,
        trigger       = trigger,
        error_message = error_message,
        payload       = payload or {},
    )
