"""
workflow_types.py -- iios.ai.orchestrator.core
===============================================
Frozen dataclasses for workflow definitions, instances, and runtime state.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import dataclasses
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Optional, Tuple

from .orchestration_types import StepStatus, WorkflowStatus


@dataclass(frozen=True)
class WorkflowStep:
    """Immutable workflow step definition."""
    step_id:         str
    name:            str
    action:          str
    parameters:      FrozenSet[Tuple[str, str]]
    condition:       Optional[str]    # informational guard expression
    on_success:      Optional[str]    # next step_id on success (None → end workflow)
    on_failure:      Optional[str]    # next step_id on failure (None → fail workflow)
    timeout_seconds: int
    max_retries:     int

    @classmethod
    def create(
        cls,
        name:            str,
        action:          str,
        condition:       Optional[str] = None,
        on_success:      Optional[str] = None,
        on_failure:      Optional[str] = None,
        timeout_seconds: int  = 60,
        max_retries:     int  = 0,
        **parameters: str,
    ) -> "WorkflowStep":
        return cls(
            step_id         = str(uuid.uuid4()),
            name            = name,
            action          = action,
            parameters      = frozenset(parameters.items()),
            condition       = condition,
            on_success      = on_success,
            on_failure      = on_failure,
            timeout_seconds = timeout_seconds,
            max_retries     = max_retries,
        )

    def get_param(self, key: str, default: str = "") -> str:
        for k, v in self.parameters:
            if k == key:
                return v
        return default


@dataclass(frozen=True)
class WorkflowDefinition:
    """Immutable workflow definition."""
    workflow_id:  str
    name:         str
    description:  str
    steps:        Tuple[WorkflowStep, ...]
    initial_step: str               # step_id of the first step
    tags:         FrozenSet[str]

    @classmethod
    def create(
        cls,
        name:        str,
        steps:       Tuple[WorkflowStep, ...],
        description: str = "",
        tags:        FrozenSet[str] = frozenset(),
    ) -> "WorkflowDefinition":
        if not steps:
            raise ValueError("WorkflowDefinition requires at least one step")
        return cls(
            workflow_id  = str(uuid.uuid4()),
            name         = name,
            description  = description,
            steps        = steps,
            initial_step = steps[0].step_id,
            tags         = tags,
        )

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        return None

    def step_count(self) -> int:
        return len(self.steps)


@dataclass(frozen=True)
class WorkflowInstance:
    """Immutable workflow runtime instance record."""
    instance_id: str
    workflow_id: str
    status:      WorkflowStatus
    context_id:  str
    created_at:  float

    @classmethod
    def create(cls, workflow_id: str, context_id: str) -> "WorkflowInstance":
        return cls(
            instance_id = str(uuid.uuid4()),
            workflow_id = workflow_id,
            status      = WorkflowStatus.PENDING,
            context_id  = context_id,
            created_at  = time.time(),
        )

    def with_status(self, status: WorkflowStatus) -> "WorkflowInstance":
        return dataclasses.replace(self, status=status)


@dataclass
class WorkflowState:
    """Mutable runtime state for a workflow instance."""
    workflow_instance_id: str
    current_step_id:      Optional[str]
    status:               WorkflowStatus
    step_outputs:         Dict[str, Any]          = field(default_factory=dict)
    step_statuses:        Dict[str, StepStatus]   = field(default_factory=dict)
    started_at:           float                   = field(default_factory=time.time)
    completed_at:         Optional[float]         = None
    error:                Optional[str]           = None

    @classmethod
    def create(cls, instance_id: str, initial_step: Optional[str] = None) -> "WorkflowState":
        return cls(
            workflow_instance_id = instance_id,
            current_step_id      = initial_step,
            status               = WorkflowStatus.PENDING,
        )
