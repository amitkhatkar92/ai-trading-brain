"""iios/execution/gateway/engine/__init__.py
==================================================
Public API for the IIOS Execution Gateway Engine.

C6 Execution Intelligence — Phase 5, Module 2

Primary entry point
-------------------
    from iios.execution.gateway.engine import ExecutionGatewayEngine
    from iios.execution.gateway.engine import EngineGatewayContext

    engine = ExecutionGatewayEngine()
    engine.start()

    ctx = engine.make_context(
        execution_id="EX-001",
        order_id="ORD-001",
        portfolio_id="PORT-A",
        strategy_id="STRAT-1",
    )
    response = engine.submit_request(ctx)
    engine.stop()
"""

# ── Primary engine ────────────────────────────────────────────────────────────
from .execution_gateway_engine import ExecutionGatewayEngine

# ── Manager ───────────────────────────────────────────────────────────────────
from .gateway_manager import GatewayManager

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (
    ENGINE_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    DISPATCHER_SYSTEM_ID,
    SESSION_SYSTEM_ID,
    VERSION,
    EngineState,
    EngineEventType,
    OperationType,
    QueueType,
    RequestStatus,
    SessionStatus,
    DispatchOutcome,
    ACTIVE_ENGINE_STATES,
    TERMINAL_ENGINE_STATES,
    ACTIVE_REQUEST_STATUSES,
    TERMINAL_REQUEST_STATUSES,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_QUEUE_SIZE,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_SESSION_TIMEOUT_SECS,
    DEFAULT_RETRY_DELAY_SECS,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    ExecutionGatewayEngineError,
    GatewayEngineNotRunningError,
    GatewayRequestSubmissionError,
    GatewayDispatchError,
    GatewayQueueFullError,
    GatewaySessionNotFoundError,
    GatewaySessionExpiredError,
    GatewayValidationFailedError,
    GatewayEngineRequestNotFoundError,
    DuplicateEngineRequestError,
    GatewayRegistryCapacityError,
)

# ── Context ───────────────────────────────────────────────────────────────────
from .gateway_context import EngineGatewayContext, make_engine_gateway_context

# ── Request ───────────────────────────────────────────────────────────────────
from .gateway_request import EngineGatewayRequest

# ── Response ──────────────────────────────────────────────────────────────────
from .gateway_response import GatewayResponse

# ── Operation ─────────────────────────────────────────────────────────────────
from .gateway_operation import GatewayOperation, make_gateway_operation

# ── Events ────────────────────────────────────────────────────────────────────
from .gateway_events import (
    GatewayEngineEvent,
    make_gateway_started_event,
    make_request_received_event,
    make_request_queued_event,
    make_request_dispatched_event,
    make_dispatch_completed_event,
    make_dispatch_failed_event,
    make_gateway_stopped_event,
)

# ── Statistics ────────────────────────────────────────────────────────────────
from .gateway_statistics import GatewayEngineStatistics

# ── Snapshot ──────────────────────────────────────────────────────────────────
from .gateway_snapshot import GatewayEngineSnapshot, GatewayRequestSummary

# ── History ───────────────────────────────────────────────────────────────────
from .gateway_history import GatewayEngineHistory

# ── Session ───────────────────────────────────────────────────────────────────
from .gateway_session import GatewaySession, GatewaySessionManager

# ── Queue ─────────────────────────────────────────────────────────────────────
from .gateway_operation_queue import (
    GatewayOperationQueue,
    FifoQueue,
    EnginePriorityQueue,
    RetryQueue,
    CancellationQueue,
    QueueStatistics,
)

# ── Factory ───────────────────────────────────────────────────────────────────
from .gateway_factory import GatewayEngineFactory

# ── Registry ──────────────────────────────────────────────────────────────────
from .gateway_registry import GatewayEngineRegistry

# ── Validation ────────────────────────────────────────────────────────────────
from .gateway_validation import EngineGatewayValidator, EngineValidationResult

# ── Dispatcher ────────────────────────────────────────────────────────────────
from .gateway_dispatcher import (
    GatewayDispatcher,
    DispatchResult,
    RouteDecision,
    BrokerAbstractionProtocol,
    RoutingFrameworkProtocol,
    SimulatedDispatch,
)

# ── State manager ─────────────────────────────────────────────────────────────
from .gateway_state_manager import GatewayStateManager


__all__ = [
    # Engine
    "ExecutionGatewayEngine",
    "GatewayManager",
    # Constants
    "ENGINE_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "DISPATCHER_SYSTEM_ID",
    "SESSION_SYSTEM_ID",
    "VERSION",
    "EngineState",
    "EngineEventType",
    "OperationType",
    "QueueType",
    "RequestStatus",
    "SessionStatus",
    "DispatchOutcome",
    "ACTIVE_ENGINE_STATES",
    "TERMINAL_ENGINE_STATES",
    "ACTIVE_REQUEST_STATUSES",
    "TERMINAL_REQUEST_STATUSES",
    "DEFAULT_MAX_REQUESTS",
    "DEFAULT_MAX_QUEUE_SIZE",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_SESSION_TIMEOUT_SECS",
    "DEFAULT_RETRY_DELAY_SECS",
    # Exceptions
    "ExecutionGatewayEngineError",
    "GatewayEngineNotRunningError",
    "GatewayRequestSubmissionError",
    "GatewayDispatchError",
    "GatewayQueueFullError",
    "GatewaySessionNotFoundError",
    "GatewaySessionExpiredError",
    "GatewayValidationFailedError",
    "GatewayEngineRequestNotFoundError",
    "DuplicateEngineRequestError",
    "GatewayRegistryCapacityError",
    # Domain objects
    "EngineGatewayContext",
    "make_engine_gateway_context",
    "EngineGatewayRequest",
    "GatewayResponse",
    "GatewayOperation",
    "make_gateway_operation",
    # Events
    "GatewayEngineEvent",
    "make_gateway_started_event",
    "make_request_received_event",
    "make_request_queued_event",
    "make_request_dispatched_event",
    "make_dispatch_completed_event",
    "make_dispatch_failed_event",
    "make_gateway_stopped_event",
    # Stats / snapshot / history
    "GatewayEngineStatistics",
    "GatewayEngineSnapshot",
    "GatewayRequestSummary",
    "GatewayEngineHistory",
    # Session
    "GatewaySession",
    "GatewaySessionManager",
    # Queue
    "GatewayOperationQueue",
    "FifoQueue",
    "EnginePriorityQueue",
    "RetryQueue",
    "CancellationQueue",
    "QueueStatistics",
    # Factory / registry / validation
    "GatewayEngineFactory",
    "GatewayEngineRegistry",
    "EngineGatewayValidator",
    "EngineValidationResult",
    # Dispatcher
    "GatewayDispatcher",
    "DispatchResult",
    "RouteDecision",
    "BrokerAbstractionProtocol",
    "RoutingFrameworkProtocol",
    "SimulatedDispatch",
    # State manager
    "GatewayStateManager",
]
