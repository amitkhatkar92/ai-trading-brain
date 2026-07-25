"""
workflow_persistence.py — iios.workflow.orchestration
------------------------------------------------------
WorkflowPersistence — abstraction layer for persisting workflow
execution state and checkpoints.

Default implementation is in-memory.  Extend or replace for durable
storage without changing any other orchestration component.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .workflow_checkpoint_manager import WorkflowCheckpoint
from .workflow_runtime import WorkflowRuntime

_log = get_logger(__name__)


class WorkflowPersistence:
    """
    In-memory persistence for workflow runtimes and checkpoints.

    Provides a stable interface that can be implemented against any
    backend (SQLite, Redis, PostgreSQL) without changing the engine.

    Thread-safe.
    """

    def __init__(self) -> None:
        self._runtimes:    Dict[str, Dict]                        = {}
        self._checkpoints: Dict[str, List[WorkflowCheckpoint]]    = {}
        self._lock = threading.Lock()

    # ── Runtime ───────────────────────────────────────────────────────────────

    def save_runtime(self, runtime: WorkflowRuntime) -> None:
        with self._lock:
            self._runtimes[runtime.runtime_id] = runtime.snapshot()
        _log.debug(f"Persistence: saved runtime={runtime.runtime_id!r}")

    def load_runtime_snapshot(self, runtime_id: str) -> Optional[Dict]:
        with self._lock:
            return dict(self._runtimes[runtime_id]) if runtime_id in self._runtimes else None

    def runtime_exists(self, runtime_id: str) -> bool:
        with self._lock:
            return runtime_id in self._runtimes

    def delete_runtime(self, runtime_id: str) -> bool:
        with self._lock:
            if runtime_id in self._runtimes:
                del self._runtimes[runtime_id]
                return True
        return False

    def all_runtime_ids(self) -> List[str]:
        with self._lock:
            return list(self._runtimes.keys())

    # ── Checkpoints ───────────────────────────────────────────────────────────

    def save_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        with self._lock:
            bucket = self._checkpoints.setdefault(checkpoint.runtime_id, [])
            bucket.append(checkpoint)
        _log.debug(f"Persistence: saved checkpoint={checkpoint.checkpoint_id!r}")

    def load_latest_checkpoint(self, runtime_id: str) -> Optional[WorkflowCheckpoint]:
        with self._lock:
            bucket = self._checkpoints.get(runtime_id, [])
            return bucket[-1] if bucket else None

    def load_all_checkpoints(self, runtime_id: str) -> List[WorkflowCheckpoint]:
        with self._lock:
            return list(self._checkpoints.get(runtime_id, []))

    # ── Introspection ─────────────────────────────────────────────────────────

    def runtime_count(self) -> int:
        with self._lock:
            return len(self._runtimes)

    def checkpoint_count(self, runtime_id: str = "") -> int:
        with self._lock:
            if runtime_id:
                return len(self._checkpoints.get(runtime_id, {}))
            return sum(len(v) for v in self._checkpoints.values())

    def clear(self) -> None:
        with self._lock:
            self._runtimes.clear()
            self._checkpoints.clear()
