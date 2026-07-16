"""iios/execution/engine/__init__.py
==================================================
IIOS Execution Engine — Public API

C6 Execution Intelligence — Phase 1, Module 2

This package coordinates the execution workflow for a single
ExecutionRequest. It does NOT communicate with brokers, does NOT
place trades, and does NOT implement execution algorithms.

Quick start
-----------
    from iios.execution.engine import (
        ExecutionManager, ExecutionFactory,
        ExecutionRequest, ExecutionResult,
        ExecutionMode, ExecutionPriority,
    )

    manager = ExecutionManager()
    manager.start()

    request = manager.create_request(
        order_id     = "ORD-001",
        decision_id  = "DEC-001",
        portfolio_id = "PORT-001",
        strategy_id  = "STRAT-001",
    )

    result = manager.submit(request, order_registry=order_registry)

    print(result.succeeded)   # True
    print(result.final_state) # EngineExecutionState.COMPLETED

    manager.stop()
"""
from .constants import (
    ENGINE_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    DEFAULT_MAX_EXECUTIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_QUEUE_SIZE,
    ACTOR_SYSTEM,
    ACTOR_ENGINE,
    ACTOR_VALIDATOR,
    ACTOR_FACTORY,
    ACTOR_REGISTRY,
    ACTOR_USER,
    ExecutionMode,
    ExecutionPriority,
    ExecutionValidationCode,
)
from .exceptions import (
    ExecutionEngineError,
    ExecutionRequestError,
    ExecutionValidationError,
    ExecutionPreparationError,
    ExecutionRegistryError,
    ExecutionNotFoundError,
    DuplicateExecutionError,
    ExecutionCapacityError,
    ExecutionEngineNotRunningError,
    ExecutionStateError,
    ExecutionCancelledError,
)
from .execution_state import (
    EngineExecutionState,
    VALID_ENGINE_TRANSITIONS,
    TERMINAL_ENGINE_STATES,
    ACTIVE_ENGINE_STATES,
    CANCELLABLE_ENGINE_STATES,
    can_engine_transition,
    allowed_engine_next,
    is_engine_terminal,
    assert_engine_transition,
)
from .execution_request import ExecutionRequest
from .execution_context import ExecutionContext
from .execution_result import ExecutionResult
from .execution_snapshot import ExecutionSnapshot
from .execution_events import (
    ExecutionEventType,
    ExecutionEvent,
    make_execution_event,
    event_type_for_state,
)
from .execution_history import (
    ExecutionHistoryEntry,
    ExecutionHistory,
    make_history_entry,
)
from .execution_statistics import ExecutionStatistics, EngineStatistics
from .execution_validation import ExecutionValidator, ValidationResult
from .execution_factory import ExecutionFactory
from .execution_registry import ExecutionRecord, ExecutionRegistry, RegistryStatistics
from .execution_engine import ExecutionEngine
from .execution_manager import ExecutionManager

__all__ = [
    # Constants — system IDs
    "ENGINE_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "VERSION",
    # Constants — capacity
    "DEFAULT_MAX_EXECUTIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_QUEUE_SIZE",
    # Constants — actors
    "ACTOR_SYSTEM",
    "ACTOR_ENGINE",
    "ACTOR_VALIDATOR",
    "ACTOR_FACTORY",
    "ACTOR_REGISTRY",
    "ACTOR_USER",
    # Enums
    "ExecutionMode",
    "ExecutionPriority",
    "ExecutionValidationCode",
    "EngineExecutionState",
    "ExecutionEventType",
    # State machine helpers
    "VALID_ENGINE_TRANSITIONS",
    "TERMINAL_ENGINE_STATES",
    "ACTIVE_ENGINE_STATES",
    "CANCELLABLE_ENGINE_STATES",
    "can_engine_transition",
    "allowed_engine_next",
    "is_engine_terminal",
    "assert_engine_transition",
    # Exceptions
    "ExecutionEngineError",
    "ExecutionRequestError",
    "ExecutionValidationError",
    "ExecutionPreparationError",
    "ExecutionRegistryError",
    "ExecutionNotFoundError",
    "DuplicateExecutionError",
    "ExecutionCapacityError",
    "ExecutionEngineNotRunningError",
    "ExecutionStateError",
    "ExecutionCancelledError",
    # Data types
    "ExecutionRequest",
    "ExecutionContext",
    "ExecutionResult",
    "ExecutionSnapshot",
    "ExecutionEvent",
    "make_execution_event",
    "event_type_for_state",
    "ExecutionHistoryEntry",
    "ExecutionHistory",
    "make_history_entry",
    "ExecutionStatistics",
    "EngineStatistics",
    "ExecutionRecord",
    "RegistryStatistics",
    # Validation
    "ValidationResult",
    "ExecutionValidator",
    # Services
    "ExecutionFactory",
    "ExecutionRegistry",
    "ExecutionEngine",
    "ExecutionManager",
]
