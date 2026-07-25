"""
workflow_runtime.py — iios.workflow.orchestration
--------------------------------------------------
WorkflowRuntime — mutable, thread-safe execution state for a single
workflow instance.

WorkflowExecutionResult — immutable summary of a completed execution.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from .constants import (
    PREFIX_RESULT,
    PREFIX_RUNTIME,
    StepStatus,
    WorkflowStatus,
)
from .workflow_definition import WorkflowExecutionRequest
from .workflow_step import StepResult


class WorkflowRuntime:
    """
    Mutable, thread-safe state for a single workflow execution instance.

    All reads and writes are protected by an internal RLock.
    """

    def __init__(
        self,
        runtime_id:    str,
        workflow_id:   str,
        definition_id: str,
        context_data:  Dict[str, Any],
    ) -> None:
        self._lock            = threading.RLock()
        self.runtime_id       = runtime_id
        self.workflow_id      = workflow_id
        self.definition_id    = definition_id
        self._status          = WorkflowStatus.PENDING
        self._step_statuses:  Dict[str, StepStatus]  = {}
        self._step_results:   Dict[str, StepResult]  = {}
        self._step_retries:   Dict[str, int]         = {}
        self._context_data:   Dict[str, Any]         = dict(context_data)
        self._completed_steps: Set[str]              = set()
        self._failed_steps:   Set[str]               = set()
        self._active_steps:   Set[str]               = set()
        self._error:          Optional[str]          = None
        self._started_at:     str = datetime.now(tz=timezone.utc).isoformat()
        self._completed_at:   Optional[str]          = None
        self._retry_total:    int                    = 0
        self._compensation_count: int               = 0
        self._checkpoint_count: int                 = 0

    @classmethod
    def create(cls, request: WorkflowExecutionRequest) -> "WorkflowRuntime":
        return cls(
            runtime_id    = f"{PREFIX_RUNTIME}{uuid.uuid4().hex[:10]}",
            workflow_id   = request.workflow_id,
            definition_id = request.definition_id,
            context_data  = request.context_data,
        )

    # ── Status ───────────────────────────────────────────────────────────────

    @property
    def status(self) -> WorkflowStatus:
        with self._lock:
            return self._status

    def set_status(self, status: WorkflowStatus) -> None:
        with self._lock:
            self._status = status
            if status in (
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
                WorkflowStatus.TIMED_OUT,
            ):
                if self._completed_at is None:
                    self._completed_at = datetime.now(tz=timezone.utc).isoformat()

    @property
    def is_terminal(self) -> bool:
        with self._lock:
            return self._status in (
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
                WorkflowStatus.TIMED_OUT,
            )

    # ── Step tracking ─────────────────────────────────────────────────────────

    def set_step_status(self, step_id: str, status: StepStatus) -> None:
        with self._lock:
            self._step_statuses[step_id] = status
            if status == StepStatus.RUNNING:
                self._active_steps.add(step_id)
            elif status == StepStatus.COMPLETED:
                self._active_steps.discard(step_id)
                self._completed_steps.add(step_id)
            elif status in (StepStatus.FAILED, StepStatus.TIMED_OUT):
                self._active_steps.discard(step_id)
                self._failed_steps.add(step_id)
            elif status == StepStatus.SKIPPED:
                self._active_steps.discard(step_id)
                self._completed_steps.add(step_id)

    def get_step_status(self, step_id: str) -> StepStatus:
        with self._lock:
            return self._step_statuses.get(step_id, StepStatus.PENDING)

    def record_step_result(self, result: StepResult) -> None:
        with self._lock:
            self._step_results[result.step_id] = result
            self._step_statuses[result.step_id] = result.status
            if result.is_success:
                self._completed_steps.add(result.step_id)
                self._active_steps.discard(result.step_id)
            elif result.is_failure:
                self._failed_steps.add(result.step_id)
                self._active_steps.discard(result.step_id)

    def increment_retry(self, step_id: str) -> int:
        with self._lock:
            self._step_retries[step_id] = self._step_retries.get(step_id, 0) + 1
            self._retry_total += 1
            return self._step_retries[step_id]

    def get_step_retry_count(self, step_id: str) -> int:
        with self._lock:
            return self._step_retries.get(step_id, 0)

    def is_step_completed(self, step_id: str) -> bool:
        with self._lock:
            return step_id in self._completed_steps

    def all_steps_completed(self, step_ids: List[str]) -> bool:
        with self._lock:
            return all(sid in self._completed_steps for sid in step_ids)

    # ── Context ───────────────────────────────────────────────────────────────

    def get_context(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._context_data)

    def update_context(self, updates: Dict[str, Any]) -> None:
        with self._lock:
            self._context_data.update(updates)

    # ── Error ─────────────────────────────────────────────────────────────────

    @property
    def error(self) -> Optional[str]:
        with self._lock:
            return self._error

    def set_error(self, error: str) -> None:
        with self._lock:
            self._error = error

    # ── Counters ──────────────────────────────────────────────────────────────

    def increment_compensation(self) -> None:
        with self._lock:
            self._compensation_count += 1

    def increment_checkpoint(self) -> None:
        with self._lock:
            self._checkpoint_count += 1

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "runtime_id":          self.runtime_id,
                "workflow_id":         self.workflow_id,
                "definition_id":       self.definition_id,
                "status":              self._status.value,
                "step_statuses":       {k: v.value for k, v in self._step_statuses.items()},
                "completed_steps":     list(self._completed_steps),
                "failed_steps":        list(self._failed_steps),
                "error":               self._error,
                "started_at":          self._started_at,
                "completed_at":        self._completed_at,
                "retry_total":         self._retry_total,
                "compensation_count":  self._compensation_count,
                "checkpoint_count":    self._checkpoint_count,
                "context_data":        dict(self._context_data),
            }

    def to_dict(self) -> Dict[str, Any]:
        s = self.snapshot()
        s.pop("context_data", None)   # omit from summary
        return s


@dataclass(frozen=True)
class WorkflowExecutionResult:
    """Immutable summary of a completed workflow execution."""
    result_id:        str
    workflow_id:      str
    runtime_id:       str
    definition_id:    str
    status:           WorkflowStatus
    outputs:          Dict[str, Any]
    step_results:     Dict[str, Any]   # step_id → StepResult.to_dict()
    error:            Optional[str]
    started_at:       str
    completed_at:     str
    duration_ms:      float
    steps_executed:   int
    steps_succeeded:  int
    steps_failed:     int
    retries:          int
    compensations:    int
    checkpoints:      int

    @classmethod
    def from_runtime(
        cls,
        runtime:     WorkflowRuntime,
        outputs:     Dict[str, Any],
        duration_ms: float,
    ) -> "WorkflowExecutionResult":
        snap = runtime.snapshot()
        step_results_raw = {}
        with runtime._lock:
            for sid, sr in runtime._step_results.items():
                step_results_raw[sid] = sr.to_dict()
            succeeded = len([
                v for v in runtime._step_results.values() if v.is_success
            ])
            failed = len([
                v for v in runtime._step_results.values() if v.is_failure
            ])
            executed = len(runtime._step_results)

        return cls(
            result_id       = f"{PREFIX_RESULT}{uuid.uuid4().hex[:10]}",
            workflow_id     = runtime.workflow_id,
            runtime_id      = runtime.runtime_id,
            definition_id   = runtime.definition_id,
            status          = runtime.status,
            outputs         = dict(outputs),
            step_results    = step_results_raw,
            error           = runtime.error,
            started_at      = snap["started_at"],
            completed_at    = snap.get("completed_at") or datetime.now(tz=timezone.utc).isoformat(),
            duration_ms     = round(duration_ms, 3),
            steps_executed  = executed,
            steps_succeeded = succeeded,
            steps_failed    = failed,
            retries         = snap["retry_total"],
            compensations   = snap["compensation_count"],
            checkpoints     = snap["checkpoint_count"],
        )

    @property
    def is_success(self) -> bool:
        return self.status == WorkflowStatus.COMPLETED

    @property
    def is_failure(self) -> bool:
        return self.status in (WorkflowStatus.FAILED, WorkflowStatus.TIMED_OUT)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id":       self.result_id,
            "workflow_id":     self.workflow_id,
            "runtime_id":      self.runtime_id,
            "definition_id":   self.definition_id,
            "status":          self.status.value,
            "error":           self.error,
            "started_at":      self.started_at,
            "completed_at":    self.completed_at,
            "duration_ms":     self.duration_ms,
            "steps_executed":  self.steps_executed,
            "steps_succeeded": self.steps_succeeded,
            "steps_failed":    self.steps_failed,
            "retries":         self.retries,
            "compensations":   self.compensations,
            "checkpoints":     self.checkpoints,
            "is_success":      self.is_success,
            "outputs":         self.outputs,
        }
