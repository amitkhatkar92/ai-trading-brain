"""
plan_types.py -- iios.ai.orchestrator.core
===========================================
Frozen dataclasses for plans and planning context.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import dataclasses
import time
import uuid
from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple

from .orchestration_types import PlanStatus


@dataclass(frozen=True)
class PlanStep:
    """Immutable plan step descriptor."""
    step_id:         str
    name:            str
    action:          str
    description:     str
    parameters:      FrozenSet[Tuple[str, str]]
    dependencies:    FrozenSet[str]    # step_ids that must complete first
    parallel:        bool              # may run concurrently with sibling steps
    timeout_seconds: int
    max_retries:     int

    @classmethod
    def create(
        cls,
        name:            str,
        action:          str,
        description:     str = "",
        dependencies:    FrozenSet[str] = frozenset(),
        parallel:        bool = False,
        timeout_seconds: int  = 60,
        max_retries:     int  = 0,
        **parameters: str,
    ) -> "PlanStep":
        return cls(
            step_id         = str(uuid.uuid4()),
            name            = name,
            action          = action,
            description     = description,
            parameters      = frozenset(parameters.items()),
            dependencies    = dependencies,
            parallel        = parallel,
            timeout_seconds = timeout_seconds,
            max_retries     = max_retries,
        )

    def get_param(self, key: str, default: str = "") -> str:
        for k, v in self.parameters:
            if k == key:
                return v
        return default


@dataclass(frozen=True)
class PlanDependency:
    """Directed dependency edge between two plan steps."""
    from_step: str    # step that must complete
    to_step:   str    # step that depends on from_step
    condition: Optional[str]  # informational condition expression

    @classmethod
    def create(
        cls,
        from_step: str,
        to_step:   str,
        condition: Optional[str] = None,
    ) -> "PlanDependency":
        return cls(from_step=from_step, to_step=to_step, condition=condition)


@dataclass(frozen=True)
class ExecutionPlan:
    """Immutable execution plan."""
    plan_id:      str
    objective:    str
    steps:        Tuple[PlanStep, ...]
    dependencies: Tuple[PlanDependency, ...]
    status:       PlanStatus
    created_at:   float

    @classmethod
    def create(
        cls,
        objective:    str,
        steps:        Tuple[PlanStep, ...] = (),
        dependencies: Tuple[PlanDependency, ...] = (),
    ) -> "ExecutionPlan":
        return cls(
            plan_id      = str(uuid.uuid4()),
            objective    = objective,
            steps        = steps,
            dependencies = dependencies,
            status       = PlanStatus.DRAFT,
            created_at   = time.time(),
        )

    def with_status(self, status: PlanStatus) -> "ExecutionPlan":
        return dataclasses.replace(self, status=status)

    def with_steps(self, steps: Tuple[PlanStep, ...]) -> "ExecutionPlan":
        return dataclasses.replace(self, steps=steps)

    def step_count(self) -> int:
        return len(self.steps)


@dataclass(frozen=True)
class PlanningContext:
    """Immutable context supplied to the planning engine."""
    planning_id:  str
    objective:    str
    constraints:  FrozenSet[str]
    preferences:  FrozenSet[Tuple[str, str]]

    @classmethod
    def create(
        cls,
        objective:   str,
        constraints: FrozenSet[str] = frozenset(),
        **preferences: str,
    ) -> "PlanningContext":
        return cls(
            planning_id = str(uuid.uuid4()),
            objective   = objective,
            constraints = constraints,
            preferences = frozenset(preferences.items()),
        )

    def get_preference(self, key: str, default: str = "") -> str:
        for k, v in self.preferences:
            if k == key:
                return v
        return default
