"""
iios.portfolio.lifecycle
========================
Portfolio Lifecycle subsystem.

Primary interface: :class:`PortfolioLifecycle`
"""
from .constants import (
    ACTIVE_STATES,
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_TRANSITIONS,
    IMMUTABLE_STATES,
    LIFECYCLE_SYSTEM_ID,
    TERMINAL_STATES,
    SUCCESS_STATES,
    VALID_TRANSITIONS,
    VERSION,
    PortfolioEventType,
    PortfolioObjective,
    PortfolioScope,
    PortfolioState,
    PortfolioStatus,
    PortfolioType,
    PortfolioValidationCode,
)
from .exceptions import (
    PortfolioCapacityExceededError,
    PortfolioConfigurationError,
    PortfolioHistoryError,
    PortfolioInvalidTransitionError,
    PortfolioLifecycleError,
    PortfolioLifecycleNotRunningError,
    PortfolioRegistryError,
    PortfolioSessionNotFoundError,
    PortfolioSessionTerminatedError,
    PortfolioValidationError,
)
from .portfolio_context import PortfolioContext
from .portfolio_events import (
    PortfolioEvent,
    make_portfolio_activated,
    make_portfolio_archived,
    make_portfolio_completed,
    make_portfolio_created,
    make_portfolio_failed,
    make_portfolio_initialized,
    make_portfolio_loaded,
    make_portfolio_paused,
    make_portfolio_rebalancing,
    make_portfolio_resumed,
    make_portfolio_validated,
)
from .portfolio_factory import PortfolioFactory
from .portfolio_history import PortfolioHistory
from .portfolio_lifecycle import PortfolioLifecycle
from .portfolio_metadata import PortfolioMetadata
from .portfolio_registry import PortfolioRegistry
from .portfolio_session import PortfolioSession
from .portfolio_state import PortfolioStateRecord, can_transition
from .portfolio_statistics import PortfolioStatistics
from .portfolio_transition import PortfolioTransition, make_transition
from .portfolio_validation import (
    PortfolioValidationCheckResult,
    PortfolioValidationResult,
    PortfolioValidator,
)

__all__ = [
    # Primary public interface
    "PortfolioLifecycle",
    # Session domain object
    "PortfolioSession",
    # Supporting objects
    "PortfolioContext",
    "PortfolioEvent",
    "PortfolioFactory",
    "PortfolioHistory",
    "PortfolioMetadata",
    "PortfolioRegistry",
    "PortfolioStateRecord",
    "PortfolioStatistics",
    "PortfolioTransition",
    "PortfolioValidationCheckResult",
    "PortfolioValidationResult",
    "PortfolioValidator",
    # Enums
    "PortfolioEventType",
    "PortfolioObjective",
    "PortfolioScope",
    "PortfolioState",
    "PortfolioStatus",
    "PortfolioType",
    "PortfolioValidationCode",
    # Exceptions
    "PortfolioLifecycleError",
    "PortfolioSessionNotFoundError",
    "PortfolioInvalidTransitionError",
    "PortfolioSessionTerminatedError",
    "PortfolioLifecycleNotRunningError",
    "PortfolioCapacityExceededError",
    "PortfolioValidationError",
    "PortfolioHistoryError",
    "PortfolioRegistryError",
    "PortfolioConfigurationError",
    # State-set constants
    "ACTIVE_STATES",
    "TERMINAL_STATES",
    "SUCCESS_STATES",
    "IMMUTABLE_STATES",
    "VALID_TRANSITIONS",
    # System constants
    "LIFECYCLE_SYSTEM_ID",
    "VERSION",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_ARCHIVED",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_TRANSITIONS",
    # Helpers
    "can_transition",
    "make_transition",
    # Event factories
    "make_portfolio_created",
    "make_portfolio_initialized",
    "make_portfolio_loaded",
    "make_portfolio_validated",
    "make_portfolio_activated",
    "make_portfolio_paused",
    "make_portfolio_resumed",
    "make_portfolio_rebalancing",
    "make_portfolio_completed",
    "make_portfolio_failed",
    "make_portfolio_archived",
]
