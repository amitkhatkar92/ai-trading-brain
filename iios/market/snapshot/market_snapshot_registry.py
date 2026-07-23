"""
market_snapshot_registry.py — iios.market.snapshot
====================================================
Thread-safe in-memory registry of market snapshots.

C12 Market Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_SNAPSHOTS, SnapshotStatus
from .exceptions import MarketSnapshotRegistryError
from .market_snapshot import MarketSnapshot


class MarketSnapshotRegistry:
    """
    Thread-safe registry holding market snapshots keyed by ``snapshot_id``.

    When capacity is reached, the oldest entry is evicted (FIFO).
    """

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        self._max   = max_snapshots
        self._lock  = threading.RLock()
        self._store: OrderedDict[str, MarketSnapshot] = OrderedDict()

    def register(self, snapshot: MarketSnapshot) -> None:
        if not snapshot.snapshot_id:
            raise MarketSnapshotRegistryError("snapshot_id must not be empty")
        with self._lock:
            if snapshot.snapshot_id in self._store:
                del self._store[snapshot.snapshot_id]
            elif len(self._store) >= self._max:
                self._store.popitem(last=False)
            self._store[snapshot.snapshot_id] = snapshot

    def get(self, snapshot_id: str) -> Optional[MarketSnapshot]:
        with self._lock:
            return self._store.get(snapshot_id)

    def get_or_raise(self, snapshot_id: str) -> MarketSnapshot:
        snap = self.get(snapshot_id)
        if snap is None:
            from .exceptions import MarketSnapshotNotFoundError
            raise MarketSnapshotNotFoundError(snapshot_id)
        return snap

    def latest_for_exchange(self, exchange: str) -> Optional[MarketSnapshot]:
        with self._lock:
            results = [s for s in self._store.values() if s.exchange == exchange]
            return results[-1] if results else None

    def latest_published(self, exchange: str) -> Optional[MarketSnapshot]:
        with self._lock:
            results = [
                s for s in self._store.values()
                if s.exchange == exchange and s.status == SnapshotStatus.PUBLISHED
            ]
            return results[-1] if results else None

    def by_status(self, status: SnapshotStatus) -> List[MarketSnapshot]:
        with self._lock:
            return [s for s in self._store.values() if s.status == status]

    def by_analysis_id(self, market_analysis_id: str) -> List[MarketSnapshot]:
        with self._lock:
            return [
                s for s in self._store.values()
                if s.market_analysis_id == market_analysis_id
            ]

    def remove(self, snapshot_id: str) -> bool:
        with self._lock:
            if snapshot_id in self._store:
                del self._store[snapshot_id]
                return True
            return False

    def all_snapshots(self) -> List[MarketSnapshot]:
        with self._lock:
            return list(self._store.values())

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def is_registered(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._store

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
