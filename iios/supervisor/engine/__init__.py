"""
iios.supervisor.engine — AI Supervisor Engine
==============================================

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2

Public API surface.  All symbols below are guaranteed stable across
minor versions.

Quickstart
----------
>>> from iios.supervisor.engine import SupervisorEngine
>>> engine = SupervisorEngine()
>>> engine.start()
>>> response = engine.supervise("sup-001", "enterprise")
>>> engine.stop()
"""
from __future__ import annotations

from .constants import (
    VERSION,
    SCHEMA_VERSION,
    ENGINE_SYSTEM_ID,
    SCHEDULER_SYSTEM_ID,
    DISPATCHER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
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
    EngineState,
    SupervisorWorkflowType,
    SubsystemType,
    SchedulerPriority,
    ResponseStatus,
    PipelineStatus,
    SupervisorEngineEventType,
    SUPERVISION_WORKFLOWS,
    MONITORING_WORKFLOWS,
    VALID_ENGINE_TRANSITIONS,
    ACTIVE_ENGINE_STATES,
    TERMINAL_ENGINE_STATES,
)
from .exceptions import (
    SupervisorEngineError,
    SupervisorEngineNotRunningError,
    SupervisorSessionError,
    SupervisorPipelineError,
    SupervisorDispatchError,
    SupervisorCollectionError,
    SupervisorPublicationError,
    SupervisorEngineValidationError,
    SupervisorSchedulerError,
    SupervisorEngineCapacityError,
)
from .supervisor_context import SupervisorEngineContext
from .supervisor_request import SupervisorRequest
from .supervisor_response import SupervisorEngineSnapshot, SupervisorResponse
from .supervisor_pipeline import PipelineStage, SupervisorPipeline
from .supervisor_scheduler import SupervisorScheduler
from .supervisor_dispatcher import SupervisorDispatcher
from .supervisor_session_manager import SupervisorSessionManager
from .supervisor_registry import SupervisorEngineRegistry
from .supervisor_validation import (
    SupervisorEngineValidator,
    SupervisorEngineValidationCheckResult,
    SupervisorEngineValidationResult,
)
from .supervisor_health import SupervisorEngineHealth
from .supervisor_status import SupervisorEngineStatus
from .supervisor_statistics import SupervisorEngineStatistics
from .supervisor_history import SupervisorEngineHistory
from .supervisor_events import (
    SupervisorEngineEvent,
    make_supervisor_engine_initialized,
    make_supervisor_engine_started,
    make_supervisor_engine_collected,
    make_supervisor_engine_validated,
    make_supervisor_engine_dispatched,
    make_supervisor_engine_monitoring_started,
    make_supervisor_engine_published,
    make_supervisor_engine_completed,
    make_supervisor_engine_failed,
    make_supervisor_engine_stopped,
)
from .supervisor_factory import SupervisorEngineFactory
from .supervisor_manager import SupervisorWorkflowManager
from .supervisor_engine import SupervisorEngine

__all__ = [
    # ---- versioning -------------------------------------------------------
    "VERSION",
    "SCHEMA_VERSION",
    # ---- system identifiers -----------------------------------------------
    "ENGINE_SYSTEM_ID",
    "SCHEDULER_SYSTEM_ID",
    "DISPATCHER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    # ---- actor names -------------------------------------------------------
    "ACTOR_ENGINE",
    "ACTOR_SCHEDULER",
    "ACTOR_DISPATCHER",
    "ACTOR_OPERATOR",
    "ACTOR_SYSTEM",
    # ---- defaults ----------------------------------------------------------
    "DEFAULT_MAX_CONCURRENT_SESSIONS",
    "DEFAULT_MAX_PIPELINES",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_SCHEDULER_QUEUE",
    "DEFAULT_MAX_ARCHIVED_PIPELINES",
    # ---- enumerations ------------------------------------------------------
    "EngineState",
    "SupervisorWorkflowType",
    "SubsystemType",
    "SchedulerPriority",
    "ResponseStatus",
    "PipelineStatus",
    "SupervisorEngineEventType",
    # ---- frozensets --------------------------------------------------------
    "SUPERVISION_WORKFLOWS",
    "MONITORING_WORKFLOWS",
    "VALID_ENGINE_TRANSITIONS",
    "ACTIVE_ENGINE_STATES",
    "TERMINAL_ENGINE_STATES",
    # ---- exceptions --------------------------------------------------------
    "SupervisorEngineError",
    "SupervisorEngineNotRunningError",
    "SupervisorSessionError",
    "SupervisorPipelineError",
    "SupervisorDispatchError",
    "SupervisorCollectionError",
    "SupervisorPublicationError",
    "SupervisorEngineValidationError",
    "SupervisorSchedulerError",
    "SupervisorEngineCapacityError",
    # ---- value objects -----------------------------------------------------
    "SupervisorEngineContext",
    "SupervisorRequest",
    "SupervisorEngineSnapshot",
    "SupervisorResponse",
    "PipelineStage",
    "SupervisorPipeline",
    # ---- engine event objects ----------------------------------------------
    "SupervisorEngineEvent",
    "make_supervisor_engine_initialized",
    "make_supervisor_engine_started",
    "make_supervisor_engine_collected",
    "make_supervisor_engine_validated",
    "make_supervisor_engine_dispatched",
    "make_supervisor_engine_monitoring_started",
    "make_supervisor_engine_published",
    "make_supervisor_engine_completed",
    "make_supervisor_engine_failed",
    "make_supervisor_engine_stopped",
    # ---- subsystems --------------------------------------------------------
    "SupervisorScheduler",
    "SupervisorDispatcher",
    "SupervisorSessionManager",
    "SupervisorEngineRegistry",
    "SupervisorEngineValidator",
    "SupervisorEngineValidationCheckResult",
    "SupervisorEngineValidationResult",
    "SupervisorEngineHealth",
    "SupervisorEngineStatus",
    "SupervisorEngineStatistics",
    "SupervisorEngineHistory",
    "SupervisorEngineFactory",
    "SupervisorWorkflowManager",
    # ---- PRIMARY PUBLIC INTERFACE ------------------------------------------
    "SupervisorEngine",
]
