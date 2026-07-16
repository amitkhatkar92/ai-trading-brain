"""iios/execution/positions/book/position_book_history.py
==================================================
BookHistory     — thread-safe, bounded, append-only list of BookEvent
SnapshotHistory — thread-safe, bounded list of PositionBookSnapshot

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import threading
from typing import Iterator, List, Optional

from .constants import BookEventType, DEFAULT_MAX_HISTORY, DEFAULT_SNAPSHOT_LIMIT
from .position_book_events import BookEvent
from .position_book_snapshot import HistoricalSnapshot, PositionBookSnapshot, make_historical_snapshot


class BookHistory:
    """
    Thread-safe, bounded, append-only record of ``BookEvent`` objects.

    When capacity is reached, the oldest entry is evicted (FIFO).
    Eviction count is tracked for audit purposes.
    """

    def __init__(self, max_size: int = DEFAULT_MAX_HISTORY) -> None:
        self._max     = max(1, max_size)
        self._events: List[BookEvent] = []
        self._evicted = 0
        self._lock    = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, event: BookEvent) -> None:
        """Append *event*; evict the oldest if at capacity."""
        with self._lock:
            if len(self._events) >= self._max:
                self._events.pop(0)
                self._evicted += 1
            self._events.append(event)

    # ── Read ──────────────────────────────────────────────────────────────────

    def all(self) -> List[BookEvent]:
        """All recorded events, oldest first."""
        with self._lock:
            return list(self._events)

    def latest(self, n: int = 10) -> List[BookEvent]:
        """The most recent *n* events, newest first."""
        with self._lock:
            return list(reversed(self._events[-n:]))

    def by_type(self, event_type: BookEventType) -> List[BookEvent]:
        """All events whose ``event_type`` matches *event_type*."""
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    def by_position(self, position_id: str) -> List[BookEvent]:
        """All events related to *position_id*."""
        with self._lock:
            return [e for e in self._events if e.position_id == position_id]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        """Total events appended (including evicted)."""
        with self._lock:
            return len(self._events) + self._evicted

    @property
    def evicted(self) -> int:
        with self._lock:
            return self._evicted

    def __len__(self) -> int:
        with self._lock:
            return len(self._events)

    def __iter__(self) -> Iterator[BookEvent]:
        with self._lock:
            return iter(list(self._events))


class SnapshotHistory:
    """
    Thread-safe, bounded list of ``PositionBookSnapshot`` objects.

    Provides access to historical snapshots via ``HistoricalSnapshot``
    wrapper objects so callers know the retrieval timestamp.

    When capacity is reached, the oldest snapshot is evicted (FIFO).
    """

    def __init__(self, max_size: int = DEFAULT_SNAPSHOT_LIMIT) -> None:
        self._max       = max(1, max_size)
        self._snapshots: List[PositionBookSnapshot] = []
        self._evicted   = 0
        self._lock      = threading.Lock()

    # ── Write ─────────────────────────────────────────────────────────────────

    def append(self, snapshot: PositionBookSnapshot) -> None:
        """Append *snapshot*; evict the oldest if at capacity."""
        with self._lock:
            if len(self._snapshots) >= self._max:
                self._snapshots.pop(0)
                self._evicted += 1
            self._snapshots.append(snapshot)

    # ── Read ──────────────────────────────────────────────────────────────────

    def latest(self) -> Optional[HistoricalSnapshot]:
        """The most recently appended snapshot, or ``None`` if empty."""
        with self._lock:
            if not self._snapshots:
                return None
            return make_historical_snapshot(self._snapshots[-1])

    def all(self) -> List[HistoricalSnapshot]:
        """All stored snapshots as ``HistoricalSnapshot`` references, oldest first."""
        with self._lock:
            return [make_historical_snapshot(s) for s in self._snapshots]

    def last_n(self, n: int) -> List[HistoricalSnapshot]:
        """The most recent *n* snapshots, newest first."""
        with self._lock:
            return [make_historical_snapshot(s) for s in reversed(self._snapshots[-n:])]

    def get_by_id(self, snapshot_id: str) -> Optional[HistoricalSnapshot]:
        """Find and return a historical snapshot by its snapshot_id."""
        with self._lock:
            for s in reversed(self._snapshots):
                if s.snapshot_id == snapshot_id:
                    return make_historical_snapshot(s)
        return None

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    @property
    def total(self) -> int:
        """Total snapshots appended (including evicted)."""
        with self._lock:
            return len(self._snapshots) + self._evicted

    @property
    def evicted(self) -> int:
        with self._lock:
            return self._evicted

    def __len__(self) -> int:
        with self._lock:
            return len(self._snapshots)
