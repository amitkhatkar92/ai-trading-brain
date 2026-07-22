"""
portfolio_snapshot_store.py — iios.portfolio.snapshot
======================================================
Thread-safe, in-memory persistent snapshot store with secondary
indexes for O(1) multi-dimensional queries.

Indexes maintained
------------------
  primary          : snapshot_id  → PortfolioSnapshot
  by_portfolio     : portfolio_id → List[snapshot_id]     (insertion order)
  by_session       : session_id   → List[snapshot_id]
  by_type          : portfolio_type → List[snapshot_id]
  by_status        : snapshot_status → List[snapshot_id]
  by_health        : portfolio_health → List[snapshot_id]
  latest_per_pf    : portfolio_id → snapshot_id (last written)

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from .constants import DEFAULT_MAX_STORE, SnapshotStatus
from .exceptions import SnapshotCapacityError, SnapshotDuplicateError, SnapshotNotFoundError
from .portfolio_snapshot import PortfolioSnapshot


class PortfolioSnapshotStore:
    """
    Thread-safe, bounded, in-memory store for PortfolioSnapshot objects.

    Parameters
    ----------
    max_size : int
        Hard limit on stored snapshots.  Exceeding it raises
        ``SnapshotCapacityError``.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_STORE) -> None:
        if max_size < 1:
            max_size = 1
        self._max_size = max_size
        self._lock = threading.Lock()
        # primary
        self._store:         Dict[str, PortfolioSnapshot] = {}
        # secondary indexes
        self._by_portfolio:  Dict[str, List[str]] = {}
        self._by_session:    Dict[str, List[str]] = {}
        self._by_type:       Dict[str, List[str]] = {}
        self._by_status:     Dict[str, List[str]] = {}
        self._by_health:     Dict[str, List[str]] = {}
        self._latest_per_pf: Dict[str, str] = {}      # portfolio_id → snapshot_id

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, snapshot: PortfolioSnapshot) -> None:
        """
        Persist a new snapshot.

        Raises
        ------
        SnapshotDuplicateError  if ``snapshot.snapshot_id`` already exists.
        SnapshotCapacityError   if the store is at capacity.
        """
        sid = snapshot.snapshot_id
        with self._lock:
            if sid in self._store:
                raise SnapshotDuplicateError(sid)
            if len(self._store) >= self._max_size:
                raise SnapshotCapacityError(self._max_size)
            self._store[sid] = snapshot
            self._index_snapshot(snapshot)

    def update(self, snapshot: PortfolioSnapshot) -> None:
        """
        Replace an existing snapshot (e.g., after a status transition).
        If it does not exist it is inserted.
        """
        sid = snapshot.snapshot_id
        with self._lock:
            if sid in self._store:
                old = self._store[sid]
                self._deindex_snapshot(old)
            elif len(self._store) >= self._max_size:
                raise SnapshotCapacityError(self._max_size)
            self._store[sid] = snapshot
            self._index_snapshot(snapshot)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> Optional[PortfolioSnapshot]:
        """Return a snapshot by ID, or None."""
        with self._lock:
            return self._store.get(snapshot_id)

    def get_or_raise(self, snapshot_id: str) -> PortfolioSnapshot:
        snap = self.get(snapshot_id)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        return snap

    def get_latest(self, portfolio_id: str) -> Optional[PortfolioSnapshot]:
        """Return the most-recently saved snapshot for a portfolio."""
        with self._lock:
            sid = self._latest_per_pf.get(portfolio_id)
            if sid is None:
                return None
            return self._store.get(sid)

    def find_by_portfolio(self, portfolio_id: str) -> List[PortfolioSnapshot]:
        with self._lock:
            sids = self._by_portfolio.get(portfolio_id, [])
            return [self._store[s] for s in sids if s in self._store]

    def find_by_session(self, session_id: str) -> List[PortfolioSnapshot]:
        with self._lock:
            sids = self._by_session.get(session_id, [])
            return [self._store[s] for s in sids if s in self._store]

    def find_by_type(self, portfolio_type: str) -> List[PortfolioSnapshot]:
        with self._lock:
            sids = self._by_type.get(portfolio_type, [])
            return [self._store[s] for s in sids if s in self._store]

    def find_by_status(self, status: str | SnapshotStatus) -> List[PortfolioSnapshot]:
        val = status.value if isinstance(status, SnapshotStatus) else status
        with self._lock:
            sids = self._by_status.get(val, [])
            return [self._store[s] for s in sids if s in self._store]

    def find_by_health(self, health: str) -> List[PortfolioSnapshot]:
        with self._lock:
            sids = self._by_health.get(health, [])
            return [self._store[s] for s in sids if s in self._store]

    def find_by_name(self, portfolio_name: str) -> List[PortfolioSnapshot]:
        with self._lock:
            return [s for s in self._store.values()
                    if s.portfolio_name == portfolio_name]

    def find_by_timestamp_range(
        self, start: float, end: float
    ) -> List[PortfolioSnapshot]:
        with self._lock:
            return [s for s in self._store.values()
                    if start <= s.timestamp <= end]

    def query(self, **filters: Any) -> List[PortfolioSnapshot]:
        """
        Generic query; supported filter keys match PortfolioSnapshot fields.

        Example::
            store.query(portfolio_type="equity", snapshot_status="published")
        """
        with self._lock:
            results = list(self._store.values())
        for key, value in filters.items():
            results = [s for s in results if getattr(s, key, None) == value]
        return results

    # ------------------------------------------------------------------
    # Status mutation (archive)
    # ------------------------------------------------------------------

    def archive(self, snapshot_id: str) -> bool:
        """
        Transition a snapshot to ARCHIVED status.

        Returns True if the snapshot was found and updated, False if
        it was already archived or not found.
        """
        with self._lock:
            snap = self._store.get(snapshot_id)
            if snap is None:
                return False
            if snap.snapshot_status == SnapshotStatus.ARCHIVED.value:
                return False
            updated = snap.with_status(SnapshotStatus.ARCHIVED)
            self._deindex_snapshot(snap)
            self._store[snapshot_id] = updated
            self._index_snapshot(updated)
            return True

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._store

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def all(self) -> List[PortfolioSnapshot]:
        with self._lock:
            return list(self._store.values())

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._by_portfolio.clear()
            self._by_session.clear()
            self._by_type.clear()
            self._by_status.clear()
            self._by_health.clear()
            self._latest_per_pf.clear()

    # ------------------------------------------------------------------
    # Private indexing helpers (must be called under self._lock)
    # ------------------------------------------------------------------

    def _index_snapshot(self, snap: PortfolioSnapshot) -> None:
        sid = snap.snapshot_id
        _idx_append(self._by_portfolio, snap.portfolio_id, sid)
        if snap.portfolio_session_id:
            _idx_append(self._by_session, snap.portfolio_session_id, sid)
        if snap.portfolio_type:
            _idx_append(self._by_type, snap.portfolio_type, sid)
        _idx_append(self._by_status, snap.snapshot_status, sid)
        _idx_append(self._by_health, snap.portfolio_health, sid)
        self._latest_per_pf[snap.portfolio_id] = sid

    def _deindex_snapshot(self, snap: PortfolioSnapshot) -> None:
        sid = snap.snapshot_id
        _idx_remove(self._by_portfolio, snap.portfolio_id, sid)
        if snap.portfolio_session_id:
            _idx_remove(self._by_session, snap.portfolio_session_id, sid)
        if snap.portfolio_type:
            _idx_remove(self._by_type, snap.portfolio_type, sid)
        _idx_remove(self._by_status, snap.snapshot_status, sid)
        _idx_remove(self._by_health, snap.portfolio_health, sid)


# ---------------------------------------------------------------------------
# Index helpers
# ---------------------------------------------------------------------------

def _idx_append(idx: Dict[str, List[str]], key: str, value: str) -> None:
    if key not in idx:
        idx[key] = []
    if value not in idx[key]:
        idx[key].append(value)


def _idx_remove(idx: Dict[str, List[str]], key: str, value: str) -> None:
    lst = idx.get(key, [])
    try:
        lst.remove(value)
    except ValueError:
        pass
