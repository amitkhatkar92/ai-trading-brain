"""
iios/execution/__init__.py

Execution Engine — Institutional Execution Platform for IIOS.

Entry points
------------
    from iios.execution import get_execution_engine, ExecutionEngine
    from iios.execution import ExecutionRequest, ExecutionResult

Singleton
---------
    engine = get_execution_engine()
    engine.initialize()
    result = engine.submit(request)
"""
from iios.execution.execution_constants import (
    ACTIVE_STATUSES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_WORKER_THREADS,
    EXECUTION_ENGINE_SYSTEM_ID,
    EXECUTION_ENGINE_VERSION,
    TERMINAL_STATUSES,
    ExecutionEventType,
    ExecutionMode,
    ExecutionPriority,
    ExecutionStatus,
    ExecutionType,
    TimeInForce,
    WorkflowStatus,
    WorkflowStepStatus,
)
from iios.execution.execution_exceptions import (
    EngineAlreadyRunningError,
    EngineError,
    EngineNotInitializedError,
    EngineShutdownError,
    ExecutionAlreadyExistsError,
    ExecutionError,
    ExecutionExpiredError,
    ExecutionInvalidError,
    ExecutionNotFoundError,
    ExecutionRequestError,
    ExecutionStateError,
    RegistryError,
    RegistryItemAlreadyExistsError,
    RegistryItemNotFoundError,
    RegistryOverflowError,
    SessionAlreadyExistsError,
    SessionError,
    SessionExpiredError,
    SessionNotFoundError,
    WorkflowCancelledError,
    WorkflowError,
    WorkflowExecutionError,
    WorkflowValidationError,
)
from iios.execution.core import (
    ExecutionHistory,
    ExecutionMetadata,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionResult,
    ExecutionSession,
    ExecutionState,
    ExecutionStatistics,
    StatusTransition,
)
from iios.execution.execution_context import (
    ExecutionContextState,
    execution_session,
    execution_stage_scope,
    get_execution_context,
    reset_execution_context,
)
from iios.execution.execution_factory  import ExecutionFactory
from iios.execution.execution_registry import (
    ExecutionRegistry,
    get_execution_registry,
    reset_execution_registry,
)
from iios.execution.execution_manager  import ExecutionManager
from iios.execution.execution_engine   import (
    ExecutionEngine,
    get_execution_engine,
    reset_execution_engine,
)

__version__ = "1.0.0"
__status__  = "production"
__layer__   = "EXECUTION"

__all__ = [
    # Engine
    "ExecutionEngine",
    "ExecutionManager",
    "ExecutionFactory",
    "ExecutionRegistry",
    "get_execution_engine",
    "reset_execution_engine",
    "get_execution_registry",
    "reset_execution_registry",
    # Context
    "ExecutionContextState",
    "get_execution_context",
    "reset_execution_context",
    "execution_session",
    "execution_stage_scope",
    # Core models
    "ExecutionRequest",
    "ExecutionPlan",
    "ExecutionSession",
    "ExecutionResult",
    "ExecutionState",
    "ExecutionStatistics",
    "ExecutionMetadata",
    "ExecutionHistory",
    "StatusTransition",
    # Constants
    "ExecutionStatus",
    "ExecutionMode",
    "ExecutionType",
    "ExecutionPriority",
    "ExecutionEventType",
    "WorkflowStatus",
    "WorkflowStepStatus",
    "TimeInForce",
    "EXECUTION_ENGINE_VERSION",
    "EXECUTION_ENGINE_SYSTEM_ID",
    "TERMINAL_STATUSES",
    "ACTIVE_STATUSES",
    # Exceptions
    "ExecutionError",
    "ExecutionNotFoundError",
    "ExecutionAlreadyExistsError",
    "ExecutionInvalidError",
    "ExecutionStateError",
    "ExecutionExpiredError",
    "WorkflowError",
    "WorkflowValidationError",
    "WorkflowExecutionError",
    "WorkflowCancelledError",
    "SessionError",
    "SessionNotFoundError",
    "SessionAlreadyExistsError",
    "SessionExpiredError",
    "EngineError",
    "EngineNotInitializedError",
    "EngineAlreadyRunningError",
    "EngineShutdownError",
    "RegistryError",
    "RegistryOverflowError",
    "RegistryItemNotFoundError",
    "RegistryItemAlreadyExistsError",
]

