"""
iios/execution/recovery/snapshot/recovery_snapshot_bundle.py
============================================================
RecoverySnapshotBundle — an ordered collection of all snapshot
versions produced for a single recovery session.

Provides version history, latest snapshot access, and completion
status for a given recovery_session_id.

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import LIFECYCLE_TERMINAL_STATES
from .execution_recovery_snapshot import ExecutionRecoverySnapshot


@dataclass(frozen=True)
class RecoverySnapshotBundle:
    """
    Immutable, ordered collection of ExecutionRecoverySnapshot versions
    for a single recovery session.

    ``snapshots`` is sorted by snapshot_version ascending.
    """

    bundle_id:            str
    recovery_session_id:  str
    snapshots:            Tuple[ExecutionRecoverySnapshot, ...]
    created_at:           float

    @property
    def latest(self) -> Optional[ExecutionRecoverySnapshot]:
        """The snapshot with the highest snapshot_version."""
        if not self.snapshots:
            return None
        return max(self.snapshots, key=lambda s: s.snapshot_version)

    @property
    def oldest(self) -> Optional[ExecutionRecoverySnapshot]:
        """The snapshot with the lowest snapshot_version."""
        if not self.snapshots:
            return None
        return min(self.snapshots, key=lambda s: s.snapshot_version)

    @property
    def version_count(self) -> int:
        return len(self.snapshots)

    @property
    def is_complete(self) -> bool:
        """True if the latest snapshot has a terminal lifecycle_state."""
        latest = self.latest
        if latest is None:
            return False
        return latest.lifecycle_state in LIFECYCLE_TERMINAL_STATES

    @property
    def is_successful(self) -> bool:
        """True if the latest snapshot reports a successful recovery."""
        latest = self.latest
        return latest.is_successful if latest else False

    def version(self, snapshot_version: int) -> Optional[ExecutionRecoverySnapshot]:
        """Return the snapshot with the given snapshot_version, or None."""
        for s in self.snapshots:
            if s.snapshot_version == snapshot_version:
                return s
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":           self.bundle_id,
            "recovery_session_id": self.recovery_session_id,
            "version_count":       self.version_count,
            "is_complete":         self.is_complete,
            "is_successful":       self.is_successful,
            "created_at":          self.created_at,
            "snapshots":           [s.to_dict() for s in self.snapshots],
        }


def make_snapshot_bundle(
    recovery_session_id: str,
    snapshots: List[ExecutionRecoverySnapshot],
    *,
    bundle_id: Optional[str] = None,
    created_at: Optional[float] = None,
) -> RecoverySnapshotBundle:
    """
    Create a RecoverySnapshotBundle from a list of snapshots.

    Snapshots are sorted by snapshot_version ascending.
    Only snapshots whose recovery_session_id matches are included.
    """
    matching = sorted(
        (s for s in snapshots if s.recovery_session_id == recovery_session_id),
        key=lambda s: s.snapshot_version,
    )
    return RecoverySnapshotBundle(
        bundle_id           = bundle_id or str(uuid.uuid4()),
        recovery_session_id = recovery_session_id,
        snapshots           = tuple(matching),
        created_at          = created_at if created_at is not None else time.time(),
    )
