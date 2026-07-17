"""iios/execution/monitoring/lifecycle/__init__.py
==================================================
Public API for the Execution Monitoring Lifecycle package.

C6 Execution Intelligence — Phase 6, Module 1
"""
from .constants import (
    ACTIVE_STATES,
    ACTOR_FACTORY,
    ACTOR_LIFECYCLE,
    ACTOR_REGISTRY,
    ACTOR_SYSTEM,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    ENDED_STATES,
    FACTORY_SYSTEM_ID,
    FAILURE_STATES,
    LIFECYCLE_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    RUNNING_STATES,
    SCHEMA_VERSION,
    SUCCESS_STATES,
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    MonitoringEventType,
    MonitoringState,
)
from .exceptions import (
    InvalidMonitoringTransitionError,
    MonitoringLifecycleError,
    MonitoringLifecycleNotRunningError,
    MonitoringRegistryCapacityError,
    MonitoringSessionAlreadyExistsError,
    MonitoringSessionNotFoundError,
    MonitoringSessionTerminalError,
    MonitoringValidationError,
)
from .monitoring_context import MonitoringContext, make_monitoring_context
from .monitoring_events import (
    MonitoringEvent,
    make_monitoring_archived,
    make_monitoring_created,
    make_monitoring_failed,
    make_monitoring_initialized,
    make_monitoring_paused,
    make_monitoring_resumed,
    make_monitoring_started,
    make_monitoring_stopped,
)
from .monitoring_factory import MonitoringFactory
from .monitoring_history import MonitoringHistory
from .monitoring_lifecycle import MonitoringLifecycle
from .monitoring_metadata import MonitoringMetadata, make_monitoring_metadata
from .monitoring_registry import MonitoringRegistry
from .monitoring_session import MonitoringSession
from .monitoring_state import MonitoringStateRecord
from .monitoring_statistics import MonitoringStatistics
from .monitoring_transition import MonitoringTransition, make_monitoring_transition
from .monitoring_validation import MonitoringValidator, ValidationResult

__all__ = [
    # Constants
    "ACTIVE_STATES",
    "ACTOR_FACTORY",
    "ACTOR_LIFECYCLE",
    "ACTOR_REGISTRY",
    "ACTOR_SYSTEM",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_SESSIONS",
    "ENDED_STATES",
    "FACTORY_SYSTEM_ID",
    "FAILURE_STATES",
    "LIFECYCLE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "RUNNING_STATES",
    "SCHEMA_VERSION",
    "SUCCESS_STATES",
    "TERMINAL_STATES",
    "VALID_TRANSITIONS",
    "VALIDATOR_SYSTEM_ID",
    "VERSION",
    "MonitoringEventType",
    "MonitoringState",
    # Exceptions
    "InvalidMonitoringTransitionError",
    "MonitoringLifecycleError",
    "MonitoringLifecycleNotRunningError",
    "MonitoringRegistryCapacityError",
    "MonitoringSessionAlreadyExistsError",
    "MonitoringSessionNotFoundError",
    "MonitoringSessionTerminalError",
    "MonitoringValidationError",
    # Context / metadata
    "MonitoringContext",
    "make_monitoring_context",
    "MonitoringMetadata",
    "make_monitoring_metadata",
    # State / transition
    "MonitoringStateRecord",
    "MonitoringTransition",
    "make_monitoring_transition",
    # Events
    "MonitoringEvent",
    "make_monitoring_archived",
    "make_monitoring_created",
    "make_monitoring_failed",
    "make_monitoring_initialized",
    "make_monitoring_paused",
    "make_monitoring_resumed",
    "make_monitoring_started",
    "make_monitoring_stopped",
    # History / statistics
    "MonitoringHistory",
    "MonitoringStatistics",
    # Validation
    "MonitoringValidator",
    "ValidationResult",
    # Domain objects
    "MonitoringSession",
    # Infrastructure
    "MonitoringRegistry",
    "MonitoringFactory",
    # Primary API
    "MonitoringLifecycle",
]
