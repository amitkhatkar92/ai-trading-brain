"""iios/execution/oms/integration/constants.py
==================================================
Constants, enumerations, and system IDs for the OMS Integration layer.

C6 Execution Intelligence — Phase 2, Module 6
"""
from __future__ import annotations

from enum import Enum

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------

OMS_INTEGRATION_SYSTEM_ID = "iios:execution:oms:integration"
ENGINE_SYSTEM_ID           = "iios:execution:oms:integration:engine"
MANAGER_SYSTEM_ID          = "iios:execution:oms:integration:manager"
REGISTRY_SYSTEM_ID         = "iios:execution:oms:integration:registry"
FACTORY_SYSTEM_ID          = "iios:execution:oms:integration:factory"
VALIDATOR_SYSTEM_ID        = "iios:execution:oms:integration:validator"

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Sizing defaults
# ---------------------------------------------------------------------------

DEFAULT_MAX_EVENTS   = 10_000
DEFAULT_MAX_HISTORY  = 5_000
DEFAULT_MAX_SNAPSHOTS = 100
REQUIRED_COMPONENT_COUNT = 5

# ---------------------------------------------------------------------------
# OMS-wide state
# ---------------------------------------------------------------------------

class OMSState(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING  = "INITIALIZING"
    RUNNING       = "RUNNING"
    DEGRADED      = "DEGRADED"   # some components degraded but OMS operable
    STOPPED       = "STOPPED"
    ERROR         = "ERROR"

TERMINAL_OMS_STATES: frozenset[OMSState] = frozenset({
    OMSState.STOPPED, OMSState.ERROR,
})

HEALTHY_OMS_STATES: frozenset[OMSState] = frozenset({
    OMSState.RUNNING,
})

# ---------------------------------------------------------------------------
# Component types — the five OMS subsystems
# ---------------------------------------------------------------------------

class ComponentType(str, Enum):
    ORDER_MANAGER = "ORDER_MANAGER"
    ORDER_BOOK    = "ORDER_BOOK"
    ORDER_ROUTER  = "ORDER_ROUTER"
    ORDER_QUEUE   = "ORDER_QUEUE"
    PERSISTENCE   = "PERSISTENCE"

REQUIRED_COMPONENTS: frozenset[ComponentType] = frozenset(ComponentType)

# Human-readable labels for logging
COMPONENT_LABELS: dict[str, str] = {
    ComponentType.ORDER_MANAGER.value: "Order Manager",
    ComponentType.ORDER_BOOK.value:    "Order Book",
    ComponentType.ORDER_ROUTER.value:  "Order Router",
    ComponentType.ORDER_QUEUE.value:   "Order Queue",
    ComponentType.PERSISTENCE.value:   "Persistence",
}

# ---------------------------------------------------------------------------
# Integration event types
# ---------------------------------------------------------------------------

class IntegrationEventType(str, Enum):
    OMS_INITIALIZED      = "OMS_INITIALIZED"
    OMS_STARTED          = "OMS_STARTED"
    OMS_STOPPED          = "OMS_STOPPED"
    OMS_VALIDATED        = "OMS_VALIDATED"
    SNAPSHOT_PUBLISHED   = "SNAPSHOT_PUBLISHED"
    COMPONENT_REGISTERED = "COMPONENT_REGISTERED"
    COMPONENT_FAILED     = "COMPONENT_FAILED"

# ---------------------------------------------------------------------------
# Integration query types
# ---------------------------------------------------------------------------

class IntegrationQueryType(str, Enum):
    FIND_ORDER     = "FIND_ORDER"
    LIST_ACTIVE    = "LIST_ACTIVE"
    COUNT_ACTIVE   = "COUNT_ACTIVE"
    BOOK_CONTAINS  = "BOOK_CONTAINS"
    BOOK_QUERY     = "BOOK_QUERY"
    QUEUE_PEEK     = "QUEUE_PEEK"
    QUEUE_SIZE     = "QUEUE_SIZE"
    ROUTER_HISTORY = "ROUTER_HISTORY"
    PERSIST_FIND   = "PERSIST_FIND"
    FULL_HEALTH    = "FULL_HEALTH"

# ---------------------------------------------------------------------------
# Validation codes
# ---------------------------------------------------------------------------

class ValidationCode(str, Enum):
    COMPONENT_MISSING        = "COMPONENT_MISSING"
    COMPONENT_NOT_RUNNING    = "COMPONENT_NOT_RUNNING"
    STATE_INCONSISTENCY      = "STATE_INCONSISTENCY"
    SNAPSHOT_INCONSISTENCY   = "SNAPSHOT_INCONSISTENCY"
    QUEUE_INCONSISTENCY      = "QUEUE_INCONSISTENCY"
    REPOSITORY_INCONSISTENCY = "REPOSITORY_INCONSISTENCY"
    HISTORY_INCONSISTENCY    = "HISTORY_INCONSISTENCY"
