"""iios/execution/gateway/snapshot/gateway_snapshot_bundle.py
==================================================
GatewaySnapshotBundle — immutable collection of related
ExecutionGatewaySnapshot IDs.

A bundle groups all snapshots for a single execution flow
(by execution_id, workflow_id, or portfolio sweep).

The bundle stores only snapshot IDs — not full snapshots — to
avoid duplication.  Retrieve full snapshots via the store.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .execution_gateway_snapshot import ExecutionGatewaySnapshot


@dataclass(frozen=True)
class GatewaySnapshotBundle:
    """
    Immutable collection of ExecutionGatewaySnapshot IDs
    belonging to a common execution context.

    Fields
    ------
    bundle_id:
        Unique bundle identifier.
    bundle_name:
        Human-readable description.
    snapshot_ids:
        Ordered tuple of snapshot IDs (chronological).
    gateway_id:
        Gateway that produced all snapshots in this bundle.
    execution_id:
        Shared execution correlation ID.
    portfolio_id:
        Shared portfolio.
    strategy_id:
        Shared strategy.
    snapshot_count:
        Convenience copy of len(snapshot_ids).
    earliest_snapshot_at:
        created_at of the oldest snapshot in the bundle.
    latest_snapshot_at:
        created_at of the most recent snapshot in the bundle.
    created_at:
        When the bundle object was created.
    metadata:
        Arbitrary key-value pairs.
    """

    bundle_id:             str
    bundle_name:           str
    snapshot_ids:          Tuple[str, ...]
    gateway_id:            str
    execution_id:          str
    portfolio_id:          str
    strategy_id:           str
    snapshot_count:        int
    earliest_snapshot_at:  float
    latest_snapshot_at:    float
    created_at:            float
    metadata:              Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_empty(self) -> bool:
        return self.snapshot_count == 0

    @property
    def time_span_seconds(self) -> float:
        if self.snapshot_count < 2:
            return 0.0
        return self.latest_snapshot_at - self.earliest_snapshot_at

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def contains(self, snapshot_id: str) -> bool:
        return snapshot_id in self.snapshot_ids

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":            self.bundle_id,
            "bundle_name":          self.bundle_name,
            "snapshot_ids":         list(self.snapshot_ids),
            "gateway_id":           self.gateway_id,
            "execution_id":         self.execution_id,
            "portfolio_id":         self.portfolio_id,
            "strategy_id":          self.strategy_id,
            "snapshot_count":       self.snapshot_count,
            "earliest_snapshot_at": self.earliest_snapshot_at,
            "latest_snapshot_at":   self.latest_snapshot_at,
            "created_at":           self.created_at,
            "metadata":             dict(self.metadata),
        }

    def __repr__(self) -> str:
        return (
            f"GatewaySnapshotBundle("
            f"id={self.bundle_id!r}, "
            f"count={self.snapshot_count}, "
            f"execution={self.execution_id!r}"
            f")"
        )


# ── Factory functions ─────────────────────────────────────────────────────────

def make_bundle_from_snapshots(
    snapshots:   List[ExecutionGatewaySnapshot],
    bundle_name: str = "",
    *,
    metadata:    Optional[Dict[str, Any]] = None,
) -> GatewaySnapshotBundle:
    """
    Create a GatewaySnapshotBundle from a list of snapshots.

    Snapshots are sorted by created_at before being stored.
    All snapshots must share the same execution_id.

    Raises
    ------
    ValueError — if snapshots list is empty or execution_ids differ.
    """
    if not snapshots:
        raise ValueError("Cannot create a bundle from an empty snapshot list.")

    sorted_snaps = sorted(snapshots, key=lambda s: s.created_at)
    first = sorted_snaps[0]

    execution_ids = {s.execution_id for s in snapshots}
    if len(execution_ids) > 1:
        raise ValueError(
            f"All snapshots in a bundle must share the same execution_id, "
            f"got {execution_ids}."
        )

    return GatewaySnapshotBundle(
        bundle_id=str(uuid.uuid4()),
        bundle_name=bundle_name or f"bundle:{first.execution_id}",
        snapshot_ids=tuple(s.snapshot_id for s in sorted_snaps),
        gateway_id=first.gateway_id,
        execution_id=first.execution_id,
        portfolio_id=first.portfolio_id,
        strategy_id=first.strategy_id,
        snapshot_count=len(sorted_snaps),
        earliest_snapshot_at=sorted_snaps[0].created_at,
        latest_snapshot_at=sorted_snaps[-1].created_at,
        created_at=time.time(),
        metadata=dict(metadata or {}),
    )
