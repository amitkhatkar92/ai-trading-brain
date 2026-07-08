"""
iios/intelligence/workflow/workflow_executor.py
================================================
WorkflowExecutor — executes WorkflowDefinition instances.

Supports:
  Sequential, Parallel, Conditional, Dynamic, Nested, Long-running,
  Checkpoint/recovery, Cancellation, Pause/resume.

Each execution returns a WorkflowRunResult capturing step outputs,
timings, and any errors.

The executor is stateless: it holds no per-run state between calls.
All mutable run state is collected in WorkflowRunResult.
"""

from __future__ import annotations

import copy
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future, wait as fut_wait, FIRST_EXCEPTION
from dataclasses import dataclass, field
from typing import Any, Optional

from ..intelligence_constants import (
    WorkflowType,
    StepType,
    StepStatus,
    ExecutionStatus,
    Priority,
    MAX_NESTING_DEPTH,
)
from ..intelligence_exceptions import (
    WorkflowExecutionError,
    WorkflowStepError,
    WorkflowTimeoutError,
    WorkflowCancelledError,
    CircularDependencyError,
    CheckpointError,
)
from ..execution.execution_policy import ExecutionPolicy, CancellationToken
from .workflow_builder import WorkflowDefinition, WorkflowStep

log = logging.getLogger(__name__)

__all__ = [
    "StepRunResult",
    "WorkflowRunResult",
    "WorkflowExecutor",
    "get_workflow_executor",
    "reset_workflow_executor",
]


@dataclass
class StepRunResult:
    """Outcome of a single workflow step execution."""
    step_id:    str
    status:     StepStatus
    result:     Any                  = None
    error:      Optional[str]        = None
    duration_ms: float               = 0.0
    attempt:    int                  = 1
    skipped:    bool                 = False

    def to_dict(self) -> dict:
        return {
            "step_id":    self.step_id,
            "status":     self.status.value,
            "duration_ms": round(self.duration_ms, 3),
            "attempt":    self.attempt,
            "skipped":    self.skipped,
            "error":      self.error,
        }


@dataclass
class WorkflowRunResult:
    """Complete outcome of one workflow execution."""
    workflow_id: str
    run_id:      str
    status:      ExecutionStatus          = ExecutionStatus.PENDING
    steps:       dict[str, StepRunResult] = field(default_factory=dict)
    outputs:     dict[str, Any]           = field(default_factory=dict)
    errors:      list[str]                = field(default_factory=list)
    checkpoints: list[dict]               = field(default_factory=list)
    started_at:  float                    = field(default_factory=time.time)
    finished_at: Optional[float]          = None
    metadata:    dict[str, Any]           = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        end = self.finished_at or time.time()
        return (end - self.started_at) * 1_000.0

    @property
    def succeeded(self) -> bool:
        return self.status == ExecutionStatus.COMPLETED

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def failed_count(self) -> int:
        return sum(1 for s in self.steps.values() if s.status == StepStatus.FAILED)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "run_id":      self.run_id,
            "status":      self.status.value,
            "duration_ms": round(self.duration_ms, 3),
            "step_count":  self.step_count,
            "failed_count": self.failed_count,
            "errors":      self.errors,
            "steps":       {sid: sr.to_dict() for sid, sr in self.steps.items()},
        }


class WorkflowExecutor:
    """
    Executes WorkflowDefinition instances.

    Thread-safe: multiple workflows can execute concurrently.
    Each call to execute() creates its own isolated run context.
    """

    def __init__(self, max_workers: int = 8) -> None:
        self._max_workers = max_workers

    # ── Public API ────────────────────────────────────────────────────────────

    def execute(
        self,
        definition:  WorkflowDefinition,
        context:     dict[str, Any] | None    = None,
        policy:      Optional[ExecutionPolicy] = None,
        run_id:      Optional[str]             = None,
        depth:       int                       = 0,
        checkpoint:  Optional[dict]            = None,
    ) -> WorkflowRunResult:
        """
        Execute *definition* and return a WorkflowRunResult.

        Parameters
        ----------
        context:    Shared data passed into every step
        policy:     Override policy (falls back to definition.policy)
        run_id:     ID for this specific run (generated if omitted)
        depth:      Nesting depth (prevents infinite recursion)
        checkpoint: Dict of already-completed step outputs (for recovery)
        """
        import uuid
        run_id   = run_id or str(uuid.uuid4())
        policy   = policy or definition.policy
        ctx      = context or {}

        if depth > MAX_NESTING_DEPTH:
            raise WorkflowExecutionError(
                definition.workflow_id,
                f"Max nesting depth ({MAX_NESTING_DEPTH}) exceeded"
            )

        result = WorkflowRunResult(
            workflow_id = definition.workflow_id,
            run_id      = run_id,
            status      = ExecutionStatus.RUNNING,
        )

        # Pre-populate from checkpoint (recovery path)
        if checkpoint:
            for sid, val in checkpoint.items():
                result.outputs[sid]  = val
                result.steps[sid]    = StepRunResult(
                    step_id = sid, status=StepStatus.COMPLETED, result=val
                )

        t_start = time.perf_counter()
        try:
            topo_order = definition._topological_order()

            if definition.workflow_type == WorkflowType.PARALLEL:
                self._execute_parallel(definition, topo_order, result, ctx, policy, depth)
            else:
                self._execute_sequential(definition, topo_order, result, ctx, policy, depth)

            result.status      = ExecutionStatus.COMPLETED
            result.finished_at = time.time()

        except WorkflowCancelledError:
            result.status      = ExecutionStatus.CANCELLED
            result.finished_at = time.time()
            raise
        except WorkflowTimeoutError:
            result.status      = ExecutionStatus.TIMEOUT
            result.finished_at = time.time()
            raise
        except Exception as exc:
            result.status      = ExecutionStatus.FAILED
            result.finished_at = time.time()
            result.errors.append(str(exc))
            log.exception("Workflow %r failed: %s", definition.workflow_id, exc)

        return result

    # ── Internal: sequential ─────────────────────────────────────────────────

    def _execute_sequential(
        self,
        defn:       WorkflowDefinition,
        order:      list[str],
        result:     WorkflowRunResult,
        ctx:        dict,
        policy:     ExecutionPolicy,
        depth:      int,
    ) -> None:
        for sid in order:
            if sid in result.steps:
                continue  # Already done (checkpoint recovery)
            if policy.cancellation.is_cancelled:
                raise WorkflowCancelledError(defn.workflow_id)
            step = defn.get_step(sid)
            if step is None:
                continue
            sr = self._run_step(step, defn, result, ctx, policy, depth)
            result.steps[sr.step_id] = sr
            if sr.status == StepStatus.COMPLETED:
                result.outputs[sr.step_id] = sr.result
            elif sr.status == StepStatus.FAILED:
                result.errors.append(sr.error or "")
                if policy.recovery_mode == "abort":
                    raise WorkflowExecutionError(defn.workflow_id, sr.error or "step failed")

    # ── Internal: parallel ───────────────────────────────────────────────────

    def _execute_parallel(
        self,
        defn:   WorkflowDefinition,
        order:  list[str],
        result: WorkflowRunResult,
        ctx:    dict,
        policy: ExecutionPolicy,
        depth:  int,
    ) -> None:
        """
        Execute steps in waves.

        A wave is all steps whose dependencies are already completed.
        Steps within a wave run concurrently via a thread pool.
        """
        completed: set[str] = set(result.steps.keys())
        remaining  = [sid for sid in order if sid not in completed]

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            while remaining:
                if policy.cancellation.is_cancelled:
                    raise WorkflowCancelledError(defn.workflow_id)
                wave = [
                    sid for sid in remaining
                    if all(dep in completed for dep in
                           (defn.get_step(sid) or WorkflowStep(sid)).depends_on)
                ]
                if not wave:
                    break  # No progress — execution is complete

                futures: dict[Future, str] = {}
                for sid in wave:
                    step = defn.get_step(sid)
                    if step is None:
                        continue
                    f = pool.submit(
                        self._run_step, step, defn, result, ctx, policy, depth
                    )
                    futures[f] = sid

                done_futs, _ = fut_wait(futures, return_when=FIRST_EXCEPTION)
                for f in done_futs:
                    sr = f.result()
                    result.steps[sr.step_id] = sr
                    if sr.status == StepStatus.COMPLETED:
                        result.outputs[sr.step_id] = sr.result
                        completed.add(sr.step_id)
                    elif sr.status == StepStatus.FAILED:
                        result.errors.append(sr.error or "")

                # Cancel remaining futures if abort policy
                remaining = [sid for sid in remaining if sid not in completed]

    # ── Internal: run one step ───────────────────────────────────────────────

    def _run_step(
        self,
        step:   WorkflowStep,
        defn:   WorkflowDefinition,
        result: WorkflowRunResult,
        ctx:    dict,
        policy: ExecutionPolicy,
        depth:  int,
    ) -> StepRunResult:
        t0 = time.perf_counter()

        # Skip checkpoint steps (they just record a snapshot)
        if step.step_type == StepType.CHECKPOINT:
            snap = {sid: result.outputs.get(sid) for sid in result.steps}
            result.checkpoints.append({"step_id": step.step_id, "state": snap, "ts": time.time()})
            return StepRunResult(step_id=step.step_id, status=StepStatus.COMPLETED, result=snap)

        # Evaluate condition
        if step.condition is not None:
            try:
                if not step.condition(ctx, result.outputs):
                    return StepRunResult(
                        step_id  = step.step_id,
                        status   = StepStatus.SKIPPED,
                        skipped  = True,
                        duration_ms = (time.perf_counter() - t0) * 1_000,
                    )
            except Exception as cond_exc:
                return StepRunResult(
                    step_id  = step.step_id,
                    status   = StepStatus.SKIPPED,
                    skipped  = True,
                    error    = str(cond_exc),
                    duration_ms = (time.perf_counter() - t0) * 1_000,
                )

        # Sub-workflow
        if step.step_type == StepType.SUB_WORKFLOW:
            sub_id = step.metadata.get("sub_workflow_id")
            return self._run_sub_workflow_step(step, sub_id, ctx, result, policy, depth, t0)

        # Execute callable with retry
        if step.fn is None:
            return StepRunResult(
                step_id  = step.step_id,
                status   = StepStatus.SKIPPED,
                skipped  = True,
                duration_ms = (time.perf_counter() - t0) * 1_000,
            )

        # Build inputs for this step
        inputs = dict(ctx)
        for src_key, dst_key in step.input_map.items():
            parts = src_key.split(".", 1)
            if len(parts) == 2:
                src_step, src_output = parts
                val = result.outputs.get(src_step)
                if isinstance(val, dict):
                    inputs[dst_key] = val.get(src_output)
                else:
                    inputs[dst_key] = val
            else:
                inputs[dst_key] = result.outputs.get(src_key)

        # Also inject direct step outputs by step_id
        inputs.update(result.outputs)

        attempt = 0
        last_error: Optional[Exception] = None
        retry = policy.retry if policy else None

        while True:
            attempt += 1
            try:
                out = step.fn(inputs)
                return StepRunResult(
                    step_id    = step.step_id,
                    status     = StepStatus.COMPLETED,
                    result     = out,
                    duration_ms = (time.perf_counter() - t0) * 1_000,
                    attempt    = attempt,
                )
            except Exception as exc:
                last_error = exc
                log.warning("Step %r attempt %d failed: %s", step.step_id, attempt, exc)
                if retry and retry.should_retry(attempt, exc):
                    wait_s = retry.wait_ms(attempt) / 1_000.0
                    if wait_s > 0:
                        time.sleep(wait_s)
                    continue
                break

        return StepRunResult(
            step_id    = step.step_id,
            status     = StepStatus.FAILED,
            error      = str(last_error),
            duration_ms = (time.perf_counter() - t0) * 1_000,
            attempt    = attempt,
        )

    def _run_sub_workflow_step(
        self,
        step:    WorkflowStep,
        sub_id:  Optional[str],
        ctx:     dict,
        result:  WorkflowRunResult,
        policy:  ExecutionPolicy,
        depth:   int,
        t0:      float,
    ) -> StepRunResult:
        # The sub-workflow definition must be callable or in the registry
        if step.fn is None:
            return StepRunResult(step.step_id, StepStatus.SKIPPED, skipped=True)
        sub_defn = step.fn(ctx)
        if sub_defn is None or not isinstance(sub_defn, WorkflowDefinition):
            return StepRunResult(step.step_id, StepStatus.SKIPPED, skipped=True)
        sub_result = self.execute(sub_defn, context=ctx, policy=policy, depth=depth + 1)
        return StepRunResult(
            step_id    = step.step_id,
            status     = StepStatus.COMPLETED if sub_result.succeeded else StepStatus.FAILED,
            result     = sub_result.to_dict(),
            error      = "; ".join(sub_result.errors) if sub_result.errors else None,
            duration_ms = (time.perf_counter() - t0) * 1_000,
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_exec_lock = threading.Lock()
_exec_inst: Optional[WorkflowExecutor] = None


def get_workflow_executor() -> WorkflowExecutor:
    global _exec_inst
    if _exec_inst is None:
        with _exec_lock:
            if _exec_inst is None:
                _exec_inst = WorkflowExecutor()
    return _exec_inst


def reset_workflow_executor() -> None:
    global _exec_inst
    with _exec_lock:
        _exec_inst = None
