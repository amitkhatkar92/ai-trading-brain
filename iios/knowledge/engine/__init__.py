"""
__init__.py — iios.knowledge.engine
--------------------------------------
Public API surface of the Knowledge Engine subsystem.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from .constants import (
    ACTOR_ENGINE,
    ACTOR_OPERATOR,
    ACTOR_SCHEDULER,
    ACTOR_SYSTEM,
    DEFAULT_MAX_CONCURRENT_SESSIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_PIPELINES,
    DEFAULT_MAX_SCHEDULER_QUEUE,
    ENGINE_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    SCHEDULER_SYSTEM_ID,
    SCHEMA_VERSION,
    VERSION,
    EngineState,
    KnowledgeEventType,
    KnowledgeSource,
    KnowledgeValidationCode,
    KnowledgeWorkflowType,
    PipelineStatus,
    ResponseStatus,
    SchedulerMode,
    SchedulerPriority,
)
from .exceptions import (
    KnowledgeCapacityError,
    KnowledgeCollectionError,
    KnowledgeDispatchError,
    KnowledgeEngineError,
    KnowledgeEngineNotRunningError,
    KnowledgeEngineValidationError,
    KnowledgePipelineError,
    KnowledgePublicationError,
    KnowledgeSchedulerError,
    KnowledgeSessionError,
)
from .knowledge_context import KnowledgeEngineContext
from .knowledge_dispatcher import KnowledgeDispatcher
from .knowledge_engine import KnowledgeEngine
from .knowledge_events import KnowledgeEngineEvent, KnowledgeEngineEventBus
from .knowledge_factory import KnowledgeEngineFactory
from .knowledge_health import KnowledgeEngineHealth
from .knowledge_history import KnowledgeEngineHistory
from .knowledge_manager import KnowledgeWorkflowManager
from .knowledge_pipeline import KnowledgePipeline, PipelineStage
from .knowledge_registry import KnowledgeEngineRegistry
from .knowledge_request import KnowledgeRequest
from .knowledge_response import KnowledgeResponse, KnowledgeSnapshot
from .knowledge_scheduler import KnowledgeScheduler
from .knowledge_session_manager import KnowledgeSessionManager
from .knowledge_statistics import KnowledgeEngineStatistics
from .knowledge_status import KnowledgeEngineStatus
from .knowledge_validation import KnowledgeEngineValidator, ValidationResult

__all__ = [
    # Constants / enums
    "VERSION", "SCHEMA_VERSION", "ENGINE_SYSTEM_ID", "SCHEDULER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID", "FACTORY_SYSTEM_ID",
    "ACTOR_ENGINE", "ACTOR_OPERATOR", "ACTOR_SCHEDULER", "ACTOR_SYSTEM",
    "DEFAULT_MAX_CONCURRENT_SESSIONS", "DEFAULT_MAX_PIPELINES",
    "DEFAULT_MAX_HISTORY", "DEFAULT_MAX_SCHEDULER_QUEUE",
    "EngineState", "KnowledgeWorkflowType", "KnowledgeSource",
    "SchedulerPriority", "SchedulerMode", "PipelineStatus", "ResponseStatus",
    "KnowledgeValidationCode", "KnowledgeEventType",
    # Exceptions
    "KnowledgeEngineError", "KnowledgeEngineNotRunningError",
    "KnowledgeEngineValidationError", "KnowledgeSessionError",
    "KnowledgeCollectionError", "KnowledgePipelineError",
    "KnowledgeDispatchError", "KnowledgePublicationError",
    "KnowledgeSchedulerError", "KnowledgeCapacityError",
    # Core value objects
    "KnowledgeEngineContext", "KnowledgeRequest",
    "KnowledgeResponse", "KnowledgeSnapshot",
    "KnowledgePipeline", "PipelineStage",
    # Infrastructure
    "KnowledgeScheduler", "KnowledgeDispatcher",
    "KnowledgeSessionManager", "KnowledgeEngineRegistry",
    "KnowledgeEngineFactory", "KnowledgeEngineValidator", "ValidationResult",
    "KnowledgeEngineHealth", "KnowledgeEngineStatus",
    "KnowledgeEngineStatistics", "KnowledgeEngineHistory",
    "KnowledgeEngineEvent", "KnowledgeEngineEventBus",
    "KnowledgeWorkflowManager",
    # Primary façade
    "KnowledgeEngine",
]
