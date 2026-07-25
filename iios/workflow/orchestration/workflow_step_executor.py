"""
workflow_step_executor.py — iios.workflow.orchestration
--------------------------------------------------------
WorkflowStepExecutor — executes a single workflow step by calling
its registered handler.

Handles input/output context mapping and duration tracking.
Retry and timeout are applied externally (see RetryEngine / TimeoutEngine).

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from .exceptions import WorkflowStepError
from .workflow_context_manager import WorkflowContextManager
from .workflow_step import StepResult, WorkflowStep

_log = get_logger(__name__)

# Type alias: handler(step, inputs, context) → outputs
StepHandler = Callable[[WorkflowStep, Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


class WorkflowStepExecutor:
    """
    Executes a single workflow step using its registered handler.

    Thread-safe — stateless.
    """

    def execute(
        self,
        step:        WorkflowStep,
        handler:     StepHandler,
        ctx_mgr:     WorkflowContextManager,
        retry_count: int = 0,
    ) -> StepResult:
        """
        Execute one step.

        1. Resolve inputs from context using step.input_mapping.
        2. Call handler(step, inputs, full_context).
        3. Apply outputs back to context using step.output_mapping.
        4. Return StepResult.

        Parameters:
            step        — the step to execute
            handler     — the callable registered for step.handler
            ctx_mgr     — the workflow context manager
            retry_count — current retry attempt (recorded in result)

        Returns:
            StepResult
        """
        t0 = time.monotonic()
        _log.debug(f"StepExecutor: executing step={step.step_id!r} name={step.name!r}")

        try:
            # Resolve inputs
            inputs = ctx_mgr.resolve_inputs(step.input_mapping)

            # Call handler
            context  = ctx_mgr.get_all()
            outputs: Dict[str, Any] = handler(step, inputs, context) or {}

            # Apply outputs back to context
            if step.output_mapping:
                ctx_mgr.apply_outputs(outputs, step.output_mapping)
            else:
                # No mapping — merge all outputs into context under step_id namespace
                ctx_mgr.merge({f"{step.step_id}.{k}": v for k, v in outputs.items()})

            duration_ms = (time.monotonic() - t0) * 1000.0
            result      = StepResult.success(step, outputs, duration_ms, retry_count)
            _log.debug(
                f"StepExecutor: step={step.step_id!r} completed "
                f"in {duration_ms:.1f}ms"
            )
            return result

        except Exception as exc:
            duration_ms = (time.monotonic() - t0) * 1000.0
            error_msg   = f"{type(exc).__name__}: {exc}"
            _log.warning(
                f"StepExecutor: step={step.step_id!r} failed "
                f"in {duration_ms:.1f}ms — {error_msg}"
            )
            return StepResult.failure(step, error_msg, duration_ms, retry_count)
