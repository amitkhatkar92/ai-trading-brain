"""
knowledge_statistics.py — iios.knowledge.engine
-------------------------------------------------
Thread-safe statistics accumulator for the Knowledge Engine.

7 tracked counters
-------------------
1. knowledge_sessions
2. knowledge_artifacts_collected
3. knowledge_sources
4. published_snapshots
5. average_collection_time_ms
6. average_processing_time_ms
7. knowledge_throughput  (artifacts / second)

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional


class KnowledgeEngineStatistics:
    """Thread-safe statistics accumulator for knowledge engine metrics."""

    def __init__(self) -> None:
        self._lock              = threading.Lock()
        self._sessions          = 0
        self._artifacts         = 0
        self._sources_seen:     set = set()
        self._snapshots         = 0
        self._collection_times: List[float] = []   # ms
        self._processing_times: List[float] = []   # ms
        self._start_time        = __import__("time").time()

    # ------------------------------------------------------------------
    # Increment helpers
    # ------------------------------------------------------------------

    def record_session(self) -> None:
        with self._lock:
            self._sessions += 1

    def record_artifacts(self, count: int, sources: Optional[List[str]] = None) -> None:
        with self._lock:
            self._artifacts += max(0, count)
            if sources:
                self._sources_seen.update(sources)

    def record_snapshot(self) -> None:
        with self._lock:
            self._snapshots += 1

    def record_collection_time(self, ms: float) -> None:
        with self._lock:
            if ms >= 0:
                self._collection_times.append(ms)

    def record_processing_time(self, ms: float) -> None:
        with self._lock:
            if ms >= 0:
                self._processing_times.append(ms)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            avg_collect = (
                sum(self._collection_times) / len(self._collection_times)
                if self._collection_times else 0.0
            )
            avg_process = (
                sum(self._processing_times) / len(self._processing_times)
                if self._processing_times else 0.0
            )
            elapsed = max(1.0, __import__("time").time() - self._start_time)
            throughput = self._artifacts / elapsed
            return {
                "knowledge_sessions":          self._sessions,
                "knowledge_artifacts_collected": self._artifacts,
                "knowledge_sources":           len(self._sources_seen),
                "published_snapshots":         self._snapshots,
                "average_collection_time_ms":  round(avg_collect, 3),
                "average_processing_time_ms":  round(avg_process, 3),
                "knowledge_throughput":        round(throughput, 6),
            }

    def reset(self) -> None:
        with self._lock:
            self._sessions          = 0
            self._artifacts         = 0
            self._sources_seen      = set()
            self._snapshots         = 0
            self._collection_times  = []
            self._processing_times  = []
            self._start_time        = __import__("time").time()
