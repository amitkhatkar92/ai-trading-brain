"""
workflow_factory.py — iios.workflow.orchestration
--------------------------------------------------
WorkflowFactory — fluent factory for creating standard orchestration
objects with sensible defaults.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .constants import StepType, WorkflowType
from .workflow_definition import WorkflowDefinition, WorkflowExecutionRequest
from .workflow_step import RetryPolicy, WorkflowStep
from .workflow_step_executor import StepHandler


class WorkflowFactory:
    """
    Factory for creating well-formed orchestration objects.

    All objects created here are valid and ready for registration
    or execution.
    """

    # ── Steps ─────────────────────────────────────────────────────────────────

    @staticmethod
    def create_task_step(
        name:    str,
        handler: str,
        *,
        dependencies:         Optional[List[str]]  = None,
        timeout_seconds:      float                = 0.0,
        retry_policy:         Optional[RetryPolicy] = None,
        compensation_step_id: Optional[str]        = None,
        condition:            Optional[str]        = None,
        metadata:             Optional[Dict[str, Any]] = None,
    ) -> WorkflowStep:
        return WorkflowStep.create(
            name                 = name,
            handler              = handler,
            step_type            = StepType.TASK,
            dependencies         = dependencies or [],
            timeout_seconds      = timeout_seconds,
            retry_policy         = retry_policy or RetryPolicy(),
            compensation_step_id = compensation_step_id,
            condition            = condition,
            metadata             = metadata or {},
        )

    @staticmethod
    def create_approval_step(
        name:    str,
        handler: str,
        *,
        dependencies:    Optional[List[str]] = None,
        timeout_seconds: float               = 3600.0,
    ) -> WorkflowStep:
        return WorkflowStep.create(
            name            = name,
            handler         = handler,
            step_type       = StepType.APPROVAL,
            dependencies    = dependencies or [],
            timeout_seconds = timeout_seconds,
            retry_policy    = RetryPolicy(max_retries=0),
        )

    @staticmethod
    def create_delay_step(
        name:          str,
        delay_handler: str,
        *,
        dependencies:  Optional[List[str]] = None,
    ) -> WorkflowStep:
        return WorkflowStep.create(
            name         = name,
            handler      = delay_handler,
            step_type    = StepType.DELAY,
            dependencies = dependencies or [],
        )

    @staticmethod
    def create_compensation_step(
        name:    str,
        handler: str,
    ) -> WorkflowStep:
        return WorkflowStep.create(
            name      = name,
            handler   = handler,
            step_type = StepType.COMPENSATION,
        )

    # ── Definitions ───────────────────────────────────────────────────────────

    @staticmethod
    def create_sequential_workflow(
        name:  str,
        steps: List[WorkflowStep],
        *,
        description:          str   = "",
        timeout_seconds:      float = 3600.0,
        enable_checkpointing: bool  = True,
        enable_compensation:  bool  = True,
    ) -> WorkflowDefinition:
        return WorkflowDefinition.create(
            name                 = name,
            steps                = steps,
            workflow_type        = WorkflowType.SEQUENTIAL,
            description          = description,
            timeout_seconds      = timeout_seconds,
            enable_checkpointing = enable_checkpointing,
            enable_compensation  = enable_compensation,
        )

    @staticmethod
    def create_parallel_workflow(
        name:  str,
        steps: List[WorkflowStep],
        *,
        description:          str   = "",
        timeout_seconds:      float = 3600.0,
        enable_checkpointing: bool  = True,
    ) -> WorkflowDefinition:
        return WorkflowDefinition.create(
            name                 = name,
            steps                = steps,
            workflow_type        = WorkflowType.PARALLEL,
            description          = description,
            timeout_seconds      = timeout_seconds,
            enable_checkpointing = enable_checkpointing,
        )

    @staticmethod
    def create_saga_workflow(
        name:  str,
        steps: List[WorkflowStep],
        *,
        description:     str   = "",
        timeout_seconds: float = 3600.0,
    ) -> WorkflowDefinition:
        """Create a saga workflow — all steps have compensation enabled."""
        return WorkflowDefinition.create(
            name                = name,
            steps               = steps,
            workflow_type       = WorkflowType.SAGA,
            description         = description,
            timeout_seconds     = timeout_seconds,
            enable_compensation = True,
        )

    # ── Requests ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_request(
        workflow_id:    str,
        definition_id:  str,
        *,
        context_data:   Optional[Dict[str, Any]] = None,
        priority:       int                      = 5,
    ) -> WorkflowExecutionRequest:
        return WorkflowExecutionRequest.create(
            workflow_id   = workflow_id,
            definition_id = definition_id,
            context_data  = context_data or {},
            priority      = priority,
        )

    # ── Retry policies ────────────────────────────────────────────────────────

    @staticmethod
    def no_retry() -> RetryPolicy:
        return RetryPolicy(max_retries=0)

    @staticmethod
    def fast_retry(max_retries: int = 3) -> RetryPolicy:
        return RetryPolicy(max_retries=max_retries, backoff_seconds=0.1, max_backoff_seconds=1.0)

    @staticmethod
    def standard_retry() -> RetryPolicy:
        return RetryPolicy(max_retries=3, backoff_seconds=1.0)

    @staticmethod
    def aggressive_retry() -> RetryPolicy:
        return RetryPolicy(max_retries=10, backoff_seconds=0.5, max_backoff_seconds=30.0)
