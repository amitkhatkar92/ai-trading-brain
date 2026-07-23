"""
iios.market.lifecycle
======================
Market Lifecycle subsystem — C12 Market Intelligence, Phase 1, Module 1.

Primary interface: :class:`MarketLifecycle`
"""
from .constants import (
    ACTIVE_STATES,
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_TRANSITIONS,
    IMMUTABLE_STATES,
    LIFECYCLE_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    TERMINAL_STATES,
    SUCCESS_STATES,
    VALID_TRANSITIONS,
    VERSION,
    MarketEventType,
    MarketPriority,
    MarketScope,
    MarketState,
    MarketTimeframe,
    MarketType,
    MarketValidationCode,
)
from .exceptions import (
    MarketLifecycleError,
    MarketSessionNotFoundError,
    MarketInvalidTransitionError,
    MarketSessionTerminatedError,
    MarketLifecycleNotRunningError,
    MarketCapacityExceededError,
    MarketValidationError,
    MarketHistoryError,
    MarketRegistryError,
    MarketConfigurationError,
)
from .market_context import MarketContext
from .market_events import (
    MarketEvent,
    make_market_archived,
    make_market_analysis_started,
    make_market_collected,
    make_market_completed,
    make_market_created,
    make_market_failed,
    make_market_initialized,
    make_market_monitoring_started,
    make_market_paused,
    make_market_resumed,
    make_market_validated,
)
from .market_factory import MarketFactory
from .market_history import MarketHistory
from .market_lifecycle import MarketLifecycle
from .market_metadata import MarketMetadata
from .market_registry import MarketRegistry
from .market_session import MarketSession
from .market_state import MarketStateRecord, can_transition
from .market_statistics import MarketStatistics
from .market_transition import MarketTransition, make_transition
from .market_validation import (
    MarketValidationCheckResult,
    MarketValidationResult,
    MarketValidator,
)

__all__ = [
    # Primary interface
    "MarketLifecycle",
    # Session domain object
    "MarketSession",
    # Supporting value objects
    "MarketContext",
    "MarketMetadata",
    "MarketStateRecord",
    "MarketTransition",
    # Events
    "MarketEvent",
    "make_market_archived",
    "make_market_analysis_started",
    "make_market_collected",
    "make_market_completed",
    "make_market_created",
    "make_market_failed",
    "make_market_initialized",
    "make_market_monitoring_started",
    "make_market_paused",
    "make_market_resumed",
    "make_market_validated",
    # Factory
    "MarketFactory",
    # History
    "MarketHistory",
    # Registry
    "MarketRegistry",
    # Statistics
    "MarketStatistics",
    # Validation
    "MarketValidationCheckResult",
    "MarketValidationResult",
    "MarketValidator",
    # Helpers
    "can_transition",
    "make_transition",
    # Constants
    "LIFECYCLE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VERSION",
    "ACTIVE_STATES",
    "TERMINAL_STATES",
    "IMMUTABLE_STATES",
    "SUCCESS_STATES",
    "VALID_TRANSITIONS",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_ARCHIVED",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_TRANSITIONS",
    # Enums
    "MarketEventType",
    "MarketPriority",
    "MarketScope",
    "MarketState",
    "MarketTimeframe",
    "MarketType",
    "MarketValidationCode",
    # Exceptions
    "MarketLifecycleError",
    "MarketSessionNotFoundError",
    "MarketInvalidTransitionError",
    "MarketSessionTerminatedError",
    "MarketLifecycleNotRunningError",
    "MarketCapacityExceededError",
    "MarketValidationError",
    "MarketHistoryError",
    "MarketRegistryError",
    "MarketConfigurationError",
]
