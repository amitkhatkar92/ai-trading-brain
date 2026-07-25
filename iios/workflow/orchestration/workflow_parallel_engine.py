"""
workflow_parallel_engine.py — iios.workflow.orchestration
----------------------------------------------------------
WorkflowParallelEngine — executes a group of steps concurrently
using daemon threads.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_PARALLEL, DEFAULT_TIMEOUT_SECONDS, StepStatus
from .workflow_context_manager import WorkflowContextManager
from .workflow_definition import WorkflowDefinition
from .workflow_runtime import WorkflowRuntime
from .workflow_retry_engine import WorkflowRetryEngine
from .workflow_step import StepResult, WorkflowStep
from .workflow_step_executor import StepHandler, WorkflowStepExecutor
from .workflow_timeout_engine import WorkflowTimeoutEngine

_log = get_logger(__name__)


class WorkflowParallelEngine:
    """
    Executes a group of steps concurrently using daemon threads.

    All steps are launched simultaneously; results are collected after
    all threads complete or time out.  Failures do not short-circuit
    parallel peers — all are allowed to complete.

    Thread-safe.
    """

    def __init__(
        self,
        step_executor:   Optional[WorkflowStepExecutor]  = None,
        retry_engine:    Optional[WorkflowRetryEngine]   = None,
        timeout_engine:  Optional[WorkflowTimeoutEngine] = None,
        max_parallel:    int                             = DEFAULT_MAX_PARALLEL,
    ) -> None:
        self._step_executor  = step_executor  or WorkflowStepExecutor()
        self._retry_engine   = retry_engine   or WorkflowRetryEngine()
        self._timeout_engine = timeout_engine or WorkflowTimeoutEngine()
        self._max_parallel   = max_parallel
        self._semaphore      = threading.Semaphore(max_parallel)

    def execute_steps(
        self,
        steps:          List[WorkflowStep],
        definition:     WorkflowDefinition,
        runtime:        WorkflowRuntime,
        ctx_mgr:        WorkflowContextManager,
        handler_lookup: Callable[[str], StepHandler],
    ) -> List[StepResult]:
        """
        Execute steps in parallel.

        Returns results in step-order (not completion order).
        """
        results: Dict[str, Optional[StepResult]] = {s.step_id: None for s in steps}
        errors:  Dict[str, str]                  = {}
        lock     = threading.Lock()
        default_timeout = DEFAULT_TIMEOUT_SECONDS

        def _run_step(step: WorkflowStep) -> None:
            with self._semaphore:
                if runtime.is_step_completed(step.step_id):
                    return

                runtime.set_step_status(step.step_id, StepStatus.RUNNING)
                handler = handler_lookup(step.handler)
                timeout  = step.timeout_seconds if step.timeout_seconds > 0 else default_timeout

                def _execute(s=step, h=handler, c=ctx_mgr, rt=runtime) -> StepResult:
                    rc = rt.get_step_retry_count(s.step_id)
                    return self._timeout_engine.execute_with_timeout(
                        s,
                        lambda ss=s, hh=h, cc=c, rrc=rc: (
                            self._step_executor.execute(ss, hh, cc, rrc)
                        ),
                        timeout,
                    )

                try:
                    result = self._retry_engine.execute_with_retry(
                        step, _execute, runtime
                    )
                except Exception as exc:
                    result = StepResult.failure(
                        step, str(exc), 0.0, runtime.get_step_retry_count(step.step_id)
                    )

                runtime.record_step_result(result)
                with lock:
                    results[step.step_id] = result

        threads = [
            threading.Thread(
                target=_run_step, args=(step,), daemon=True,
                name=f"wf-par-{step.step_id}",
            )
            for step in steps
        ]
        for t in threads:
            t.start()

        # Use wall-clock timeout if defined
        max_wait = definition.timeout_seconds if definition.timeout_seconds > 0 else None
        for t in threads:
            t.join(timeout=max_wait)

        _log.debug(
            f"Parallel: completed {len(steps)} steps "
            f"for {definition.definition_id!r}"
        )

        return [
            results.get(s.step_id) or StepResult.failure(s, "Did not complete", 0.0)
            for s in steps
        ]
