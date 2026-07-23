"""
constants.py — iios.supervisor.engine
=======================================
Enumerations, state machine, identifiers, and numeric defaults for the
Institutional AI Supervisor Engine subsystem.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
ENGINE_SYSTEM_ID:     str = "iios:supervisor:engine"
SCHEDULER_SYSTEM_ID:  str = "iios:supervisor:engine:scheduler"
DISPATCHER_SYSTEM_ID: str = "iios:supervisor:engine:dispatcher"
REGISTRY_SYSTEM_ID:   str = "iios:supervisor:engine:registry"
FACTORY_SYSTEM_ID:    str = "iios:supervisor:engine:factory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_ENGINE:     str = "iios:supervisor:engine"
ACTOR_SCHEDULER:  str = "iios:supervisor:engine:scheduler"
ACTOR_DISPATCHER: str = "iios:supervisor:engine:dispatcher"
ACTOR_OPERATOR:   str = "operator"
ACTOR_SYSTEM:     str = "iios:system"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_CONCURRENT_SESSIONS: int   = 200
DEFAULT_MAX_PIPELINES:           int   = 5_000
DEFAULT_MAX_HISTORY:             int   = 1_000
DEFAULT_MAX_SCHEDULER_QUEUE:     int   = 10_000
DEFAULT_MAX_ARCHIVED_PIPELINES:  int   = 10_000

# ---------------------------------------------------------------------------
# Timeout defaults (seconds)
# ---------------------------------------------------------------------------
DEFAULT_COLLECT_TIMEOUT_S:  float = 30.0
DEFAULT_DISPATCH_TIMEOUT_S: float = 60.0
DEFAULT_PUBLISH_TIMEOUT_S:  float = 30.0


# ---------------------------------------------------------------------------
# EngineState — supervisor engine processing states
# ---------------------------------------------------------------------------
class EngineState(str, Enum):
    """
    States of a supervisor engine processing cycle.

    Lifecycle progression (happy path)::

        IDLE → INITIALIZING → DISCOVERING → COLLECTING → VALIDATING
             → DISPATCHING → SUPERVISING → MONITORING → PUBLISHING
             → COMPLETED → IDLE

    Failure::

        any active state → FAILED → IDLE

    Stop::

        any state → STOPPED (terminal)
    """
    IDLE         = "idle"
    INITIALIZING = "initializing"
    DISCOVERING  = "discovering"
    COLLECTING   = "collecting"
    VALIDATING   = "validating"
    DISPATCHING  = "dispatching"
    SUPERVISING  = "supervising"
    MONITORING   = "monitoring"
    PUBLISHING   = "publishing"
    COMPLETED    = "completed"
    FAILED       = "failed"
    STOPPED      = "stopped"


# ---------------------------------------------------------------------------
# Valid engine-state transitions
# ---------------------------------------------------------------------------
VALID_ENGINE_TRANSITIONS: Dict[EngineState, FrozenSet[EngineState]] = {
    EngineState.IDLE: frozenset({
        EngineState.INITIALIZING,
        EngineState.STOPPED,
    }),
    EngineState.INITIALIZING: frozenset({
        EngineState.DISCOVERING,
        EngineState.FAILED,
    }),
    EngineState.DISCOVERING: frozenset({
        EngineState.COLLECTING,
        EngineState.FAILED,
    }),
    EngineState.COLLECTING: frozenset({
        EngineState.VALIDATING,
        EngineState.FAILED,
    }),
    EngineState.VALIDATING: frozenset({
        EngineState.DISPATCHING,
        EngineState.FAILED,
    }),
    EngineState.DISPATCHING: frozenset({
        EngineState.SUPERVISING,
        EngineState.MONITORING,
        EngineState.PUBLISHING,
        EngineState.FAILED,
    }),
    EngineState.SUPERVISING: frozenset({
        EngineState.MONITORING,
        EngineState.PUBLISHING,
        EngineState.FAILED,
    }),
    EngineState.MONITORING: frozenset({
        EngineState.PUBLISHING,
        EngineState.FAILED,
    }),
    EngineState.PUBLISHING: frozenset({
        EngineState.COMPLETED,
        EngineState.FAILED,
    }),
    EngineState.COMPLETED: frozenset({
        EngineState.IDLE,
    }),
    EngineState.FAILED: frozenset({
        EngineState.IDLE,
    }),
    EngineState.STOPPED: frozenset(),  # terminal
}

# Active (non-terminal, non-idle) processing states
ACTIVE_ENGINE_STATES: FrozenSet[EngineState] = frozenset({
    EngineState.INITIALIZING,
    EngineState.DISCOVERING,
    EngineState.COLLECTING,
    EngineState.VALIDATING,
    EngineState.DISPATCHING,
    EngineState.SUPERVISING,
    EngineState.MONITORING,
    EngineState.PUBLISHING,
})

TERMINAL_ENGINE_STATES: FrozenSet[EngineState] = frozenset({
    EngineState.COMPLETED,
    EngineState.FAILED,
    EngineState.STOPPED,
})


# ---------------------------------------------------------------------------
# SupervisorWorkflowType — supported supervision workflows
# ---------------------------------------------------------------------------
class SupervisorWorkflowType(str, Enum):
    """Supported supervisor workflow types."""
    ENTERPRISE_HEALTH_REVIEW      = "enterprise_health_review"
    SUBSYSTEM_SUPERVISION         = "subsystem_supervision"
    AUTONOMOUS_SESSION_MANAGEMENT = "autonomous_session_management"
    PLATFORM_STATUS_REVIEW        = "platform_status_review"
    GOVERNANCE_PREPARATION        = "governance_preparation"
    SNAPSHOT_AGGREGATION          = "snapshot_aggregation"
    OPERATIONAL_MONITORING        = "operational_monitoring"
    PERIODIC_SUPERVISION          = "periodic_supervision"


# ---------------------------------------------------------------------------
# SubsystemType — supervised subsystems
# ---------------------------------------------------------------------------
class SubsystemType(str, Enum):
    """Classification of supervised IIOS subsystems."""
    EXECUTION_INTELLIGENCE  = "execution_intelligence"
    EXECUTION_RECOVERY      = "execution_recovery"
    EXECUTION_ANALYTICS     = "execution_analytics"
    DECISION_INTELLIGENCE   = "decision_intelligence"
    PORTFOLIO_INTELLIGENCE  = "portfolio_intelligence"
    RISK_INTELLIGENCE       = "risk_intelligence"
    MARKET_INTELLIGENCE     = "market_intelligence"
    CUSTOM                  = "custom"


# ---------------------------------------------------------------------------
# SchedulerPriority
# ---------------------------------------------------------------------------
class SchedulerPriority(IntEnum):
    """Scheduling priority — lower integer = higher priority."""
    CRITICAL = 0
    HIGH     = 1
    NORMAL   = 2
    LOW      = 3
    BATCH    = 4


# ---------------------------------------------------------------------------
# ResponseStatus
# ---------------------------------------------------------------------------
class ResponseStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


# ---------------------------------------------------------------------------
# PipelineStatus
# ---------------------------------------------------------------------------
class PipelineStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# SupervisorEngineEventType — ten event types
# ---------------------------------------------------------------------------
class SupervisorEngineEventType(str, Enum):
    """Event types emitted by the Supervisor Engine."""
    SUPERVISOR_INITIALIZED        = "supervisor_initialized"
    SUPERVISOR_STARTED            = "supervisor_started"
    SUPERVISOR_COLLECTED          = "supervisor_collected"
    SUPERVISOR_VALIDATED          = "supervisor_validated"
    SUPERVISOR_DISPATCHED         = "supervisor_dispatched"
    SUPERVISOR_MONITORING_STARTED = "supervisor_monitoring_started"
    SUPERVISOR_PUBLISHED          = "supervisor_published"
    SUPERVISOR_COMPLETED          = "supervisor_completed"
    SUPERVISOR_FAILED             = "supervisor_failed"
    SUPERVISOR_STOPPED            = "supervisor_stopped"


# ---------------------------------------------------------------------------
# Workflow routing sets
# ---------------------------------------------------------------------------

# Workflows requiring full supervision pass (governance + autonomous)
SUPERVISION_WORKFLOWS: FrozenSet[SupervisorWorkflowType] = frozenset({
    SupervisorWorkflowType.ENTERPRISE_HEALTH_REVIEW,
    SupervisorWorkflowType.SUBSYSTEM_SUPERVISION,
    SupervisorWorkflowType.GOVERNANCE_PREPARATION,
    SupervisorWorkflowType.AUTONOMOUS_SESSION_MANAGEMENT,
})

# Workflows that are primarily monitoring (may skip supervision phase)
MONITORING_WORKFLOWS: FrozenSet[SupervisorWorkflowType] = frozenset({
    SupervisorWorkflowType.OPERATIONAL_MONITORING,
    SupervisorWorkflowType.PERIODIC_SUPERVISION,
    SupervisorWorkflowType.PLATFORM_STATUS_REVIEW,
    SupervisorWorkflowType.SNAPSHOT_AGGREGATION,
})
