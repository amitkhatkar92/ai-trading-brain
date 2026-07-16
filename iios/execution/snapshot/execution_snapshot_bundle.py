"""iios/execution/snapshot/execution_snapshot_bundle.py
==================================================
ExecutionSnapshotBundle — an immutable group of related
ExecutionSnapshot objects for a single workflow.

C6 Execution Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator

from iios.execution.snapshot.constants import SnapshotLifecycle
from iios.execution.snapshot.execution_snapshot import ExecutionSnapshot


@dataclass(frozen=True)
class ExecutionSnapshotBundle:
    """
    Immutable collection of related ExecutionSnapshot objects.

    Snapshots in a bundle share a common workflow_id.
    Used to publish atomic multi-execution state updates.
    """

    bundle_id:      str                            = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id:    str                            = ""
    snapshots:      tuple[ExecutionSnapshot, ...]  = field(default_factory=tuple)

    created_at:     float          = field(default_factory=time.time)
    correlation_id: str            = ""
    tags:           frozenset[str] = field(default_factory=frozenset)
    metadata:       dict[str, Any] = field(default_factory=dict)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def size(self) -> int:
        return len(self.snapshots)

    @property
    def is_empty(self) -> bool:
        return self.size == 0

    @property
    def snapshot_ids(self) -> tuple[str, ...]:
        return tuple(s.snapshot_id for s in self.snapshots)

    @property
    def execution_ids(self) -> tuple[str, ...]:
        return tuple(s.execution_id for s in self.snapshots)

    @property
    def order_ids(self) -> tuple[str, ...]:
        return tuple(s.order_id for s in self.snapshots)

    @property
    def terminal_count(self) -> int:
        return sum(1 for s in self.snapshots if s.is_terminal)

    @property
    def succeeded_count(self) -> int:
        return sum(1 for s in self.snapshots if s.succeeded)

    @property
    def all_terminal(self) -> bool:
        return all(s.is_terminal for s in self.snapshots)

    @property
    def all_succeeded(self) -> bool:
        return all(s.succeeded for s in self.snapshots)

    # ── Iteration ─────────────────────────────────────────────────────────────

    def __iter__(self) -> Iterator[ExecutionSnapshot]:
        return iter(self.snapshots)

    def __len__(self) -> int:
        return self.size

    def __contains__(self, snapshot_id: str) -> bool:
        return snapshot_id in self.snapshot_ids

    def get(self, snapshot_id: str) -> ExecutionSnapshot | None:
        for s in self.snapshots:
            if s.snapshot_id == snapshot_id:
                return s
        return None

    def get_by_execution(self, execution_id: str) -> list[ExecutionSnapshot]:
        return [s for s in self.snapshots if s.execution_id == execution_id]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id":       self.bundle_id,
            "workflow_id":     self.workflow_id,
            "size":            self.size,
            "snapshot_ids":    list(self.snapshot_ids),
            "execution_ids":   list(self.execution_ids),
            "order_ids":       list(self.order_ids),
            "terminal_count":  self.terminal_count,
            "succeeded_count": self.succeeded_count,
            "all_terminal":    self.all_terminal,
            "all_succeeded":   self.all_succeeded,
            "created_at":      self.created_at,
            "correlation_id":  self.correlation_id,
            "tags":            sorted(self.tags),
        }

    def __repr__(self) -> str:
        return (
            f"ExecutionSnapshotBundle("
            f"id={self.bundle_id[:8]}, "
            f"workflow={self.workflow_id[:8] if self.workflow_id else '?'}, "
            f"size={self.size})"
        )
