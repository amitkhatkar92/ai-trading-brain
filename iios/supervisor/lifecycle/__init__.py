"""
iios.supervisor.lifecycle
==========================
AI Supervisor Lifecycle subsystem — C13 AI Supervisor & Autonomous Governance,
Phase 1, Module 1.

Primary interface: :class:`SupervisorLifecycle`
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
    SupervisorEventType,
    SupervisorPriority,
    SupervisorScope,
    SupervisorState,
    SupervisorType,
    SupervisorValidationCode,
)
from .exceptions import (
    SupervisorLifecycleError,
    SupervisorSessionNotFoundError,
    SupervisorInvalidTransitionError,
    SupervisorSessionTerminatedError,
    SupervisorLifecycleNotRunningError,
    SupervisorCapacityExceededError,
    SupervisorValidationError,
    SupervisorHistoryError,
    SupervisorRegistryError,
    SupervisorConfigurationError,
)
from .supervisor_context import SupervisorContext
from .supervisor_events import (
    SupervisorEvent,
    make_supervisor_archived,
    make_supervisor_completed,
    make_supervisor_created,
    make_supervisor_failed,
    make_supervisor_initialized,
    make_supervisor_monitoring_started,
    make_supervisor_paused,
    make_supervisor_resumed,
    make_supervisor_started,
    make_supervisor_validated,
)
from .supervisor_factory import SupervisorFactory
from .supervisor_history import SupervisorHistory
from .supervisor_lifecycle import SupervisorLifecycle
from .supervisor_metadata import SupervisorMetadata
from .supervisor_registry import SupervisorRegistry
from .supervisor_session import SupervisorSession
from .supervisor_state import SupervisorStateRecord, can_transition
from .supervisor_statistics import SupervisorStatistics
from .supervisor_transition import SupervisorTransition, make_transition
from .supervisor_validation import (
    SupervisorValidationCheckResult,
    SupervisorValidationResult,
    SupervisorValidator,
)

__all__ = [
    # Primary interface
    "SupervisorLifecycle",
    # Session domain object
    "SupervisorSession",
    # Supporting value objects
    "SupervisorContext",
    "SupervisorMetadata",
    "SupervisorStateRecord",
    "SupervisorTransition",
    # Events
    "SupervisorEvent",
    "make_supervisor_archived",
    "make_supervisor_completed",
    "make_supervisor_created",
    "make_supervisor_failed",
    "make_supervisor_initialized",
    "make_supervisor_monitoring_started",
    "make_supervisor_paused",
    "make_supervisor_resumed",
    "make_supervisor_started",
    "make_supervisor_validated",
    # Factory
    "SupervisorFactory",
    # History
    "SupervisorHistory",
    # Registry
    "SupervisorRegistry",
    # Statistics
    "SupervisorStatistics",
    # Validation
    "SupervisorValidationCheckResult",
    "SupervisorValidationResult",
    "SupervisorValidator",
    # State helpers
    "can_transition",
    "make_transition",
    # Enumerations
    "SupervisorEventType",
    "SupervisorPriority",
    "SupervisorScope",
    "SupervisorState",
    "SupervisorType",
    "SupervisorValidationCode",
    # Constants
    "ACTIVE_STATES",
    "TERMINAL_STATES",
    "IMMUTABLE_STATES",
    "SUCCESS_STATES",
    "VALID_TRANSITIONS",
    "LIFECYCLE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VERSION",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_ARCHIVED",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_TRANSITIONS",
    # Exceptions
    "SupervisorLifecycleError",
    "SupervisorSessionNotFoundError",
    "SupervisorInvalidTransitionError",
    "SupervisorSessionTerminatedError",
    "SupervisorLifecycleNotRunningError",
    "SupervisorCapacityExceededError",
    "SupervisorValidationError",
    "SupervisorHistoryError",
    "SupervisorRegistryError",
    "SupervisorConfigurationError",
]
