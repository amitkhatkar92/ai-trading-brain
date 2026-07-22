"""
portfolio_snapshot_cache.py — iios.portfolio.snapshot
======================================================
Thread-safe, bounded LRU cache for PortfolioSnapshot objects.

The cache maintains two indexes:
  - primary   : snapshot_id  → PortfolioSnapshot
  - secondary : portfolio_id → latest snapshot_id

When capacity is reached the least-recently-used entry is evicted.

C10 Portfolio Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from .constants import DEFAULT_MAX_CACHE
from .exceptions import SnapshotCacheError
from .portfolio_snapshot import PortfolioSnapshot


class PortfolioSnapshotCache:
    """
    Thread-safe, bounded LRU cache for PortfolioSnapshot objects.

    Parameters
    ----------
    max_size : int
        Maximum number of snapshots held in memory.
        When full the LRU entry is evicted on the next ``put``.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_CACHE) -> None:
        if max_size < 1:
            raise SnapshotCacheError(f"max_size must be ≥ 1 (got {max_size})")
        self._max_size = max_size
        self._lock = threading.Lock()
        self._store: OrderedDict[str, PortfolioSnapshot] = OrderedDict()
        self._latest: Dict[str, str] = {}   # portfolio_id → snapshot_id

        # stats
        self._hits   = 0
        self._misses = 0
        self._evictions = 0

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def put(self, snapshot: PortfolioSnapshot) -> None:
        """Insert or update a snapshot in the cache."""
        sid = snapshot.snapshot_id
        pid = snapshot.portfolio_id
        with self._lock:
            if sid in self._store:
                # Refresh position — move to end (most recent)
                self._store.move_to_end(sid)
                self._store[sid] = snapshot
            else:
                if len(self._store) >= self._max_size:
                    # Evict the LRU entry (first item)
                    self._store.popitem(last=False)
                    self._evictions += 1
                self._store[sid] = snapshot
            # Update latest pointer
            self._latest[pid] = sid

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, snapshot_id: str) -> Optional[PortfolioSnapshot]:
        """Return a snapshot by ID, or None if not cached."""
        with self._lock:
            snap = self._store.get(snapshot_id)
            if snap is not None:
                self._store.move_to_end(snapshot_id)
                self._hits += 1
                return snap
            self._misses += 1
            return None

    def get_latest(self, portfolio_id: str) -> Optional[PortfolioSnapshot]:
        """Return the most-recently cached snapshot for a portfolio."""
        with self._lock:
            sid = self._latest.get(portfolio_id)
            if sid is None:
                self._misses += 1
                return None
            snap = self._store.get(sid)
            if snap is not None:
                self._store.move_to_end(sid)
                self._hits += 1
                return snap
            # Stale pointer
            del self._latest[portfolio_id]
            self._misses += 1
            return None

    # ------------------------------------------------------------------
    # Invalidation
    # ------------------------------------------------------------------

    def invalidate(self, snapshot_id: str) -> bool:
        """Remove a specific snapshot; return True if it was present."""
        with self._lock:
            if snapshot_id not in self._store:
                return False
            snap = self._store.pop(snapshot_id)
            pid = snap.portfolio_id
            if self._latest.get(pid) == snapshot_id:
                del self._latest[pid]
            return True

    def invalidate_portfolio(self, portfolio_id: str) -> int:
        """Remove all cached snapshots for a portfolio; return count removed."""
        with self._lock:
            to_remove = [
                sid for sid, s in self._store.items()
                if s.portfolio_id == portfolio_id
            ]
            for sid in to_remove:
                del self._store[sid]
            self._latest.pop(portfolio_id, None)
            return len(to_remove)

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._store

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._latest.clear()

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total else 0.0
            return {
                "size":       len(self._store),
                "max_size":   self._max_size,
                "hits":       self._hits,
                "misses":     self._misses,
                "evictions":  self._evictions,
                "hit_rate":   hit_rate,
            }
