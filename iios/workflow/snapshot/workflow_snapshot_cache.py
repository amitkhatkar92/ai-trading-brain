"""
workflow_snapshot_cache.py — iios.workflow.snapshot
----------------------------------------------------
WorkflowSnapshotCache — bounded LRU-style in-memory cache for hot snapshots.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_CACHE_SIZE
from .workflow_snapshot import WorkflowSnapshot

_log = get_logger(__name__)


class WorkflowSnapshotCache:
    """
    Thread-safe, bounded LRU cache for WorkflowSnapshot objects.

    Most-recently-accessed snapshots are kept hot.
    """

    def __init__(self, capacity: int = DEFAULT_CACHE_SIZE) -> None:
        self._capacity = max(1, capacity)
        self._cache: OrderedDict[str, WorkflowSnapshot] = OrderedDict()
        self._hits   = 0
        self._misses = 0
        self._lock   = threading.Lock()

    # ── Cache operations ──────────────────────────────────────────────────────

    def put(self, snapshot: WorkflowSnapshot) -> None:
        with self._lock:
            if snapshot.snapshot_id in self._cache:
                self._cache.move_to_end(snapshot.snapshot_id)
                self._cache[snapshot.snapshot_id] = snapshot
            else:
                if len(self._cache) >= self._capacity:
                    evicted, _ = self._cache.popitem(last=False)
                    _log.debug(f"Cache: evicted snapshot={evicted!r}")
                self._cache[snapshot.snapshot_id] = snapshot

    def get(self, snapshot_id: str) -> Optional[WorkflowSnapshot]:
        with self._lock:
            snap = self._cache.get(snapshot_id)
            if snap is not None:
                self._cache.move_to_end(snapshot_id)
                self._hits += 1
            else:
                self._misses += 1
        return snap

    def remove(self, snapshot_id: str) -> bool:
        with self._lock:
            if snapshot_id in self._cache:
                del self._cache[snapshot_id]
                return True
        return False

    def contains(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._cache

    # ── Introspection ─────────────────────────────────────────────────────────

    def size(self) -> int:
        with self._lock:
            return len(self._cache)

    def hit_rate(self) -> float:
        with self._lock:
            total = self._hits + self._misses
        return round(self._hits / total, 4) if total else 0.0

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "capacity": self._capacity,
                "size":     len(self._cache),
                "hits":     self._hits,
                "misses":   self._misses,
                "hit_rate": round(self._hits / total, 4) if total else 0.0,
            }

    def clear(self) -> int:
        with self._lock:
            n = len(self._cache)
            self._cache.clear()
            self._hits   = 0
            self._misses = 0
        return n
