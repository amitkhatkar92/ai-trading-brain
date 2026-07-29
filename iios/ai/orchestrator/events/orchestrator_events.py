"""
orchestrator_events.py -- iios.ai.orchestrator.events
=======================================================
Immutable event types for the A10 Enterprise AI Orchestrator.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class OrchestratorEventType(str, Enum):
    """All event types emitted by the orchestrator platform."""
    OBJECTIVE_RECEIVED  = "objective_received"
    PLAN_GENERATED      = "plan_generated"
    PLAN_REPLANNED      = "plan_replanned"
    WORKFLOW_REGISTERED = "workflow_registered"
    WORKFLOW_STARTED    = "workflow_started"
    WORKFLOW_PAUSED     = "workflow_paused"
    WORKFLOW_RESUMED    = "workflow_resumed"
    WORKFLOW_COMPLETED  = "workflow_completed"
    WORKFLOW_FAILED     = "workflow_failed"
    WORKFLOW_CANCELLED  = "workflow_cancelled"
    TASK_SCHEDULED      = "task_scheduled"
    TASK_STARTED        = "task_started"
    TASK_COMPLETED      = "task_completed"
    TASK_FAILED         = "task_failed"
    TASK_CANCELLED      = "task_cancelled"
    AGENT_ALLOCATED     = "agent_allocated"
    AGENT_RELEASED      = "agent_released"
    RESOURCE_RESERVED   = "resource_reserved"
    RESOURCE_RELEASED   = "resource_released"
    RECOVERY_STARTED    = "recovery_started"
    RECOVERY_COMPLETED  = "recovery_completed"
    RECOVERY_FAILED     = "recovery_failed"
    SESSION_STARTED     = "session_started"
    SESSION_COMPLETED   = "session_completed"
    SESSION_CANCELLED   = "session_cancelled"


@dataclass(frozen=True)
class OrchestratorEvent:
    """Immutable base orchestrator event."""
    event_id:    str
    event_type:  OrchestratorEventType
    source:      str
    occurred_at: float


# ── Session ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ObjectiveReceivedEvent(OrchestratorEvent):
    session_id: str
    objective:  str

    @classmethod
    def create(cls, source: str, session_id: str, objective: str) -> "ObjectiveReceivedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = OrchestratorEventType.OBJECTIVE_RECEIVED,
            source      = source,
            occurred_at = time.time(),
            session_id  = session_id,
            objective   = objective,
        )


@dataclass(frozen=True)
class PlanGeneratedEvent(OrchestratorEvent):
    session_id: str
    plan_id:    str
    step_count: int

    @classmethod
    def create(cls, source: str, session_id: str, plan_id: str, step_count: int) -> "PlanGeneratedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = OrchestratorEventType.PLAN_GENERATED,
            source      = source,
            occurred_at = time.time(),
            session_id  = session_id,
            plan_id     = plan_id,
            step_count  = step_count,
        )


@dataclass(frozen=True)
class PlanReplannedEvent(OrchestratorEvent):
    session_id:     str
    new_plan_id:    str
    failed_step_id: str

    @classmethod
    def create(cls, source: str, session_id: str, new_plan_id: str, failed_step_id: str) -> "PlanReplannedEvent":
        return cls(
            event_id       = str(uuid.uuid4()),
            event_type     = OrchestratorEventType.PLAN_REPLANNED,
            source         = source,
            occurred_at    = time.time(),
            session_id     = session_id,
            new_plan_id    = new_plan_id,
            failed_step_id = failed_step_id,
        )


@dataclass(frozen=True)
class SessionStartedEvent(OrchestratorEvent):
    session_id:   str
    principal_id: str

    @classmethod
    def create(cls, source: str, session_id: str, principal_id: str) -> "SessionStartedEvent":
        return cls(
            event_id     = str(uuid.uuid4()),
            event_type   = OrchestratorEventType.SESSION_STARTED,
            source       = source,
            occurred_at  = time.time(),
            session_id   = session_id,
            principal_id = principal_id,
        )


@dataclass(frozen=True)
class SessionCompletedEvent(OrchestratorEvent):
    session_id:  str
    duration_ms: float

    @classmethod
    def create(cls, source: str, session_id: str, duration_ms: float) -> "SessionCompletedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = OrchestratorEventType.SESSION_COMPLETED,
            source      = source,
            occurred_at = time.time(),
            session_id  = session_id,
            duration_ms = duration_ms,
        )


@dataclass(frozen=True)
class SessionCancelledEvent(OrchestratorEvent):
    session_id: str

    @classmethod
    def create(cls, source: str, session_id: str) -> "SessionCancelledEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = OrchestratorEventType.SESSION_CANCELLED,
            source      = source,
            occurred_at = time.time(),
            session_id  = session_id,
        )


# ── Workflow ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class WorkflowRegisteredEvent(OrchestratorEvent):
    workflow_id:   str
    workflow_name: str

    @classmethod
    def create(cls, source: str, workflow_id: str, workflow_name: str) -> "WorkflowRegisteredEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = OrchestratorEventType.WORKFLOW_REGISTERED,
            source        = source,
            occurred_at   = time.time(),
            workflow_id   = workflow_id,
            workflow_name = workflow_name,
        )


@dataclass(frozen=True)
class WorkflowStartedEvent(OrchestratorEvent):
    workflow_id: str
    instance_id: str

    @classmethod
    def create(cls, source: str, workflow_id: str, instance_id: str) -> "WorkflowStartedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = OrchestratorEventType.WORKFLOW_STARTED,
            source      = source,
            occurred_at = time.time(),
            workflow_id = workflow_id,
            instance_id = instance_id,
        )


@dataclass(frozen=True)
class WorkflowCompletedEvent(OrchestratorEvent):
    instance_id: str
    duration_ms: float

    @classmethod
    def create(cls, source: str, instance_id: str, duration_ms: float) -> "WorkflowCompletedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = OrchestratorEventType.WORKFLOW_COMPLETED,
            source      = source,
            occurred_at = time.time(),
            instance_id = instance_id,
            duration_ms = duration_ms,
        )


@dataclass(frozen=True)
class WorkflowFailedEvent(OrchestratorEvent):
    instance_id:   str
    error_message: str

    @classmethod
    def create(cls, source: str, instance_id: str, error_message: str) -> "WorkflowFailedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = OrchestratorEventType.WORKFLOW_FAILED,
            source        = source,
            occurred_at   = time.time(),
            instance_id   = instance_id,
            error_message = error_message,
        )


@dataclass(frozen=True)
class WorkflowCancelledEvent(OrchestratorEvent):
    instance_id: str

    @classmethod
    def create(cls, source: str, instance_id: str) -> "WorkflowCancelledEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = OrchestratorEventType.WORKFLOW_CANCELLED,
            source      = source,
            occurred_at = time.time(),
            instance_id = instance_id,
        )


# ── Task ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TaskScheduledEvent(OrchestratorEvent):
    task_id:   str
    task_name: str
    priority:  int

    @classmethod
    def create(cls, source: str, task_id: str, task_name: str, priority: int) -> "TaskScheduledEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = OrchestratorEventType.TASK_SCHEDULED,
            source      = source,
            occurred_at = time.time(),
            task_id     = task_id,
            task_name   = task_name,
            priority    = priority,
        )


@dataclass(frozen=True)
class TaskCompletedEvent(OrchestratorEvent):
    task_id:     str
    duration_ms: float

    @classmethod
    def create(cls, source: str, task_id: str, duration_ms: float) -> "TaskCompletedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = OrchestratorEventType.TASK_COMPLETED,
            source      = source,
            occurred_at = time.time(),
            task_id     = task_id,
            duration_ms = duration_ms,
        )


@dataclass(frozen=True)
class TaskFailedEvent(OrchestratorEvent):
    task_id:       str
    error_message: str

    @classmethod
    def create(cls, source: str, task_id: str, error_message: str) -> "TaskFailedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = OrchestratorEventType.TASK_FAILED,
            source        = source,
            occurred_at   = time.time(),
            task_id       = task_id,
            error_message = error_message,
        )


# ── Recovery ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RecoveryStartedEvent(OrchestratorEvent):
    session_id:    str
    failed_action: str
    strategy:      str

    @classmethod
    def create(cls, source: str, session_id: str, failed_action: str, strategy: str) -> "RecoveryStartedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = OrchestratorEventType.RECOVERY_STARTED,
            source        = source,
            occurred_at   = time.time(),
            session_id    = session_id,
            failed_action = failed_action,
            strategy      = strategy,
        )


@dataclass(frozen=True)
class RecoveryCompletedEvent(OrchestratorEvent):
    session_id: str
    success:    bool

    @classmethod
    def create(cls, source: str, session_id: str, success: bool) -> "RecoveryCompletedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = OrchestratorEventType.RECOVERY_COMPLETED,
            source      = source,
            occurred_at = time.time(),
            session_id  = session_id,
            success     = success,
        )


# ── Resource ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class AgentAllocatedEvent(OrchestratorEvent):
    agent_id:      str
    capability_id: str

    @classmethod
    def create(cls, source: str, agent_id: str, capability_id: str) -> "AgentAllocatedEvent":
        return cls(
            event_id      = str(uuid.uuid4()),
            event_type    = OrchestratorEventType.AGENT_ALLOCATED,
            source        = source,
            occurred_at   = time.time(),
            agent_id      = agent_id,
            capability_id = capability_id,
        )


@dataclass(frozen=True)
class ResourceReservedEvent(OrchestratorEvent):
    reservation_id: str
    capability_id:  str

    @classmethod
    def create(cls, source: str, reservation_id: str, capability_id: str) -> "ResourceReservedEvent":
        return cls(
            event_id        = str(uuid.uuid4()),
            event_type      = OrchestratorEventType.RESOURCE_RESERVED,
            source          = source,
            occurred_at     = time.time(),
            reservation_id  = reservation_id,
            capability_id   = capability_id,
        )
