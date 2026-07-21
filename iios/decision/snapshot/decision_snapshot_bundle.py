"""
decision_snapshot_bundle.py — iios.decision.snapshot
=====================================================
DecisionSnapshotBundle — a named, immutable collection of related snapshots.

Useful when publishing a coherent set of decisions for a workflow,
portfolio rebalancing cycle, or batch evaluation run.

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .constants import VERSION
from .decision_snapshot import DecisionSnapshot


@dataclass(frozen=True)
class DecisionSnapshotBundle:
    """
    An immutable, ordered collection of :class:`DecisionSnapshot` objects.

    Parameters
    ----------
    bundle_id :         Unique identifier.
    name :              Human-readable bundle name.
    snapshots :         Ordered tuple of snapshots in this bundle.
    workflow_id :       Optional workflow context.
    portfolio_id :      Optional portfolio context.
    description :       Optional human-readable description.
    metadata :          Arbitrary supplementary data.
    created_at :        UTC creation timestamp.
    framework_version : Framework version.
    """

    bundle_id:         str
    name:              str
    snapshots:         Tuple[DecisionSnapshot, ...]
    workflow_id:       str              = ""
    portfolio_id:      str              = ""
    description:       str              = ""
    metadata:          Dict[str, Any]   = field(default_factory=dict)
    created_at:        datetime         = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    framework_version: str              = VERSION

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self.snapshots)

    @property
    def decision_ids(self) -> List[str]:
        return [s.decision_id for s in self.snapshots]

    @property
    def snapshot_ids(self) -> List[str]:
        return [s.snapshot_id for s in self.snapshots]

    @property
    def approved_count(self) -> int:
        return sum(1 for s in self.snapshots if s.is_approved)

    @property
    def rejected_count(self) -> int:
        return sum(1 for s in self.snapshots if s.is_rejected)

    @property
    def healthy_count(self) -> int:
        return sum(1 for s in self.snapshots if s.is_healthy)

    @property
    def successful_count(self) -> int:
        return sum(1 for s in self.snapshots if s.is_successful)

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> Optional[DecisionSnapshot]:
        for s in self.snapshots:
            if s.snapshot_id == snapshot_id:
                return s
        return None

    def for_decision(self, decision_id: str) -> Optional[DecisionSnapshot]:
        for s in self.snapshots:
            if s.decision_id == decision_id:
                return s
        return None

    def __iter__(self) -> Iterator[DecisionSnapshot]:
        return iter(self.snapshots)

    def __len__(self) -> int:
        return len(self.snapshots)

    def __contains__(self, snapshot_id: str) -> bool:
        return any(s.snapshot_id == snapshot_id for s in self.snapshots)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":         self.bundle_id,
            "name":              self.name,
            "size":              self.size,
            "workflow_id":       self.workflow_id,
            "portfolio_id":      self.portfolio_id,
            "description":       self.description,
            "snapshot_ids":      self.snapshot_ids,
            "decision_ids":      self.decision_ids,
            "approved_count":    self.approved_count,
            "rejected_count":    self.rejected_count,
            "healthy_count":     self.healthy_count,
            "successful_count":  self.successful_count,
            "created_at":        self.created_at.isoformat(),
            "framework_version": self.framework_version,
        }

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name:      str,
        snapshots: List[DecisionSnapshot],
        *,
        bundle_id:    Optional[str]        = None,
        workflow_id:  str                  = "",
        portfolio_id: str                  = "",
        description:  str                  = "",
        metadata:     Optional[Dict]        = None,
    ) -> "DecisionSnapshotBundle":
        return cls(
            bundle_id    = bundle_id or str(uuid.uuid4()),
            name         = name,
            snapshots    = tuple(snapshots),
            workflow_id  = workflow_id,
            portfolio_id = portfolio_id,
            description  = description,
            metadata     = metadata or {},
        )
