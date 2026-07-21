"""
decision_snapshot_history.py — iios.decision.snapshot
======================================================
Thread-safe bounded history of snapshots and events.

C9 Decision Intelligence — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Deque, List, Optional

from .constants import DEFAULT_MAX_HISTORY, SnapshotEventType
from .decision_snapshot import DecisionSnapshot
from .decision_snapshot_events import DecisionSnapshotEvent


class DecisionSnapshotHistory:
    """
    Thread-safe bounded history for :class:`DecisionSnapshot` and
    :class:`DecisionSnapshotEvent` objects.

    Parameters
    ----------
    max_snapshots : Maximum snapshots retained (FIFO eviction).
    max_events :    Maximum events retained.
    """

    def __init__(
        self,
        max_snapshots: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self._lock      = threading.Lock()
        self._snapshots: Deque[DecisionSnapshot]     = deque(maxlen=max_snapshots)
        self._events:    Deque[DecisionSnapshotEvent] = deque(maxlen=max_events)

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def record_snapshot(self, snapshot: DecisionSnapshot) -> None:
        with self._lock:
            self._snapshots.append(snapshot)

    def snapshots(self) -> List[DecisionSnapshot]:
        with self._lock:
            return list(self._snapshots)

    def latest_snapshot(self) -> Optional[DecisionSnapshot]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    def snapshots_for_decision(self, decision_id: str) -> List[DecisionSnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.decision_id == decision_id]

    def snapshots_for_session(self, session_id: str) -> List[DecisionSnapshot]:
        with self._lock:
            return [s for s in self._snapshots if s.session_id == session_id]

    def latest_for_decision(self, decision_id: str) -> Optional[DecisionSnapshot]:
        """Return the most recently recorded snapshot for *decision_id*."""
        with self._lock:
            snaps = [s for s in self._snapshots if s.decision_id == decision_id]
            return snaps[-1] if snaps else None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def record_event(self, event: DecisionSnapshotEvent) -> None:
        with self._lock:
            self._events.append(event)

    def events(self) -> List[DecisionSnapshotEvent]:
        with self._lock:
            return list(self._events)

    def latest_event(self) -> Optional[DecisionSnapshotEvent]:
        with self._lock:
            return self._events[-1] if self._events else None

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def events_for_snapshot(self, snapshot_id: str) -> List[DecisionSnapshotEvent]:
        with self._lock:
            return [e for e in self._events if e.snapshot_id == snapshot_id]

    def events_by_type(self, event_type: SnapshotEventType) -> List[DecisionSnapshotEvent]:
        with self._lock:
            return [e for e in self._events if e.event_type == event_type]

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._events.clear()
