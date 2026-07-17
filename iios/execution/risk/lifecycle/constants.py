"""iios/execution/risk/lifecycle/constants.py
==================================================
Constants, enumerations, and state machine for the IIOS
Execution Risk Lifecycle layer.

C6 Execution Intelligence — Phase 4, Module 1
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

LIFECYCLE_SYSTEM_ID = "iios:execution:risk:lifecycle"
REGISTRY_SYSTEM_ID  = "iios:execution:risk:lifecycle:registry"
FACTORY_SYSTEM_ID   = "iios:execution:risk:lifecycle:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:risk:lifecycle:validator"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_EVALUATIONS = 10_000
DEFAULT_MAX_HISTORY     = 500
DEFAULT_SEARCH_LIMIT    = 1_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_LIFECYCLE = "iios:execution:risk:lifecycle"
ACTOR_REGISTRY  = "iios:execution:risk:lifecycle:registry"
ACTOR_FACTORY   = "iios:execution:risk:lifecycle:factory"


# ── Risk state ────────────────────────────────────────────────────────────────

class RiskState(str, Enum):
    """All valid lifecycle states for an execution risk evaluation."""
    CREATED            = "CREATED"
    PENDING_EVALUATION = "PENDING_EVALUATION"
    EVALUATING         = "EVALUATING"
    PASSED             = "PASSED"
    WARNING            = "WARNING"
    BLOCKED            = "BLOCKED"
    OVERRIDDEN         = "OVERRIDDEN"
    EXPIRED            = "EXPIRED"
    FAILED             = "FAILED"
    ARCHIVED           = "ARCHIVED"


# ── Risk category ─────────────────────────────────────────────────────────────

class RiskCategory(str, Enum):
    """Type of risk being evaluated."""
    EXPOSURE      = "EXPOSURE"
    MARGIN        = "MARGIN"
    LIQUIDITY     = "LIQUIDITY"
    CONCENTRATION = "CONCENTRATION"
    ORDER_SIZE    = "ORDER_SIZE"
    PRICE         = "PRICE"
    EXECUTION     = "EXECUTION"
    COMPLIANCE    = "COMPLIANCE"
    OPERATIONAL   = "OPERATIONAL"


# ── Risk event types ──────────────────────────────────────────────────────────

class RiskEventType(str, Enum):
    """Domain events emitted by the execution risk lifecycle."""
    RISK_CREATED            = "RISK_CREATED"
    RISK_EVALUATION_STARTED = "RISK_EVALUATION_STARTED"
    RISK_PASSED             = "RISK_PASSED"
    RISK_WARNING            = "RISK_WARNING"
    RISK_BLOCKED            = "RISK_BLOCKED"
    RISK_OVERRIDDEN         = "RISK_OVERRIDDEN"
    RISK_EXPIRED            = "RISK_EXPIRED"
    RISK_ARCHIVED           = "RISK_ARCHIVED"


# ── State machine ─────────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[RiskState, frozenset[RiskState]] = {
    RiskState.CREATED: frozenset({
        RiskState.PENDING_EVALUATION,
        RiskState.EXPIRED,
        RiskState.FAILED,
    }),
    RiskState.PENDING_EVALUATION: frozenset({
        RiskState.EVALUATING,
        RiskState.EXPIRED,
        RiskState.FAILED,
    }),
    RiskState.EVALUATING: frozenset({
        RiskState.PASSED,
        RiskState.WARNING,
        RiskState.BLOCKED,
        RiskState.EXPIRED,
        RiskState.FAILED,
    }),
    RiskState.PASSED: frozenset({
        RiskState.OVERRIDDEN,
        RiskState.EXPIRED,
        RiskState.ARCHIVED,
    }),
    RiskState.WARNING: frozenset({
        RiskState.OVERRIDDEN,
        RiskState.BLOCKED,
        RiskState.EXPIRED,
        RiskState.ARCHIVED,
    }),
    RiskState.BLOCKED: frozenset({
        RiskState.OVERRIDDEN,
        RiskState.EXPIRED,
        RiskState.ARCHIVED,
    }),
    RiskState.OVERRIDDEN: frozenset({
        RiskState.EXPIRED,
        RiskState.ARCHIVED,
    }),
    RiskState.EXPIRED: frozenset({
        RiskState.ARCHIVED,
    }),
    RiskState.FAILED: frozenset({
        RiskState.ARCHIVED,
    }),
    RiskState.ARCHIVED: frozenset(),
}

TERMINAL_STATES = frozenset({RiskState.ARCHIVED})

ACTIVE_STATES = frozenset({
    RiskState.PENDING_EVALUATION,
    RiskState.EVALUATING,
})

OUTCOME_STATES = frozenset({
    RiskState.PASSED,
    RiskState.WARNING,
    RiskState.BLOCKED,
    RiskState.OVERRIDDEN,
})

ENDED_STATES = frozenset({
    RiskState.EXPIRED,
    RiskState.FAILED,
    RiskState.ARCHIVED,
})

PASS_STATES = frozenset({
    RiskState.PASSED,
    RiskState.WARNING,
    RiskState.OVERRIDDEN,
})

BLOCKING_STATES = frozenset({
    RiskState.BLOCKED,
})
