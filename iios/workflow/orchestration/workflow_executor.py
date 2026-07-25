"""
workflow_executor.py — iios.workflow.orchestration
---------------------------------------------------
WorkflowExecutor — central per-workflow execution coordinator.

Drives the full execution pipeline:
  1. Validate definition
  2. Create & initialise runtime
  3. Resolve dependency order
  4. Execute steps (sequential/parallel per workflow type + step wave)
  5. Apply conditional skip logic
  6. Handle retries and timeouts
  7. Checkpoint at each wave (if enabled)
  8. Compensate on failure (if enabled)
  9. Persist final state
  10. Emit orchestration events
  11. Return WorkflowExecutionResult

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import (
    DEFAULT_TIMEOUT_SECONDS,
    OrchestrationEventType,
    StepStatus,
    WorkflowStatus,
    WorkflowType,
)
from .exceptions import WorkflowExecutionError, WorkflowValidationError
from .workflow_checkpoint_manager import WorkflowCheckpointManager
from .workflow_compensation_engine import WorkflowCompensationEngine
from .workflow_conditional_engine import ConditionHandler, WorkflowConditionalEngine
from .workflow_context_manager import WorkflowContextManager
from .workflow_definition import WorkflowDefinition, WorkflowExecutionRequest
from .workflow_dependency_engine import WorkflowDependencyEngine
from .workflow_parallel_engine import WorkflowParallelEngine
from .workflow_persistence import WorkflowPersistence
from .workflow_recovery_engine import WorkflowRecoveryEngine
from .workflow_runtime import WorkflowExecutionResult, WorkflowRuntime
from .workflow_sequential_engine import WorkflowSequentialEngine
from .workflow_state_store import WorkflowStateStore
from .workflow_step import StepResult, WorkflowStep
from .workflow_step_executor import StepHandler, WorkflowStepExecutor
from .workflow_validator import WorkflowValidator

_log = get_logger(__name__)


class WorkflowExecutor:
    """
    Central per-workflow execution coordinator.

    Instantiated once by the WorkflowOrchestrationEngine and shared
    across all workflow executions.  Thread-safe.
    """

    def __init__(
        self,
        *,
        state_store:           Optional[WorkflowStateStore]         = None,
        dep_engine:            Optional[WorkflowDependencyEngine]   = None,
        sequential_engine:     Optional[WorkflowSequentialEngine]   = None,
        parallel_engine:       Optional[WorkflowParallelEngine]     = None,
        conditional_engine:    Optional[WorkflowConditionalEngine]  = None,
        compensation_engine:   Optional[WorkflowCompensationEngine] = None,
        checkpoint_manager:    Optional[WorkflowCheckpointManager]  = None,
        recovery_engine:       Optional[WorkflowRecoveryEngine]     = None,
        persistence:           Optional[WorkflowPersistence]        = None,
        validator:             Optional[WorkflowValidator]          = None,
        event_emitter:         Optional[Callable]                   = None,
    ) -> None:
        self._state_store         = state_store         or WorkflowStateStore()
        self._dep_engine          = dep_engine          or WorkflowDependencyEngine()
        self._sequential_engine   = sequential_engine   or WorkflowSequentialEngine()
        self._parallel_engine     = parallel_engine     or WorkflowParallelEngine()
        self._conditional_engine  = conditional_engine  or WorkflowConditionalEngine()
        self._compensation_engine = compensation_engine or WorkflowCompensationEngine()
        self._checkpoint_manager  = checkpoint_manager  or WorkflowCheckpointManager()
        self._recovery_engine     = WorkflowRecoveryEngine(self._checkpoint_manager)
        self._persistence         = persistence         or WorkflowPersistence()
        self._validator           = validator           or WorkflowValidator()
        # event_emitter: (event_type: OrchestrationEventType, payload: Dict) → None
        self._emit                = event_emitter or (lambda et, p: None)

    # ── Main entry ────────────────────────────────────────────────────────────

    def execute(
        self,
        request:          WorkflowExecutionRequest,
        definition:       WorkflowDefinition,
        handler_lookup:   Callable[[str], StepHandler],
        condition_lookup: Optional[Callable[[str], ConditionHandler]] = None,
    ) -> WorkflowExecutionResult:
        """
        Execute a workflow from a governance-approved request.

        Returns WorkflowExecutionResult regardless of success or failure.
        """
        t0      = time.monotonic()
        runtime = WorkflowRuntime.create(request)
        ctx_mgr = WorkflowContextManager(request.context_data)

        self._state_store.put(runtime)
        self._persistence.save_runtime(runtime)

        self._emit(OrchestrationEventType.WORKFLOW_EXECUTION_STARTED, {
            "workflow_id":   runtime.workflow_id,
            "runtime_id":    runtime.runtime_id,
            "definition_id": definition.definition_id,
        })

        runtime.set_status(WorkflowStatus.RUNNING)
        _log.info(
            f"Executor: starting workflow_id={runtime.workflow_id!r} "
            f"runtime={runtime.runtime_id!r} "
            f"type={definition.workflow_type.value!r}"
        )

        try:
            self._run_workflow(runtime, definition, ctx_mgr, handler_lookup, condition_lookup)
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            _log.error(f"Executor: workflow={runtime.workflow_id!r} error: {error_msg}")
            runtime.set_error(error_msg)
            runtime.set_status(WorkflowStatus.FAILED)

        # Compensate on failure if enabled
        had_failure = runtime.status == WorkflowStatus.FAILED
        if had_failure and definition.enable_compensation:
            try:
                self._compensation_engine.compensate(
                    runtime, definition, ctx_mgr, handler_lookup
                )
            except Exception as ce:
                _log.error(f"Executor: compensation error: {ce!r}")
            # Restore FAILED status — compensation doesn't change the outcome
            runtime.set_status(WorkflowStatus.FAILED)

        # Set final status if not yet terminal
        if not runtime.is_terminal:
            runtime.set_status(WorkflowStatus.COMPLETED)

        self._persistence.save_runtime(runtime)
        duration_ms = (time.monotonic() - t0) * 1000.0
        result      = WorkflowExecutionResult.from_runtime(
            runtime, ctx_mgr.get_all(), duration_ms
        )

        event_type = (
            OrchestrationEventType.WORKFLOW_COMPLETED
            if result.is_success
            else OrchestrationEventType.WORKFLOW_EXECUTION_FAILED
        )
        self._emit(event_type, {
            "workflow_id":  runtime.workflow_id,
            "runtime_id":   runtime.runtime_id,
            "status":       runtime.status.value,
            "duration_ms":  duration_ms,
        })

        return result

    # ── Internal execution ────────────────────────────────────────────────────

    def _run_workflow(
        self,
        runtime:          WorkflowRuntime,
        definition:       WorkflowDefinition,
        ctx_mgr:          WorkflowContextManager,
        handler_lookup:   Callable[[str], StepHandler],
        condition_lookup: Optional[Callable[[str], ConditionHandler]],
    ) -> None:
        """Drive execution through dependency waves."""
        waves = self._dep_engine.get_execution_waves(definition)
        parallel = definition.workflow_type in (
            WorkflowType.PARALLEL,
            WorkflowType.SAGA,
            WorkflowType.PIPELINE,
        )

        for wave_idx, wave_step_ids in enumerate(waves):
            if runtime.is_terminal:
                break

            # Get step objects for this wave
            step_map  = definition.step_map
            wave_steps = [step_map[sid] for sid in wave_step_ids if sid in step_map]

            # Apply conditional filtering
            executable, skipped = self._conditional_engine.filter_executable_steps(
                wave_steps, ctx_mgr, condition_lookup
            )

            # Record skipped
            for step in skipped:
                runtime.record_step_result(StepResult.skipped(step))

            if not executable:
                continue

            # Emit step-started events
            for step in executable:
                self._emit(OrchestrationEventType.WORKFLOW_STEP_STARTED, {
                    "step_id":     step.step_id,
                    "step_name":   step.name,
                    "workflow_id": runtime.workflow_id,
                })

            # Execute the wave
            if parallel and len(executable) > 1:
                step_results = self._parallel_engine.execute_steps(
                    executable, definition, runtime, ctx_mgr, handler_lookup
                )
            else:
                step_results = self._sequential_engine.execute_steps(
                    executable, definition, runtime, ctx_mgr, handler_lookup
                )

            # Emit per-step events and check for failure
            any_failed = False
            for res in step_results:
                evt = (
                    OrchestrationEventType.WORKFLOW_STEP_COMPLETED
                    if res.is_success
                    else OrchestrationEventType.WORKFLOW_STEP_FAILED
                )
                self._emit(evt, {
                    "step_id":     res.step_id,
                    "step_name":   res.step_name,
                    "workflow_id": runtime.workflow_id,
                    "status":      res.status.value,
                })
                if res.is_failure:
                    any_failed = True

            # Checkpoint after each wave (if enabled)
            if definition.enable_checkpointing:
                chk = self._checkpoint_manager.create(runtime, ctx_mgr.snapshot())
                self._persistence.save_checkpoint(chk)
                self._emit(OrchestrationEventType.CHECKPOINT_CREATED, {
                    "checkpoint_id": chk.checkpoint_id,
                    "workflow_id":   runtime.workflow_id,
                })

            if any_failed:
                err = f"Wave {wave_idx} had failed steps — stopping"
                runtime.set_error(err)
                runtime.set_status(WorkflowStatus.FAILED)
                return

        runtime.set_status(WorkflowStatus.COMPLETED)

    # ── State store access ────────────────────────────────────────────────────

    def get_runtime(self, runtime_id: str) -> Optional[WorkflowRuntime]:
        return self._state_store.get_or_none(runtime_id)

    def active_runtime_count(self) -> int:
        return self._state_store.active_count()
