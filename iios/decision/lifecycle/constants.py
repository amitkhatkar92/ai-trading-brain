"""
constants.py — iios.decision.lifecycle
=======================================
Enumerations, state machine, identifiers, and numeric defaults for the
Institutional Decision Lifecycle subsystem.

C9 Decision Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
LIFECYCLE_SYSTEM_ID: str = "iios:decision:lifecycle"
REGISTRY_SYSTEM_ID: str  = "iios:decision:lifecycle:registry"
FACTORY_SYSTEM_ID: str   = "iios:decision:lifecycle:factory"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION: str        = "1.0.0"
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
ACTOR_LIFECYCLE: str = "iios:decision:lifecycle"
ACTOR_OPERATOR:  str = "operator"
ACTOR_SYSTEM:    str = "iios:system"
ACTOR_ENGINE:    str = "iios:decision:engine"
ACTOR_SCHEDULER: str = "iios:decision:scheduler"


# ---------------------------------------------------------------------------
# DecisionState — the eleven lifecycle states
# ---------------------------------------------------------------------------
class DecisionState(str, Enum):
    """
    All possible lifecycle states for a decision session.

    Lifecycle progression (happy path)::

        CREATED → INITIALIZING → COLLECTING → EVALUATING → READY
                → ACTIVE → COMPLETED → ARCHIVED

    Pause / resume::

        any active state → PAUSED → RESUMING → (prior active state)

    Failure::

        any non-terminal state → FAILED → ARCHIVED
    """
    CREATED      = "created"
    INITIALIZING = "initializing"
    COLLECTING   = "collecting"
    EVALUATING   = "evaluating"
    READY        = "ready"
    ACTIVE       = "active"
    PAUSED       = "paused"
    RESUMING     = "resuming"
    COMPLETED    = "completed"
    FAILED       = "failed"
    ARCHIVED     = "archived"


# ---------------------------------------------------------------------------
# State machine — strict institutional transitions
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: Dict[DecisionState, FrozenSet[DecisionState]] = {
    DecisionState.CREATED: frozenset({
        DecisionState.INITIALIZING,
        DecisionState.FAILED,
    }),
    DecisionState.INITIALIZING: frozenset({
        DecisionState.COLLECTING,
        DecisionState.FAILED,
    }),
    DecisionState.COLLECTING: frozenset({
        DecisionState.EVALUATING,
        DecisionState.PAUSED,
        DecisionState.FAILED,
    }),
    DecisionState.EVALUATING: frozenset({
        DecisionState.READY,
        DecisionState.COLLECTING,    # re-collect if data insufficient
        DecisionState.PAUSED,
        DecisionState.FAILED,
    }),
    DecisionState.READY: frozenset({
        DecisionState.ACTIVE,
        DecisionState.PAUSED,
        DecisionState.FAILED,
    }),
    DecisionState.ACTIVE: frozenset({
        DecisionState.COMPLETED,
        DecisionState.PAUSED,
        DecisionState.EVALUATING,    # re-evaluate cycle
        DecisionState.FAILED,
    }),
    DecisionState.PAUSED: frozenset({
        DecisionState.RESUMING,
        DecisionState.FAILED,
    }),
    DecisionState.RESUMING: frozenset({
        DecisionState.COLLECTING,
        DecisionState.EVALUATING,
        DecisionState.READY,
        DecisionState.ACTIVE,
        DecisionState.FAILED,
    }),
    DecisionState.COMPLETED: frozenset({
        DecisionState.ARCHIVED,
    }),
    DecisionState.FAILED: frozenset({
        DecisionState.ARCHIVED,
    }),
    DecisionState.ARCHIVED: frozenset(),    # terminal — nothing allowed
}

#: States where a session is still in-flight.
ACTIVE_STATES: FrozenSet[DecisionState] = frozenset({
    DecisionState.INITIALIZING,
    DecisionState.COLLECTING,
    DecisionState.EVALUATING,
    DecisionState.READY,
    DecisionState.ACTIVE,
    DecisionState.PAUSED,
    DecisionState.RESUMING,
})

#: States where a session has ended.
TERMINAL_STATES: FrozenSet[DecisionState] = frozenset({
    DecisionState.COMPLETED,
    DecisionState.FAILED,
    DecisionState.ARCHIVED,
})

#: States that are truly immutable — no further transitions are accepted.
IMMUTABLE_STATES: FrozenSet[DecisionState] = frozenset({
    DecisionState.ARCHIVED,
})

#: States that represent a successful outcome.
SUCCESS_STATES: FrozenSet[DecisionState] = frozenset({
    DecisionState.COMPLETED,
    DecisionState.ARCHIVED,
})


# ---------------------------------------------------------------------------
# DecisionScope — what the decision covers
# ---------------------------------------------------------------------------
class DecisionScope(str, Enum):
    """Defines the scope of a decision session."""
    ORDER     = "order"       # single order decision
    POSITION  = "position"    # position management
    PORTFOLIO = "portfolio"   # portfolio-level decision
    STRATEGY  = "strategy"    # strategy-level decision
    WORKFLOW  = "workflow"    # workflow-scoped decision
    SYSTEM    = "system"      # system-level decision
    CUSTOM    = "custom"      # caller-defined scope


# ---------------------------------------------------------------------------
# DecisionType — the kind of decision being made
# ---------------------------------------------------------------------------
class DecisionType(str, Enum):
    """Classifies the nature of the institutional decision."""
    ORDER     = "order"      # order placement/cancellation/modification
    POSITION  = "position"   # position sizing / scaling
    RISK      = "risk"       # risk management action
    REBALANCE = "rebalance"  # portfolio rebalancing
    EXIT      = "exit"       # position exit
    HEDGE     = "hedge"      # hedging action
    SIGNAL    = "signal"     # raw signal evaluation
    SYSTEM    = "system"     # system-level decision
    CUSTOM    = "custom"     # caller-defined type


# ---------------------------------------------------------------------------
# DecisionPriority — scheduling priority
# ---------------------------------------------------------------------------
class DecisionPriority(int, Enum):
    """
    Institutional scheduling priority for decision sessions.

    Lower numeric value = higher priority.
    """
    CRITICAL   = 1
    HIGH       = 2
    MEDIUM     = 3
    LOW        = 4
    BACKGROUND = 5


# ---------------------------------------------------------------------------
# DecisionTrigger — what initiated the decision session
# ---------------------------------------------------------------------------
class DecisionTrigger(str, Enum):
    """Classifies what triggered a decision session."""
    MANUAL       = "manual"
    AUTOMATIC    = "automatic"
    SCHEDULED    = "scheduled"
    EVENT_DRIVEN = "event_driven"
    SIGNAL       = "signal"
    SYSTEM       = "system"


# ---------------------------------------------------------------------------
# DecisionEventType — lifecycle event types (8 total)
# ---------------------------------------------------------------------------
class DecisionEventType(str, Enum):
    """Types of lifecycle events emitted by :class:`DecisionLifecycle`."""
    DECISION_CREATED     = "decision_created"
    DECISION_INITIALIZED = "decision_initialized"
    DECISION_STARTED     = "decision_started"
    DECISION_PAUSED      = "decision_paused"
    DECISION_RESUMED     = "decision_resumed"
    DECISION_COMPLETED   = "decision_completed"
    DECISION_FAILED      = "decision_failed"
    DECISION_ARCHIVED    = "decision_archived"


# ---------------------------------------------------------------------------
# ValidationCode — identifiers for the five validation checks
# ---------------------------------------------------------------------------
class DecisionValidationCode(str, Enum):
    """Identifies each of the five decision lifecycle validation checks."""
    IDENTIFIER_CONSISTENCY  = "identifier_consistency"
    LIFECYCLE_CONSISTENCY   = "lifecycle_consistency"
    TRANSITION_VALIDITY     = "transition_validity"
    TIMESTAMP_CONSISTENCY   = "timestamp_consistency"
    HISTORY_INTEGRITY       = "history_integrity"
