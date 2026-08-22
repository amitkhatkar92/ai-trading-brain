"""iios/execution/workflow/execution_workflow.py"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from iios.execution.core.execution_session import ExecutionSession
from iios.execution.core.execution_request import ExecutionRequest
from iios.execution.core.execution_plan    import ExecutionPlan
from iios.execution.core.execution_result  import ExecutionResult
from iios.execution.execution_constants    import WorkflowStepStatus


@dataclass
class StepResult:
    """Outcome of a single workflow step."""

    step_name:   str               = ""
    status:      WorkflowStepStatus = WorkflowStepStatus.PENDING
    output:      Any               = None
    error:       str               = ""
    duration_ms: float             = 0.0
    metadata:    dict[str, Any]    = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.status == WorkflowStepStatus.COMPLETED

    @property
    def failed(self) -> bool:
        return self.status == WorkflowStepStatus.FAILED

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_name":   self.step_name,
            "status":      self.status.value,
            "error":       self.error,
            "duration_ms": round(self.duration_ms, 2),
            "metadata":    dict(self.metadata),
        }


@dataclass
class WorkflowContext:
    """
    Mutable shared context passed through every step in a workflow run.

    Steps read from ``session`` and may write to ``plan``, ``result``,
    and ``step_results``.  Errors accumulated here are surfaced to the
    caller by the WorkflowEngine.
    """

    execution_id: str
    session:      ExecutionSession
    step_results: dict[str, StepResult] = field(default_factory=dict)
    errors:       list[str]             = field(default_factory=list)
    metadata:     dict[str, Any]        = field(default_factory=dict)

    # ── Convenience proxies ───────────────────────────────────────────────────

    @property
    def request(self) -> ExecutionRequest:
        return self.session.request

    @property
    def plan(self) -> ExecutionPlan | None:
        return self.session.plan

    @plan.setter
    def plan(self, value: ExecutionPlan) -> None:
        self.session.plan = value

    @property
    def result(self) -> ExecutionResult | None:
        return self.session.result

    @result.setter
    def result(self, value: ExecutionResult) -> None:
        self.session.result = value

    def record(self, step_result: StepResult) -> None:
        self.step_results[step_result.step_name] = step_result

    def has_errors(self) -> bool:
        return bool(self.errors)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)


class WorkflowStep(ABC):
    """Abstract base class for all workflow steps."""

    step_name: str = "unnamed"

    @abstractmethod
    def execute(self, ctx: WorkflowContext) -> StepResult:
        """Execute the step and return a StepResult.  Must not raise."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(step={self.step_name!r})"
