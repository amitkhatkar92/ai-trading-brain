"""
workflow_snapshot_history.py — iios.workflow.snapshot
------------------------------------------------------
WorkflowSnapshotHistory — bounded, thread-safe version history for snapshots.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_HISTORY
from .workflow_snapshot import WorkflowSnapshot

_log = get_logger(__name__)


class WorkflowSnapshotHistory:
    """
    Thread-safe, bounded history of WorkflowSnapshot objects.

    Maintains a chronological deque and workflow-id index.
    """

    def __init__(self, max_entries: int = DEFAULT_MAX_HISTORY) -> None:
        self._max   = max_entries
        self._deque: deque[WorkflowSnapshot]      = deque(maxlen=max_entries)
        self._by_id: Dict[str, WorkflowSnapshot]  = {}
        self._by_wf: Dict[str, List[str]]         = {}
        self._lock  = threading.Lock()

    def record(self, snapshot: WorkflowSnapshot) -> None:
        with self._lock:
            if len(self._deque) == self._max and self._deque:
                oldest = self._deque[0]
                self._by_id.pop(oldest.snapshot_id, None)
            self._deque.append(snapshot)
            self._by_id[snapshot.snapshot_id] = snapshot
            self._by_wf.setdefault(snapshot.workflow_id, [])
            if snapshot.snapshot_id not in self._by_wf[snapshot.workflow_id]:
                self._by_wf[snapshot.workflow_id].append(snapshot.snapshot_id)

    def get(self, snapshot_id: str) -> Optional[WorkflowSnapshot]:
        with self._lock:
            return self._by_id.get(snapshot_id)

    def for_workflow(self, workflow_id: str) -> List[WorkflowSnapshot]:
        with self._lock:
            ids   = list(self._by_wf.get(workflow_id, []))
            snaps = [self._by_id[sid] for sid in ids if sid in self._by_id]
        return snaps

    def recent(self, n: int = 20) -> List[WorkflowSnapshot]:
        with self._lock:
            items = list(self._deque)
        return list(reversed(items[-n:]))

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
