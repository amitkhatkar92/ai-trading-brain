"""iios/execution/orders/__init__.py

Public API for the Order Management System (OMS).
"""
from __future__ import annotations

# ── Constants ─────────────────────────────────────────────────────────────────
from .order_constants import (
    ACTIVE_STATUSES,
    CANCELLABLE_STATUSES,
    DEFAULT_MAX_ORDERS,
    DEFAULT_MAX_QUEUE_SIZE,
    MODIFIABLE_STATUSES,
    OMS_SYSTEM_ID,
    OMS_VERSION,
    PRIORITY_WEIGHT,
    TERMINAL_STATUSES,
    VALID_TRANSITIONS,
    FillStatus,
    OrderAssetClass,
    OrderMode,
    OrderPriority,
    OrderSide,
    OrderStatus,
    OrderType,
    QueueType,
    TimeInForce,
    ValidationStatus,
)

# ── Context ───────────────────────────────────────────────────────────────────
from .order_context import (
    OrderContextState,
    clear_order_context,
    get_order_context,
    order_session,
    order_stage_scope,
    require_order_context,
    set_order_context,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .order_exceptions import (
    InvalidOrderStatusError,
    NoRouteFoundError,
    OMSCapacityError,
    OMSError,
    OMSNotInitializedError,
    OMSShutdownError,
    OrderAlreadyExistsError,
    OrderConstraintViolationError,
    OrderCreationError,
    OrderFillError,
    OrderNotFoundError,
    OrderRoutingError,
    OrderTerminalError,
    OrderValidationError,
    OverfillError,
    QueueFullError,
    QueueNotFoundError,
)

# ── Core models ───────────────────────────────────────────────────────────────
from .core import (
    LiveOrderStatistics,
    Order,
    OrderExecution,
    OrderHistory,
    OrderMetadata,
    OrderRequest,
    OrderResponse,
    OrderStatistics,
    OrderStatusTransition,
)

# ── Services ──────────────────────────────────────────────────────────────────
from .order_factory import OrderFactory
from .order_management_system import (
    OrderManagementSystem,
    get_oms,
    reset_oms,
)
from .order_manager import OrderManager
from .order_registry import OrderRegistry

# ── Subpackage re-exports ─────────────────────────────────────────────────────
from .lifecycle import LifecycleEngine, OrderLifecycle, TransitionHook
from .queue import OrderQueue, PriorityQueue, QueueManager, QueueMonitor
from .tracking import (
    ExecutionTracker,
    OrderMonitor,
    OrderTracker,
    StatusTracker,
)
from .validation import (
    DEFAULT_RULES,
    OrderValidator,
    ValidationEngine,
    ValidationReport,
)

__all__ = [
    # Constants
    "OrderStatus",
    "OrderType",
    "OrderSide",
    "OrderPriority",
    "OrderMode",
    "OrderAssetClass",
    "TimeInForce",
    "FillStatus",
    "QueueType",
    "ValidationStatus",
    "TERMINAL_STATUSES",
    "ACTIVE_STATUSES",
    "CANCELLABLE_STATUSES",
    "MODIFIABLE_STATUSES",
    "VALID_TRANSITIONS",
    "PRIORITY_WEIGHT",
    "OMS_VERSION",
    "OMS_SYSTEM_ID",
    "DEFAULT_MAX_ORDERS",
    "DEFAULT_MAX_QUEUE_SIZE",
    # Context
    "OrderContextState",
    "get_order_context",
    "set_order_context",
    "clear_order_context",
    "require_order_context",
    "order_session",
    "order_stage_scope",
    # Exceptions
    "OMSError",
    "OrderNotFoundError",
    "OrderAlreadyExistsError",
    "OrderCreationError",
    "InvalidOrderStatusError",
    "OrderTerminalError",
    "OrderValidationError",
    "OrderConstraintViolationError",
    "OrderFillError",
    "OverfillError",
    "QueueFullError",
    "QueueNotFoundError",
    "OMSCapacityError",
    "OMSNotInitializedError",
    "OMSShutdownError",
    "OrderRoutingError",
    "NoRouteFoundError",
    # Core models
    "Order",
    "OrderExecution",
    "OrderHistory",
    "OrderMetadata",
    "OrderRequest",
    "OrderResponse",
    "OrderStatistics",
    "LiveOrderStatistics",
    "OrderStatusTransition",
    # Services
    "OrderFactory",
    "OrderRegistry",
    "OrderManager",
    "OrderManagementSystem",
    "get_oms",
    "reset_oms",
    # Lifecycle
    "OrderLifecycle",
    "LifecycleEngine",
    "TransitionHook",
    # Queue
    "OrderQueue",
    "PriorityQueue",
    "QueueManager",
    "QueueMonitor",
    # Tracking
    "OrderTracker",
    "StatusTracker",
    "ExecutionTracker",
    "OrderMonitor",
    # Validation
    "OrderValidator",
    "ValidationEngine",
    "ValidationReport",
    "DEFAULT_RULES",
]
