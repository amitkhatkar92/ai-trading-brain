"""
constants.py — iios.supervisor.lifecycle
==========================================
Enumerations, state machine, identifiers, and numeric defaults for the
Institutional AI Supervisor Lifecycle subsystem.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 1
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
LIFECYCLE_SYSTEM_ID: str = "iios:supervisor:lifecycle"
REGISTRY_SYSTEM_ID:  str = "iios:supervisor:lifecycle:registry"
FACTORY_SYSTEM_ID:   str = "iios:supervisor:lifecycle:factory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_SESSIONS:    int = 5_000
DEFAULT_MAX_ARCHIVED:    int = 10_000
DEFAULT_MAX_HISTORY:     int = 1_000
DEFAULT_MAX_TRANSITIONS: int = 50_000

# ---------------------------------------------------------------------------
# Actor constants
# ---------------------------------------------------------------------------
ACTOR_LIFECYCLE:  str = "iios:supervisor:lifecycle"
ACTOR_OPERATOR:   str = "operator"
ACTOR_SYSTEM:     str = "iios:system"
ACTOR_SUPERVISOR: str = "iios:supervisor:engine"
ACTOR_MONITOR:    str = "iios:supervisor:monitor"


# ---------------------------------------------------------------------------
# SupervisorState — twelve lifecycle states
# ---------------------------------------------------------------------------
class SupervisorState(str, Enum):
    """
    All possible lifecycle states for a supervisor session.

    Lifecycle progression (happy path)::

        CREATED → INITIALIZING → DISCOVERING → VALIDATING → READY
                → SUPERVISING → MONITORING → COMPLETED → ARCHIVED

    Pause / resume::

        any active state → PAUSED → RESUMING → (prior active state)

    Failure::

        any non-terminal state → FAILED → ARCHIVED
    """
    CREATED      = "created"
    INITIALIZING = "initializing"
    DISCOVERING  = "discovering"
    VALIDATING   = "validating"
    READY        = "ready"
    SUPERVISING  = "supervising"
    MONITORING   = "monitoring"
    PAUSED       = "paused"
    RESUMING     = "resuming"
    COMPLETED    = "completed"
    FAILED       = "failed"
    ARCHIVED     = "archived"


# ---------------------------------------------------------------------------
# SupervisorType
# ---------------------------------------------------------------------------
class SupervisorType(str, Enum):
    """Classification of the autonomous supervisor."""
    PROCESS     = "process"
    RISK        = "risk"
    EXECUTION   = "execution"
    PORTFOLIO   = "portfolio"
    COMPLIANCE  = "compliance"
    GOVERNANCE  = "governance"
    ANALYTICS   = "analytics"
    INTEGRATION = "integration"
    CUSTOM      = "custom"


# ---------------------------------------------------------------------------
# SupervisorScope
# ---------------------------------------------------------------------------
class SupervisorScope(str, Enum):
    """Institutional scope of the supervisor session."""
    ENTERPRISE = "enterprise"
    DEPARTMENT = "department"
    SYSTEM     = "system"
    SUBSYSTEM  = "subsystem"
    COMPONENT  = "component"
    CUSTOM     = "custom"


# ---------------------------------------------------------------------------
# SupervisorPriority
# ---------------------------------------------------------------------------
class SupervisorPriority(str, Enum):
    """Priority level of the supervisor session."""
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


# ---------------------------------------------------------------------------
# SupervisorEventType — ten event types
# ---------------------------------------------------------------------------
class SupervisorEventType(str, Enum):
    """All event types emitted by the supervisor lifecycle subsystem."""
    SUPERVISOR_CREATED            = "supervisor_created"
    SUPERVISOR_INITIALIZED        = "supervisor_initialized"
    SUPERVISOR_VALIDATED          = "supervisor_validated"
    SUPERVISOR_STARTED            = "supervisor_started"
    SUPERVISOR_MONITORING_STARTED = "supervisor_monitoring_started"
    SUPERVISOR_PAUSED             = "supervisor_paused"
    SUPERVISOR_RESUMED            = "supervisor_resumed"
    SUPERVISOR_COMPLETED          = "supervisor_completed"
    SUPERVISOR_FAILED             = "supervisor_failed"
    SUPERVISOR_ARCHIVED           = "supervisor_archived"


# ---------------------------------------------------------------------------
# SupervisorValidationCode
# ---------------------------------------------------------------------------
class SupervisorValidationCode(str, Enum):
    """Validation check identifiers used in validation results."""
    IDENTIFIER_CONSISTENCY = "identifier_consistency"
    LIFECYCLE_CONSISTENCY  = "lifecycle_consistency"
    TRANSITION_VALIDITY    = "transition_validity"
    TIMESTAMP_CONSISTENCY  = "timestamp_consistency"
    HISTORY_INTEGRITY      = "history_integrity"


# ---------------------------------------------------------------------------
# State machine — strict institutional transitions
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: Dict[SupervisorState, FrozenSet[SupervisorState]] = {
    SupervisorState.CREATED: frozenset({
        SupervisorState.INITIALIZING,
        SupervisorState.FAILED,
    }),
    SupervisorState.INITIALIZING: frozenset({
        SupervisorState.DISCOVERING,
        SupervisorState.FAILED,
    }),
    SupervisorState.DISCOVERING: frozenset({
        SupervisorState.VALIDATING,
        SupervisorState.FAILED,
    }),
    SupervisorState.VALIDATING: frozenset({
        SupervisorState.READY,
        SupervisorState.DISCOVERING,  # re-discover when validation is insufficient
        SupervisorState.FAILED,
    }),
    SupervisorState.READY: frozenset({
        SupervisorState.SUPERVISING,
        SupervisorState.PAUSED,
        SupervisorState.FAILED,
    }),
    SupervisorState.SUPERVISING: frozenset({
        SupervisorState.MONITORING,
        SupervisorState.PAUSED,
        SupervisorState.COMPLETED,
        SupervisorState.FAILED,
    }),
    SupervisorState.MONITORING: frozenset({
        SupervisorState.SUPERVISING,  # re-supervise on trigger
        SupervisorState.PAUSED,
        SupervisorState.COMPLETED,
        SupervisorState.FAILED,
    }),
    SupervisorState.PAUSED: frozenset({
        SupervisorState.RESUMING,
        SupervisorState.FAILED,
    }),
    SupervisorState.RESUMING: frozenset({
        SupervisorState.SUPERVISING,
        SupervisorState.MONITORING,
        SupervisorState.READY,
        SupervisorState.FAILED,
    }),
    SupervisorState.COMPLETED: frozenset({
        SupervisorState.ARCHIVED,
    }),
    SupervisorState.FAILED: frozenset({
        SupervisorState.ARCHIVED,
    }),
    SupervisorState.ARCHIVED: frozenset(),  # terminal + immutable
}

# ---------------------------------------------------------------------------
# Semantic state sets
# ---------------------------------------------------------------------------

#: States in which a supervisor session is actively being managed
ACTIVE_STATES: FrozenSet[SupervisorState] = frozenset({
    SupervisorState.INITIALIZING,
    SupervisorState.DISCOVERING,
    SupervisorState.VALIDATING,
    SupervisorState.READY,
    SupervisorState.SUPERVISING,
    SupervisorState.MONITORING,
    SupervisorState.PAUSED,
    SupervisorState.RESUMING,
})

#: Terminal states — no further transitions (except to ARCHIVED)
TERMINAL_STATES: FrozenSet[SupervisorState] = frozenset({
    SupervisorState.COMPLETED,
    SupervisorState.FAILED,
    SupervisorState.ARCHIVED,
})

#: States from which the session cannot be modified
IMMUTABLE_STATES: FrozenSet[SupervisorState] = frozenset({
    SupervisorState.ARCHIVED,
})

#: Successful terminal states
SUCCESS_STATES: FrozenSet[SupervisorState] = frozenset({
    SupervisorState.COMPLETED,
    SupervisorState.ARCHIVED,
})
