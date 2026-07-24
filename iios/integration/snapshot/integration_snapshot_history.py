"""
integration_snapshot_history.py — iios.integration.snapshot
-------------------------------------------------------------
IntegrationSnapshotHistory — bounded, thread-safe chronological log of
integration snapshot events.

C15 Enterprise Integration & Connectivity — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_HISTORY_SIZE, ENTRY_ID_PREFIX, SnapshotStatus
from .integration_snapshot import IntegrationSnapshot

_log = get_logger(__name__)


@dataclass(frozen=True)
class SnapshotHistoryEntry:
    """Immutable record of a single snapshot event in the history log."""
    entry_id:         str
    snapshot_id:      str
    session_id:       str
    workflow_id:      str
    snapshot_version: str
    status:           SnapshotStatus
    lifecycle_state:  str
    governance_state: str
    recorded_at:      str


@dataclass(frozen=True)
class SnapshotHistoryReport:
    """Immutable summary of the history log."""
    total_entries: int
    published:     int
    archived:      int
    expired:       int
    by_session:    Dict[str, int]    # session_id → entry count
    generated_at:  str


class IntegrationSnapshotHistory:
    """
    Thread-safe, bounded chronological log of IntegrationSnapshot entries.

    Oldest entries are dropped when max_size is reached (FIFO).
    """

    def __init__(self, max_size: int = DEFAULT_HISTORY_SIZE) -> None:
        self._max_size: int                        = max_size
        self._entries:  Deque[SnapshotHistoryEntry] = deque(maxlen=max_size)
        self._lock:     threading.Lock             = threading.Lock()

    def record(self, snapshot: IntegrationSnapshot) -> SnapshotHistoryEntry:
        """
        Record a snapshot event in the history log.

        Returns the created SnapshotHistoryEntry.
        """
        entry = SnapshotHistoryEntry(
            entry_id         = f"{ENTRY_ID_PREFIX}{uuid.uuid4().hex[:12]}",
            snapshot_id      = snapshot.snapshot_id,
            session_id       = snapshot.integration_session_id,
            workflow_id      = snapshot.integration_workflow_id,
            snapshot_version = snapshot.snapshot_version,
            status           = snapshot.status,
            lifecycle_state  = snapshot.lifecycle_state.value,
            governance_state = snapshot.governance_state.value,
            recorded_at      = datetime.now(tz=timezone.utc).isoformat(),
        )
        with self._lock:
            self._entries.append(entry)
        return entry

    def recent(self, n: int = 20) -> List[SnapshotHistoryEntry]:
        """Return the n most-recent entries (newest last)."""
        with self._lock:
            entries = list(self._entries)
        return entries[-n:]

    def by_session(self, session_id: str) -> List[SnapshotHistoryEntry]:
        """Return all entries for a given integration_session_id."""
        with self._lock:
            return [e for e in self._entries if e.session_id == session_id]

    def by_status(self, status: SnapshotStatus) -> List[SnapshotHistoryEntry]:
        """Return all entries with a given SnapshotStatus."""
        with self._lock:
            return [e for e in self._entries if e.status == status]

    def report(self) -> SnapshotHistoryReport:
        """Generate an immutable summary report of the history log."""
        with self._lock:
            entries = list(self._entries)

        session_counts: Dict[str, int] = {}
        published = archived = expired = 0
        for e in entries:
            session_counts[e.session_id] = session_counts.get(e.session_id, 0) + 1
            if e.status == SnapshotStatus.PUBLISHED:
                published += 1
            elif e.status == SnapshotStatus.ARCHIVED:
                archived  += 1
            elif e.status == SnapshotStatus.EXPIRED:
                expired   += 1

        return SnapshotHistoryReport(
            total_entries = len(entries),
            published     = published,
            archived      = archived,
            expired       = expired,
            by_session    = session_counts,
            generated_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    def clear(self) -> int:
        """Clear the history log. Returns the number of entries cleared."""
        with self._lock:
            n = len(self._entries)
            self._entries.clear()
        return n

    @property
    def size(self) -> int:
        """Current number of entries in the log."""
        with self._lock:
            return len(self._entries)

    @property
    def max_size(self) -> int:
        return self._max_size
