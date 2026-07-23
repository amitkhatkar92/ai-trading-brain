"""
risk_snapshot_registry.py — iios.risk.snapshot
================================================
Thread-safe in-memory registry for RiskSnapshot instances.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_SNAPSHOTS, SnapshotStatus
from .exceptions import (
    RiskSnapshotCapacityError,
    RiskSnapshotNotFoundError,
    RiskSnapshotRegistryError,
)
from .risk_snapshot import RiskSnapshot


class RiskSnapshotRegistry:
    """
    Thread-safe in-memory registry for :class:`~.risk_snapshot.RiskSnapshot`.

    Supports:
    - Registration and retrieval by snapshot_id
    - Latest snapshot per portfolio_id
    - Latest snapshot per risk_assessment_id
    - Versioned snapshots per assessment
    - Capacity enforcement

    Parameters
    ----------
    max_snapshots :
        Maximum total snapshots to retain.
    """

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        self._max  = max_snapshots
        self._lock = threading.RLock()
        # snapshot_id → RiskSnapshot
        self._snapshots: Dict[str, RiskSnapshot] = {}
        # portfolio_id → latest snapshot_id
        self._latest_by_portfolio: Dict[str, str] = {}
        # assessment_id → latest snapshot_id
        self._latest_by_assessment: Dict[str, str] = {}
        # assessment_id → list[snapshot_id] ordered by snapshot_version
        self._versions_by_assessment: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, snapshot: RiskSnapshot) -> None:
        """
        Register a snapshot.

        Raises
        ------
        RiskSnapshotCapacityError
            When registry is at capacity.
        RiskSnapshotRegistryError
            When a duplicate snapshot_id is detected.
        """
        with self._lock:
            if len(self._snapshots) >= self._max:
                raise RiskSnapshotCapacityError(
                    f"Registry capacity exceeded ({self._max} snapshots)"
                )
            if snapshot.snapshot_id in self._snapshots:
                raise RiskSnapshotRegistryError(
                    f"Snapshot already registered: {snapshot.snapshot_id}"
                )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._latest_by_portfolio[snapshot.portfolio_id]       = snapshot.snapshot_id
            self._latest_by_assessment[snapshot.risk_assessment_id] = snapshot.snapshot_id
            versions = self._versions_by_assessment.setdefault(
                snapshot.risk_assessment_id, []
            )
            versions.append(snapshot.snapshot_id)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> RiskSnapshot:
        """
        Retrieve a snapshot by ID.

        Raises
        ------
        RiskSnapshotNotFoundError
        """
        with self._lock:
            snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise RiskSnapshotNotFoundError(f"Snapshot not found: {snapshot_id}")
        return snapshot

    def get_or_none(self, snapshot_id: str) -> Optional[RiskSnapshot]:
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def latest_for_portfolio(self, portfolio_id: str) -> Optional[RiskSnapshot]:
        """Return the most recently registered snapshot for a portfolio."""
        with self._lock:
            sid = self._latest_by_portfolio.get(portfolio_id)
            if sid is None:
                return None
            return self._snapshots.get(sid)

    def latest_for_assessment(self, assessment_id: str) -> Optional[RiskSnapshot]:
        """Return the most recently registered snapshot for an assessment."""
        with self._lock:
            sid = self._latest_by_assessment.get(assessment_id)
            if sid is None:
                return None
            return self._snapshots.get(sid)

    def versions_for_assessment(self, assessment_id: str) -> List[RiskSnapshot]:
        """Return all versions of a snapshot for an assessment, in order."""
        with self._lock:
            ids = list(self._versions_by_assessment.get(assessment_id, []))
            return [self._snapshots[sid] for sid in ids if sid in self._snapshots]

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def all_snapshots(self) -> List[RiskSnapshot]:
        with self._lock:
            return list(self._snapshots.values())

    def snapshots_for_portfolio(self, portfolio_id: str) -> List[RiskSnapshot]:
        with self._lock:
            return [
                s for s in self._snapshots.values()
                if s.portfolio_id == portfolio_id
            ]

    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------

    def remove(self, snapshot_id: str) -> bool:
        """Remove a snapshot by ID. Returns True if removed, False if not found."""
        with self._lock:
            snapshot = self._snapshots.pop(snapshot_id, None)
            if snapshot is None:
                return False
            # Clean up index references (leave latest intact if different version exists)
            if self._latest_by_portfolio.get(snapshot.portfolio_id) == snapshot_id:
                remaining = [
                    s for s in self._snapshots.values()
                    if s.portfolio_id == snapshot.portfolio_id
                ]
                if remaining:
                    newest = max(remaining, key=lambda x: x.created_time)
                    self._latest_by_portfolio[snapshot.portfolio_id] = newest.snapshot_id
                else:
                    del self._latest_by_portfolio[snapshot.portfolio_id]
            versions = self._versions_by_assessment.get(snapshot.risk_assessment_id)
            if versions and snapshot_id in versions:
                versions.remove(snapshot_id)
            return True

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._latest_by_portfolio.clear()
            self._latest_by_assessment.clear()
            self._versions_by_assessment.clear()

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    def portfolio_count(self) -> int:
        with self._lock:
            return len(self._latest_by_portfolio)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._snapshots) == 0
