"""
constants.py — iios.market.lifecycle
======================================
Enumerations, state machine, identifiers, and numeric defaults for the
Institutional Market Lifecycle subsystem.

C12 Market Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
LIFECYCLE_SYSTEM_ID: str = "iios:market:lifecycle"
REGISTRY_SYSTEM_ID:  str = "iios:market:lifecycle:registry"
FACTORY_SYSTEM_ID:   str = "iios:market:lifecycle:factory"

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
ACTOR_LIFECYCLE: str = "iios:market:lifecycle"
ACTOR_OPERATOR:  str = "operator"
ACTOR_SYSTEM:    str = "iios:system"
ACTOR_MARKET:    str = "iios:market:engine"
ACTOR_MONITOR:   str = "iios:market:monitor"


# ---------------------------------------------------------------------------
# MarketState — twelve lifecycle states
# ---------------------------------------------------------------------------
class MarketState(str, Enum):
    """
    All possible lifecycle states for a market session.

    Lifecycle progression (happy path)::

        CREATED → INITIALIZING → COLLECTING → VALIDATING → READY
                → ANALYZING → MONITORING → COMPLETED → ARCHIVED

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
    ANALYZING    = "analyzing"
    MONITORING   = "monitoring"
    PAUSED       = "paused"
    RESUMING     = "resuming"
    COMPLETED    = "completed"
    FAILED       = "failed"
    ARCHIVED     = "archived"


# ---------------------------------------------------------------------------
# MarketType
# ---------------------------------------------------------------------------
class MarketType(str, Enum):
    """Classification of the market being analysed."""
    EQUITY      = "equity"
    FUTURES     = "futures"
    OPTIONS     = "options"
    CURRENCY    = "currency"
    COMMODITY   = "commodity"
    BOND        = "bond"
    INDEX       = "index"
    CRYPTO      = "crypto"
    CUSTOM      = "custom"


# ---------------------------------------------------------------------------
# MarketScope
# ---------------------------------------------------------------------------
class MarketScope(str, Enum):
    """Institutional scope of the market analysis."""
    DOMESTIC   = "domestic"
    REGIONAL   = "regional"
    GLOBAL     = "global"
    SECTOR     = "sector"
    SEGMENT    = "segment"
    ENTERPRISE = "enterprise"
    CUSTOM     = "custom"


# ---------------------------------------------------------------------------
# MarketPriority
# ---------------------------------------------------------------------------
class MarketPriority(str, Enum):
    """Priority level of the market session."""
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


# ---------------------------------------------------------------------------
# MarketTimeframe
# ---------------------------------------------------------------------------
class MarketTimeframe(str, Enum):
    """Analysis timeframe for the market session."""
    TICK    = "tick"
    M1      = "1m"
    M5      = "5m"
    M15     = "15m"
    M30     = "30m"
    H1      = "1h"
    H4      = "4h"
    D1      = "1d"
    W1      = "1w"
    MN      = "1mo"
    CUSTOM  = "custom"


# ---------------------------------------------------------------------------
# MarketEventType — eleven event types
# ---------------------------------------------------------------------------
class MarketEventType(str, Enum):
    """All event types emitted by the market lifecycle subsystem."""
    MARKET_CREATED            = "market_created"
    MARKET_INITIALIZED        = "market_initialized"
    MARKET_COLLECTED          = "market_collected"
    MARKET_VALIDATED          = "market_validated"
    MARKET_ANALYSIS_STARTED   = "market_analysis_started"
    MARKET_MONITORING_STARTED = "market_monitoring_started"
    MARKET_PAUSED             = "market_paused"
    MARKET_RESUMED            = "market_resumed"
    MARKET_COMPLETED          = "market_completed"
    MARKET_FAILED             = "market_failed"
    MARKET_ARCHIVED           = "market_archived"


# ---------------------------------------------------------------------------
# MarketValidationCode
# ---------------------------------------------------------------------------
class MarketValidationCode(str, Enum):
    """Validation check identifiers used in validation results."""
    IDENTIFIER_CONSISTENCY = "identifier_consistency"
    LIFECYCLE_CONSISTENCY  = "lifecycle_consistency"
    TRANSITION_VALIDITY    = "transition_validity"
    TIMESTAMP_CONSISTENCY  = "timestamp_consistency"
    HISTORY_INTEGRITY      = "history_integrity"


# ---------------------------------------------------------------------------
# State machine — strict institutional transitions
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: Dict[MarketState, FrozenSet[MarketState]] = {
    MarketState.CREATED: frozenset({
        MarketState.INITIALIZING,
        MarketState.FAILED,
    }),
    MarketState.INITIALIZING: frozenset({
        MarketState.COLLECTING,
        MarketState.FAILED,
    }),
    MarketState.COLLECTING: frozenset({
        MarketState.VALIDATING,
        MarketState.FAILED,
    }),
    MarketState.VALIDATING: frozenset({
        MarketState.READY,
        MarketState.COLLECTING,   # re-collect when data is insufficient
        MarketState.FAILED,
    }),
    MarketState.READY: frozenset({
        MarketState.ANALYZING,
        MarketState.PAUSED,
        MarketState.FAILED,
    }),
    MarketState.ANALYZING: frozenset({
        MarketState.MONITORING,
        MarketState.PAUSED,
        MarketState.COMPLETED,
        MarketState.FAILED,
    }),
    MarketState.MONITORING: frozenset({
        MarketState.ANALYZING,    # re-analyze on new market data
        MarketState.PAUSED,
        MarketState.COMPLETED,
        MarketState.FAILED,
    }),
    MarketState.PAUSED: frozenset({
        MarketState.RESUMING,
        MarketState.FAILED,
    }),
    MarketState.RESUMING: frozenset({
        MarketState.ANALYZING,
        MarketState.MONITORING,
        MarketState.READY,
        MarketState.FAILED,
    }),
    MarketState.COMPLETED: frozenset({
        MarketState.ARCHIVED,
    }),
    MarketState.FAILED: frozenset({
        MarketState.ARCHIVED,
    }),
    MarketState.ARCHIVED: frozenset(),   # terminal + immutable
}

# ---------------------------------------------------------------------------
# Semantic state sets
# ---------------------------------------------------------------------------

#: States in which a market session is actively being managed
ACTIVE_STATES: FrozenSet[MarketState] = frozenset({
    MarketState.INITIALIZING,
    MarketState.COLLECTING,
    MarketState.VALIDATING,
    MarketState.READY,
    MarketState.ANALYZING,
    MarketState.MONITORING,
    MarketState.PAUSED,
    MarketState.RESUMING,
})

#: Terminal states — no further transitions (except to ARCHIVED)
TERMINAL_STATES: FrozenSet[MarketState] = frozenset({
    MarketState.COMPLETED,
    MarketState.FAILED,
    MarketState.ARCHIVED,
})

#: States from which the session cannot be modified
IMMUTABLE_STATES: FrozenSet[MarketState] = frozenset({
    MarketState.ARCHIVED,
})

#: Successful terminal states
SUCCESS_STATES: FrozenSet[MarketState] = frozenset({
    MarketState.COMPLETED,
    MarketState.ARCHIVED,
})
