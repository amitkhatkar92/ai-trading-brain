"""
market_snapshot_store.py — iios.market.snapshot
================================================
In-memory snapshot store with optional eviction policy.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Callable, Dict, List, Optional

from .constants import DEFAULT_MAX_SNAPSHOTS, SnapshotStatus
from .exceptions import MarketSnapshotStoreError
from .market_snapshot import MarketSnapshot


class MarketSnapshotStore:
    """
    Thread-safe snapshot store.  Stores all snapshots keyed by
    ``snapshot_id``; supports lookup by exchange and analysis ID.

    When ``max_snapshots`` is reached, the oldest entry is evicted (FIFO).
    """

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        self._max   = max_snapshots
        self._lock  = threading.RLock()
        self._store: OrderedDict[str, MarketSnapshot] = OrderedDict()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def save(self, snapshot: MarketSnapshot) -> None:
        """Persist *snapshot*; update if already present, evict oldest if full."""
        if not snapshot.snapshot_id:
            raise MarketSnapshotStoreError("snapshot_id must not be empty")
        with self._lock:
            if snapshot.snapshot_id in self._store:
                del self._store[snapshot.snapshot_id]
            elif len(self._store) >= self._max:
                self._store.popitem(last=False)
            self._store[snapshot.snapshot_id] = snapshot

    def delete(self, snapshot_id: str) -> bool:
        with self._lock:
            if snapshot_id in self._store:
                del self._store[snapshot_id]
                return True
            return False

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load(self, snapshot_id: str) -> Optional[MarketSnapshot]:
        with self._lock:
            return self._store.get(snapshot_id)

    def load_or_raise(self, snapshot_id: str) -> MarketSnapshot:
        snap = self.load(snapshot_id)
        if snap is None:
            from .exceptions import MarketSnapshotNotFoundError
            raise MarketSnapshotNotFoundError(snapshot_id)
        return snap

    def latest_for_exchange(self, exchange: str) -> Optional[MarketSnapshot]:
        with self._lock:
            results = [s for s in self._store.values() if s.exchange == exchange]
            return results[-1] if results else None

    def by_status(self, status: SnapshotStatus) -> List[MarketSnapshot]:
        with self._lock:
            return [s for s in self._store.values() if s.status == status]

    def by_analysis_id(self, market_analysis_id: str) -> List[MarketSnapshot]:
        with self._lock:
            return [s for s in self._store.values()
                    if s.market_analysis_id == market_analysis_id]

    def query(self, predicate: Callable[[MarketSnapshot], bool]) -> List[MarketSnapshot]:
        """Return all snapshots for which *predicate* returns True."""
        with self._lock:
            return [s for s in self._store.values() if predicate(s)]

    def all_snapshots(self) -> List[MarketSnapshot]:
        with self._lock:
            return list(self._store.values())

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def exists(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._store

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
