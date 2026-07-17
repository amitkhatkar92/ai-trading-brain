"""iios/execution/risk/snapshot/execution_risk_snapshot_cache.py
==================================================
SnapshotCache — bounded LRU fast-lookup cache.

Backed by OrderedDict for O(1) LRU eviction.  Thread-safe.

C6 Execution Intelligence — Phase 4, Module 5
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional

from .constants import DEFAULT_MAX_CACHE_SIZE
from .execution_risk_snapshot import ExecutionRiskSnapshot


class SnapshotCache:
    """
    Bounded LRU cache for ExecutionRiskSnapshot objects.

    On access (get), the entry is moved to the most-recently-used
    position.  When the cache is full and a new entry is inserted, the
    least-recently-used entry is silently evicted.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_CACHE_SIZE) -> None:
        self._max_size = max(1, max_size)
        self._lock     = threading.RLock()
        self._data: OrderedDict[str, ExecutionRiskSnapshot] = OrderedDict()

    # ── Write ─────────────────────────────────────────────────────────────────

    def put(self, snapshot: ExecutionRiskSnapshot) -> None:
        with self._lock:
            sid = snapshot.snapshot_id
            if sid in self._data:
                # Refresh position
                self._data.move_to_end(sid)
                self._data[sid] = snapshot
            else:
                self._data[sid] = snapshot
                if len(self._data) > self._max_size:
                    # Evict LRU (leftmost)
                    self._data.popitem(last=False)

    def evict(self, snapshot_id: str) -> bool:
        """Remove *snapshot_id* from cache.  Returns True if it was present."""
        with self._lock:
            if snapshot_id in self._data:
                del self._data[snapshot_id]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional[ExecutionRiskSnapshot]:
        """Return snapshot and promote to MRU position, or None."""
        with self._lock:
            if snapshot_id in self._data:
                self._data.move_to_end(snapshot_id)
                return self._data[snapshot_id]
            return None

    def peek(self, snapshot_id: str) -> Optional[ExecutionRiskSnapshot]:
        """Return snapshot WITHOUT changing its LRU position."""
        with self._lock:
            return self._data.get(snapshot_id)

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._data

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._data)

    @property
    def is_full(self) -> bool:
        with self._lock:
            return len(self._data) >= self._max_size

    @property
    def max_size(self) -> int:
        return self._max_size
