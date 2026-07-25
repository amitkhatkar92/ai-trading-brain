"""
workflow_checkpoint_manager.py — iios.workflow.orchestration
-------------------------------------------------------------
WorkflowCheckpoint + WorkflowCheckpointManager — snapshot and restore
workflow execution state.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import PREFIX_CHECKPOINT
from .exceptions import WorkflowCheckpointError
from .workflow_runtime import WorkflowRuntime

_log = get_logger(__name__)


@dataclass(frozen=True)
class WorkflowCheckpoint:
    """Immutable snapshot of a WorkflowRuntime at a point in time."""
    checkpoint_id:   str
    runtime_id:      str
    workflow_id:     str
    step_statuses:   Dict[str, str]     # step_id → StepStatus.value
    completed_steps: tuple              # Tuple[str, ...]
    failed_steps:    tuple
    context_snapshot: Dict[str, Any]
    retry_total:     int
    created_at:      str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id":  self.checkpoint_id,
            "runtime_id":     self.runtime_id,
            "workflow_id":    self.workflow_id,
            "created_at":     self.created_at,
            "completed_steps": list(self.completed_steps),
            "failed_steps":   list(self.failed_steps),
        }


class WorkflowCheckpointManager:
    """
    Thread-safe checkpoint creation and restore for workflow runtimes.

    Stores up to `max_per_runtime` checkpoints per runtime_id.
    Oldest checkpoints are evicted when the limit is reached.
    """

    def __init__(self, max_per_runtime: int = 20) -> None:
        self._max = max_per_runtime
        self._checkpoints: Dict[str, List[WorkflowCheckpoint]] = {}
        self._lock = threading.Lock()

    # ── Create ────────────────────────────────────────────────────────────────

    def create(
        self,
        runtime:          WorkflowRuntime,
        context_snapshot: Dict[str, Any],
    ) -> WorkflowCheckpoint:
        """Snapshot the current runtime state into a checkpoint."""
        snap = runtime.snapshot()
        chk  = WorkflowCheckpoint(
            checkpoint_id    = f"{PREFIX_CHECKPOINT}{uuid.uuid4().hex[:10]}",
            runtime_id       = runtime.runtime_id,
            workflow_id      = runtime.workflow_id,
            step_statuses    = snap["step_statuses"],
            completed_steps  = tuple(snap["completed_steps"]),
            failed_steps     = tuple(snap["failed_steps"]),
            context_snapshot = dict(context_snapshot),
            retry_total      = snap["retry_total"],
            created_at       = datetime.now(tz=timezone.utc).isoformat(),
        )
        with self._lock:
            bucket = self._checkpoints.setdefault(runtime.runtime_id, [])
            if len(bucket) >= self._max:
                bucket.pop(0)   # evict oldest
            bucket.append(chk)

        runtime.increment_checkpoint()
        _log.debug(
            f"Checkpoint: created {chk.checkpoint_id!r} "
            f"for runtime={runtime.runtime_id!r}"
        )
        return chk

    # ── Retrieve ──────────────────────────────────────────────────────────────

    def get_latest(self, runtime_id: str) -> Optional[WorkflowCheckpoint]:
        with self._lock:
            bucket = self._checkpoints.get(runtime_id, [])
            return bucket[-1] if bucket else None

    def get_all(self, runtime_id: str) -> List[WorkflowCheckpoint]:
        with self._lock:
            return list(self._checkpoints.get(runtime_id, []))

    def get_by_id(self, checkpoint_id: str) -> Optional[WorkflowCheckpoint]:
        with self._lock:
            for bucket in self._checkpoints.values():
                for chk in bucket:
                    if chk.checkpoint_id == checkpoint_id:
                        return chk
        return None

    # ── Restore ───────────────────────────────────────────────────────────────

    def restore(
        self,
        checkpoint: WorkflowCheckpoint,
        runtime:    WorkflowRuntime,
    ) -> None:
        """Apply a checkpoint's state back to a runtime."""
        if checkpoint.runtime_id != runtime.runtime_id:
            raise WorkflowCheckpointError(
                f"Checkpoint {checkpoint.checkpoint_id!r} belongs to "
                f"runtime {checkpoint.runtime_id!r}, not {runtime.runtime_id!r}"
            )
        from .constants import StepStatus
        for step_id, status_val in checkpoint.step_statuses.items():
            runtime.set_step_status(step_id, StepStatus(status_val))
        runtime.update_context(checkpoint.context_snapshot)
        _log.info(
            f"Checkpoint: restored {checkpoint.checkpoint_id!r} "
            f"to runtime={runtime.runtime_id!r}"
        )

    # ── Introspection ─────────────────────────────────────────────────────────

    def checkpoint_count(self, runtime_id: str) -> int:
        with self._lock:
            return len(self._checkpoints.get(runtime_id, []))

    def clear(self, runtime_id: Optional[str] = None) -> int:
        with self._lock:
            if runtime_id:
                n = len(self._checkpoints.pop(runtime_id, []))
                return n
            n = sum(len(v) for v in self._checkpoints.values())
            self._checkpoints.clear()
            return n
