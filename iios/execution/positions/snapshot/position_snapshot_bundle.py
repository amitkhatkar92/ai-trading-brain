"""iios/execution/positions/snapshot/position_snapshot_bundle.py
==================================================
SnapshotBundle — immutable collection of PositionSnapshot objects
produced for a common context (portfolio, strategy, instrument, etc.).

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import VERSION
from .position_snapshot import PositionSnapshot


@dataclass(frozen=True)
class SnapshotBundle:
    """
    Immutable collection of ``PositionSnapshot`` objects.

    Produced by ``PositionSnapshotStore.bundle_*`` methods for callers
    that need a consistent point-in-time view of multiple positions.
    """

    bundle_id:  str
    label:      str
    snapshots:  Tuple[PositionSnapshot, ...]
    created_at: float
    version:    str = VERSION
    metadata:   Dict[str, Any] = field(default_factory=dict, compare=False)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return len(self.snapshots)

    @property
    def is_empty(self) -> bool:
        return len(self.snapshots) == 0

    @property
    def position_ids(self) -> List[str]:
        return [s.position_id for s in self.snapshots]

    # ── Filtering ─────────────────────────────────────────────────────────────

    def by_portfolio(self, portfolio_id: str) -> List[PositionSnapshot]:
        return [s for s in self.snapshots if s.portfolio_id == portfolio_id]

    def by_strategy(self, strategy_id: str) -> List[PositionSnapshot]:
        return [s for s in self.snapshots if s.strategy_id == strategy_id]

    def by_instrument(self, instrument: str) -> List[PositionSnapshot]:
        return [s for s in self.snapshots if s.instrument == instrument]

    def by_lifecycle_state(self, state: str) -> List[PositionSnapshot]:
        return [s for s in self.snapshots if s.lifecycle_state == state]

    def by_risk_state(self, risk_state: str) -> List[PositionSnapshot]:
        return [s for s in self.snapshots if s.risk_state == risk_state]

    def published_only(self) -> List[PositionSnapshot]:
        return [s for s in self.snapshots if s.is_published]

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":   self.bundle_id,
            "label":       self.label,
            "count":       self.count,
            "position_ids": self.position_ids,
            "created_at":  self.created_at,
            "version":     self.version,
        }


def make_snapshot_bundle(
    snapshots:  List[PositionSnapshot],
    *,
    label:    str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> SnapshotBundle:
    """Factory for ``SnapshotBundle`` with a generated UUID and current timestamp."""
    return SnapshotBundle(
        bundle_id=str(uuid.uuid4()),
        label=label,
        snapshots=tuple(snapshots),
        created_at=time.time(),
        metadata=metadata or {},
    )
