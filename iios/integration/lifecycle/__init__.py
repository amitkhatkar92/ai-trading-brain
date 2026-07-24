"""
iios/integration/lifecycle/__init__.py
---------------------------------------
Public API for the Integration Lifecycle module.

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from .constants import (
    ACTIVE_STATES,
    ACTOR_LIFECYCLE,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    BUILD_VERSION,
    DEFAULT_MAX_ARCHIVED,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    DEFAULT_MAX_TRANSITIONS,
    DEFAULT_VERSION,
    FRAMEWORK_VERSION,
    IMMUTABLE_STATES,
    LIFECYCLE_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    SCHEMA_VERSION,
    SUCCESS_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VERSION,
    IntegrationEventType,
    IntegrationLifecycleState,
    IntegrationScope,
    IntegrationType,
    IntegrationValidationCode,
)
from .exceptions import (
    IntegrationCapacityError,
    IntegrationHistoryError,
    IntegrationInvalidTransitionError,
    IntegrationLifecycleError,
    IntegrationSessionNotFoundError,
    IntegrationSessionTerminatedError,
    IntegrationValidationError,
)
from .integration_context import IntegrationContext
from .integration_events import (
    IntegrationLifecycleEvent,
    IntegrationLifecycleEventBus,
)
from .integration_factory import IntegrationFactory
from .integration_history import IntegrationHistory
from .integration_lifecycle import IntegrationLifecycle
from .integration_metadata import IntegrationMetadata
from .integration_registry import IntegrationRegistry
from .integration_session import IntegrationSession
from .integration_state import IntegrationStateRecord
from .integration_statistics import (
    IntegrationLifecycleStatistics,
    IntegrationLifecycleStatisticsReport,
)
from .integration_transition import IntegrationTransition
from .integration_validation import (
    IntegrationValidationReport,
    IntegrationValidationResult,
    IntegrationValidator,
)

__all__ = [
    # Enums & constants
    "IntegrationLifecycleState",
    "IntegrationEventType",
    "IntegrationType",
    "IntegrationScope",
    "IntegrationValidationCode",
    "VALID_TRANSITIONS",
    "ACTIVE_STATES",
    "TERMINAL_STATES",
    "SUCCESS_STATES",
    "IMMUTABLE_STATES",
    "LIFECYCLE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "FRAMEWORK_VERSION",
    "BUILD_VERSION",
    "DEFAULT_VERSION",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_TRANSITIONS",
    "DEFAULT_MAX_ARCHIVED",
    "ACTOR_LIFECYCLE",
    "ACTOR_OPERATOR",
    "ACTOR_SYSTEM",
    # Exceptions
    "IntegrationLifecycleError",
    "IntegrationSessionNotFoundError",
    "IntegrationInvalidTransitionError",
    "IntegrationSessionTerminatedError",
    "IntegrationValidationError",
    "IntegrationCapacityError",
    "IntegrationHistoryError",
    # Data objects
    "IntegrationContext",
    "IntegrationMetadata",
    "IntegrationStateRecord",
    "IntegrationTransition",
    # Session
    "IntegrationSession",
    # Subsystems
    "IntegrationRegistry",
    "IntegrationHistory",
    "IntegrationLifecycleStatistics",
    "IntegrationLifecycleStatisticsReport",
    "IntegrationFactory",
    "IntegrationValidator",
    "IntegrationValidationResult",
    "IntegrationValidationReport",
    # Events
    "IntegrationLifecycleEvent",
    "IntegrationLifecycleEventBus",
    # Main lifecycle
    "IntegrationLifecycle",
]
