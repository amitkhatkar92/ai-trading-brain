"""
iios.risk.engine
=================
Institutional Risk Engine subsystem.

Public API:
-----------
Primary interface
  RiskEngine                — primary public entry point (LifecycleAwareMixin)

Value objects
  RiskRequest               — immutable risk workflow request
  RiskResponse              — immutable risk workflow response
  RiskEngineSnapshot        — immutable risk snapshot
  RiskEngineContext         — immutable engine-level context
  RiskPipeline              — mutable workflow pipeline
  PipelineStage             — immutable stage record
  RiskEngineStatus          — immutable engine status snapshot
  RiskEngineEvent           — immutable domain event

Enumerations
  EngineState               — engine processing states
  RiskWorkflowType          — supported risk workflow types
  SchedulerPriority         — scheduling priority levels
  ResponseStatus            — response outcome statuses
  PipelineStatus            — pipeline execution statuses
  RiskEngineEventType       — event type enumeration

Component interfaces
  RiskDispatcher            — M3/M4 framework hook
  RiskScheduler             — priority queue scheduler
  RiskSessionManager        — M1 lifecycle wrapper
  RiskEngineRegistry        — pipeline + request store
  RiskEngineValidator       — input validation
  RiskEngineHealth          — health reporter
  RiskEngineStatistics      — thread-safe counters
  RiskEngineHistory         — bounded history store
  RiskEngineFactory         — value-object factory

Exceptions (RE-000 — RE-009)
  RiskEngineError            — RE-000 base
  RiskEngineNotRunningError  — RE-001
  RiskSessionError           — RE-002
  RiskPipelineError          — RE-003
  RiskDispatchError          — RE-004
  RiskCollectionError        — RE-005
  RiskPublicationError       — RE-006
  RiskEngineValidationError  — RE-007
  RiskSchedulerError         — RE-008
  RiskCapacityError          — RE-009

Event factory functions (nine)
  make_risk_initialized
  make_risk_started
  make_risk_collected
  make_risk_dispatched
  make_risk_assessment_started
  make_risk_published
  make_risk_completed
  make_risk_failed
  make_risk_stopped

Validation result types
  RiskEngineValidationResult
  RiskEngineValidationCheckResult

Constants
  ENGINE_SYSTEM_ID, VERSION, SCHEMA_VERSION
  ASSESSMENT_WORKFLOWS, MONITORING_WORKFLOWS
  VALID_ENGINE_TRANSITIONS, ACTIVE_ENGINE_STATES, TERMINAL_ENGINE_STATES
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
from .constants import (
    ENGINE_SYSTEM_ID,
    SCHEDULER_SYSTEM_ID,
    DISPATCHER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    VERSION,
    SCHEMA_VERSION,
    ACTOR_ENGINE,
    ACTOR_SCHEDULER,
    ACTOR_DISPATCHER,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    DEFAULT_MAX_PIPELINES,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SCHEDULER_QUEUE,
    DEFAULT_MAX_ARCHIVED_PIPELINES,
    DEFAULT_COLLECT_TIMEOUT_S,
    DEFAULT_DISPATCH_TIMEOUT_S,
    DEFAULT_PUBLISH_TIMEOUT_S,
    EngineState,
    VALID_ENGINE_TRANSITIONS,
    ACTIVE_ENGINE_STATES,
    TERMINAL_ENGINE_STATES,
    RiskWorkflowType,
    SchedulerPriority,
    ResponseStatus,
    PipelineStatus,
    RiskEngineEventType,
    ASSESSMENT_WORKFLOWS,
    MONITORING_WORKFLOWS,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
from .exceptions import (
    RiskEngineError,
    RiskEngineNotRunningError,
    RiskSessionError,
    RiskPipelineError,
    RiskDispatchError,
    RiskCollectionError,
    RiskPublicationError,
    RiskEngineValidationError,
    RiskSchedulerError,
    RiskCapacityError,
)

# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------
from .risk_context import RiskEngineContext
from .risk_request import RiskRequest
from .risk_response import RiskEngineSnapshot, RiskResponse
from .risk_pipeline import PipelineStage, RiskPipeline
from .risk_status import RiskEngineStatus
from .risk_events import (
    RiskEngineEvent,
    make_risk_initialized,
    make_risk_started,
    make_risk_collected,
    make_risk_dispatched,
    make_risk_assessment_started,
    make_risk_published,
    make_risk_completed,
    make_risk_failed,
    make_risk_stopped,
)

# ---------------------------------------------------------------------------
# Component interfaces
# ---------------------------------------------------------------------------
from .risk_scheduler import RiskScheduler
from .risk_dispatcher import RiskDispatcher
from .risk_session_manager import RiskSessionManager
from .risk_registry import RiskEngineRegistry
from .risk_validation import (
    RiskEngineValidator,
    RiskEngineValidationResult,
    RiskEngineValidationCheckResult,
)
from .risk_health import RiskEngineHealth
from .risk_statistics import RiskEngineStatistics
from .risk_history import RiskEngineHistory
from .risk_factory import RiskEngineFactory

# ---------------------------------------------------------------------------
# Primary public interface
# ---------------------------------------------------------------------------
from .risk_engine import RiskEngine

__all__ = [
    # Constants
    "ENGINE_SYSTEM_ID", "SCHEDULER_SYSTEM_ID", "DISPATCHER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID", "FACTORY_SYSTEM_ID", "VERSION", "SCHEMA_VERSION",
    "ACTOR_ENGINE", "ACTOR_SCHEDULER", "ACTOR_DISPATCHER",
    "ACTOR_OPERATOR", "ACTOR_SYSTEM",
    "DEFAULT_MAX_CONCURRENT_SESSIONS", "DEFAULT_MAX_PIPELINES",
    "DEFAULT_MAX_HISTORY", "DEFAULT_MAX_SCHEDULER_QUEUE",
    "DEFAULT_MAX_ARCHIVED_PIPELINES",
    "DEFAULT_COLLECT_TIMEOUT_S", "DEFAULT_DISPATCH_TIMEOUT_S",
    "DEFAULT_PUBLISH_TIMEOUT_S",
    # Enumerations
    "EngineState", "RiskWorkflowType", "SchedulerPriority",
    "ResponseStatus", "PipelineStatus", "RiskEngineEventType",
    "VALID_ENGINE_TRANSITIONS", "ACTIVE_ENGINE_STATES", "TERMINAL_ENGINE_STATES",
    "ASSESSMENT_WORKFLOWS", "MONITORING_WORKFLOWS",
    # Exceptions
    "RiskEngineError", "RiskEngineNotRunningError", "RiskSessionError",
    "RiskPipelineError", "RiskDispatchError", "RiskCollectionError",
    "RiskPublicationError", "RiskEngineValidationError",
    "RiskSchedulerError", "RiskCapacityError",
    # Value objects
    "RiskEngineContext", "RiskRequest", "RiskEngineSnapshot",
    "RiskResponse", "PipelineStage", "RiskPipeline",
    "RiskEngineStatus", "RiskEngineEvent",
    # Event factories
    "make_risk_initialized", "make_risk_started", "make_risk_collected",
    "make_risk_dispatched", "make_risk_assessment_started",
    "make_risk_published", "make_risk_completed",
    "make_risk_failed", "make_risk_stopped",
    # Components
    "RiskScheduler", "RiskDispatcher", "RiskSessionManager",
    "RiskEngineRegistry", "RiskEngineValidator",
    "RiskEngineValidationResult", "RiskEngineValidationCheckResult",
    "RiskEngineHealth", "RiskEngineStatistics",
    "RiskEngineHistory", "RiskEngineFactory",
    # Primary interface
    "RiskEngine",
]
