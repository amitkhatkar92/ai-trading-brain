"""
iios/events/workflow/workflow_engine.py
=========================================
Lightweight saga-style workflow engine with compensation (rollback) support.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from ..event_exceptions import (
    WorkflowError, WorkflowStepError, WorkflowTimeoutError, WorkflowRollbackError,
)
from ..event_constants import DEFAULT_WORKFLOW_TIMEOUT, MAX_WORKFLOW_STEPS

__all__ = [
    "WorkflowStatus",
    "StepResult",
    "WorkflowStep",
    "WorkflowState",
    "WorkflowPipeline",
    "SagaWorkflow",
    "WorkflowEngine",
    "get_workflow_engine",
    "reset_workflow_engine",
]

_LOG = logging.getLogger("iios.events.workflow")

_engine_lock = threading.Lock()
_engine: Optional["WorkflowEngine"] = None

StepHandler = Callable[[dict[str, Any]], Any]
CompensateHandler = Callable[[dict[str, Any]], None]


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    TIMED_OUT = "timed_out"


@dataclass
class StepResult:
    step_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class WorkflowStep:
    """A single step in a workflow."""

    name: str
    handler: StepHandler
    compensate: Optional[CompensateHandler] = None  # saga rollback handler
    timeout: float = 0.0           # 0 = inherit from workflow
    max_retries: int = 0
    retry_delay: float = 1.0
    description: str = ""


@dataclass
class WorkflowState:
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: dict[str, Any] = field(default_factory=dict)
    step_results: list[StepResult] = field(default_factory=list)
    current_step: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    error: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        end = self.finished_at or time.time()
        return (end - self.started_at) * 1000


class WorkflowPipeline:
    """Linear execution of steps — if one fails, execution stops."""

    def __init__(self, name: str, timeout: float = DEFAULT_WORKFLOW_TIMEOUT) -> None:
        self.name = name
        self.timeout = timeout
        self._steps: list[WorkflowStep] = []

    def step(
        self,
        name: str,
        handler: StepHandler,
        *,
        timeout: float = 0.0,
        max_retries: int = 0,
        retry_delay: float = 1.0,
        description: str = "",
    ) -> "WorkflowPipeline":
        if len(self._steps) >= MAX_WORKFLOW_STEPS:
            raise WorkflowError(f"Pipeline '{self.name}' exceeds MAX_WORKFLOW_STEPS")
        self._steps.append(
            WorkflowStep(
                name=name,
                handler=handler,
                timeout=timeout,
                max_retries=max_retries,
                retry_delay=retry_delay,
                description=description,
            )
        )
        return self

    def execute(self, context: Optional[dict[str, Any]] = None) -> WorkflowState:
        state = WorkflowState(
            workflow_id=str(uuid.uuid4()),
            workflow_name=self.name,
            context=dict(context or {}),
            status=WorkflowStatus.RUNNING,
        )
        deadline = time.monotonic() + self.timeout if self.timeout else None
        try:
            for step in self._steps:
                if deadline and time.monotonic() > deadline:
                    state.status = WorkflowStatus.TIMED_OUT
                    state.error = f"Timeout after {self.timeout}s"
                    raise WorkflowTimeoutError(self.name, self.timeout)
                state.current_step = step.name
                result = _run_step(step, state.context, deadline)
                state.step_results.append(result)
                if not result.success:
                    state.status = WorkflowStatus.FAILED
                    state.error = result.error
                    raise WorkflowStepError(self.name, step.name, result.error or "")
                if result.output is not None:
                    state.context[step.name] = result.output
        except (WorkflowStepError, WorkflowTimeoutError):
            pass
        except Exception as exc:
            state.status = WorkflowStatus.FAILED
            state.error = str(exc)
        else:
            state.status = WorkflowStatus.COMPLETED
        finally:
            state.finished_at = time.time()
        return state


class SagaWorkflow:
    """Saga pattern: each step has a compensate handler for rollback on failure."""

    def __init__(self, name: str, timeout: float = DEFAULT_WORKFLOW_TIMEOUT) -> None:
        self.name = name
        self.timeout = timeout
        self._steps: list[WorkflowStep] = []

    def step(
        self,
        name: str,
        handler: StepHandler,
        compensate: Optional[CompensateHandler] = None,
        *,
        timeout: float = 0.0,
        max_retries: int = 0,
        description: str = "",
    ) -> "SagaWorkflow":
        if len(self._steps) >= MAX_WORKFLOW_STEPS:
            raise WorkflowError(f"Saga '{self.name}' exceeds MAX_WORKFLOW_STEPS")
        self._steps.append(
            WorkflowStep(
                name=name,
                handler=handler,
                compensate=compensate,
                timeout=timeout,
                max_retries=max_retries,
                description=description,
            )
        )
        return self

    def execute(self, context: Optional[dict[str, Any]] = None) -> WorkflowState:
        state = WorkflowState(
            workflow_id=str(uuid.uuid4()),
            workflow_name=self.name,
            context=dict(context or {}),
            status=WorkflowStatus.RUNNING,
        )
        deadline = time.monotonic() + self.timeout if self.timeout else None
        completed: list[WorkflowStep] = []
        failed_at: Optional[WorkflowStep] = None
        try:
            for step in self._steps:
                if deadline and time.monotonic() > deadline:
                    state.status = WorkflowStatus.TIMED_OUT
                    state.error = f"Timeout after {self.timeout}s"
                    failed_at = step
                    raise WorkflowTimeoutError(self.name, self.timeout)
                state.current_step = step.name
                result = _run_step(step, state.context, deadline)
                state.step_results.append(result)
                if not result.success:
                    state.status = WorkflowStatus.FAILED
                    state.error = result.error
                    failed_at = step
                    raise WorkflowStepError(self.name, step.name, result.error or "")
                completed.append(step)
                if result.output is not None:
                    state.context[step.name] = result.output
        except (WorkflowStepError, WorkflowTimeoutError):
            _compensate(state, completed, failed_at)
        except Exception as exc:
            state.status = WorkflowStatus.FAILED
            state.error = str(exc)
            _compensate(state, completed, None)
        else:
            state.status = WorkflowStatus.COMPLETED
        finally:
            state.finished_at = time.time()
        return state


def _run_step(step: WorkflowStep, context: dict[str, Any], deadline: Optional[float]) -> StepResult:
    step_timeout = step.timeout if step.timeout > 0 else (
        max(0.0, deadline - time.monotonic()) if deadline else 0.0
    )
    attempts = step.max_retries + 1
    last_error: Optional[str] = None
    t0 = time.monotonic()
    for attempt in range(attempts):
        try:
            output = step.handler(context)
            return StepResult(
                step_name=step.name,
                success=True,
                output=output,
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as exc:
            last_error = str(exc)
            if attempt < attempts - 1:
                time.sleep(step.retry_delay)
    return StepResult(
        step_name=step.name,
        success=False,
        error=last_error,
        duration_ms=(time.monotonic() - t0) * 1000,
    )


def _compensate(
    state: WorkflowState,
    completed: list[WorkflowStep],
    failed_at: Optional[WorkflowStep],
) -> None:
    state.status = WorkflowStatus.COMPENSATING
    errors: list[str] = []
    for step in reversed(completed):
        if step.compensate:
            try:
                step.compensate(state.context)
            except Exception as exc:
                errors.append(f"{step.name}: {exc}")
    if errors:
        state.status = WorkflowStatus.FAILED
        _LOG.error("Compensation errors in saga '%s': %s", state.workflow_name, errors)
    else:
        state.status = WorkflowStatus.COMPENSATED


class WorkflowEngine:
    """Registry and executor for named workflow pipelines and sagas."""

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowPipeline | SagaWorkflow] = {}
        self._history: list[WorkflowState] = []
        self._lock = threading.RLock()
        self._max_history = 1000

    def register(self, workflow: "WorkflowPipeline | SagaWorkflow") -> None:
        with self._lock:
            self._workflows[workflow.name] = workflow

    def execute(
        self,
        name: str,
        context: Optional[dict[str, Any]] = None,
    ) -> WorkflowState:
        with self._lock:
            wf = self._workflows.get(name)
        if wf is None:
            raise WorkflowError(f"Unknown workflow: '{name}'")
        state = wf.execute(context)
        with self._lock:
            self._history.append(state)
            if len(self._history) > self._max_history:
                self._history.pop(0)
        return state

    def has_workflow(self, name: str) -> bool:
        with self._lock:
            return name in self._workflows

    def registered_names(self) -> list[str]:
        with self._lock:
            return list(self._workflows.keys())

    def history(self, limit: int = 50) -> list[WorkflowState]:
        with self._lock:
            return list(self._history[-limit:])

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()


def get_workflow_engine() -> WorkflowEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = WorkflowEngine()
        return _engine


def reset_workflow_engine() -> None:
    global _engine
    with _engine_lock:
        _engine = None
