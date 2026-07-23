"""
risk_snapshot_store.py — iios.risk.snapshot
=============================================
Persistent-style in-memory store for RiskSnapshot instances.

Provides ordered storage with query capabilities beyond the registry.
In production this would wrap a database; here it uses an ordered
dict for full test coverage and framework compliance.

C11 Risk Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_SNAPSHOTS, SnapshotStatus
from .exceptions import (
    RiskSnapshotCapacityError,
    RiskSnapshotNotFoundError,
    RiskSnapshotStoreError,
)
from .risk_snapshot import RiskSnapshot


class RiskSnapshotStore:
    """
    Thread-safe ordered snapshot store.

    Supports:
    - Persistence of snapshots with insertion order
    - Query by portfolio, status, score range
    - Count queries

    Parameters
    ----------
    max_snapshots :
        Maximum snapshots to persist.
    """

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        self._max  = max_snapshots
        self._lock = threading.RLock()
        self._store: Dict[str, RiskSnapshot] = {}   # insertion-ordered

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def store(self, snapshot: RiskSnapshot) -> None:
        """
        Persist a snapshot.

        Raises
        ------
        RiskSnapshotCapacityError
            When store is at capacity.
        """
        with self._lock:
            if snapshot.snapshot_id in self._store:
                # Allow idempotent re-storage (update in place)
                self._store[snapshot.snapshot_id] = snapshot
                return
            if len(self._store) >= self._max:
                raise RiskSnapshotCapacityError(
                    f"Snapshot store capacity exceeded ({self._max})"
                )
            self._store[snapshot.snapshot_id] = snapshot

    def store_many(self, snapshots: List[RiskSnapshot]) -> int:
        """Persist multiple snapshots. Returns count stored."""
        count = 0
        for s in snapshots:
            self.store(s)
            count += 1
        return count

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def load(self, snapshot_id: str) -> RiskSnapshot:
        """
        Retrieve a snapshot by ID.

        Raises
        ------
        RiskSnapshotNotFoundError
        """
        with self._lock:
            snapshot = self._store.get(snapshot_id)
        if snapshot is None:
            raise RiskSnapshotNotFoundError(f"Snapshot not found: {snapshot_id}")
        return snapshot

    def load_or_none(self, snapshot_id: str) -> Optional[RiskSnapshot]:
        with self._lock:
            return self._store.get(snapshot_id)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query_by_portfolio(
        self,
        portfolio_id: str,
        *,
        limit: int = 100,
    ) -> List[RiskSnapshot]:
        """Return snapshots for a portfolio, most recent first."""
        with self._lock:
            matches = [
                s for s in reversed(list(self._store.values()))
                if s.portfolio_id == portfolio_id
            ]
        return matches[:limit]

    def query_by_status(self, status: SnapshotStatus) -> List[RiskSnapshot]:
        with self._lock:
            return [s for s in self._store.values() if s.risk_status == status]

    def query_by_score_range(
        self,
        min_score: float = 0.0,
        max_score: float = 100.0,
    ) -> List[RiskSnapshot]:
        with self._lock:
            return [
                s for s in self._store.values()
                if min_score <= s.risk_score <= max_score
            ]

    def query_published(self) -> List[RiskSnapshot]:
        return self.query_by_status(SnapshotStatus.PUBLISHED)

    def latest_for_portfolio(self, portfolio_id: str) -> Optional[RiskSnapshot]:
        results = self.query_by_portfolio(portfolio_id, limit=1)
        return results[0] if results else None

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def delete(self, snapshot_id: str) -> bool:
        with self._lock:
            return self._store.pop(snapshot_id, None) is not None

    def delete_by_portfolio(self, portfolio_id: str) -> int:
        with self._lock:
            to_delete = [
                sid for sid, s in self._store.items()
                if s.portfolio_id == portfolio_id
            ]
            for sid in to_delete:
                del self._store[sid]
        return len(to_delete)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._store) == 0

    def count_by_portfolio(self, portfolio_id: str) -> int:
        with self._lock:
            return sum(1 for s in self._store.values() if s.portfolio_id == portfolio_id)
