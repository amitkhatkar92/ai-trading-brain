"""
workflow_compensation_engine.py — iios.workflow.orchestration
-------------------------------------------------------------
WorkflowCompensationEngine — runs compensation steps in reverse order
when a workflow fails (saga-style rollback).

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import StepStatus, WorkflowStatus
from .exceptions import WorkflowCompensationError
from .workflow_context_manager import WorkflowContextManager
from .workflow_definition import WorkflowDefinition
from .workflow_runtime import WorkflowRuntime
from .workflow_step import StepResult, WorkflowStep
from .workflow_step_executor import StepHandler, WorkflowStepExecutor

_log = get_logger(__name__)


class WorkflowCompensationEngine:
    """
    Executes compensation steps in reverse order for completed steps.

    Only steps that:
    1. Have completed successfully, AND
    2. Have a compensation_step_id, AND
    3. The compensation step exists in the definition

    …are compensated.  Compensation errors are logged but do not prevent
    other compensations from running.

    Thread-safe — stateless.
    """

    def __init__(self, step_executor: Optional[WorkflowStepExecutor] = None) -> None:
        self._step_executor = step_executor or WorkflowStepExecutor()

    def compensate(
        self,
        runtime:        WorkflowRuntime,
        definition:     WorkflowDefinition,
        ctx_mgr:        WorkflowContextManager,
        handler_lookup: Callable[[str], StepHandler],
    ) -> List[StepResult]:
        """
        Run compensation for all completed steps in reverse execution order.

        Returns:
            List of compensation StepResults (may include failures).
        """
        runtime.set_status(WorkflowStatus.COMPENSATING)
        step_map = definition.step_map

        # Collect completed steps that have a compensation step
        completed_with_comp: List[WorkflowStep] = []
        for step in definition.steps:
            if (
                runtime.is_step_completed(step.step_id)
                and step.has_compensation
                and step.compensation_step_id in step_map
            ):
                completed_with_comp.append(step)

        # Reverse order for LIFO rollback
        completed_with_comp.reverse()

        compensation_results: List[StepResult] = []
        for step in completed_with_comp:
            comp_step_id = step.compensation_step_id
            comp_step    = step_map[comp_step_id]  # type: ignore[index]

            runtime.set_step_status(comp_step.step_id, StepStatus.COMPENSATING)
            _log.info(
                f"Compensation: running step={comp_step.step_id!r} "
                f"for original step={step.step_id!r}"
            )

            try:
                handler = handler_lookup(comp_step.handler)
                result  = self._step_executor.execute(comp_step, handler, ctx_mgr)
                runtime.record_step_result(result)
                runtime.increment_compensation()
                compensation_results.append(result)

                if result.is_failure:
                    _log.warning(
                        f"Compensation: step={comp_step.step_id!r} failed — "
                        f"continuing with remaining compensations"
                    )
            except Exception as exc:
                _log.error(
                    f"Compensation: step={comp_step.step_id!r} raised {exc!r}"
                )
                err_result = StepResult.failure(comp_step, str(exc), 0.0)
                compensation_results.append(err_result)

        return compensation_results
