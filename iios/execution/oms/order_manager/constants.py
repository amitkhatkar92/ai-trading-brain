"""iios/execution/oms/order_manager/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS Order Manager.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

OMS_SYSTEM_ID       = "iios:execution:oms"
MANAGER_SYSTEM_ID   = "iios:execution:oms:order_manager"
REGISTRY_SYSTEM_ID  = "iios:execution:oms:order_manager:registry"
FACTORY_SYSTEM_ID   = "iios:execution:oms:order_manager:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:oms:order_manager:validator"

VERSION = "1.0.0"

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_MANAGER   = "iios:execution:oms:order_manager"
ACTOR_REGISTRY  = "iios:execution:oms:order_manager:registry"
ACTOR_FACTORY   = "iios:execution:oms:order_manager:factory"
ACTOR_VALIDATOR = "iios:execution:oms:order_manager:validator"
ACTOR_USER      = "iios:user"

# ── Capacity defaults ─────────────────────────────────────────────────────────

DEFAULT_MAX_MANAGED_ORDERS = 500_000
DEFAULT_MAX_HISTORY        = 500
DEFAULT_MAX_ACTIVE_ORDERS  = 100_000

# ── Enumerations ──────────────────────────────────────────────────────────────


class ManagerOrderState(str, Enum):
    """
    OMS-level state of a ManagedOrder.

    This is distinct from the M1 OrderState (which tracks exchange lifecycle).
    ManagerOrderState tracks the OMS coordination lifecycle.
    """
    INITIALIZED = "INITIALIZED"   # ManagedOrder created, not yet registered
    READY       = "READY"         # Registered, ready for processing
    PROCESSING  = "PROCESSING"    # Being actively coordinated
    WAITING     = "WAITING"       # Awaiting external event (broker ACK, etc.)
    COMPLETED   = "COMPLETED"     # OMS processing finished
    FAILED      = "FAILED"        # OMS processing failed


# Terminal states
TERMINAL_MANAGER_STATES = frozenset({
    ManagerOrderState.COMPLETED,
    ManagerOrderState.FAILED,
})

# Active states
ACTIVE_MANAGER_STATES = frozenset({
    ManagerOrderState.READY,
    ManagerOrderState.PROCESSING,
    ManagerOrderState.WAITING,
})

# Valid OMS state transitions
VALID_MANAGER_TRANSITIONS: dict[ManagerOrderState, frozenset[ManagerOrderState]] = {
    ManagerOrderState.INITIALIZED: frozenset({
        ManagerOrderState.READY,
        ManagerOrderState.FAILED,
    }),
    ManagerOrderState.READY: frozenset({
        ManagerOrderState.PROCESSING,
        ManagerOrderState.COMPLETED,
        ManagerOrderState.FAILED,
    }),
    ManagerOrderState.PROCESSING: frozenset({
        ManagerOrderState.WAITING,
        ManagerOrderState.COMPLETED,
        ManagerOrderState.FAILED,
    }),
    ManagerOrderState.WAITING: frozenset({
        ManagerOrderState.PROCESSING,
        ManagerOrderState.COMPLETED,
        ManagerOrderState.FAILED,
    }),
    ManagerOrderState.COMPLETED: frozenset(),
    ManagerOrderState.FAILED:    frozenset(),
}


class OrderOwnership(str, Enum):
    """Who owns / initiated a managed order."""
    SYSTEM    = "SYSTEM"     # Platform-generated
    STRATEGY  = "STRATEGY"   # Strategy-generated
    MANUAL    = "MANUAL"     # Manually entered
    RECOVERY  = "RECOVERY"   # Recovered from failure
    REPLAYED  = "REPLAYED"   # Replayed for backtesting


class OrderGroupType(str, Enum):
    """Classification of an order group."""
    BASKET     = "BASKET"     # Independent orders, executed together
    BRACKET    = "BRACKET"    # Entry + profit target + stop loss
    OCO        = "OCO"        # One-Cancels-Other
    SEQUENCE   = "SEQUENCE"   # Must execute in order
    HEDGE      = "HEDGE"      # Paired hedge orders
    CUSTOM     = "CUSTOM"


class ManagerEventType(str, Enum):
    """Events emitted by the Order Manager."""
    MANAGER_STARTED     = "MANAGER_STARTED"
    MANAGER_STOPPED     = "MANAGER_STOPPED"
    ORDER_REGISTERED    = "ORDER_REGISTERED"
    ORDER_UPDATED       = "ORDER_UPDATED"
    ORDER_SUSPENDED     = "ORDER_SUSPENDED"
    ORDER_RESUMED       = "ORDER_RESUMED"
    ORDER_CLOSED        = "ORDER_CLOSED"
    ORDER_ARCHIVED      = "ORDER_ARCHIVED"
    ORDER_REMOVED       = "ORDER_REMOVED"


class ManagerValidationCode(str, Enum):
    """Machine-readable validation failure codes."""
    MISSING_ORDER_ID        = "MISSING_ORDER_ID"
    DUPLICATE_ORDER_ID      = "DUPLICATE_ORDER_ID"
    INVALID_MANAGER_STATE   = "INVALID_MANAGER_STATE"
    INVALID_PARENT_ID       = "INVALID_PARENT_ID"
    PARENT_NOT_FOUND        = "PARENT_NOT_FOUND"
    CIRCULAR_PARENT         = "CIRCULAR_PARENT"
    INVALID_ORDER_STATE     = "INVALID_ORDER_STATE"
    INVALID_OWNERSHIP       = "INVALID_OWNERSHIP"
    REGISTRY_CAPACITY       = "REGISTRY_CAPACITY"
    MANAGER_NOT_RUNNING     = "MANAGER_NOT_RUNNING"
    ORDER_NOT_FOUND         = "ORDER_NOT_FOUND"
    ORDER_TERMINAL          = "ORDER_TERMINAL"
