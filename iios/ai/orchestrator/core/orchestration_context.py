"""
orchestration_context.py -- iios.ai.orchestrator.core
=======================================================
OrchestrationContext, OrchestrationSession, OrchestrationResult.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import dataclasses
import time
import uuid
from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple

from .orchestration_types import ObjectiveStatus


@dataclass(frozen=True)
class OrchestrationContext:
    """Immutable invocation context for a single orchestration objective."""
    context_id:   str
    objective:    str
    principal_id: str
    session_id:   str
    trace_id:     str
    metadata:     FrozenSet[Tuple[str, str]]

    @classmethod
    def create(
        cls,
        objective:    str,
        principal_id: str,
        session_id:   Optional[str] = None,
        trace_id:     Optional[str] = None,
        **metadata: str,
    ) -> "OrchestrationContext":
        sid = session_id or str(uuid.uuid4())
        return cls(
            context_id   = str(uuid.uuid4()),
            objective    = objective,
            principal_id = principal_id,
            session_id   = sid,
            trace_id     = trace_id or str(uuid.uuid4()),
            metadata     = frozenset(metadata.items()),
        )

    def get_meta(self, key: str, default: str = "") -> str:
        for k, v in self.metadata:
            if k == key:
                return v
        return default


@dataclass(frozen=True)
class OrchestrationSession:
    """Immutable snapshot of an orchestration session."""
    session_id:  str
    context:     OrchestrationContext
    status:      ObjectiveStatus
    started_at:  float
    state_items: FrozenSet[Tuple[str, str]]

    @classmethod
    def create(cls, context: OrchestrationContext) -> "OrchestrationSession":
        return cls(
            session_id  = context.session_id,
            context     = context,
            status      = ObjectiveStatus.PENDING,
            started_at  = time.time(),
            state_items = frozenset(),
        )

    def with_status(self, status: ObjectiveStatus) -> "OrchestrationSession":
        return dataclasses.replace(self, status=status)

    def with_state(self, key: str, value: str) -> "OrchestrationSession":
        new_items = dict(self.state_items)
        new_items[key] = value
        return dataclasses.replace(self, state_items=frozenset(new_items.items()))

    def get_state(self, key: str, default: str = "") -> str:
        for k, v in self.state_items:
            if k == key:
                return v
        return default


@dataclass(frozen=True)
class OrchestrationResult:
    """Immutable result of a completed orchestration."""
    result_id:       str
    session_id:      str
    objective:       str
    status:          ObjectiveStatus
    output:          Optional[str]
    error_message:   Optional[str]
    steps_completed: int
    steps_failed:    int
    started_at:      float
    completed_at:    float

    @property
    def duration_ms(self) -> float:
        return (self.completed_at - self.started_at) * 1000.0

    @property
    def is_successful(self) -> bool:
        return self.status == ObjectiveStatus.COMPLETED

    @classmethod
    def success(
        cls,
        session_id:      str,
        objective:       str,
        started_at:      float,
        output:          Optional[str] = None,
        steps_completed: int = 0,
    ) -> "OrchestrationResult":
        return cls(
            result_id        = str(uuid.uuid4()),
            session_id       = session_id,
            objective        = objective,
            status           = ObjectiveStatus.COMPLETED,
            output           = output,
            error_message    = None,
            steps_completed  = steps_completed,
            steps_failed     = 0,
            started_at       = started_at,
            completed_at     = time.time(),
        )

    @classmethod
    def failure(
        cls,
        session_id:      str,
        objective:       str,
        started_at:      float,
        error_message:   str,
        steps_completed: int = 0,
        steps_failed:    int = 1,
    ) -> "OrchestrationResult":
        return cls(
            result_id        = str(uuid.uuid4()),
            session_id       = session_id,
            objective        = objective,
            status           = ObjectiveStatus.FAILED,
            output           = None,
            error_message    = error_message,
            steps_completed  = steps_completed,
            steps_failed     = steps_failed,
            started_at       = started_at,
            completed_at     = time.time(),
        )

    @classmethod
    def cancelled(
        cls,
        session_id: str,
        objective:  str,
        started_at: float,
    ) -> "OrchestrationResult":
        return cls(
            result_id        = str(uuid.uuid4()),
            session_id       = session_id,
            objective        = objective,
            status           = ObjectiveStatus.CANCELLED,
            output           = None,
            error_message    = "Cancelled",
            steps_completed  = 0,
            steps_failed     = 0,
            started_at       = started_at,
            completed_at     = time.time(),
        )
