"""
agent_events.py -- iios.ai.agent_framework.events
===================================================
Immutable event types for the A5 Agent Framework.

All events are frozen dataclasses.  Each has a ``create()`` factory that
sets ``event_id`` and ``occurred_at`` automatically.

Event types
-----------
AgentRegistered      — agent joined the registry
AgentStarted         — agent activated
AgentStopped         — agent deactivated
AgentSuspended       — agent temporarily suspended
AgentResumed         — agent resumed from suspension
AgentHealthChanged   — health status transitioned
TaskAssigned         — task dispatched to an agent
TaskStarted          — agent began executing the task
TaskCompleted        — task finished successfully
TaskFailed           — task execution failed
CapabilityAdded      — new capability registered to an agent
PermissionGranted    — new permission granted to an agent
PermissionRevoked    — permission removed from an agent

A5 AI Agent Framework — Phase 3, Module 5
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AgentEventType(str, Enum):
    """All agent event identifiers.  Values are persisted — do not rename."""

    AGENT_REGISTERED    = "agent_registered"
    AGENT_STARTED       = "agent_started"
    AGENT_STOPPED       = "agent_stopped"
    AGENT_SUSPENDED     = "agent_suspended"
    AGENT_RESUMED       = "agent_resumed"
    AGENT_HEALTH_CHANGED = "agent_health_changed"
    TASK_ASSIGNED       = "task_assigned"
    TASK_STARTED        = "task_started"
    TASK_COMPLETED      = "task_completed"
    TASK_FAILED         = "task_failed"
    CAPABILITY_ADDED    = "capability_added"
    PERMISSION_GRANTED  = "permission_granted"
    PERMISSION_REVOKED  = "permission_revoked"


# ---------------------------------------------------------------------------
# Base event
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentEvent:
    """Base class for all A5 agent events."""

    event_id:   str
    event_type: AgentEventType
    agent_id:   str
    occurred_at: float


# ---------------------------------------------------------------------------
# Agent lifecycle events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentRegisteredEvent(AgentEvent):
    agent_name: str
    agent_type: str

    @classmethod
    def create(
        cls,
        agent_id:   str,
        agent_name: str,
        agent_type: str,
    ) -> "AgentRegisteredEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = AgentEventType.AGENT_REGISTERED,
            agent_id    = agent_id,
            occurred_at = time.time(),
            agent_name  = agent_name,
            agent_type  = agent_type,
        )


@dataclass(frozen=True)
class AgentStartedEvent(AgentEvent):
    @classmethod
    def create(cls, agent_id: str) -> "AgentStartedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = AgentEventType.AGENT_STARTED,
            agent_id    = agent_id,
            occurred_at = time.time(),
        )


@dataclass(frozen=True)
class AgentStoppedEvent(AgentEvent):
    @classmethod
    def create(cls, agent_id: str) -> "AgentStoppedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = AgentEventType.AGENT_STOPPED,
            agent_id    = agent_id,
            occurred_at = time.time(),
        )


@dataclass(frozen=True)
class AgentSuspendedEvent(AgentEvent):
    @classmethod
    def create(cls, agent_id: str) -> "AgentSuspendedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = AgentEventType.AGENT_SUSPENDED,
            agent_id    = agent_id,
            occurred_at = time.time(),
        )


@dataclass(frozen=True)
class AgentResumedEvent(AgentEvent):
    @classmethod
    def create(cls, agent_id: str) -> "AgentResumedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = AgentEventType.AGENT_RESUMED,
            agent_id    = agent_id,
            occurred_at = time.time(),
        )


@dataclass(frozen=True)
class AgentHealthChangedEvent(AgentEvent):
    previous_status: str
    current_status:  str
    message:         str

    @classmethod
    def create(
        cls,
        agent_id:        str,
        previous_status: str,
        current_status:  str,
        message:         str = "",
    ) -> "AgentHealthChangedEvent":
        return cls(
            event_id         = str(uuid.uuid4()),
            event_type       = AgentEventType.AGENT_HEALTH_CHANGED,
            agent_id         = agent_id,
            occurred_at      = time.time(),
            previous_status  = previous_status,
            current_status   = current_status,
            message          = message,
        )


# ---------------------------------------------------------------------------
# Task events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TaskAssignedEvent(AgentEvent):
    task_id:   str
    task_type: str
    priority:  str

    @classmethod
    def create(
        cls,
        agent_id:  str,
        task_id:   str,
        task_type: str,
        priority:  str,
    ) -> "TaskAssignedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = AgentEventType.TASK_ASSIGNED,
            agent_id    = agent_id,
            occurred_at = time.time(),
            task_id     = task_id,
            task_type   = task_type,
            priority    = priority,
        )


@dataclass(frozen=True)
class TaskStartedEvent(AgentEvent):
    task_id: str

    @classmethod
    def create(cls, agent_id: str, task_id: str) -> "TaskStartedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = AgentEventType.TASK_STARTED,
            agent_id    = agent_id,
            occurred_at = time.time(),
            task_id     = task_id,
        )


@dataclass(frozen=True)
class TaskCompletedEvent(AgentEvent):
    task_id:      str
    execution_ms: float

    @classmethod
    def create(
        cls,
        agent_id:     str,
        task_id:      str,
        execution_ms: float,
    ) -> "TaskCompletedEvent":
        return cls(
            event_id     = str(uuid.uuid4()),
            event_type   = AgentEventType.TASK_COMPLETED,
            agent_id     = agent_id,
            occurred_at  = time.time(),
            task_id      = task_id,
            execution_ms = execution_ms,
        )


@dataclass(frozen=True)
class TaskFailedEvent(AgentEvent):
    task_id:      str
    error_message: str

    @classmethod
    def create(
        cls,
        agent_id:      str,
        task_id:       str,
        error_message: str = "",
    ) -> "TaskFailedEvent":
        return cls(
            event_id       = str(uuid.uuid4()),
            event_type     = AgentEventType.TASK_FAILED,
            agent_id       = agent_id,
            occurred_at    = time.time(),
            task_id        = task_id,
            error_message  = error_message,
        )


# ---------------------------------------------------------------------------
# Capability / permission events
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CapabilityAddedEvent(AgentEvent):
    capability_type: str
    capability_name: str

    @classmethod
    def create(
        cls,
        agent_id:        str,
        capability_type: str,
        capability_name: str,
    ) -> "CapabilityAddedEvent":
        return cls(
            event_id         = str(uuid.uuid4()),
            event_type       = AgentEventType.CAPABILITY_ADDED,
            agent_id         = agent_id,
            occurred_at      = time.time(),
            capability_type  = capability_type,
            capability_name  = capability_name,
        )


@dataclass(frozen=True)
class PermissionGrantedEvent(AgentEvent):
    resource:         str
    permission_level: str

    @classmethod
    def create(
        cls,
        agent_id:         str,
        resource:         str,
        permission_level: str,
    ) -> "PermissionGrantedEvent":
        return cls(
            event_id          = str(uuid.uuid4()),
            event_type        = AgentEventType.PERMISSION_GRANTED,
            agent_id          = agent_id,
            occurred_at       = time.time(),
            resource          = resource,
            permission_level  = permission_level,
        )


@dataclass(frozen=True)
class PermissionRevokedEvent(AgentEvent):
    resource: str

    @classmethod
    def create(cls, agent_id: str, resource: str) -> "PermissionRevokedEvent":
        return cls(
            event_id    = str(uuid.uuid4()),
            event_type  = AgentEventType.PERMISSION_REVOKED,
            agent_id    = agent_id,
            occurred_at = time.time(),
            resource    = resource,
        )
