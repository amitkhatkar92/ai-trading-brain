"""
__init__.py — iios.market.engine
===================================
Public API for the Institutional Market Engine subsystem.

C12 Market Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

# Primary interface
from .market_engine import MarketEngine

# Value objects
from .market_context import MarketEngineContext
from .market_request import MarketRequest
from .market_response import MarketEngineSnapshot, MarketResponse
from .market_pipeline import MarketPipeline, PipelineStage
from .market_status import MarketEngineStatus

# Events
from .market_events import (
    MarketEngineEvent,
    MarketEngineEventType,
    make_market_engine_analysis_started,
    make_market_engine_collected,
    make_market_engine_completed,
    make_market_engine_dispatched,
    make_market_engine_failed,
    make_market_engine_initialized,
    make_market_engine_published,
    make_market_engine_started,
    make_market_engine_stopped,
)

# Re-export MarketEngineEventType alias
from .constants import MarketEngineEventType

# Sub-components
from .market_dispatcher import MarketDispatcher
from .market_factory import MarketEngineFactory
from .market_health import MarketEngineHealth
from .market_history import MarketEngineHistory
from .market_manager import MarketManager
from .market_registry import MarketEngineRegistry
from .market_scheduler import MarketScheduler
from .market_session_manager import MarketSessionManager
from .market_statistics import MarketEngineStatistics
from .market_validation import (
    MarketEngineValidator,
    MarketEngineValidationResult,
    MarketEngineValidationCheckResult,
)

# Enums & constants
from .constants import (
    ENGINE_SYSTEM_ID,
    SCHEDULER_SYSTEM_ID,
    DISPATCHER_SYSTEM_ID,
    VERSION,
    SCHEMA_VERSION,
    ACTOR_ENGINE,
    ACTOR_SYSTEM,
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    DEFAULT_MAX_PIPELINES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SCHEDULER_QUEUE,
    EngineState,
    MarketWorkflowType,
    SchedulerPriority,
    ResponseStatus,
    PipelineStatus,
    VALID_ENGINE_TRANSITIONS,
    ACTIVE_ENGINE_STATES,
    TERMINAL_ENGINE_STATES,
    ANALYSIS_WORKFLOWS,
    MONITORING_WORKFLOWS,
)

# Exceptions
from .exceptions import (
    MarketEngineError,
    MarketEngineCapacityError,
    MarketCollectionError,
    MarketDispatchError,
    MarketEngineNotRunningError,
    MarketEngineValidationError,
    MarketPipelineError,
    MarketPublicationError,
    MarketSchedulerError,
    MarketSessionError,
)

__all__ = [
    # Primary interface
    "MarketEngine",
    # Value objects
    "MarketEngineContext",
    "MarketRequest",
    "MarketEngineSnapshot",
    "MarketResponse",
    "MarketPipeline",
    "PipelineStage",
    "MarketEngineStatus",
    # Events
    "MarketEngineEvent",
    "MarketEngineEventType",
    "make_market_engine_analysis_started",
    "make_market_engine_collected",
    "make_market_engine_completed",
    "make_market_engine_dispatched",
    "make_market_engine_failed",
    "make_market_engine_initialized",
    "make_market_engine_published",
    "make_market_engine_started",
    "make_market_engine_stopped",
    # Sub-components
    "MarketDispatcher",
    "MarketEngineFactory",
    "MarketEngineHealth",
    "MarketEngineHistory",
    "MarketManager",
    "MarketEngineRegistry",
    "MarketScheduler",
    "MarketSessionManager",
    "MarketEngineStatistics",
    "MarketEngineValidator",
    "MarketEngineValidationResult",
    "MarketEngineValidationCheckResult",
    # Enums & constants
    "ENGINE_SYSTEM_ID",
    "SCHEDULER_SYSTEM_ID",
    "DISPATCHER_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "ACTOR_ENGINE",
    "ACTOR_SYSTEM",
    "DEFAULT_MAX_CONCURRENT_SESSIONS",
    "DEFAULT_MAX_PIPELINES",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_SCHEDULER_QUEUE",
    "EngineState",
    "MarketWorkflowType",
    "SchedulerPriority",
    "ResponseStatus",
    "PipelineStatus",
    "VALID_ENGINE_TRANSITIONS",
    "ACTIVE_ENGINE_STATES",
    "TERMINAL_ENGINE_STATES",
    "ANALYSIS_WORKFLOWS",
    "MONITORING_WORKFLOWS",
    # Exceptions
    "MarketEngineError",
    "MarketEngineCapacityError",
    "MarketCollectionError",
    "MarketDispatchError",
    "MarketEngineNotRunningError",
    "MarketEngineValidationError",
    "MarketPipelineError",
    "MarketPublicationError",
    "MarketSchedulerError",
    "MarketSessionError",
]
