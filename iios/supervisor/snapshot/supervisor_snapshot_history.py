"""
supervisor_snapshot_history.py — iios.supervisor.snapshot
----------------------------------------------------------
Bounded history store for supervisor snapshot artefacts.

Thread-safe.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, List

from .constants import DEFAULT_MAX_HISTORY


class SupervisorSnapshotHistory:
    """
    Thread-safe bounded history store.

    Maintains separate bounded deques for snapshots and events.
    """

    def __init__(
        self,
        max_snapshots: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock:      threading.Lock = threading.Lock()
        self._snapshots: Deque[Any]     = deque(maxlen=max_snapshots)
        self._events:    Deque[Any]     = deque(maxlen=max_events)

    # ------------------------------------------------------------------
    # Recorders
    # ------------------------------------------------------------------

    def record_snapshot(self, snapshot: Any) -> None:
        with self._lock:
            self._snapshots.append(snapshot)

    def record_event(self, event: Any) -> None:
        with self._lock:
            self._events.append(event)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def recent_snapshots(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._snapshots)
        return items[-n:] if n > 0 else items

    def recent_events(self, n: int = 10) -> List[Any]:
        with self._lock:
            items = list(self._events)
        return items[-n:] if n > 0 else items

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def counts(self) -> Dict[str, int]:
        with self._lock:
            return {
                "snapshots": len(self._snapshots),
                "events":    len(self._events),
            }

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._events.clear()
