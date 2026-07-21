"""
iios.portfolio.engine
=====================
Institutional Portfolio Engine subsystem.

Primary interface: :class:`PortfolioEngine`
"""
from .constants import (
    ACTIVE_ENGINE_STATES,
    ACTOR_ENGINE,
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_PIPELINES,
    DEFAULT_MAX_SCHEDULER_QUEUE,
    ENGINE_SYSTEM_ID,
    TERMINAL_ENGINE_STATES,
    VALID_ENGINE_TRANSITIONS,
    VERSION,
    EngineState,
    PipelineStatus,
    PortfolioEventType,
    PortfolioOperationType,
    PortfolioWorkflowType,
    ResponseStatus,
    SchedulerPriority,
    ValidationCode,
)
from .exceptions import (
    PortfolioCapacityError,
    PortfolioCollectionError,
    PortfolioDispatchError,
    PortfolioEngineError,
    PortfolioEngineNotRunningError,
    PortfolioEngineValidationError,
    PortfolioPipelineError,
    PortfolioPublicationError,
    PortfolioSchedulerError,
    PortfolioSessionError,
)
from .portfolio_context import PortfolioContext
from .portfolio_dispatcher import PortfolioDispatcher
from .portfolio_engine import PortfolioEngine
from .portfolio_events import (
    PortfolioEngineEvent,
    make_portfolio_collected,
    make_portfolio_completed,
    make_portfolio_dispatched,
    make_portfolio_failed,
    make_portfolio_initialized,
    make_portfolio_published,
    make_portfolio_started,
    make_portfolio_stopped,
)
from .portfolio_factory import PortfolioEngineFactory
from .portfolio_health import PortfolioEngineHealth, SubsystemHealthRecord
from .portfolio_history import PortfolioEngineHistory
from .portfolio_manager import PortfolioManager
from .portfolio_pipeline import PortfolioPipeline, PipelineStage
from .portfolio_registry import PortfolioEngineRegistry
from .portfolio_request import PortfolioRequest
from .portfolio_response import PortfolioResponse, PortfolioSnapshot
from .portfolio_scheduler import PortfolioScheduler
from .portfolio_session_manager import PortfolioSessionManager
from .portfolio_statistics import PortfolioEngineStatistics
from .portfolio_status import PortfolioEngineStatus
from .portfolio_validation import (
    PortfolioEngineValidator,
    PortfolioValidationCheckResult,
    PortfolioValidationResult,
)

__all__ = [
    # Primary public interface
    "PortfolioEngine",
    # Request / Response / Snapshot
    "PortfolioRequest",
    "PortfolioResponse",
    "PortfolioSnapshot",
    # Context
    "PortfolioContext",
    # Domain objects
    "PortfolioPipeline",
    "PipelineStage",
    "PortfolioEngineEvent",
    # Sub-components
    "PortfolioDispatcher",
    "PortfolioEngineFactory",
    "PortfolioEngineHealth",
    "PortfolioEngineHistory",
    "PortfolioEngineRegistry",
    "PortfolioEngineStatistics",
    "PortfolioEngineStatus",
    "PortfolioEngineValidator",
    "PortfolioManager",
    "PortfolioScheduler",
    "PortfolioSessionManager",
    "SubsystemHealthRecord",
    # Validation
    "PortfolioValidationCheckResult",
    "PortfolioValidationResult",
    # Enums
    "EngineState",
    "PipelineStatus",
    "PortfolioEventType",
    "PortfolioOperationType",
    "PortfolioWorkflowType",
    "ResponseStatus",
    "SchedulerPriority",
    "ValidationCode",
    # Exceptions
    "PortfolioEngineError",
    "PortfolioEngineNotRunningError",
    "PortfolioSessionError",
    "PortfolioPipelineError",
    "PortfolioDispatchError",
    "PortfolioCollectionError",
    "PortfolioPublicationError",
    "PortfolioEngineValidationError",
    "PortfolioSchedulerError",
    "PortfolioCapacityError",
    # Constants
    "ENGINE_SYSTEM_ID",
    "VERSION",
    "ACTIVE_ENGINE_STATES",
    "TERMINAL_ENGINE_STATES",
    "VALID_ENGINE_TRANSITIONS",
    "DEFAULT_MAX_CONCURRENT_SESSIONS",
    "DEFAULT_MAX_PIPELINES",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_SCHEDULER_QUEUE",
    "ACTOR_ENGINE",
    # Event factories
    "make_portfolio_initialized",
    "make_portfolio_started",
    "make_portfolio_collected",
    "make_portfolio_dispatched",
    "make_portfolio_published",
    "make_portfolio_completed",
    "make_portfolio_failed",
    "make_portfolio_stopped",
]
