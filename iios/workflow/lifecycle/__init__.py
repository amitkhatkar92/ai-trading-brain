"""
iios/workflow/lifecycle/__init__.py
-------------------------------------
Public API for the Workflow Lifecycle module.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
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
    WorkflowEventType,
    WorkflowLifecycleState,
    WorkflowPriority,
    WorkflowType,
    WorkflowValidationCode,
)
from .exceptions import (
    WorkflowCapacityError,
    WorkflowHistoryError,
    WorkflowInvalidTransitionError,
    WorkflowLifecycleError,
    WorkflowSessionNotFoundError,
    WorkflowSessionTerminatedError,
    WorkflowValidationError,
)
from .workflow_context import WorkflowContext
from .workflow_events import (
    WorkflowLifecycleEvent,
    WorkflowLifecycleEventBus,
)
from .workflow_factory import WorkflowFactory
from .workflow_history import WorkflowHistory
from .workflow_lifecycle import WorkflowLifecycle
from .workflow_metadata import WorkflowMetadata
from .workflow_registry import WorkflowRegistry
from .workflow_session import WorkflowSession
from .workflow_state import WorkflowStateRecord
from .workflow_statistics import (
    WorkflowLifecycleStatistics,
    WorkflowLifecycleStatisticsReport,
)
from .workflow_transition import WorkflowTransition
from .workflow_validation import (
    WorkflowValidationReport,
    WorkflowValidationResult,
    WorkflowValidator,
)

__all__ = [
    # Enums & constants
    "WorkflowLifecycleState",
    "WorkflowEventType",
    "WorkflowType",
    "WorkflowPriority",
    "WorkflowValidationCode",
    "VALID_TRANSITIONS",
    "ACTIVE_STATES",
    "TERMINAL_STATES",
    "SUCCESS_STATES",
    "IMMUTABLE_STATES",
    "LIFECYCLE_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "VERSION",
    "FRAMEWORK_VERSION",
    "BUILD_VERSION",
    "SCHEMA_VERSION",
    "DEFAULT_VERSION",
    "DEFAULT_MAX_SESSIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_TRANSITIONS",
    "DEFAULT_MAX_ARCHIVED",
    "ACTOR_LIFECYCLE",
    "ACTOR_SYSTEM",
    "ACTOR_OPERATOR",
    # Exceptions
    "WorkflowLifecycleError",
    "WorkflowSessionNotFoundError",
    "WorkflowInvalidTransitionError",
    "WorkflowSessionTerminatedError",
    "WorkflowValidationError",
    "WorkflowCapacityError",
    "WorkflowHistoryError",
    # Core entities
    "WorkflowSession",
    "WorkflowContext",
    "WorkflowMetadata",
    "WorkflowStateRecord",
    "WorkflowTransition",
    # Lifecycle manager
    "WorkflowLifecycle",
    # Supporting infrastructure
    "WorkflowRegistry",
    "WorkflowHistory",
    "WorkflowFactory",
    "WorkflowValidator",
    "WorkflowValidationResult",
    "WorkflowValidationReport",
    "WorkflowLifecycleEvent",
    "WorkflowLifecycleEventBus",
    "WorkflowLifecycleStatistics",
    "WorkflowLifecycleStatisticsReport",
]
