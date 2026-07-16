"""iios/execution/positions/lifecycle/constants.py
==================================================
Constants, enumerations, and state machine for the IIOS
Position Lifecycle layer.

C6 Execution Intelligence — Phase 3, Module 1
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

LIFECYCLE_SYSTEM_ID = "iios:execution:positions:lifecycle"
REGISTRY_SYSTEM_ID  = "iios:execution:positions:lifecycle:registry"
FACTORY_SYSTEM_ID   = "iios:execution:positions:lifecycle:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:positions:lifecycle:validator"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_POSITIONS = 10_000
DEFAULT_MAX_HISTORY   = 500
DEFAULT_SEARCH_LIMIT  = 1_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_LIFECYCLE = "iios:execution:positions:lifecycle"
ACTOR_REGISTRY  = "iios:execution:positions:lifecycle:registry"
ACTOR_FACTORY   = "iios:execution:positions:lifecycle:factory"


# ── Position state ────────────────────────────────────────────────────────────

class PositionState(str, Enum):
    """All valid lifecycle states for a trading position."""
    CREATED          = "CREATED"
    OPENING          = "OPENING"
    OPEN             = "OPEN"
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"
    CLOSING          = "CLOSING"
    CLOSED           = "CLOSED"
    SUSPENDED        = "SUSPENDED"
    RECOVERING       = "RECOVERING"
    RECOVERED        = "RECOVERED"
    ARCHIVED         = "ARCHIVED"


# ── Position direction ────────────────────────────────────────────────────────

class PositionDirection(str, Enum):
    """Market direction of the position."""
    LONG  = "LONG"
    SHORT = "SHORT"


# ── Position product ──────────────────────────────────────────────────────────

class PositionProduct(str, Enum):
    """Financial product type."""
    EQUITY    = "EQUITY"
    FUTURES   = "FUTURES"
    OPTIONS   = "OPTIONS"
    CURRENCY  = "CURRENCY"
    COMMODITY = "COMMODITY"
    BOND      = "BOND"


# ── Position event types ──────────────────────────────────────────────────────

class PositionEventType(str, Enum):
    """Domain events emitted by the position lifecycle."""
    POSITION_CREATED          = "POSITION_CREATED"
    POSITION_OPENED           = "POSITION_OPENED"
    POSITION_UPDATED          = "POSITION_UPDATED"
    POSITION_PARTIALLY_CLOSED = "POSITION_PARTIALLY_CLOSED"
    POSITION_CLOSED           = "POSITION_CLOSED"
    POSITION_RECOVERED        = "POSITION_RECOVERED"
    POSITION_ARCHIVED         = "POSITION_ARCHIVED"


# ── State machine ─────────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[PositionState, frozenset[PositionState]] = {
    PositionState.CREATED: frozenset({
        PositionState.OPENING,
    }),
    PositionState.OPENING: frozenset({
        PositionState.OPEN,
        PositionState.CLOSED,
    }),
    PositionState.OPEN: frozenset({
        PositionState.PARTIALLY_CLOSED,
        PositionState.CLOSING,
        PositionState.SUSPENDED,
    }),
    PositionState.PARTIALLY_CLOSED: frozenset({
        PositionState.CLOSING,
        PositionState.OPEN,
        PositionState.SUSPENDED,
    }),
    PositionState.CLOSING: frozenset({
        PositionState.CLOSED,
        PositionState.SUSPENDED,
        PositionState.RECOVERING,
    }),
    PositionState.CLOSED: frozenset({
        PositionState.ARCHIVED,
    }),
    PositionState.SUSPENDED: frozenset({
        PositionState.RECOVERING,
        PositionState.CLOSED,
    }),
    PositionState.RECOVERING: frozenset({
        PositionState.RECOVERED,
        PositionState.CLOSED,
    }),
    PositionState.RECOVERED: frozenset({
        PositionState.OPEN,
        PositionState.CLOSING,
    }),
    PositionState.ARCHIVED: frozenset(),
}

TERMINAL_STATES = frozenset({PositionState.ARCHIVED})

ACTIVE_STATES = frozenset({
    PositionState.OPENING,
    PositionState.OPEN,
    PositionState.PARTIALLY_CLOSED,
    PositionState.CLOSING,
})

SUSPENDED_STATES = frozenset({
    PositionState.SUSPENDED,
    PositionState.RECOVERING,
    PositionState.RECOVERED,
})

CLOSED_STATES = frozenset({
    PositionState.CLOSED,
    PositionState.ARCHIVED,
})
