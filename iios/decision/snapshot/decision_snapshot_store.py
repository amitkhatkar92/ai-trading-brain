"""
decision_snapshot_store.py — iios.decision.snapshot
====================================================
Thread-safe snapshot store providing:
- Primary storage (in-memory)
- Version history per decision_id
- Multiple query dimensions
- Latest snapshot lookup
- Historical version retrieval

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .constants import (
    DEFAULT_MAX_SNAPSHOTS,
    DEFAULT_MAX_VERSIONS,
    SnapshotStatus,
)
from .decision_snapshot import DecisionSnapshot
from .decision_snapshot_cache import DecisionSnapshotCache
from .decision_snapshot_validation import DecisionSnapshotValidator
from .exceptions import (
    DuplicateSnapshotError,
    SnapshotNotFoundError,
    SnapshotStoreError,
    SnapshotValidationError,
)


class DecisionSnapshotStore:
    """
    Provides snapshot persistence, versioning, and multi-dimensional queries.

    Architecture
    ------------
    * Primary dict keyed by snapshot_id.
    * Per-decision version lists (ordered by snapshot_version).
    * Integrated LRU cache for hot-path reads.
    * Built-in validator — :meth:`save` rejects invalid snapshots.

    Parameters
    ----------
    max_snapshots : Hard limit on stored snapshots.
    max_versions :  Max versions retained per decision_id.
    cache_size :    LRU cache capacity.
    validate :      If True (default) validate before storing.
    """

    def __init__(
        self,
        max_snapshots: int  = DEFAULT_MAX_SNAPSHOTS,
        max_versions:  int  = DEFAULT_MAX_VERSIONS,
        cache_size:    int  = 1_000,
        validate:      bool = True,
    ) -> None:
        self._lock         = threading.RLock()
        self._store:       Dict[str, DecisionSnapshot]          = {}
        self._versions:    Dict[str, List[DecisionSnapshot]]    = defaultdict(list)
        self._max          = max_snapshots
        self._max_versions = max_versions
        self._cache        = DecisionSnapshotCache(cache_size)
        self._validator    = DecisionSnapshotValidator() if validate else None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, snapshot: DecisionSnapshot) -> None:
        """
        Persist *snapshot*.

        Raises
        ------
        :class:`DuplicateSnapshotError`   : snapshot_id already exists.
        :class:`SnapshotStoreError`        : capacity exceeded.
        :class:`SnapshotValidationError`   : validation failed.
        """
        # Validate outside the lock (stateless operation)
        if self._validator is not None:
            result = self._validator.validate(snapshot)
            if not result.is_valid:
                raise SnapshotValidationError(
                    f"Snapshot {snapshot.snapshot_id!r} failed validation: "
                    + "; ".join(result.error_messages),
                    failed_checks=tuple(c.value for c in result.failed_checks),
                )

        with self._lock:
            sid = snapshot.snapshot_id
            if sid in self._store:
                raise DuplicateSnapshotError(sid)
            if len(self._store) >= self._max:
                raise SnapshotStoreError(f"Store full (max {self._max})")

            did = snapshot.decision_id
            if len(self._versions[did]) >= self._max_versions:
                # Evict oldest version to make room
                oldest = self._versions[did].pop(0)
                self._store.pop(oldest.snapshot_id, None)
                self._cache.invalidate(oldest.snapshot_id)

            self._store[sid] = snapshot
            self._versions[did].append(snapshot)
            self._versions[did].sort(key=lambda s: s.snapshot_version)
            self._cache.put(snapshot)

    def delete(self, snapshot_id: str) -> Optional[DecisionSnapshot]:
        """Remove and return the snapshot, or None if not found."""
        with self._lock:
            snap = self._store.pop(snapshot_id, None)
            if snap is None:
                return None
            did = snap.decision_id
            self._versions[did] = [
                s for s in self._versions[did] if s.snapshot_id != snapshot_id
            ]
            if not self._versions[did]:
                del self._versions[did]
            self._cache.invalidate(snapshot_id)
            return snap

    # ------------------------------------------------------------------
    # Read — by snapshot_id
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> DecisionSnapshot:
        """Return the snapshot or raise :class:`SnapshotNotFoundError`."""
        cached = self._cache.get(snapshot_id)
        if cached is not None:
            return cached
        with self._lock:
            if snapshot_id not in self._store:
                raise SnapshotNotFoundError(snapshot_id)
            snap = self._store[snapshot_id]
        self._cache.put(snap)
        return snap

    def find(self, snapshot_id: str) -> Optional[DecisionSnapshot]:
        """Return the snapshot or None."""
        try:
            return self.get(snapshot_id)
        except SnapshotNotFoundError:
            return None

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._store

    # ------------------------------------------------------------------
    # Read — by decision_id
    # ------------------------------------------------------------------

    def latest(self, decision_id: str) -> Optional[DecisionSnapshot]:
        """Return the highest-version snapshot for *decision_id*, or None."""
        with self._lock:
            versions = self._versions.get(decision_id, [])
            return versions[-1] if versions else None

    def history(self, decision_id: str) -> List[DecisionSnapshot]:
        """Return all versions for *decision_id*, oldest first."""
        with self._lock:
            return list(self._versions.get(decision_id, []))

    def version(self, decision_id: str, version: int) -> Optional[DecisionSnapshot]:
        """Return the snapshot with exactly *version* for *decision_id*."""
        with self._lock:
            for snap in self._versions.get(decision_id, []):
                if snap.snapshot_version == version:
                    return snap
            return None

    # ------------------------------------------------------------------
    # Query — by secondary dimensions
    # ------------------------------------------------------------------

    def by_session(self, session_id: str) -> List[DecisionSnapshot]:
        with self._lock:
            return [s for s in self._store.values() if s.session_id == session_id]

    def by_workflow(self, workflow_id: str) -> List[DecisionSnapshot]:
        with self._lock:
            return [s for s in self._store.values() if s.workflow_id == workflow_id]

    def by_portfolio(self, portfolio_id: str) -> List[DecisionSnapshot]:
        with self._lock:
            return [s for s in self._store.values() if s.portfolio_id == portfolio_id]

    def by_strategy(self, strategy_id: str) -> List[DecisionSnapshot]:
        with self._lock:
            return [s for s in self._store.values() if s.strategy_id == strategy_id]

    def by_status(self, status: str) -> List[DecisionSnapshot]:
        with self._lock:
            return [
                s for s in self._store.values()
                if s.decision_status.value == status
            ]

    def by_type(self, decision_type: str) -> List[DecisionSnapshot]:
        with self._lock:
            return [s for s in self._store.values() if s.decision_type == decision_type]

    def by_priority(self, decision_priority: str) -> List[DecisionSnapshot]:
        with self._lock:
            return [
                s for s in self._store.values()
                if s.decision_priority == decision_priority
            ]

    def by_timestamp_range(
        self,
        start: datetime,
        end:   datetime,
    ) -> List[DecisionSnapshot]:
        """Return snapshots whose created_at falls within [start, end]."""
        with self._lock:
            return [
                s for s in self._store.values()
                if start <= s.created_at <= end
            ]

    # ------------------------------------------------------------------
    # Bulk
    # ------------------------------------------------------------------

    def all_snapshots(self) -> List[DecisionSnapshot]:
        with self._lock:
            return list(self._store.values())

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def decision_count(self) -> int:
        with self._lock:
            return len(self._versions)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._versions.clear()
            self._cache.clear()
