"""
iios.risk.lifecycle
====================
Risk Lifecycle subsystem.

Primary interface: :class:`RiskLifecycle`

C11 Risk Intelligence — Phase 1, Module 1
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
    RiskEventType,
    RiskPriority,
    RiskScope,
    RiskState,
    RiskType,
    RiskValidationCode,
)
from .exceptions import (
    RiskLifecycleError,
    RiskSessionNotFoundError,
    RiskInvalidTransitionError,
    RiskSessionTerminatedError,
    RiskLifecycleNotRunningError,
    RiskCapacityExceededError,
    RiskValidationError,
    RiskHistoryError,
    RiskRegistryError,
    RiskConfigurationError,
)
from .risk_context import RiskContext
from .risk_events import (
    RiskEvent,
    make_risk_archived,
    make_risk_assessment_started,
    make_risk_collected,
    make_risk_completed,
    make_risk_created,
    make_risk_failed,
    make_risk_initialized,
    make_risk_monitoring_started,
    make_risk_paused,
    make_risk_resumed,
    make_risk_validated,
)
from .risk_factory import RiskFactory
from .risk_history import RiskHistory
from .risk_lifecycle import RiskLifecycle
from .risk_metadata import RiskMetadata
from .risk_registry import RiskRegistry
from .risk_session import RiskSession
from .risk_state import RiskStateRecord, can_transition
from .risk_statistics import RiskStatistics
from .risk_transition import RiskTransition, make_transition
from .risk_validation import (
    RiskValidationCheckResult,
    RiskValidationResult,
    RiskValidator,
)

__all__ = [
    # Primary public interface
    "RiskLifecycle",
    # Session domain object
    "RiskSession",
    # Supporting objects
    "RiskContext",
    "RiskEvent",
    "RiskFactory",
    "RiskHistory",
    "RiskMetadata",
    "RiskRegistry",
    "RiskStateRecord",
    "RiskStatistics",
    "RiskTransition",
    "RiskValidationCheckResult",
    "RiskValidationResult",
    "RiskValidator",
    # Enums
    "RiskEventType",
    "RiskPriority",
    "RiskScope",
    "RiskState",
    "RiskType",
    "RiskValidationCode",
    # Exceptions
    "RiskLifecycleError",
    "RiskSessionNotFoundError",
    "RiskInvalidTransitionError",
    "RiskSessionTerminatedError",
    "RiskLifecycleNotRunningError",
    "RiskCapacityExceededError",
    "RiskValidationError",
    "RiskHistoryError",
    "RiskRegistryError",
    "RiskConfigurationError",
    # State-set constants
    "ACTIVE_STATES",
    "TERMINAL_STATES",
    "SUCCESS_STATES",
    "IMMUTABLE_STATES",
    "VALID_TRANSITIONS",
    # System constants
    "LIFECYCLE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VERSION",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_ARCHIVED",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_TRANSITIONS",
    # Helpers
    "can_transition",
    "make_transition",
    # Event factories
    "make_risk_created",
    "make_risk_initialized",
    "make_risk_collected",
    "make_risk_validated",
    "make_risk_assessment_started",
    "make_risk_monitoring_started",
    "make_risk_paused",
    "make_risk_resumed",
    "make_risk_completed",
    "make_risk_failed",
    "make_risk_archived",
]
