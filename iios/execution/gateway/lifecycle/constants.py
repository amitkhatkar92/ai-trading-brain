"""iios/execution/gateway/lifecycle/constants.py
==================================================
Constants, enumerations, and state machine for the IIOS
Execution Gateway Lifecycle layer.

C6 Execution Intelligence — Phase 5, Module 1
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

LIFECYCLE_SYSTEM_ID = "iios:execution:gateway:lifecycle"
REGISTRY_SYSTEM_ID  = "iios:execution:gateway:lifecycle:registry"
FACTORY_SYSTEM_ID   = "iios:execution:gateway:lifecycle:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:gateway:lifecycle:validator"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_REQUESTS = 10_000
DEFAULT_MAX_HISTORY  = 500
DEFAULT_SEARCH_LIMIT = 1_000

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_LIFECYCLE = "iios:execution:gateway:lifecycle"
ACTOR_REGISTRY  = "iios:execution:gateway:lifecycle:registry"
ACTOR_FACTORY   = "iios:execution:gateway:lifecycle:factory"


# ── Gateway state ─────────────────────────────────────────────────────────────

class GatewayState(str, Enum):
    """All valid lifecycle states for an execution gateway request."""
    CREATED    = "CREATED"
    RECEIVED   = "RECEIVED"
    VALIDATING = "VALIDATING"
    READY      = "READY"
    QUEUED     = "QUEUED"
    ROUTING    = "ROUTING"
    DISPATCHED = "DISPATCHED"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"
    CANCELLED  = "CANCELLED"
    ARCHIVED   = "ARCHIVED"


# ── Gateway event types ───────────────────────────────────────────────────────

class GatewayEventType(str, Enum):
    """Domain events emitted by the execution gateway lifecycle."""
    GATEWAY_CREATED    = "GATEWAY_CREATED"
    GATEWAY_RECEIVED   = "GATEWAY_RECEIVED"
    GATEWAY_VALIDATED  = "GATEWAY_VALIDATED"
    GATEWAY_QUEUED     = "GATEWAY_QUEUED"
    GATEWAY_DISPATCHED = "GATEWAY_DISPATCHED"
    GATEWAY_COMPLETED  = "GATEWAY_COMPLETED"
    GATEWAY_FAILED     = "GATEWAY_FAILED"
    GATEWAY_CANCELLED  = "GATEWAY_CANCELLED"
    GATEWAY_ARCHIVED   = "GATEWAY_ARCHIVED"


# ── State machine ─────────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[GatewayState, frozenset[GatewayState]] = {
    GatewayState.CREATED: frozenset({
        GatewayState.RECEIVED,
        GatewayState.FAILED,
        GatewayState.CANCELLED,
    }),
    GatewayState.RECEIVED: frozenset({
        GatewayState.VALIDATING,
        GatewayState.FAILED,
        GatewayState.CANCELLED,
    }),
    GatewayState.VALIDATING: frozenset({
        GatewayState.READY,
        GatewayState.FAILED,
        GatewayState.CANCELLED,
    }),
    GatewayState.READY: frozenset({
        GatewayState.QUEUED,
        GatewayState.FAILED,
        GatewayState.CANCELLED,
    }),
    GatewayState.QUEUED: frozenset({
        GatewayState.ROUTING,
        GatewayState.FAILED,
        GatewayState.CANCELLED,
    }),
    GatewayState.ROUTING: frozenset({
        GatewayState.DISPATCHED,
        GatewayState.FAILED,
        GatewayState.CANCELLED,
    }),
    GatewayState.DISPATCHED: frozenset({
        GatewayState.COMPLETED,
        GatewayState.FAILED,
        GatewayState.CANCELLED,
    }),
    GatewayState.COMPLETED: frozenset({
        GatewayState.ARCHIVED,
    }),
    GatewayState.FAILED: frozenset({
        GatewayState.ARCHIVED,
    }),
    GatewayState.CANCELLED: frozenset({
        GatewayState.ARCHIVED,
    }),
    GatewayState.ARCHIVED: frozenset(),    # terminal — no further transitions
}

# ── Sentinel sets ─────────────────────────────────────────────────────────────

TERMINAL_STATES: frozenset[GatewayState] = frozenset({
    GatewayState.ARCHIVED,
})

OUTCOME_STATES: frozenset[GatewayState] = frozenset({
    GatewayState.COMPLETED,
    GatewayState.FAILED,
    GatewayState.CANCELLED,
})

ACTIVE_STATES: frozenset[GatewayState] = frozenset({
    GatewayState.CREATED,
    GatewayState.RECEIVED,
    GatewayState.VALIDATING,
    GatewayState.READY,
    GatewayState.QUEUED,
    GatewayState.ROUTING,
    GatewayState.DISPATCHED,
})

ENDED_STATES:   frozenset[GatewayState] = TERMINAL_STATES | OUTCOME_STATES
SUCCESS_STATES: frozenset[GatewayState] = frozenset({GatewayState.COMPLETED})
FAILURE_STATES: frozenset[GatewayState] = frozenset({
    GatewayState.FAILED,
    GatewayState.CANCELLED,
})
