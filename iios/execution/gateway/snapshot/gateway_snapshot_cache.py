"""iios/execution/gateway/snapshot/gateway_snapshot_cache.py
==================================================
GatewaySnapshotCache — thread-safe LRU bounded cache for
recently published or retrieved snapshots.

C6 Execution Intelligence — Phase 5, Module 5
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import List, Optional

from .constants import DEFAULT_MAX_CACHE_SIZE
from .execution_gateway_snapshot import ExecutionGatewaySnapshot


class GatewaySnapshotCache:
    """
    Thread-safe LRU (Least Recently Used) bounded cache.

    When the cache is full, the oldest (least recently accessed)
    snapshot is evicted to make room for a new one.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_CACHE_SIZE) -> None:
        self._max_size = max(1, max_size)
        self._cache: OrderedDict[str, ExecutionGatewaySnapshot] = OrderedDict()
        self._lock = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def put(self, snapshot: ExecutionGatewaySnapshot) -> bool:
        """
        Insert or update a snapshot in the cache.

        Returns True if the cache was full and an entry was evicted.
        """
        with self._lock:
            evicted = False
            if snapshot.snapshot_id in self._cache:
                self._cache.move_to_end(snapshot.snapshot_id)
            else:
                if len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)  # evict LRU
                    evicted = True
                self._cache[snapshot.snapshot_id] = snapshot
            return evicted

    def evict(self, snapshot_id: str) -> bool:
        """Explicitly remove a snapshot from the cache.  Returns True if found."""
        with self._lock:
            if snapshot_id in self._cache:
                del self._cache[snapshot_id]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> Optional[ExecutionGatewaySnapshot]:
        """
        Retrieve a snapshot by ID, promoting it to most-recently-used.

        Returns None if not cached.
        """
        with self._lock:
            if snapshot_id not in self._cache:
                return None
            self._cache.move_to_end(snapshot_id)
            return self._cache[snapshot_id]

    def peek(self, snapshot_id: str) -> Optional[ExecutionGatewaySnapshot]:
        """Retrieve without affecting LRU order."""
        with self._lock:
            return self._cache.get(snapshot_id)

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._cache

    def snapshot_ids(self) -> List[str]:
        """Return cached IDs in LRU → MRU order."""
        with self._lock:
            return list(self._cache.keys())

    # ── State ─────────────────────────────────────────────────────────────────

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    @property
    def max_size(self) -> int:
        return self._max_size

    @property
    def is_full(self) -> bool:
        with self._lock:
            return len(self._cache) >= self._max_size

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._cache) == 0
