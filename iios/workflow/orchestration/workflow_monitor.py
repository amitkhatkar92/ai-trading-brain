"""
workflow_monitor.py — iios.workflow.orchestration
--------------------------------------------------
WorkflowMonitor — real-time monitoring of active workflow executions.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .workflow_state_store import WorkflowStateStore
from .workflow_runtime import WorkflowRuntime

_log = get_logger(__name__)


@dataclass(frozen=True)
class WorkflowMonitorSnapshot:
    """Point-in-time snapshot of all active workflows."""
    active_count:   int
    total_count:    int
    snapshots:      tuple   # Tuple[Dict, ...]
    captured_at:    str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_count": self.active_count,
            "total_count":  self.total_count,
            "captured_at":  self.captured_at,
        }


class WorkflowMonitor:
    """
    Real-time monitoring of active and completed workflow executions.

    Thread-safe.
    """

    def __init__(self, state_store: Optional[WorkflowStateStore] = None) -> None:
        self._state_store = state_store or WorkflowStateStore()
        self._lock        = threading.Lock()

    def snapshot(self) -> WorkflowMonitorSnapshot:
        """Capture a monitoring snapshot of all runtimes."""
        all_rt   = self._state_store.all_runtimes()
        active   = [rt for rt in all_rt if not rt.is_terminal]
        snaps    = tuple(rt.to_dict() for rt in all_rt)
        return WorkflowMonitorSnapshot(
            active_count = len(active),
            total_count  = len(all_rt),
            snapshots    = snaps,
            captured_at  = datetime.now(tz=timezone.utc).isoformat(),
        )

    def active_workflows(self) -> List[WorkflowRuntime]:
        return self._state_store.active_runtimes()

    def get_runtime(self, runtime_id: str) -> Optional[WorkflowRuntime]:
        return self._state_store.get_or_none(runtime_id)

    def active_count(self) -> int:
        return self._state_store.active_count()

    def total_count(self) -> int:
        return self._state_store.runtime_count()

    def health(self) -> Dict[str, Any]:
        return {
            "active_workflows": self.active_count(),
            "total_workflows":  self.total_count(),
            "captured_at":      datetime.now(tz=timezone.utc).isoformat(),
        }
