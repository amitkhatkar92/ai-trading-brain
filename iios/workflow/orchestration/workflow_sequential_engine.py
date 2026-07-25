"""
workflow_sequential_engine.py — iios.workflow.orchestration
------------------------------------------------------------
WorkflowSequentialEngine — executes workflow steps one at a time
in dependency order.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_TIMEOUT_SECONDS, StepStatus
from .workflow_context_manager import WorkflowContextManager
from .workflow_definition import WorkflowDefinition
from .workflow_runtime import WorkflowRuntime
from .workflow_retry_engine import WorkflowRetryEngine
from .workflow_step import StepResult, WorkflowStep
from .workflow_step_executor import StepHandler, WorkflowStepExecutor
from .workflow_timeout_engine import WorkflowTimeoutEngine

_log = get_logger(__name__)


class WorkflowSequentialEngine:
    """
    Executes a list of steps one at a time, in order.

    Applies retry and timeout for each step.
    Thread-safe — stateless (runtime carries mutable state).
    """

    def __init__(
        self,
        step_executor:   Optional[WorkflowStepExecutor]  = None,
        retry_engine:    Optional[WorkflowRetryEngine]   = None,
        timeout_engine:  Optional[WorkflowTimeoutEngine] = None,
    ) -> None:
        self._step_executor  = step_executor  or WorkflowStepExecutor()
        self._retry_engine   = retry_engine   or WorkflowRetryEngine()
        self._timeout_engine = timeout_engine or WorkflowTimeoutEngine()

    def execute_steps(
        self,
        steps:         List[WorkflowStep],
        definition:    WorkflowDefinition,
        runtime:       WorkflowRuntime,
        ctx_mgr:       WorkflowContextManager,
        handler_lookup: Callable[[str], StepHandler],
    ) -> List[StepResult]:
        """
        Execute steps sequentially.

        Parameters:
            steps          — ordered list of steps to execute
            definition     — workflow definition (for timeout fallback)
            runtime        — mutable execution state
            ctx_mgr        — context manager
            handler_lookup — callable that resolves a handler name → StepHandler

        Returns:
            List of StepResult for each step.
        """
        results: List[StepResult] = []
        default_timeout = (
            definition.timeout_seconds / max(len(steps), 1)
            if definition.timeout_seconds > 0 else DEFAULT_TIMEOUT_SECONDS
        )

        for step in steps:
            # Skip if already completed (e.g. after recovery)
            if runtime.is_step_completed(step.step_id):
                _log.debug(f"Sequential: skipping completed step={step.step_id!r}")
                continue

            runtime.set_step_status(step.step_id, StepStatus.RUNNING)
            handler = handler_lookup(step.handler)
            timeout  = step.timeout_seconds if step.timeout_seconds > 0 else default_timeout

            def _execute(s=step, h=handler, r=runtime, c=ctx_mgr) -> StepResult:
                retry_count = r.get_step_retry_count(s.step_id)
                return self._timeout_engine.execute_with_timeout(
                    s,
                    lambda ss=s, hh=h, cc=c, rc=retry_count: (
                        self._step_executor.execute(ss, hh, cc, rc)
                    ),
                    timeout,
                )

            try:
                result = self._retry_engine.execute_with_retry(
                    step, _execute, runtime
                )
            except Exception as exc:
                result = StepResult.failure(step, str(exc), 0.0,
                                            runtime.get_step_retry_count(step.step_id))

            runtime.record_step_result(result)
            results.append(result)

            if result.is_failure:
                _log.warning(
                    f"Sequential: step={step.step_id!r} failed — stopping"
                )
                break   # stop sequential execution on first failure

        return results
