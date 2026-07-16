"""iios/execution/positions/snapshot/position_snapshot_history.py
==================================================
SnapshotEventHistory — bounded circular log of SnapshotEvent objects.
SnapshotVersionHistory — per-position ordered list of PositionSnapshot versions.

C6 Execution Intelligence — Phase 3, Module 5
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Callable, Dict, List, Optional

from .constants import DEFAULT_MAX_EVENT_HISTORY, DEFAULT_MAX_VERSIONS_PER_POSITION
from .position_snapshot_events import SnapshotEvent, SnapshotEventType
from .position_snapshot import PositionSnapshot


# ── SnapshotEventHistory ──────────────────────────────────────────────────────

class SnapshotEventHistory:
    """
    Thread-safe, bounded circular history of ``SnapshotEvent`` objects.

    When ``max_events`` is reached, the oldest entries are evicted.
    """

    def __init__(self, max_events: int = DEFAULT_MAX_EVENT_HISTORY) -> None:
        if max_events < 1:
            raise ValueError(f"max_events must be >= 1, got {max_events}")
        self._max_events = max_events
        self._events: deque[SnapshotEvent] = deque(maxlen=max_events)
        self._lock = threading.Lock()

    def append(self, event: SnapshotEvent) -> None:
        with self._lock:
            self._events.append(event)

    def extend(self, events: List[SnapshotEvent]) -> None:
        with self._lock:
            for e in events:
                self._events.append(e)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def all(self) -> List[SnapshotEvent]:
        with self._lock:
            return list(self._events)

    def latest(self, n: int = 10) -> List[SnapshotEvent]:
        with self._lock:
            return list(self._events)[-n:]

    def for_position(self, position_id: str) -> List[SnapshotEvent]:
        with self._lock:
            return [e for e in self._events if e.position_id == position_id]

    def for_type(self, event_type: SnapshotEventType) -> List[SnapshotEvent]:
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    def filter(self, predicate: Callable[[SnapshotEvent], bool]) -> List[SnapshotEvent]:
        with self._lock:
            return [e for e in self._events if predicate(e)]

    def count(self) -> int:
        with self._lock:
            return len(self._events)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._events) == 0

    @property
    def max_events(self) -> int:
        return self._max_events

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)


# ── SnapshotVersionHistory ────────────────────────────────────────────────────

class SnapshotVersionHistory:
    """
    Thread-safe, bounded per-position version list of ``PositionSnapshot`` objects.

    Maintains an ordered list of snapshots per position_id (newest last).
    When ``max_versions`` is reached for a position, the oldest version
    is evicted to make room.
    """

    def __init__(self, max_versions: int = DEFAULT_MAX_VERSIONS_PER_POSITION) -> None:
        if max_versions < 1:
            raise ValueError(f"max_versions must be >= 1, got {max_versions}")
        self._max_versions = max_versions
        self._history: Dict[str, deque[PositionSnapshot]] = {}
        self._lock = threading.Lock()

    def add(self, snapshot: PositionSnapshot) -> None:
        """
        Add *snapshot* to the version history for its position.

        If the position's history is at capacity, the oldest version
        is evicted first.
        """
        pid = snapshot.position_id
        with self._lock:
            if pid not in self._history:
                self._history[pid] = deque(maxlen=self._max_versions)
            self._history[pid].append(snapshot)

    def get_latest(self, position_id: str) -> Optional[PositionSnapshot]:
        """Return the most recently added snapshot for *position_id*, or ``None``."""
        with self._lock:
            q = self._history.get(position_id)
            if not q:
                return None
            return q[-1]

    def get_all_versions(self, position_id: str) -> List[PositionSnapshot]:
        """Return all stored versions for *position_id*, oldest first."""
        with self._lock:
            q = self._history.get(position_id)
            return list(q) if q else []

    def get_version(self, position_id: str, version: int) -> Optional[PositionSnapshot]:
        """
        Return the snapshot whose ``snapshot_version`` equals *version*,
        or ``None`` if not found.
        """
        with self._lock:
            q = self._history.get(position_id)
            if not q:
                return None
            for snap in q:
                if snap.snapshot_version == version:
                    return snap
            return None

    def get_by_snapshot_id(self, snapshot_id: str) -> Optional[PositionSnapshot]:
        """Return the snapshot with matching ``snapshot_id``, or ``None``."""
        with self._lock:
            for q in self._history.values():
                for snap in q:
                    if snap.snapshot_id == snapshot_id:
                        return snap
            return None

    def count(self, position_id: str) -> int:
        """Return the number of stored versions for *position_id*."""
        with self._lock:
            q = self._history.get(position_id)
            return len(q) if q else 0

    def purge(self, position_id: str) -> int:
        """
        Remove all versions for *position_id*.

        Returns the number of versions that were removed.
        """
        with self._lock:
            q = self._history.pop(position_id, None)
            return len(q) if q else 0

    def all_position_ids(self) -> List[str]:
        with self._lock:
            return list(self._history.keys())

    def total_count(self) -> int:
        with self._lock:
            return sum(len(q) for q in self._history.values())

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._history) == 0

    @property
    def max_versions(self) -> int:
        return self._max_versions
