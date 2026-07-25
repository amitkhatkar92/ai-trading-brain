"""
workflow_step.py — iios.workflow.orchestration
-----------------------------------------------
WorkflowStep, RetryPolicy, StepResult — immutable step definitions
and per-step execution results.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_BACKOFF_MULTIPLIER,
    DEFAULT_BACKOFF_SECONDS,
    DEFAULT_MAX_BACKOFF,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    PREFIX_STEP,
    StepStatus,
    StepType,
)


@dataclass(frozen=True)
class RetryPolicy:
    """Retry behaviour for a single workflow step."""
    max_retries:        int   = DEFAULT_MAX_RETRIES
    backoff_seconds:    float = DEFAULT_BACKOFF_SECONDS
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER
    max_backoff_seconds: float = DEFAULT_MAX_BACKOFF

    def backoff_for(self, attempt: int) -> float:
        """Return the wait duration (seconds) before the given retry attempt."""
        delay = self.backoff_seconds * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_backoff_seconds)


@dataclass(frozen=True)
class WorkflowStep:
    """
    Immutable definition of a single workflow step.

    All behaviour is driven by configuration and registered handlers;
    no business logic lives here.
    """
    step_id:              str
    name:                 str
    step_type:            StepType
    handler:              str               # registered handler name
    dependencies:         tuple             # Tuple[str, ...]  — step_ids
    retry_policy:         RetryPolicy
    timeout_seconds:      float             # 0 = use workflow default
    compensation_step_id: Optional[str]     # step to run on rollback
    condition:            Optional[str]     # registered condition handler name
    input_mapping:        Dict[str, str]    # context_key → step_input_key
    output_mapping:       Dict[str, str]    # step_output_key → context_key
    metadata:             Dict[str, Any]

    @classmethod
    def create(
        cls,
        name:     str,
        handler:  str,
        *,
        step_type:            StepType                   = StepType.TASK,
        dependencies:         Optional[List[str]]        = None,
        retry_policy:         Optional[RetryPolicy]      = None,
        timeout_seconds:      float                      = 0.0,
        compensation_step_id: Optional[str]              = None,
        condition:            Optional[str]              = None,
        input_mapping:        Optional[Dict[str, str]]   = None,
        output_mapping:       Optional[Dict[str, str]]   = None,
        metadata:             Optional[Dict[str, Any]]   = None,
        step_id:              Optional[str]              = None,
    ) -> "WorkflowStep":
        return cls(
            step_id              = step_id or f"{PREFIX_STEP}{uuid.uuid4().hex[:10]}",
            name                 = name,
            step_type            = step_type,
            handler              = handler,
            dependencies         = tuple(dependencies or []),
            retry_policy         = retry_policy or RetryPolicy(),
            timeout_seconds      = timeout_seconds,
            compensation_step_id = compensation_step_id,
            condition            = condition,
            input_mapping        = dict(input_mapping or {}),
            output_mapping       = dict(output_mapping or {}),
            metadata             = dict(metadata or {}),
        )

    @property
    def has_dependencies(self) -> bool:
        return len(self.dependencies) > 0

    @property
    def has_compensation(self) -> bool:
        return self.compensation_step_id is not None

    @property
    def has_condition(self) -> bool:
        return self.condition is not None

    @property
    def effective_timeout(self) -> float:
        """Return timeout; 0 means no step-level timeout (use workflow default)."""
        from .constants import DEFAULT_TIMEOUT_SECONDS
        return self.timeout_seconds if self.timeout_seconds > 0.0 else DEFAULT_TIMEOUT_SECONDS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id":              self.step_id,
            "name":                 self.name,
            "step_type":            self.step_type.value,
            "handler":              self.handler,
            "dependencies":         list(self.dependencies),
            "timeout_seconds":      self.timeout_seconds,
            "compensation_step_id": self.compensation_step_id,
            "condition":            self.condition,
        }


@dataclass(frozen=True)
class StepResult:
    """Immutable result of executing a single workflow step."""
    step_id:     str
    step_name:   str
    status:      StepStatus
    outputs:     Dict[str, Any]
    error:       Optional[str]
    retry_count: int
    duration_ms: float
    executed_at: str

    @classmethod
    def success(
        cls,
        step:        WorkflowStep,
        outputs:     Dict[str, Any],
        duration_ms: float,
        retry_count: int = 0,
    ) -> "StepResult":
        return cls(
            step_id     = step.step_id,
            step_name   = step.name,
            status      = StepStatus.COMPLETED,
            outputs     = dict(outputs),
            error       = None,
            retry_count = retry_count,
            duration_ms = round(duration_ms, 3),
            executed_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def failure(
        cls,
        step:        WorkflowStep,
        error:       str,
        duration_ms: float,
        retry_count: int = 0,
    ) -> "StepResult":
        return cls(
            step_id     = step.step_id,
            step_name   = step.name,
            status      = StepStatus.FAILED,
            outputs     = {},
            error       = error,
            retry_count = retry_count,
            duration_ms = round(duration_ms, 3),
            executed_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def skipped(cls, step: WorkflowStep) -> "StepResult":
        return cls(
            step_id     = step.step_id,
            step_name   = step.name,
            status      = StepStatus.SKIPPED,
            outputs     = {},
            error       = None,
            retry_count = 0,
            duration_ms = 0.0,
            executed_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    @classmethod
    def timed_out(cls, step: WorkflowStep, duration_ms: float) -> "StepResult":
        return cls(
            step_id     = step.step_id,
            step_name   = step.name,
            status      = StepStatus.TIMED_OUT,
            outputs     = {},
            error       = f"Step timed out after {duration_ms:.0f}ms",
            retry_count = 0,
            duration_ms = round(duration_ms, 3),
            executed_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    @property
    def is_success(self) -> bool:
        return self.status == StepStatus.COMPLETED

    @property
    def is_failure(self) -> bool:
        return self.status in (StepStatus.FAILED, StepStatus.TIMED_OUT)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id":     self.step_id,
            "step_name":   self.step_name,
            "status":      self.status.value,
            "outputs":     self.outputs,
            "error":       self.error,
            "retry_count": self.retry_count,
            "duration_ms": self.duration_ms,
            "executed_at": self.executed_at,
        }
