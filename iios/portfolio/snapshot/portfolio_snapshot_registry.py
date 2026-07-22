"""
portfolio_snapshot_registry.py — iios.portfolio.snapshot
=========================================================
PortfolioSnapshotRegistry — central coordinator for snapshot storage,
caching, history, and publication.

All downstream consumers MUST interact with the registry rather than
the individual store, cache, or history components.

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from .constants import SnapshotStatus, PortfolioHealth
from .exceptions import SnapshotNotFoundError
from .portfolio_snapshot import PortfolioSnapshot
from .portfolio_snapshot_cache import PortfolioSnapshotCache
from .portfolio_snapshot_history import PortfolioSnapshotHistory
from .portfolio_snapshot_statistics import PortfolioSnapshotStatistics
from .portfolio_snapshot_store import PortfolioSnapshotStore
from .portfolio_snapshot_validation import PortfolioSnapshotValidator


class PortfolioSnapshotRegistry:
    """
    Thread-safe central coordinator for the Portfolio Snapshot subsystem.

    The registry:
    - Stores every registered snapshot in the persistent store.
    - Caches recently accessed snapshots for fast lookup.
    - Tracks per-portfolio version history.
    - Exposes a unified query interface to downstream consumers.
    - Records lifecycle statistics.

    Parameters
    ----------
    store :     Persistent store (injected; default is a new instance).
    cache :     LRU cache (injected; default is a new instance).
    history :   Version history (injected; default is a new instance).
    statistics: Statistics accumulator (injected; default is a new instance).
    """

    def __init__(
        self,
        *,
        store:      Optional[PortfolioSnapshotStore]      = None,
        cache:      Optional[PortfolioSnapshotCache]      = None,
        history:    Optional[PortfolioSnapshotHistory]    = None,
        statistics: Optional[PortfolioSnapshotStatistics] = None,
        auto_validate: bool = False,
    ) -> None:
        self._store      = store      or PortfolioSnapshotStore()
        self._cache      = cache      or PortfolioSnapshotCache()
        self._history    = history    or PortfolioSnapshotHistory()
        self._stats      = statistics or PortfolioSnapshotStatistics()
        self._validator  = PortfolioSnapshotValidator()
        self._auto_validate = auto_validate
        self._lock       = threading.Lock()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        """
        Register a snapshot.

        Saves to the persistent store, warms the cache, and records the
        version in history.  Returns the (potentially status-updated)
        snapshot.

        If auto_validate=True was set at construction time the validator
        runs automatically and the snapshot status transitions from
        DRAFT → VALIDATED on success.

        Raises
        ------
        SnapshotDuplicateError  if the snapshot_id already exists.
        SnapshotCapacityError   if the store is full.
        """
        if self._auto_validate and snapshot.snapshot_status == SnapshotStatus.DRAFT.value:
            result = self._validator.validate(snapshot)
            duration_ms = result.duration_s * 1000
            if result.is_valid:
                snapshot = snapshot.with_status(SnapshotStatus.VALIDATED)
                self._stats.record_validation_success(duration_ms)
            else:
                self._stats.record_validation_failure(duration_ms)

        self._store.save(snapshot)
        self._cache.put(snapshot)
        self._history.record(snapshot)
        self._stats.record_created()
        return snapshot

    def publish(self, snapshot_id: str) -> PortfolioSnapshot:
        """
        Transition a VALIDATED snapshot to PUBLISHED.

        Raises
        ------
        SnapshotNotFoundError if the snapshot does not exist.
        """
        snap = self._store.get_or_raise(snapshot_id)
        published = snap.with_status(SnapshotStatus.PUBLISHED)
        self._store.update(published)
        self._cache.put(published)
        self._history.record(published)
        self._stats.record_published()
        return published

    def archive(self, snapshot_id: str) -> bool:
        """
        Archive a snapshot.  Returns True if the store was mutated.
        """
        archived = self._store.archive(snapshot_id)
        if archived:
            snap = self._store.get(snapshot_id)
            if snap:
                self._cache.put(snap)
            self._stats.record_archived()
        return archived

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> Optional[PortfolioSnapshot]:
        """Return a snapshot by ID (cache-first, store fallback)."""
        snap = self._cache.get(snapshot_id)
        if snap is not None:
            self._stats.record_cache_hit()
            return snap
        self._stats.record_cache_miss()
        snap = self._store.get(snapshot_id)
        if snap is not None:
            self._cache.put(snap)
        return snap

    def get_or_raise(self, snapshot_id: str) -> PortfolioSnapshot:
        snap = self.get(snapshot_id)
        if snap is None:
            raise SnapshotNotFoundError(snapshot_id)
        return snap

    def get_latest(self, portfolio_id: str) -> Optional[PortfolioSnapshot]:
        """Return the latest snapshot for a portfolio."""
        snap = self._cache.get_latest(portfolio_id)
        if snap is not None:
            return snap
        return self._store.get_latest(portfolio_id)

    def get_history(
        self, portfolio_id: str, limit: int = 0
    ) -> List[PortfolioSnapshot]:
        """Return version history for a portfolio (chronological order)."""
        return self._history.get_versions(portfolio_id, limit=limit)

    def get_by_session(self, session_id: str) -> List[PortfolioSnapshot]:
        """Return all snapshots for a portfolio lifecycle session."""
        return self._store.find_by_session(session_id)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def query(self, **filters: Any) -> List[PortfolioSnapshot]:
        """
        Query snapshots by arbitrary field filters.

        Supported keys: any field on PortfolioSnapshot.

        Examples::
            registry.query(portfolio_type="equity")
            registry.query(snapshot_status="published", portfolio_health="healthy")
        """
        return self._store.query(**filters)

    def find_by_portfolio(self, portfolio_id: str) -> List[PortfolioSnapshot]:
        return self._store.find_by_portfolio(portfolio_id)

    def find_by_type(self, portfolio_type: str) -> List[PortfolioSnapshot]:
        return self._store.find_by_type(portfolio_type)

    def find_by_status(self, status: str | SnapshotStatus) -> List[PortfolioSnapshot]:
        return self._store.find_by_status(status)

    def find_by_health(self, health: str | PortfolioHealth) -> List[PortfolioSnapshot]:
        h = health.value if isinstance(health, PortfolioHealth) else health
        return self._store.find_by_health(h)

    def find_by_name(self, portfolio_name: str) -> List[PortfolioSnapshot]:
        return self._store.find_by_name(portfolio_name)

    # ------------------------------------------------------------------
    # Statistics and inspection
    # ------------------------------------------------------------------

    def count(self) -> int:
        return self._store.count()

    def statistics(self) -> Dict[str, Any]:
        return self._stats.snapshot()

    def validate(self, snapshot: PortfolioSnapshot):
        """Run validation on a snapshot without registering it."""
        return self._validator.validate(snapshot)

    def clear(self) -> None:
        self._store.clear()
        self._cache.clear()
        self._history.clear()
        self._stats.reset()
