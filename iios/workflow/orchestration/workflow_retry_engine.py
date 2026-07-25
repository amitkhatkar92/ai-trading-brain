"""
workflow_retry_engine.py — iios.workflow.orchestration
-------------------------------------------------------
WorkflowRetryEngine — wraps step execution with configurable
exponential-backoff retry logic.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import StepStatus
from .exceptions import WorkflowRetryExhaustedError
from .workflow_runtime import WorkflowRuntime
from .workflow_step import RetryPolicy, StepResult, WorkflowStep

_log = get_logger(__name__)


class WorkflowRetryEngine:
    """
    Wraps step execution callables with retry and backoff logic.

    Thread-safe — stateless.
    """

    def execute_with_retry(
        self,
        step:    WorkflowStep,
        execute: Callable[[], StepResult],
        runtime: WorkflowRuntime,
        policy:  Optional[RetryPolicy] = None,
    ) -> StepResult:
        """
        Execute `execute()` with retry semantics defined by `policy`.

        On each failure (non-COMPLETED status), waits backoff_for(attempt)
        seconds before retrying.  After exhausting retries, raises
        WorkflowRetryExhaustedError.

        Parameters:
            step    — the step being executed (for logging / ID)
            execute — a zero-arg callable that runs the step and returns StepResult
            runtime — workflow runtime (tracks retry counts)
            policy  — RetryPolicy to use; falls back to step.retry_policy
        """
        p         = policy or step.retry_policy
        last_result: Optional[StepResult] = None

        for attempt in range(p.max_retries + 1):
            if attempt > 0:
                backoff = p.backoff_for(attempt - 1)
                _log.debug(
                    f"RetryEngine: step={step.step_id!r} "
                    f"attempt={attempt}/{p.max_retries} "
                    f"backoff={backoff:.2f}s"
                )
                runtime.set_step_status(step.step_id, StepStatus.RETRYING)
                runtime.increment_retry(step.step_id)
                time.sleep(backoff)

            try:
                result = execute()
            except Exception as exc:
                result = StepResult.failure(
                    step, str(exc), duration_ms=0.0, retry_count=attempt
                )

            last_result = result

            if result.is_success:
                return result

            # Step failed — check if we should retry
            if attempt >= p.max_retries:
                _log.warning(
                    f"RetryEngine: step={step.step_id!r} "
                    f"exhausted {p.max_retries} retries"
                )
                raise WorkflowRetryExhaustedError(
                    f"Step {step.name!r} exhausted {p.max_retries} retries: "
                    f"{result.error}",
                    step_id  = step.step_id,
                    attempts = attempt + 1,
                )

        # Should not reach here
        return last_result  # type: ignore[return-value]
