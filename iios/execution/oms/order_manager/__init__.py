"""iios/execution/oms/order_manager/__init__.py
==================================================
Public API for the IIOS Order Manager.

C6 Execution Intelligence — Phase 2, Module 1
"""
from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.constants import (
    OMS_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    ACTOR_SYSTEM,
    ACTOR_MANAGER,
    ACTOR_REGISTRY,
    ACTOR_FACTORY,
    ACTOR_VALIDATOR,
    ACTOR_USER,
    DEFAULT_MAX_MANAGED_ORDERS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_ACTIVE_ORDERS,
    ManagerOrderState,
    TERMINAL_MANAGER_STATES,
    ACTIVE_MANAGER_STATES,
    VALID_MANAGER_TRANSITIONS,
    OrderOwnership,
    OrderGroupType,
    ManagerEventType,
    ManagerValidationCode,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.exceptions import (
    OrderManagerError,
    OrderRegistrationError,
    OrderNotFoundError,
    DuplicateOrderError,
    OrderManagerCapacityError,
    OrderManagerNotRunning,
    OrderManagerStateError,
    OrderValidationError,
    OrderOwnershipError,
    OrderParentError,
    OrderGroupError,
    OrderAlreadyTerminalError,
)

# ── Core entities ─────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.order_manager_context import (
    ManagedOrder,
    OrderManagerSnapshot,
)

# ── State machine ─────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.order_manager_state import (
    can_manager_transition,
    assert_manager_transition,
    is_terminal,
    allowed_next,
)

# ── Requests ──────────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.order_manager_request import (
    OrderManagerRequest,
    CreateOrderRequest,
    UpdateOrderRequest,
    SuspendOrderRequest,
    ResumeOrderRequest,
    CloseOrderRequest,
    ArchiveOrderRequest,
    RemoveOrderRequest,
    LookupOrderRequest,
)

# ── Responses ─────────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.order_manager_response import (
    OrderManagerResponse,
)

# ── Events ────────────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.order_manager_events import (
    OrderManagerEvent,
    make_manager_event,
)

# ── Validation ────────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.order_manager_validation import (
    OrderManagerValidator,
    ManagerValidationResult,
)

# ── History ───────────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.order_manager_history import (
    ManagerTransition,
    OrderManagerHistory,
    make_transition,
)

# ── Statistics ────────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.order_manager_statistics import (
    OrderManagerStatistics,
)

# ── Registry ─────────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.order_manager_registry import (
    OrderManagerRegistry,
)

# ── Factory ───────────────────────────────────────────────────────────────────
from iios.execution.oms.order_manager.order_manager_factory import (
    OrderManagerFactory,
)

# ── Manager (primary entry point) ─────────────────────────────────────────────
from iios.execution.oms.order_manager.order_manager import OrderManager

__all__ = [
    # System IDs
    "OMS_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "VERSION",
    # Actors
    "ACTOR_SYSTEM",
    "ACTOR_MANAGER",
    "ACTOR_REGISTRY",
    "ACTOR_FACTORY",
    "ACTOR_VALIDATOR",
    "ACTOR_USER",
    # Capacity
    "DEFAULT_MAX_MANAGED_ORDERS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_ACTIVE_ORDERS",
    # Enums
    "ManagerOrderState",
    "TERMINAL_MANAGER_STATES",
    "ACTIVE_MANAGER_STATES",
    "VALID_MANAGER_TRANSITIONS",
    "OrderOwnership",
    "OrderGroupType",
    "ManagerEventType",
    "ManagerValidationCode",
    # Exceptions
    "OrderManagerError",
    "OrderRegistrationError",
    "OrderNotFoundError",
    "DuplicateOrderError",
    "OrderManagerCapacityError",
    "OrderManagerNotRunning",
    "OrderManagerStateError",
    "OrderValidationError",
    "OrderOwnershipError",
    "OrderParentError",
    "OrderGroupError",
    "OrderAlreadyTerminalError",
    # Core entities
    "ManagedOrder",
    "OrderManagerSnapshot",
    # State machine
    "can_manager_transition",
    "assert_manager_transition",
    "is_terminal",
    "allowed_next",
    # Requests
    "OrderManagerRequest",
    "CreateOrderRequest",
    "UpdateOrderRequest",
    "SuspendOrderRequest",
    "ResumeOrderRequest",
    "CloseOrderRequest",
    "ArchiveOrderRequest",
    "RemoveOrderRequest",
    "LookupOrderRequest",
    # Responses
    "OrderManagerResponse",
    # Events
    "OrderManagerEvent",
    "make_manager_event",
    # Validation
    "OrderManagerValidator",
    "ManagerValidationResult",
    # History
    "ManagerTransition",
    "OrderManagerHistory",
    "make_transition",
    # Statistics
    "OrderManagerStatistics",
    # Registry
    "OrderManagerRegistry",
    # Factory
    "OrderManagerFactory",
    # Manager
    "OrderManager",
]
