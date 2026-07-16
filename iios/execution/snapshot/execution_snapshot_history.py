"""iios/execution/snapshot/execution_snapshot_history.py
==================================================
ExecutionSnapshotHistory — append-only, immutable-entry version
history of snapshots for a single execution.

Supports version diff comparison and timeline reconstruction.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from iios.execution.snapshot.constants import SnapshotLifecycle, SnapshotTrigger
from iios.execution.snapshot.execution_snapshot import ExecutionSnapshot


@dataclass(frozen=True)
class SnapshotRevision:
    """
    Immutable record of one version in a snapshot's history.
    """
    revision_id:  str              = field(default_factory=lambda: str(uuid.uuid4()))
    snapshot_id:  str              = ""
    execution_id: str              = ""
    version:      int              = 1
    sequence:     int              = 0
    lifecycle:    SnapshotLifecycle = SnapshotLifecycle.CREATED
    execution_state: str           = ""
    succeeded:    bool             = False
    recorded_at:  float            = field(default_factory=time.time)
    actor:        str              = "iios:system"
    reason:       str              = ""
    # Slim snapshot dict for diff comparison (None by default to save memory)
    snapshot_dict: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_id":    self.revision_id,
            "snapshot_id":    self.snapshot_id,
            "execution_id":   self.execution_id,
            "version":        self.version,
            "sequence":       self.sequence,
            "lifecycle":      self.lifecycle.value,
            "execution_state": self.execution_state,
            "succeeded":      self.succeeded,
            "recorded_at":    self.recorded_at,
            "actor":          self.actor,
            "reason":         self.reason,
        }

    def __repr__(self) -> str:
        return (
            f"SnapshotRevision("
            f"version={self.version}, "
            f"state={self.execution_state}, "
            f"lifecycle={self.lifecycle.value})"
        )


class ExecutionSnapshotHistory:
    """
    Append-only, thread-safe history of ExecutionSnapshot revisions.

    Maintains one history per execution_id.
    Oldest entries evicted when max_entries is reached.
    Supports version diff comparison and timeline reconstruction.
    """

    def __init__(
        self,
        execution_id: str,
        max_entries:  int = 200,
    ) -> None:
        self._execution_id = execution_id
        self._max_entries  = max_entries
        self._entries:     deque[SnapshotRevision] = deque(maxlen=max_entries)
        self._lock         = threading.Lock()
        self._total:       int = 0
        self._evicted:     int = 0

    # ── Append ────────────────────────────────────────────────────────────────

    def record(self, revision: SnapshotRevision) -> None:
        with self._lock:
            if len(self._entries) == self._max_entries:
                self._evicted += 1
            self._entries.append(revision)
            self._total += 1

    # ── Queries ───────────────────────────────────────────────────────────────

    def entries(self) -> list[SnapshotRevision]:
        with self._lock:
            return list(self._entries)

    def first(self) -> Optional[SnapshotRevision]:
        with self._lock:
            return self._entries[0] if self._entries else None

    def last(self) -> Optional[SnapshotRevision]:
        with self._lock:
            return self._entries[-1] if self._entries else None

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def get_by_version(self, version: int) -> Optional[SnapshotRevision]:
        with self._lock:
            for entry in self._entries:
                if entry.version == version:
                    return entry
        return None

    def get_by_sequence(self, sequence: int) -> Optional[SnapshotRevision]:
        with self._lock:
            for entry in self._entries:
                if entry.sequence == sequence:
                    return entry
        return None

    @property
    def execution_id(self) -> str:
        return self._execution_id

    @property
    def total_recorded(self) -> int:
        return self._total

    @property
    def evicted_count(self) -> int:
        return self._evicted

    def timeline(self) -> list[dict[str, Any]]:
        """Return chronological list of state transitions."""
        with self._lock:
            return [
                {
                    "sequence":        e.sequence,
                    "version":         e.version,
                    "execution_state": e.execution_state,
                    "lifecycle":       e.lifecycle.value,
                    "succeeded":       e.succeeded,
                    "recorded_at":     e.recorded_at,
                    "reason":          e.reason,
                }
                for e in self._entries
            ]

    # ── Diff / comparison ─────────────────────────────────────────────────────

    def diff(
        self,
        version_a: int,
        version_b: int,
    ) -> dict[str, Any]:
        """Compare two versions. Returns a diff dict."""
        a = self.get_by_version(version_a)
        b = self.get_by_version(version_b)
        if a is None or b is None:
            return {
                "version_a":        version_a,
                "version_b":        version_b,
                "found_a":          a is not None,
                "found_b":          b is not None,
                "state_changed":    None,
                "lifecycle_changed": None,
                "succeeded_changed": None,
            }
        return {
            "version_a":         version_a,
            "version_b":         version_b,
            "found_a":           True,
            "found_b":           True,
            "state_changed":     a.execution_state != b.execution_state,
            "state_a":           a.execution_state,
            "state_b":           b.execution_state,
            "lifecycle_changed": a.lifecycle != b.lifecycle,
            "lifecycle_a":       a.lifecycle.value,
            "lifecycle_b":       b.lifecycle.value,
            "succeeded_changed": a.succeeded != b.succeeded,
            "elapsed_ms":        (b.recorded_at - a.recorded_at) * 1_000,
        }

    # ── Iteration ─────────────────────────────────────────────────────────────

    def __iter__(self) -> Iterator[SnapshotRevision]:
        with self._lock:
            entries = list(self._entries)
        return iter(entries)

    def __len__(self) -> int:
        return self.count()


def make_snapshot_revision(
    snap:    ExecutionSnapshot,
    *,
    actor:           str = "iios:system",
    reason:          str = "",
    include_full_dict: bool = False,
) -> SnapshotRevision:
    """Factory helper for SnapshotRevision."""
    return SnapshotRevision(
        snapshot_id     = snap.snapshot_id,
        execution_id    = snap.execution_id,
        version         = snap.version,
        sequence        = snap.sequence_number,
        lifecycle       = snap.lifecycle,
        execution_state = snap.execution_state,
        succeeded       = snap.succeeded,
        actor           = actor,
        reason          = reason,
        snapshot_dict   = snap.to_dict() if include_full_dict else None,
    )
