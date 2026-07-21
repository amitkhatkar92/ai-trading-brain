"""
constants.py — iios.portfolio.lifecycle
=========================================
Enumerations, state machine, identifiers, and numeric defaults for the
Institutional Portfolio Lifecycle subsystem.

C10 Portfolio Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
LIFECYCLE_SYSTEM_ID: str = "iios:portfolio:lifecycle"
REGISTRY_SYSTEM_ID: str  = "iios:portfolio:lifecycle:registry"
FACTORY_SYSTEM_ID:  str  = "iios:portfolio:lifecycle:factory"

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
ACTOR_LIFECYCLE:  str = "iios:portfolio:lifecycle"
ACTOR_OPERATOR:   str = "operator"
ACTOR_SYSTEM:     str = "iios:system"
ACTOR_ENGINE:     str = "iios:portfolio:engine"
ACTOR_REBALANCER: str = "iios:portfolio:rebalancer"


# ---------------------------------------------------------------------------
# PortfolioState — the twelve lifecycle states
# ---------------------------------------------------------------------------
class PortfolioState(str, Enum):
    """
    All possible lifecycle states for a portfolio session.

    Lifecycle progression (happy path)::

        CREATED → INITIALIZING → LOADING → VALIDATING → READY
                → ACTIVE → COMPLETED → ARCHIVED

    Rebalancing::

        ACTIVE → REBALANCING → ACTIVE

    Pause / resume::

        any active state → PAUSED → RESUMING → (prior active state)

    Failure::

        any non-terminal state → FAILED → ARCHIVED
    """
    CREATED      = "created"
    INITIALIZING = "initializing"
    LOADING      = "loading"
    VALIDATING   = "validating"
    READY        = "ready"
    ACTIVE       = "active"
    PAUSED       = "paused"
    RESUMING     = "resuming"
    REBALANCING  = "rebalancing"
    COMPLETED    = "completed"
    FAILED       = "failed"
    ARCHIVED     = "archived"


# ---------------------------------------------------------------------------
# PortfolioType
# ---------------------------------------------------------------------------
class PortfolioType(str, Enum):
    """Classification of the portfolio by asset composition."""
    EQUITY         = "equity"
    FIXED_INCOME   = "fixed_income"
    BALANCED       = "balanced"
    DERIVATIVES    = "derivatives"
    ALTERNATIVES   = "alternatives"
    MULTI_ASSET    = "multi_asset"
    CASH           = "cash"
    CUSTOM         = "custom"


# ---------------------------------------------------------------------------
# PortfolioScope
# ---------------------------------------------------------------------------
class PortfolioScope(str, Enum):
    """Institutional scope / ownership of the portfolio."""
    INSTITUTIONAL = "institutional"
    RETAIL        = "retail"
    PROPRIETARY   = "proprietary"
    CLIENT        = "client"
    SYNTHETIC     = "synthetic"


# ---------------------------------------------------------------------------
# PortfolioObjective
# ---------------------------------------------------------------------------
class PortfolioObjective(str, Enum):
    """Investment objective of the portfolio."""
    GROWTH           = "growth"
    INCOME           = "income"
    BALANCED         = "balanced"
    PRESERVATION     = "preservation"
    ABSOLUTE_RETURN  = "absolute_return"
    INDEX_TRACKING   = "index_tracking"
    RISK_PARITY      = "risk_parity"
    CUSTOM           = "custom"


# ---------------------------------------------------------------------------
# PortfolioStatus
# ---------------------------------------------------------------------------
class PortfolioStatus(str, Enum):
    """Operational status of the portfolio (orthogonal to lifecycle state)."""
    ACTIVE    = "active"
    INACTIVE  = "inactive"
    SUSPENDED = "suspended"
    CLOSED    = "closed"


# ---------------------------------------------------------------------------
# PortfolioEventType
# ---------------------------------------------------------------------------
class PortfolioEventType(str, Enum):
    """All event types emitted by the portfolio lifecycle subsystem."""
    PORTFOLIO_CREATED      = "portfolio_created"
    PORTFOLIO_INITIALIZED  = "portfolio_initialized"
    PORTFOLIO_LOADED       = "portfolio_loaded"
    PORTFOLIO_VALIDATED    = "portfolio_validated"
    PORTFOLIO_ACTIVATED    = "portfolio_activated"
    PORTFOLIO_PAUSED       = "portfolio_paused"
    PORTFOLIO_RESUMED      = "portfolio_resumed"
    PORTFOLIO_REBALANCING  = "portfolio_rebalancing"
    PORTFOLIO_COMPLETED    = "portfolio_completed"
    PORTFOLIO_FAILED       = "portfolio_failed"
    PORTFOLIO_ARCHIVED     = "portfolio_archived"


# ---------------------------------------------------------------------------
# PortfolioValidationCode
# ---------------------------------------------------------------------------
class PortfolioValidationCode(str, Enum):
    """Validation check identifiers used in validation results."""
    IDENTIFIER_CONSISTENCY  = "identifier_consistency"
    LIFECYCLE_CONSISTENCY   = "lifecycle_consistency"
    TRANSITION_VALIDITY     = "transition_validity"
    TIMESTAMP_CONSISTENCY   = "timestamp_consistency"
    HISTORY_INTEGRITY       = "history_integrity"


# ---------------------------------------------------------------------------
# State machine — strict institutional transitions
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: Dict[PortfolioState, FrozenSet[PortfolioState]] = {
    PortfolioState.CREATED: frozenset({
        PortfolioState.INITIALIZING,
        PortfolioState.FAILED,
    }),
    PortfolioState.INITIALIZING: frozenset({
        PortfolioState.LOADING,
        PortfolioState.FAILED,
    }),
    PortfolioState.LOADING: frozenset({
        PortfolioState.VALIDATING,
        PortfolioState.FAILED,
    }),
    PortfolioState.VALIDATING: frozenset({
        PortfolioState.READY,
        PortfolioState.LOADING,      # re-load if data insufficient
        PortfolioState.FAILED,
    }),
    PortfolioState.READY: frozenset({
        PortfolioState.ACTIVE,
        PortfolioState.PAUSED,
        PortfolioState.FAILED,
    }),
    PortfolioState.ACTIVE: frozenset({
        PortfolioState.REBALANCING,
        PortfolioState.PAUSED,
        PortfolioState.COMPLETED,
        PortfolioState.FAILED,
    }),
    PortfolioState.PAUSED: frozenset({
        PortfolioState.RESUMING,
        PortfolioState.FAILED,
    }),
    PortfolioState.RESUMING: frozenset({
        PortfolioState.READY,
        PortfolioState.ACTIVE,
        PortfolioState.REBALANCING,
        PortfolioState.LOADING,
    }),
    PortfolioState.REBALANCING: frozenset({
        PortfolioState.ACTIVE,
        PortfolioState.PAUSED,
        PortfolioState.COMPLETED,
        PortfolioState.FAILED,
    }),
    PortfolioState.COMPLETED: frozenset({
        PortfolioState.ARCHIVED,
    }),
    PortfolioState.FAILED: frozenset({
        PortfolioState.ARCHIVED,
    }),
    PortfolioState.ARCHIVED: frozenset(),  # terminal
}

# ---------------------------------------------------------------------------
# State sets
# ---------------------------------------------------------------------------
ACTIVE_STATES: FrozenSet[PortfolioState] = frozenset({
    PortfolioState.INITIALIZING,
    PortfolioState.LOADING,
    PortfolioState.VALIDATING,
    PortfolioState.READY,
    PortfolioState.ACTIVE,
    PortfolioState.PAUSED,
    PortfolioState.RESUMING,
    PortfolioState.REBALANCING,
})

TERMINAL_STATES: FrozenSet[PortfolioState] = frozenset({
    PortfolioState.COMPLETED,
    PortfolioState.FAILED,
    PortfolioState.ARCHIVED,
})

SUCCESS_STATES: FrozenSet[PortfolioState] = frozenset({
    PortfolioState.COMPLETED,
})

IMMUTABLE_STATES: FrozenSet[PortfolioState] = frozenset({
    PortfolioState.ARCHIVED,
})
