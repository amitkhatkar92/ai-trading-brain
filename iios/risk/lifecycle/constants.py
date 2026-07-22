"""
constants.py — iios.risk.lifecycle
====================================
Enumerations, state machine, identifiers, and numeric defaults for the
Institutional Risk Lifecycle subsystem.

C11 Risk Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
LIFECYCLE_SYSTEM_ID: str = "iios:risk:lifecycle"
REGISTRY_SYSTEM_ID:  str = "iios:risk:lifecycle:registry"
FACTORY_SYSTEM_ID:   str = "iios:risk:lifecycle:factory"

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
ACTOR_LIFECYCLE: str = "iios:risk:lifecycle"
ACTOR_OPERATOR:  str = "operator"
ACTOR_SYSTEM:    str = "iios:system"
ACTOR_RISK:      str = "iios:risk:engine"
ACTOR_MONITOR:   str = "iios:risk:monitor"


# ---------------------------------------------------------------------------
# RiskState — twelve lifecycle states
# ---------------------------------------------------------------------------
class RiskState(str, Enum):
    """
    All possible lifecycle states for a risk session.

    Lifecycle progression (happy path)::

        CREATED → INITIALIZING → COLLECTING → VALIDATING → READY
                → ASSESSING → MONITORING → COMPLETED → ARCHIVED

    Pause / resume::

        any active state → PAUSED → RESUMING → (prior active state)

    Failure::

        any non-terminal state → FAILED → ARCHIVED
    """
    CREATED      = "created"
    INITIALIZING = "initializing"
    COLLECTING   = "collecting"
    VALIDATING   = "validating"
    READY        = "ready"
    ASSESSING    = "assessing"
    MONITORING   = "monitoring"
    PAUSED       = "paused"
    RESUMING     = "resuming"
    COMPLETED    = "completed"
    FAILED       = "failed"
    ARCHIVED     = "archived"


# ---------------------------------------------------------------------------
# RiskType
# ---------------------------------------------------------------------------
class RiskType(str, Enum):
    """Classification of the risk assessment type."""
    MARKET      = "market"
    CREDIT      = "credit"
    LIQUIDITY   = "liquidity"
    OPERATIONAL = "operational"
    SYSTEMATIC  = "systematic"
    IDIOSYNCRATIC = "idiosyncratic"
    CONCENTRATION = "concentration"
    TAIL        = "tail"
    CUSTOM      = "custom"


# ---------------------------------------------------------------------------
# RiskScope
# ---------------------------------------------------------------------------
class RiskScope(str, Enum):
    """Institutional scope of the risk assessment."""
    PORTFOLIO  = "portfolio"
    STRATEGY   = "strategy"
    POSITION   = "position"
    SECTOR     = "sector"
    ASSET      = "asset"
    ENTERPRISE = "enterprise"
    CUSTOM     = "custom"


# ---------------------------------------------------------------------------
# RiskPriority
# ---------------------------------------------------------------------------
class RiskPriority(str, Enum):
    """Priority level of the risk session."""
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


# ---------------------------------------------------------------------------
# RiskEventType — eleven event types
# ---------------------------------------------------------------------------
class RiskEventType(str, Enum):
    """All event types emitted by the risk lifecycle subsystem."""
    RISK_CREATED            = "risk_created"
    RISK_INITIALIZED        = "risk_initialized"
    RISK_COLLECTED          = "risk_collected"
    RISK_VALIDATED          = "risk_validated"
    RISK_ASSESSMENT_STARTED = "risk_assessment_started"
    RISK_MONITORING_STARTED = "risk_monitoring_started"
    RISK_PAUSED             = "risk_paused"
    RISK_RESUMED            = "risk_resumed"
    RISK_COMPLETED          = "risk_completed"
    RISK_FAILED             = "risk_failed"
    RISK_ARCHIVED           = "risk_archived"


# ---------------------------------------------------------------------------
# RiskValidationCode
# ---------------------------------------------------------------------------
class RiskValidationCode(str, Enum):
    """Validation check identifiers used in validation results."""
    IDENTIFIER_CONSISTENCY = "identifier_consistency"
    LIFECYCLE_CONSISTENCY  = "lifecycle_consistency"
    TRANSITION_VALIDITY    = "transition_validity"
    TIMESTAMP_CONSISTENCY  = "timestamp_consistency"
    HISTORY_INTEGRITY      = "history_integrity"


# ---------------------------------------------------------------------------
# State machine — strict institutional transitions
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: Dict[RiskState, FrozenSet[RiskState]] = {
    RiskState.CREATED: frozenset({
        RiskState.INITIALIZING,
        RiskState.FAILED,
    }),
    RiskState.INITIALIZING: frozenset({
        RiskState.COLLECTING,
        RiskState.FAILED,
    }),
    RiskState.COLLECTING: frozenset({
        RiskState.VALIDATING,
        RiskState.FAILED,
    }),
    RiskState.VALIDATING: frozenset({
        RiskState.READY,
        RiskState.COLLECTING,   # re-collect when data is insufficient
        RiskState.FAILED,
    }),
    RiskState.READY: frozenset({
        RiskState.ASSESSING,
        RiskState.PAUSED,
        RiskState.FAILED,
    }),
    RiskState.ASSESSING: frozenset({
        RiskState.MONITORING,
        RiskState.PAUSED,
        RiskState.COMPLETED,
        RiskState.FAILED,
    }),
    RiskState.MONITORING: frozenset({
        RiskState.ASSESSING,    # re-assess on new data
        RiskState.PAUSED,
        RiskState.COMPLETED,
        RiskState.FAILED,
    }),
    RiskState.PAUSED: frozenset({
        RiskState.RESUMING,
        RiskState.FAILED,
    }),
    RiskState.RESUMING: frozenset({
        RiskState.ASSESSING,
        RiskState.MONITORING,
        RiskState.READY,
        RiskState.FAILED,
    }),
    RiskState.COMPLETED: frozenset({
        RiskState.ARCHIVED,
    }),
    RiskState.FAILED: frozenset({
        RiskState.ARCHIVED,
    }),
    RiskState.ARCHIVED: frozenset(),   # terminal + immutable
}

# ---------------------------------------------------------------------------
# Semantic state sets
# ---------------------------------------------------------------------------

#: States in which a risk session is actively being managed
ACTIVE_STATES: FrozenSet[RiskState] = frozenset({
    RiskState.INITIALIZING,
    RiskState.COLLECTING,
    RiskState.VALIDATING,
    RiskState.READY,
    RiskState.ASSESSING,
    RiskState.MONITORING,
    RiskState.PAUSED,
    RiskState.RESUMING,
})

#: Terminal states — no further transitions (except to ARCHIVED)
TERMINAL_STATES: FrozenSet[RiskState] = frozenset({
    RiskState.COMPLETED,
    RiskState.FAILED,
    RiskState.ARCHIVED,
})

#: States from which the session cannot be modified
IMMUTABLE_STATES: FrozenSet[RiskState] = frozenset({
    RiskState.ARCHIVED,
})

#: Successful terminal states
SUCCESS_STATES: FrozenSet[RiskState] = frozenset({
    RiskState.COMPLETED,
    RiskState.ARCHIVED,
})
