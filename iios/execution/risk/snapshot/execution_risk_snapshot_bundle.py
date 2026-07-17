"""iios/execution/risk/snapshot/execution_risk_snapshot_bundle.py
==================================================
SnapshotBundle — immutable group of related ExecutionRiskSnapshots.

Useful for batch reporting, auditing, or passing a correlated set of
evaluation results to a downstream consumer as a single unit.

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .execution_risk_snapshot import ExecutionRiskSnapshot


@dataclass(frozen=True)
class SnapshotBundle:
    """
    Immutable group of ExecutionRiskSnapshots.

    Bundles are typically produced at the end of a workflow or a batch
    evaluation run.  They are not stored in SnapshotStore — they are
    ephemeral transfer objects consumed by external systems.
    """

    bundle_id:  str
    created_at: float
    snapshots:  Tuple[ExecutionRiskSnapshot, ...]
    metadata:   Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return len(self.snapshots)

    @property
    def blocked_snapshots(self) -> Tuple[ExecutionRiskSnapshot, ...]:
        return tuple(s for s in self.snapshots if s.is_blocked)

    @property
    def allowed_snapshots(self) -> Tuple[ExecutionRiskSnapshot, ...]:
        return tuple(s for s in self.snapshots if s.allowed)

    @property
    def emergencies(self) -> Tuple[ExecutionRiskSnapshot, ...]:
        return tuple(s for s in self.snapshots if s.is_emergency)

    @property
    def has_blocks(self) -> bool:
        return any(s.is_blocked for s in self.snapshots)

    @property
    def has_emergencies(self) -> bool:
        return any(s.is_emergency for s in self.snapshots)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional[ExecutionRiskSnapshot]:
        for s in self.snapshots:
            if s.snapshot_id == snapshot_id:
                return s
        return None

    def ids(self) -> List[str]:
        return [s.snapshot_id for s in self.snapshots]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":          self.bundle_id,
            "created_at":         self.created_at,
            "count":              self.count,
            "has_blocks":         self.has_blocks,
            "has_emergencies":    self.has_emergencies,
            "snapshot_ids":       self.ids(),
            "snapshots":          [s.to_dict() for s in self.snapshots],
            "metadata":           dict(self.metadata),
        }


# ── Factory ───────────────────────────────────────────────────────────────────

def make_snapshot_bundle(
    snapshots: List[ExecutionRiskSnapshot],
    **metadata,
) -> SnapshotBundle:
    """
    Construct a SnapshotBundle from a list of snapshots.

    The snapshots are stored in the order provided.
    """
    return SnapshotBundle(
        bundle_id=str(uuid.uuid4()),
        created_at=time.time(),
        snapshots=tuple(snapshots),
        metadata=metadata,
    )
