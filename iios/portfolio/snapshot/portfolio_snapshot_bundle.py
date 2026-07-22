"""
portfolio_snapshot_bundle.py — iios.portfolio.snapshot
=======================================================
PortfolioSnapshotBundle — an immutable container that groups multiple
PortfolioSnapshot objects for coordinated delivery to downstream
consumers (e.g., risk engine batch update, dashboard refresh).

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .constants import VERSION, SNAPSHOT_SYSTEM_ID
from .portfolio_snapshot import PortfolioSnapshot


@dataclass(frozen=True)
class PortfolioSnapshotBundle:
    """
    Immutable collection of PortfolioSnapshot objects.

    A bundle is a single published artefact that carries zero or more
    snapshots together.  It does not own the snapshots — it merely
    references them.  Downstream consumers unpack the bundle and
    process each snapshot independently.

    Fields
    ------
    bundle_id :       Unique identifier for this bundle.
    bundle_name :     Human-readable name.
    snapshots :       Tuple of PortfolioSnapshot objects (insertion order).
    created_at :      Wall-clock bundle creation timestamp.
    metadata :        Arbitrary supplementary metadata dict.
    framework_version: Framework version string.
    """
    bundle_id:         str
    bundle_name:       str
    snapshots:         tuple          # Tuple[PortfolioSnapshot, ...]
    created_at:        float
    metadata:          Dict[str, Any]
    framework_version: str

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def snapshot_count(self) -> int:
        return len(self.snapshots)

    @property
    def is_empty(self) -> bool:
        return len(self.snapshots) == 0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_by_portfolio(self, portfolio_id: str) -> List[PortfolioSnapshot]:
        """Return all snapshots for a given portfolio_id."""
        return [s for s in self.snapshots if s.portfolio_id == portfolio_id]

    def get_by_id(self, snapshot_id: str) -> Optional[PortfolioSnapshot]:
        """Return the snapshot with the given ID, or None."""
        for snap in self.snapshots:
            if snap.snapshot_id == snapshot_id:
                return snap
        return None

    def latest_per_portfolio(self) -> Dict[str, PortfolioSnapshot]:
        """
        Return the highest-versioned snapshot per portfolio.

        If multiple snapshots for the same portfolio are present in the
        bundle the one with the largest ``snapshot_version`` is returned.
        """
        result: Dict[str, PortfolioSnapshot] = {}
        for snap in self.snapshots:
            pid = snap.portfolio_id
            if pid not in result or snap.snapshot_version > result[pid].snapshot_version:
                result[pid] = snap
        return result

    def portfolio_ids(self) -> List[str]:
        """Return the distinct portfolio IDs present in the bundle."""
        seen: List[str] = []
        for snap in self.snapshots:
            if snap.portfolio_id not in seen:
                seen.append(snap.portfolio_id)
        return seen

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":        self.bundle_id,
            "bundle_name":      self.bundle_name,
            "snapshot_count":   self.snapshot_count,
            "snapshots":        [s.to_dict() for s in self.snapshots],
            "created_at":       self.created_at,
            "metadata":         dict(self.metadata),
            "framework_version": self.framework_version,
        }

    # ------------------------------------------------------------------
    # Factory class methods
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        snapshots:  List[PortfolioSnapshot],
        *,
        bundle_name: str = "",
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> "PortfolioSnapshotBundle":
        """Create a new bundle from a list of snapshots."""
        return cls(
            bundle_id         = str(uuid.uuid4()),
            bundle_name       = bundle_name,
            snapshots         = tuple(snapshots),
            created_at        = time.time(),
            metadata          = dict(metadata or {}),
            framework_version = VERSION,
        )

    @classmethod
    def empty(cls, *, bundle_name: str = "empty") -> "PortfolioSnapshotBundle":
        """Create an empty bundle (e.g., for initialisation)."""
        return cls.create([], bundle_name=bundle_name)
