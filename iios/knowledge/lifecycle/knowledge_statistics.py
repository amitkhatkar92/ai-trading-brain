"""
knowledge_statistics.py — iios.knowledge.lifecycle
----------------------------------------------------
Thread-safe statistics accumulator for the Knowledge Lifecycle subsystem.

Tracked counters (6)
--------------------
1. knowledge_sessions_created
2. knowledge_sessions_completed
3. knowledge_sessions_failed
4. knowledge_sessions_archived
5. transition_count
6. average_session_duration_seconds

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional


class KnowledgeStatistics:
    """Thread-safe statistics accumulator for knowledge lifecycle events."""

    def __init__(self) -> None:
        self._lock          = threading.Lock()
        self._created       = 0
        self._completed     = 0
        self._failed        = 0
        self._archived      = 0
        self._transitions   = 0
        self._durations: List[float] = []      # session duration in seconds

    # ------------------------------------------------------------------
    # Increment helpers (called by KnowledgeLifecycle)
    # ------------------------------------------------------------------

    def record_created(self) -> None:
        with self._lock:
            self._created += 1

    def record_completed(self) -> None:
        with self._lock:
            self._completed += 1

    def record_failed(self) -> None:
        with self._lock:
            self._failed += 1

    def record_archived(self, duration_seconds: Optional[float] = None) -> None:
        with self._lock:
            self._archived += 1
            if duration_seconds is not None and duration_seconds >= 0:
                self._durations.append(duration_seconds)

    def record_transition(self) -> None:
        with self._lock:
            self._transitions += 1

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Return a consistent snapshot of all statistics."""
        with self._lock:
            avg_duration = (
                sum(self._durations) / len(self._durations)
                if self._durations else 0.0
            )
            return {
                "knowledge_sessions_created":          self._created,
                "knowledge_sessions_completed":        self._completed,
                "knowledge_sessions_failed":           self._failed,
                "knowledge_sessions_archived":         self._archived,
                "transition_count":                    self._transitions,
                "average_session_duration_seconds":    round(avg_duration, 6),
            }

    def reset(self) -> None:
        """Reset all counters (used in tests / reinitialization)."""
        with self._lock:
            self._created     = 0
            self._completed   = 0
            self._failed      = 0
            self._archived    = 0
            self._transitions = 0
            self._durations   = []
