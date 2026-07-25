"""
workflow_snapshot_store.py — iios.workflow.snapshot
----------------------------------------------------
WorkflowSnapshotStore — bounded, thread-safe persistent-style store for
snapshots, indexed by snapshot_id and workflow_id.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_HISTORY
from .exceptions import WorkflowSnapshotNotFoundError, WorkflowSnapshotStoreError
from .workflow_snapshot import WorkflowSnapshot

_log = get_logger(__name__)


class WorkflowSnapshotStore:
    """
    Thread-safe, bounded store for WorkflowSnapshot objects.

    Oldest entries are evicted automatically when capacity is exceeded.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._max       = max_entries
        self._deque:    deque[WorkflowSnapshot]       = deque(maxlen=max_entries)
        self._by_id:    Dict[str, WorkflowSnapshot]   = {}
        self._by_wf:    Dict[str, List[str]]          = {}
        self._lock      = threading.Lock()

    # ── Storage ───────────────────────────────────────────────────────────────

    def save(self, snapshot: WorkflowSnapshot) -> None:
        with self._lock:
            # Evict oldest from by_id index when deque is full
            if len(self._deque) == self._max and self._deque:
                oldest = self._deque[0]
                self._by_id.pop(oldest.snapshot_id, None)
            self._deque.append(snapshot)
            self._by_id[snapshot.snapshot_id] = snapshot
            self._by_wf.setdefault(snapshot.workflow_id, [])
            if snapshot.snapshot_id not in self._by_wf[snapshot.workflow_id]:
                self._by_wf[snapshot.workflow_id].append(snapshot.snapshot_id)
        _log.debug(f"Store: saved snapshot={snapshot.snapshot_id!r}")

    def delete(self, snapshot_id: str) -> bool:
        with self._lock:
            snap = self._by_id.pop(snapshot_id, None)
            if snap is None:
                return False
            wf_list = self._by_wf.get(snap.workflow_id, [])
            if snapshot_id in wf_list:
                wf_list.remove(snapshot_id)
        return True

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> WorkflowSnapshot:
        with self._lock:
            snap = self._by_id.get(snapshot_id)
        if snap is None:
            raise WorkflowSnapshotNotFoundError(snapshot_id)
        return snap

    def get_or_none(self, snapshot_id: str) -> Optional[WorkflowSnapshot]:
        with self._lock:
            return self._by_id.get(snapshot_id)

    def get_by_workflow(self, workflow_id: str) -> List[WorkflowSnapshot]:
        with self._lock:
            ids   = list(self._by_wf.get(workflow_id, []))
            snaps = [self._by_id[sid] for sid in ids if sid in self._by_id]
        return snaps

    def recent(self, n: int = 20) -> List[WorkflowSnapshot]:
        with self._lock:
            items = list(self._deque)
        return list(reversed(items[-n:]))

    def exists(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._by_id

    # ── Introspection ─────────────────────────────────────────────────────────

    def count(self) -> int:
        with self._lock:
            return len(self._deque)

    def clear(self) -> int:
        with self._lock:
            n = len(self._deque)
            self._deque.clear()
            self._by_id.clear()
            self._by_wf.clear()
        return n
