"""
workflow_conditional_engine.py — iios.workflow.orchestration
-------------------------------------------------------------
WorkflowConditionalEngine — evaluates step conditions and routes
execution to the correct branch.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .workflow_context_manager import WorkflowContextManager
from .workflow_runtime import WorkflowRuntime
from .workflow_step import StepResult, WorkflowStep

_log = get_logger(__name__)

# Condition handler: (context: Dict) → bool
ConditionHandler = Callable[[Dict[str, Any]], bool]


class WorkflowConditionalEngine:
    """
    Evaluates step conditions and decides whether to execute or skip a step.

    A step with `condition` set will be executed only if the condition
    evaluates to True.  A step with no condition is always executed.

    Thread-safe — stateless.
    """

    def should_execute(
        self,
        step:               WorkflowStep,
        ctx_mgr:            WorkflowContextManager,
        condition_lookup:   Optional[Callable[[str], ConditionHandler]] = None,
    ) -> bool:
        """
        Evaluate whether step should execute.

        If step.condition is None, always returns True.
        Otherwise, calls condition_lookup(step.condition)(context).
        If condition_lookup is None or handler not found, defaults to True
        (fail-open to avoid silently skipping steps).

        Returns:
            True  — step should execute
            False — step should be skipped
        """
        if not step.has_condition:
            return True

        if condition_lookup is None:
            _log.warning(
                f"Conditional: step={step.step_id!r} has condition={step.condition!r} "
                f"but no condition_lookup provided — defaulting to execute"
            )
            return True

        try:
            handler = condition_lookup(step.condition)
            context = ctx_mgr.get_all()
            result  = handler(context)
            _log.debug(
                f"Conditional: step={step.step_id!r} "
                f"condition={step.condition!r} → {result!r}"
            )
            return bool(result)
        except Exception as exc:
            _log.warning(
                f"Conditional: step={step.step_id!r} "
                f"condition evaluation failed: {exc!r} — defaulting to execute"
            )
            return True

    def filter_executable_steps(
        self,
        steps:              List[WorkflowStep],
        ctx_mgr:            WorkflowContextManager,
        condition_lookup:   Optional[Callable[[str], ConditionHandler]] = None,
    ) -> tuple:
        """
        Partition steps into (executable, skipped) based on conditions.

        Returns:
            (executable: List[WorkflowStep], skipped: List[WorkflowStep])
        """
        executable = []
        skipped    = []
        for step in steps:
            if self.should_execute(step, ctx_mgr, condition_lookup):
                executable.append(step)
            else:
                skipped.append(step)
        return executable, skipped
