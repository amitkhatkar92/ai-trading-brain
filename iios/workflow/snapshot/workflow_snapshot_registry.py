"""
workflow_snapshot_registry.py — iios.workflow.snapshot
-------------------------------------------------------
WorkflowSnapshotRegistry — thread-safe in-memory registry for snapshots.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_SNAPSHOTS
from .exceptions import WorkflowSnapshotNotFoundError, WorkflowSnapshotRegistryError
from .workflow_snapshot import WorkflowSnapshot

_log = get_logger(__name__)


class WorkflowSnapshotRegistry:
    """
    Thread-safe registry for WorkflowSnapshot objects.

    Indexed by snapshot_id and workflow_id for fast lookup.
    """

    def __init__(self, max_snapshots: int = DEFAULT_MAX_SNAPSHOTS) -> None:
        self._max        = max_snapshots
        self._snapshots: Dict[str, WorkflowSnapshot]  = {}
        self._by_wf:     Dict[str, List[str]]          = {}  # workflow_id → [snapshot_id]
        self._lock       = threading.Lock()

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, snapshot: WorkflowSnapshot) -> None:
        with self._lock:
            if len(self._snapshots) >= self._max:
                raise WorkflowSnapshotRegistryError(
                    f"Registry at capacity: limit={self._max}"
                )
            self._snapshots[snapshot.snapshot_id] = snapshot
            self._by_wf.setdefault(snapshot.workflow_id, [])
            if snapshot.snapshot_id not in self._by_wf[snapshot.workflow_id]:
                self._by_wf[snapshot.workflow_id].append(snapshot.snapshot_id)
        _log.debug(f"Registry: registered snapshot={snapshot.snapshot_id!r}")

    def deregister(self, snapshot_id: str) -> bool:
        with self._lock:
            snap = self._snapshots.pop(snapshot_id, None)
            if snap is None:
                return False
            wf_list = self._by_wf.get(snap.workflow_id, [])
            if snapshot_id in wf_list:
                wf_list.remove(snapshot_id)
        return True

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, snapshot_id: str) -> WorkflowSnapshot:
        with self._lock:
            snap = self._snapshots.get(snapshot_id)
        if snap is None:
            raise WorkflowSnapshotNotFoundError(snapshot_id)
        return snap

    def get_or_none(self, snapshot_id: str) -> Optional[WorkflowSnapshot]:
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def get_by_workflow(self, workflow_id: str) -> List[WorkflowSnapshot]:
        with self._lock:
            ids   = list(self._by_wf.get(workflow_id, []))
            snaps = [self._snapshots[sid] for sid in ids if sid in self._snapshots]
        return snaps

    def latest_for_workflow(self, workflow_id: str) -> Optional[WorkflowSnapshot]:
        """Return the most-recently registered snapshot for a workflow."""
        snaps = self.get_by_workflow(workflow_id)
        if not snaps:
            return None
        return max(snaps, key=lambda s: s.snapshot_timestamp)

    def all_snapshots(self) -> List[WorkflowSnapshot]:
        with self._lock:
            return list(self._snapshots.values())

    def exists(self, snapshot_id: str) -> bool:
        with self._lock:
            return snapshot_id in self._snapshots

    # ── Introspection ─────────────────────────────────────────────────────────

    def snapshot_count(self) -> int:
        with self._lock:
            return len(self._snapshots)

    def clear(self) -> int:
        with self._lock:
            n = len(self._snapshots)
            self._snapshots.clear()
            self._by_wf.clear()
        return n
