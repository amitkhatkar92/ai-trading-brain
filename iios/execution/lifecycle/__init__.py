"""iios/execution/lifecycle/__init__.py
==================================================
IIOS Order Lifecycle — Public API

Phase 1 / Module 1 of C6 Execution Intelligence.

Provides the complete, broker-agnostic order lifecycle:
state machine, transition history, fill tracking, validation,
factory, and thread-safe registry.

Quick start
-----------
    from iios.execution.lifecycle import (
        OrderFactory, OrderRegistry, OrderContext,
        OrderSide, OrderType, TimeInForce,
    )
    from decimal import Decimal

    factory  = OrderFactory()
    registry = OrderRegistry()
    registry.start()

    ctx = OrderContext(
        strategy_id  = "STRAT-001",
        portfolio_id = "PORT-001",
        decision_id  = "DEC-001",
        workflow_id  = "WF-001",
    )
    order = factory.create_limit_order(
        context     = ctx,
        instrument  = "RELIANCE",
        exchange    = "NSE",
        side        = OrderSide.BUY,
        quantity    = Decimal("100"),
        limit_price = Decimal("2800.00"),
    )
    registry.register(order)

    # Advance through lifecycle
    from iios.execution.lifecycle import OrderState, ACTOR_VALIDATOR
    registry.apply_transition(
        order.order_id, OrderState.VALIDATED,
        reason="validation passed", actor=ACTOR_VALIDATOR,
    )
"""
from .constants import (
    LIFECYCLE_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    DEFAULT_MAX_ORDERS,
    DEFAULT_MAX_HISTORY,
    MIN_QUANTITY,
    MAX_QUANTITY,
    MIN_PRICE,
    MAX_PRICE,
    ACTOR_SYSTEM,
    ACTOR_VALIDATOR,
    ACTOR_BROKER,
    ACTOR_EXCHANGE,
    ACTOR_RISK,
    ACTOR_SCHEDULER,
    ACTOR_USER,
    OrderSide,
    OrderType,
    TimeInForce,
)
from .exceptions import (
    OrderLifecycleError,
    InvalidTransitionError,
    OrderNotFoundError,
    OrderValidationError,
    DuplicateOrderError,
    RegistryCapacityError,
    OrderTerminalError,
    InvalidFillError,
    RegistryNotRunningError,
)
from .order_state import (
    OrderState,
    VALID_TRANSITIONS,
    TERMINAL_STATES,
    ACTIVE_STATES,
    CANCELLABLE_STATES,
    RECOVERABLE_STATES,
    FILL_STATES,
    can_transition,
    allowed_next,
    is_terminal,
)
from .order_transition import OrderTransition, make_transition
from .order_event import OrderEvent, OrderEventType, event_type_for_state, make_event
from .order_context import OrderContext
from .order_metadata import OrderMetadata
from .order_history import OrderHistory
from .order_statistics import OrderStatistics
from .order import Order
from .order_validation import OrderValidator, ValidationResult
from .order_factory import OrderFactory
from .order_registry import OrderRegistry, RegistryStatistics

__all__ = [
    # Constants — system IDs
    "LIFECYCLE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "VERSION",
    # Constants — capacity
    "DEFAULT_MAX_ORDERS",
    "DEFAULT_MAX_HISTORY",
    "MIN_QUANTITY",
    "MAX_QUANTITY",
    "MIN_PRICE",
    "MAX_PRICE",
    # Constants — actor labels
    "ACTOR_SYSTEM",
    "ACTOR_VALIDATOR",
    "ACTOR_BROKER",
    "ACTOR_EXCHANGE",
    "ACTOR_RISK",
    "ACTOR_SCHEDULER",
    "ACTOR_USER",
    # Enums
    "OrderSide",
    "OrderType",
    "TimeInForce",
    "OrderState",
    "OrderEventType",
    # State machine helpers
    "VALID_TRANSITIONS",
    "TERMINAL_STATES",
    "ACTIVE_STATES",
    "CANCELLABLE_STATES",
    "RECOVERABLE_STATES",
    "FILL_STATES",
    "can_transition",
    "allowed_next",
    "is_terminal",
    # Exceptions
    "OrderLifecycleError",
    "InvalidTransitionError",
    "OrderNotFoundError",
    "OrderValidationError",
    "DuplicateOrderError",
    "RegistryCapacityError",
    "OrderTerminalError",
    "InvalidFillError",
    "RegistryNotRunningError",
    # Data types
    "OrderTransition",
    "make_transition",
    "OrderEvent",
    "make_event",
    "event_type_for_state",
    "OrderContext",
    "OrderMetadata",
    "OrderHistory",
    "OrderStatistics",
    "Order",
    "ValidationResult",
    "RegistryStatistics",
    # Services
    "OrderValidator",
    "OrderFactory",
    "OrderRegistry",
]
