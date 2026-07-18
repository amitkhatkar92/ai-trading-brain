"""iios/execution/recovery/lifecycle/constants.py
==================================================
Constants and enumerations for the C7 Execution Recovery Lifecycle.

C7 Execution Recovery & Resilience — Phase 1, Module 1
"""
from __future__ import annotations

from enum import Enum
from typing import FrozenSet


# ── System identifiers ────────────────────────────────────────────────────────

LIFECYCLE_SYSTEM_ID = "iios:execution:recovery:lifecycle"
REGISTRY_SYSTEM_ID  = "iios:execution:recovery:lifecycle:registry"
FACTORY_SYSTEM_ID   = "iios:execution:recovery:lifecycle:factory"

# ── Versioning ────────────────────────────────────────────────────────────────

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Default limits ────────────────────────────────────────────────────────────

DEFAULT_MAX_SESSIONS    = 5_000
DEFAULT_MAX_HISTORY     = 1_000
DEFAULT_MAX_TRANSITIONS = 50_000

# ── Actor constants ───────────────────────────────────────────────────────────

ACTOR_LIFECYCLE = "iios:execution:recovery:lifecycle"
ACTOR_OPERATOR  = "operator"
ACTOR_SYSTEM    = "iios:system"
ACTOR_POLICY    = "iios:recovery:policy"
ACTOR_WATCHDOG  = "iios:recovery:watchdog"


# ── Recovery state enumeration ────────────────────────────────────────────────

class RecoveryState(str, Enum):
    """
    All possible states for an execution recovery session.

    Lifecycle progression:
        CREATED → INITIALIZING → DETECTING → ASSESSING → READY
                → RECOVERING → VERIFYING → COMPLETED
        Any active state → FAILED / ABORTED
        Terminal states → ARCHIVED
    """

    CREATED      = "created"
    INITIALIZING = "initializing"
    DETECTING    = "detecting"
    ASSESSING    = "assessing"
    READY        = "ready"
    RECOVERING   = "recovering"
    VERIFYING    = "verifying"
    COMPLETED    = "completed"
    FAILED       = "failed"
    ABORTED      = "aborted"
    ARCHIVED     = "archived"


# ── State machine ─────────────────────────────────────────────────────────────

#: Exhaustive map of all allowed forward and backward edges.
VALID_TRANSITIONS: dict[RecoveryState, FrozenSet[RecoveryState]] = {
    RecoveryState.CREATED: frozenset({
        RecoveryState.INITIALIZING,
    }),
    RecoveryState.INITIALIZING: frozenset({
        RecoveryState.DETECTING,
        RecoveryState.FAILED,
        RecoveryState.ABORTED,
    }),
    RecoveryState.DETECTING: frozenset({
        RecoveryState.ASSESSING,
        RecoveryState.FAILED,
        RecoveryState.ABORTED,
    }),
    RecoveryState.ASSESSING: frozenset({
        RecoveryState.READY,
        RecoveryState.FAILED,
        RecoveryState.ABORTED,
    }),
    RecoveryState.READY: frozenset({
        RecoveryState.RECOVERING,
        RecoveryState.FAILED,
        RecoveryState.ABORTED,
    }),
    RecoveryState.RECOVERING: frozenset({
        RecoveryState.VERIFYING,
        RecoveryState.FAILED,
        RecoveryState.ABORTED,
    }),
    RecoveryState.VERIFYING: frozenset({
        RecoveryState.COMPLETED,
        RecoveryState.RECOVERING,   # retry loop
        RecoveryState.FAILED,
        RecoveryState.ABORTED,
    }),
    RecoveryState.COMPLETED: frozenset({
        RecoveryState.ARCHIVED,
    }),
    RecoveryState.FAILED: frozenset({
        RecoveryState.ARCHIVED,
    }),
    RecoveryState.ABORTED: frozenset({
        RecoveryState.ARCHIVED,
    }),
    RecoveryState.ARCHIVED: frozenset(),   # terminal
}

#: States that represent an in-flight session.
ACTIVE_STATES: FrozenSet[RecoveryState] = frozenset({
    RecoveryState.INITIALIZING,
    RecoveryState.DETECTING,
    RecoveryState.ASSESSING,
    RecoveryState.READY,
    RecoveryState.RECOVERING,
    RecoveryState.VERIFYING,
})

#: States where the session has ended (outcome determined).
TERMINAL_STATES: FrozenSet[RecoveryState] = frozenset({
    RecoveryState.COMPLETED,
    RecoveryState.FAILED,
    RecoveryState.ABORTED,
    RecoveryState.ARCHIVED,
})

#: States where no further transitions are allowed.
IMMUTABLE_STATES: FrozenSet[RecoveryState] = frozenset({
    RecoveryState.ARCHIVED,
})

#: States that represent a successful outcome.
SUCCESS_STATES: FrozenSet[RecoveryState] = frozenset({
    RecoveryState.COMPLETED,
    RecoveryState.ARCHIVED,
})


# ── Recovery trigger ──────────────────────────────────────────────────────────

class RecoveryTrigger(str, Enum):
    """Classifies what triggered a recovery session."""

    MANUAL         = "manual"          # operator-initiated
    AUTOMATIC      = "automatic"       # system rule matched
    POLICY         = "policy"          # policy engine decision
    HEALTH_CHECK   = "health_check"    # health monitor detection
    WATCHDOG       = "watchdog"        # watchdog timer expired
    CIRCUIT_BREAKER= "circuit_breaker" # circuit breaker tripped
    EXTERNAL       = "external"        # external signal


# ── Event types ───────────────────────────────────────────────────────────────

class RecoveryEventType(str, Enum):
    """Types of lifecycle events emitted by RecoveryLifecycle."""

    RECOVERY_CREATED     = "recovery_created"
    RECOVERY_INITIALIZED = "recovery_initialized"
    RECOVERY_DETECTING   = "recovery_detecting"
    RECOVERY_ASSESSING   = "recovery_assessing"
    RECOVERY_READY       = "recovery_ready"
    RECOVERY_STARTED     = "recovery_started"
    RECOVERY_VERIFYING   = "recovery_verifying"
    RECOVERY_COMPLETED   = "recovery_completed"
    RECOVERY_FAILED      = "recovery_failed"
    RECOVERY_ABORTED     = "recovery_aborted"
    RECOVERY_ARCHIVED    = "recovery_archived"
