"""
iios/execution/recovery/snapshot/recovery_snapshot_history.py
=============================================================
RecoverySnapshotHistory — bounded, thread-safe history of snapshots
and snapshot events.

C7 Execution Recovery & Resilience — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import deque
from typing import List, Optional, TYPE_CHECKING

from .constants import DEFAULT_MAX_HISTORY

if TYPE_CHECKING:
    from .execution_recovery_snapshot import ExecutionRecoverySnapshot
    from .recovery_snapshot_events import SnapshotEvent


class RecoverySnapshotHistory:
    """
    Bounded, thread-safe history of ExecutionRecoverySnapshot and SnapshotEvent objects.

    Supports:
      • append/read snapshots and events
      • session and failure-based filtering
      • latest snapshot access
      • bounded capacity (oldest entries are discarded when full)
    """

    def __init__(
        self,
        max_snapshots: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY * 2,
    ) -> None:
        self._max_snapshots = max_snapshots
        self._max_events    = max_events
        self._lock          = threading.Lock()
        self._snapshots: deque["ExecutionRecoverySnapshot"] = deque(maxlen=max_snapshots)
        self._events:    deque["SnapshotEvent"]              = deque(maxlen=max_events)

    # ── Append ────────────────────────────────────────────────────────────────

    def append(self, snapshot: "ExecutionRecoverySnapshot") -> None:
        with self._lock:
            self._snapshots.append(snapshot)

    def append_event(self, event: "SnapshotEvent") -> None:
        with self._lock:
            self._events.append(event)

    # ── Read ──────────────────────────────────────────────────────────────────

    def snapshots(self) -> List["ExecutionRecoverySnapshot"]:
        with self._lock:
            return list(self._snapshots)

    def events(self) -> List["SnapshotEvent"]:
        with self._lock:
            return list(self._events)

    def latest(self) -> Optional["ExecutionRecoverySnapshot"]:
        with self._lock:
            return self._snapshots[-1] if self._snapshots else None

    # ── Filtered lookups ──────────────────────────────────────────────────────

    def for_session(self, recovery_session_id: str) -> List["ExecutionRecoverySnapshot"]:
        with self._lock:
            return [s for s in self._snapshots if s.recovery_session_id == recovery_session_id]

    def for_failure(self, failure_id: str) -> List["ExecutionRecoverySnapshot"]:
        with self._lock:
            return [s for s in self._snapshots if s.failure_id == failure_id]

    def for_execution(self, execution_session_id: str) -> List["ExecutionRecoverySnapshot"]:
        with self._lock:
            return [
                s for s in self._snapshots
                if s.execution_session_id == execution_session_id
            ]

    # ── Counts ────────────────────────────────────────────────────────────────

    @property
    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    @property
    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def clear(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._events.clear()
