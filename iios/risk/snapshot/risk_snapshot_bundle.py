"""
risk_snapshot_bundle.py — iios.risk.snapshot
=============================================
Bundle of multiple RiskSnapshot instances for batch operations.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .constants import DEFAULT_MAX_BUNDLE_SIZE, VERSION
from .exceptions import RiskSnapshotCapacityError
from .risk_snapshot import RiskSnapshot


@dataclass(frozen=True)
class RiskSnapshotBundle:
    """
    Immutable collection of :class:`~.risk_snapshot.RiskSnapshot` instances.

    Used for batch publishing, transmission, or archival of multiple
    snapshots in a single operation.
    """
    bundle_id:     str
    snapshots:     Tuple[RiskSnapshot, ...]
    portfolio_ids: Tuple[str, ...]
    bundle_size:   int
    avg_risk_score: float
    max_risk_score: float
    min_risk_score: float
    created_at:    float
    framework_version: str = VERSION

    def __len__(self) -> int:
        return self.bundle_size

    def __iter__(self) -> Iterator[RiskSnapshot]:
        return iter(self.snapshots)

    def __contains__(self, snapshot_id: str) -> bool:  # type: ignore[override]
        return any(s.snapshot_id == snapshot_id for s in self.snapshots)

    def get(self, snapshot_id: str) -> Optional[RiskSnapshot]:
        for s in self.snapshots:
            if s.snapshot_id == snapshot_id:
                return s
        return None

    def filter_by_portfolio(self, portfolio_id: str) -> List[RiskSnapshot]:
        return [s for s in self.snapshots if s.portfolio_id == portfolio_id]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":        self.bundle_id,
            "bundle_size":      self.bundle_size,
            "portfolio_ids":    list(self.portfolio_ids),
            "avg_risk_score":   self.avg_risk_score,
            "max_risk_score":   self.max_risk_score,
            "min_risk_score":   self.min_risk_score,
            "created_at":       self.created_at,
            "framework_version": self.framework_version,
        }

    @classmethod
    def create(
        cls,
        snapshots:  List[RiskSnapshot],
        *,
        bundle_id: Optional[str] = None,
        max_size:  int           = DEFAULT_MAX_BUNDLE_SIZE,
    ) -> "RiskSnapshotBundle":
        if len(snapshots) > max_size:
            raise RiskSnapshotCapacityError(
                f"Bundle size {len(snapshots)} exceeds maximum {max_size}"
            )
        if not snapshots:
            return cls(
                bundle_id      = bundle_id or str(uuid.uuid4()),
                snapshots      = (),
                portfolio_ids  = (),
                bundle_size    = 0,
                avg_risk_score = 0.0,
                max_risk_score = 0.0,
                min_risk_score = 0.0,
                created_at     = time.time(),
            )
        scores = [s.risk_score for s in snapshots]
        return cls(
            bundle_id      = bundle_id or str(uuid.uuid4()),
            snapshots      = tuple(snapshots),
            portfolio_ids  = tuple(sorted({s.portfolio_id for s in snapshots})),
            bundle_size    = len(snapshots),
            avg_risk_score = sum(scores) / len(scores),
            max_risk_score = max(scores),
            min_risk_score = min(scores),
            created_at     = time.time(),
        )


class RiskSnapshotBundleBuilder:
    """Builder for accumulating snapshots into a bundle."""

    def __init__(self, max_size: int = DEFAULT_MAX_BUNDLE_SIZE) -> None:
        self._max_size = max_size
        self._snapshots: List[RiskSnapshot] = []

    def add(self, snapshot: RiskSnapshot) -> "RiskSnapshotBundleBuilder":
        if len(self._snapshots) >= self._max_size:
            raise RiskSnapshotCapacityError(
                f"Bundle capacity {self._max_size} exceeded"
            )
        self._snapshots.append(snapshot)
        return self

    def size(self) -> int:
        return len(self._snapshots)

    def build(self, bundle_id: Optional[str] = None) -> RiskSnapshotBundle:
        return RiskSnapshotBundle.create(
            self._snapshots,
            bundle_id=bundle_id,
            max_size=self._max_size,
        )
