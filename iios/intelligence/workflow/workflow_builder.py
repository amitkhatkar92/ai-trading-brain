"""
iios/intelligence/workflow/workflow_builder.py
=============================================
Fluent builder for constructing WorkflowDefinition objects.

A workflow is a DAG of WorkflowSteps.  Steps declare their explicit
upstream dependencies; the executor resolves the topological order.
Steps without dependencies can run in parallel (if the workflow type
permits it).

Usage
-----
wf = (
    WorkflowBuilder("my_wf", WorkflowType.PARALLEL)
    .step("step_a", fn_a)
    .step("step_b", fn_b, depends_on=["step_a"])
    .step("step_c", fn_c, depends_on=["step_a"])
    .timeout(120_000)
    .build()
)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..intelligence_constants import (
    WorkflowType,
    StepType,
    StepStatus,
    Priority,
    MAX_WORKFLOW_STEPS,
    STEP_TIMEOUT_MS,
    WORKFLOW_TIMEOUT_MS,
    SYSTEM_ACTOR,
)
from ..intelligence_exceptions import (
    CircularDependencyError,
    WorkflowStepError,
)
from ..execution.execution_policy import ExecutionPolicy, RetryPolicy, TimeoutPolicy

__all__ = [
    "WorkflowStep",
    "WorkflowDefinition",
    "WorkflowBuilder",
]


@dataclass
class WorkflowStep:
    """
    One step within a workflow.

    Fields
    ------
    step_id:      Unique within the workflow
    name:         Human-readable label
    step_type:    Classification of the step
    fn:           Callable (args: step inputs dict → result Any)
    depends_on:   Step IDs that must complete before this step runs
    input_map:    Maps output keys from dependency steps to input keys for this step
                  e.g. {"step_a.result": "data"} passes step_a's "result" as "data"
    policy:       Override execution policy for this step
    condition:    Optional callable that returns bool; if False, step is skipped
    timeout_ms:   Per-step timeout override
    retry:        Per-step retry override
    metadata:     Arbitrary key/value data
    """
    step_id:     str
    name:        str                        = ""
    step_type:   StepType                   = StepType.COMPUTATION
    fn:          Optional[Callable]         = field(default=None, repr=False)
    depends_on:  list[str]                  = field(default_factory=list)
    input_map:   dict[str, str]             = field(default_factory=dict)
    policy:      Optional[ExecutionPolicy]  = field(default=None, repr=False)
    condition:   Optional[Callable]         = field(default=None, repr=False)
    timeout_ms:  float                      = STEP_TIMEOUT_MS
    max_retries: int                        = 0
    metadata:    dict[str, Any]             = field(default_factory=dict)
    # Runtime state (mutable during execution)
    status:      StepStatus                 = field(default=StepStatus.PENDING, compare=False)
    result:      Any                        = field(default=None, compare=False)
    error:       Optional[str]              = field(default=None, compare=False)
    started_at:  Optional[float]            = field(default=None, compare=False)
    finished_at: Optional[float]            = field(default=None, compare=False)
    attempt:     int                        = field(default=0, compare=False)

    @property
    def duration_ms(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.finished_at or time.time()
        return (end - self.started_at) * 1_000.0

    def to_dict(self) -> dict:
        return {
            "step_id":    self.step_id,
            "name":       self.name,
            "step_type":  self.step_type.value,
            "depends_on": self.depends_on,
            "status":     self.status.value,
            "duration_ms": round(self.duration_ms, 3),
            "attempt":    self.attempt,
            "error":      self.error,
        }


@dataclass
class WorkflowDefinition:
    """
    Immutable-ish description of a workflow.

    Contains ordered steps, policies, and metadata.
    The executor operates on a *copy* of the steps so the original
    definition can be re-used across multiple executions.
    """
    workflow_id:  str
    name:         str
    workflow_type: WorkflowType           = WorkflowType.SEQUENTIAL
    steps:        list[WorkflowStep]      = field(default_factory=list)
    policy:       ExecutionPolicy         = field(default_factory=ExecutionPolicy)
    tags:         list[str]               = field(default_factory=list)
    metadata:     dict[str, Any]          = field(default_factory=dict)
    version:      str                     = "1.0.0"
    actor:        str                     = SYSTEM_ACTOR
    created_at:   float                   = field(default_factory=time.time)
    description:  str                     = ""

    def step_ids(self) -> list[str]:
        return [s.step_id for s in self.steps]

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        return next((s for s in self.steps if s.step_id == step_id), None)

    def validate(self) -> list[str]:
        """Return list of validation error strings (empty = valid)."""
        errors: list[str] = []
        ids = {s.step_id for s in self.steps}
        # Check missing dependencies
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in ids:
                    errors.append(
                        f"Step {step.step_id!r} depends on unknown step {dep!r}"
                    )
        # Check for cycles
        try:
            self._topological_order()
        except CircularDependencyError as e:
            errors.append(str(e))
        return errors

    def _topological_order(self) -> list[str]:
        """
        Return step IDs in topological order (Kahn's algorithm).
        Raises CircularDependencyError if a cycle is detected.
        """
        in_degree: dict[str, int]    = {s.step_id: 0 for s in self.steps}
        adjacency: dict[str, list[str]] = {s.step_id: [] for s in self.steps}
        for step in self.steps:
            for dep in step.depends_on:
                adjacency.setdefault(dep, []).append(step.step_id)
                in_degree[step.step_id] = in_degree.get(step.step_id, 0) + 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        order: list[str] = []
        while queue:
            n = queue.pop(0)
            order.append(n)
            for child in adjacency.get(n, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(order) != len(self.steps):
            # Find cycle
            remaining = [sid for sid, deg in in_degree.items() if deg > 0]
            raise CircularDependencyError(remaining[:4])
        return order

    def to_dict(self) -> dict:
        return {
            "workflow_id":   self.workflow_id,
            "name":          self.name,
            "workflow_type": self.workflow_type.value,
            "steps":         [s.to_dict() for s in self.steps],
            "version":       self.version,
            "description":   self.description,
            "created_at":    self.created_at,
        }


class WorkflowBuilder:
    """
    Fluent builder for WorkflowDefinition.

    Example
    -------
    wf = (
        WorkflowBuilder("wf1")
        .name("My Workflow")
        .type(WorkflowType.PARALLEL)
        .step("load",    fn_load)
        .step("process", fn_process, depends_on=["load"])
        .step("save",    fn_save,    depends_on=["process"])
        .timeout(60_000)
        .tag("daily")
        .build()
    )
    """

    def __init__(self, workflow_id: Optional[str] = None) -> None:
        self._wf_id      = workflow_id or str(uuid.uuid4())
        self._name       = self._wf_id
        self._type       = WorkflowType.SEQUENTIAL
        self._steps:     list[WorkflowStep] = []
        self._policy     = ExecutionPolicy()
        self._tags:      list[str]  = []
        self._metadata:  dict       = {}
        self._version    = "1.0.0"
        self._actor      = SYSTEM_ACTOR
        self._description = ""

    # ── Fluent setters ────────────────────────────────────────────────────────

    def name(self, name: str) -> "WorkflowBuilder":
        self._name = name
        return self

    def type(self, wf_type: WorkflowType) -> "WorkflowBuilder":
        self._type = wf_type
        return self

    def description(self, text: str) -> "WorkflowBuilder":
        self._description = text
        return self

    def version(self, v: str) -> "WorkflowBuilder":
        self._version = v
        return self

    def tag(self, *tags: str) -> "WorkflowBuilder":
        self._tags.extend(tags)
        return self

    def metadata(self, **kwargs: Any) -> "WorkflowBuilder":
        self._metadata.update(kwargs)
        return self

    def timeout(self, workflow_ms: float, step_ms: Optional[float] = None) -> "WorkflowBuilder":
        self._policy.timeout.workflow_timeout_ms = workflow_ms
        if step_ms is not None:
            self._policy.timeout.step_timeout_ms = step_ms
        return self

    def retry(self, max_attempts: int, backoff_ms: float = 500.0) -> "WorkflowBuilder":
        self._policy.retry.max_attempts = max_attempts
        self._policy.retry.backoff_ms   = backoff_ms
        return self

    def priority(self, p: Priority) -> "WorkflowBuilder":
        self._policy.priority = p
        return self

    # ── Step addition ─────────────────────────────────────────────────────────

    def step(
        self,
        step_id:    str,
        fn:         Optional[Callable] = None,
        *,
        name:       str                = "",
        step_type:  StepType           = StepType.COMPUTATION,
        depends_on: list[str] | None   = None,
        input_map:  dict | None        = None,
        condition:  Optional[Callable] = None,
        timeout_ms: float              = STEP_TIMEOUT_MS,
        max_retries: int               = 0,
        metadata:   dict | None        = None,
    ) -> "WorkflowBuilder":
        if len(self._steps) >= MAX_WORKFLOW_STEPS:
            raise OverflowError(
                f"Workflow step limit ({MAX_WORKFLOW_STEPS}) exceeded"
            )
        s = WorkflowStep(
            step_id    = step_id,
            name       = name or step_id,
            step_type  = step_type,
            fn         = fn,
            depends_on = depends_on or [],
            input_map  = input_map or {},
            condition  = condition,
            timeout_ms = timeout_ms,
            max_retries = max_retries,
            metadata   = metadata or {},
        )
        self._steps.append(s)
        return self

    def sub_workflow(
        self,
        step_id:    str,
        sub_def:    "WorkflowDefinition",
        depends_on: list[str] | None = None,
    ) -> "WorkflowBuilder":
        """Embed another WorkflowDefinition as a nested step."""
        return self.step(
            step_id    = step_id,
            fn         = lambda _inp: sub_def,  # executor resolves sub-workflow defn
            step_type  = StepType.SUB_WORKFLOW,
            depends_on = depends_on or [],
            metadata   = {"sub_workflow_id": sub_def.workflow_id},
        )

    def checkpoint(self, step_id: str, depends_on: list[str] | None = None) -> "WorkflowBuilder":
        return self.step(
            step_id    = step_id,
            fn         = None,
            step_type  = StepType.CHECKPOINT,
            depends_on = depends_on or [],
        )

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self) -> WorkflowDefinition:
        defn = WorkflowDefinition(
            workflow_id   = self._wf_id,
            name          = self._name,
            workflow_type = self._type,
            steps         = self._steps,
            policy        = self._policy,
            tags          = self._tags,
            metadata      = self._metadata,
            version       = self._version,
            actor         = self._actor,
            description   = self._description,
        )
        errors = defn.validate()
        if errors:
            raise ValueError(f"Invalid workflow: {'; '.join(errors)}")
        return defn
