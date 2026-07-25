"""
workflow_state_store.py — iios.workflow.orchestration
------------------------------------------------------
WorkflowStateStore — thread-safe in-memory store for active
WorkflowRuntime instances.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import WorkflowStatus
from .exceptions import WorkflowExecutionError, WorkflowRegistryError
from .workflow_runtime import WorkflowRuntime

_log = get_logger(__name__)


class WorkflowStateStore:
    """
    Thread-safe in-memory store for WorkflowRuntime instances.

    Provides O(1) lookup, status-based filtering, and bulk retrieval.
    Does not persist across restarts (see WorkflowPersistence for that).
    """

    def __init__(self) -> None:
        self._runtimes: Dict[str, WorkflowRuntime] = {}
        self._by_workflow: Dict[str, List[str]]    = {}  # workflow_id → [runtime_id]
        self._lock = threading.Lock()

    def put(self, runtime: WorkflowRuntime) -> None:
        with self._lock:
            self._runtimes[runtime.runtime_id] = runtime
            self._by_workflow.setdefault(runtime.workflow_id, []).append(runtime.runtime_id)

    def get(self, runtime_id: str) -> WorkflowRuntime:
        with self._lock:
            rt = self._runtimes.get(runtime_id)
        if rt is None:
            raise WorkflowExecutionError(f"Runtime not found: {runtime_id!r}")
        return rt

    def get_or_none(self, runtime_id: str) -> Optional[WorkflowRuntime]:
        with self._lock:
            return self._runtimes.get(runtime_id)

    def get_by_workflow(self, workflow_id: str) -> List[WorkflowRuntime]:
        with self._lock:
            ids = list(self._by_workflow.get(workflow_id, []))
            return [self._runtimes[rid] for rid in ids if rid in self._runtimes]

    def all_runtimes(self) -> List[WorkflowRuntime]:
        with self._lock:
            return list(self._runtimes.values())

    def active_runtimes(self) -> List[WorkflowRuntime]:
        with self._lock:
            return [
                rt for rt in self._runtimes.values()
                if not rt.is_terminal
            ]

    def exists(self, runtime_id: str) -> bool:
        with self._lock:
            return runtime_id in self._runtimes

    def remove(self, runtime_id: str) -> bool:
        with self._lock:
            rt = self._runtimes.pop(runtime_id, None)
            if rt is not None:
                ids = self._by_workflow.get(rt.workflow_id, [])
                if runtime_id in ids:
                    ids.remove(runtime_id)
                return True
        return False

    def runtime_count(self) -> int:
        with self._lock:
            return len(self._runtimes)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for rt in self._runtimes.values() if not rt.is_terminal)

    def clear(self) -> int:
        with self._lock:
            n = len(self._runtimes)
            self._runtimes.clear()
            self._by_workflow.clear()
        return n
