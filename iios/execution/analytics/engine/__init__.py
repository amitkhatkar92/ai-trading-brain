"""
iios/execution/analytics/engine/__init__.py
==========================================
Public API for the C8 Execution Analytics Engine.

Primary entry point: ExecutionAnalyticsEngine

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

# ── Primary entry point ───────────────────────────────────────────────────────
from .execution_analytics_engine import ExecutionAnalyticsEngine  # noqa: F401

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (  # noqa: F401
    ENGINE_SYSTEM_ID,
    MANAGER_SYSTEM_ID,
    SCHEDULER_SYSTEM_ID,
    DISPATCHER_SYSTEM_ID,
    SESSION_MGR_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    VERSION,
    SCHEMA_VERSION,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_PIPELINES,
    DEFAULT_SCHEDULER_QUEUE,
    DEFAULT_MAX_SESSIONS,
    ACTOR_ENGINE,
    ACTOR_MANAGER,
    ACTOR_SCHEDULER,
    ACTOR_DISPATCHER,
    ACTOR_SYSTEM,
    ACTOR_OPERATOR,
    EngineAnalyticsState,
    ENGINE_STATE_TRANSITIONS,
    ACTIVE_ENGINE_STATES,
    TERMINAL_ENGINE_STATES,
    EngineOperation,
    AnalyticsRequestType,
    PipelineStage,
    PipelineStatus,
    ResponseStatus,
    ScheduleType,
    EngineHealthStatus,
    EngineEventType,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (  # noqa: F401
    AnalyticsEngineError,
    AnalyticsEngineNotRunningError,
    AnalyticsEngineAlreadyRunningError,
    AnalyticsRequestNotFoundError,
    AnalyticsRequestValidationError,
    AnalyticsPipelineError,
    AnalyticsSessionManagerError,
    AnalyticsDispatchError,
    AnalyticsSchedulerError,
    AnalyticsPublishError,
)

# ── Request / Response ────────────────────────────────────────────────────────
from .analytics_request import (  # noqa: F401
    AnalyticsRequest,
    make_analytics_request,
)
from .analytics_response import (  # noqa: F401
    AnalyticsResponse,
    AnalyticsSnapshot,
    make_analytics_response,
    make_analytics_snapshot,
)
from .analytics_context import (  # noqa: F401
    EngineAnalyticsContext,
    make_engine_analytics_context,
)

# ── Pipeline ──────────────────────────────────────────────────────────────────
from .analytics_pipeline import (  # noqa: F401
    AnalyticsPipeline,
    make_analytics_pipeline,
)

# ── Events ────────────────────────────────────────────────────────────────────
from .analytics_events import (  # noqa: F401
    EngineAnalyticsEvent,
    make_analytics_engine_initialized,
    make_analytics_engine_started,
    make_analytics_engine_collected,
    make_analytics_engine_dispatched,
    make_analytics_engine_completed,
    make_analytics_engine_published,
    make_analytics_engine_failed,
    make_analytics_engine_stopped,
)

# ── Statistics / History ──────────────────────────────────────────────────────
from .analytics_statistics import EngineAnalyticsStatistics  # noqa: F401
from .analytics_history import EngineAnalyticsHistory        # noqa: F401

# ── Health / Status ───────────────────────────────────────────────────────────
from .analytics_health import (  # noqa: F401
    AnalyticsEngineHealth,
    assess_engine_health,
)
from .analytics_status import AnalyticsEngineStatus  # noqa: F401

# ── Sub-components (for direct use where needed) ──────────────────────────────
from .analytics_scheduler import AnalyticsScheduler    # noqa: F401
from .analytics_dispatcher import AnalyticsDispatcher  # noqa: F401
from .analytics_validation import (  # noqa: F401
    EngineAnalyticsValidationResult,
    EngineAnalyticsValidator,
)

__all__ = [
    # Primary interface
    "ExecutionAnalyticsEngine",
    # Constants
    "ENGINE_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "EngineAnalyticsState",
    "ENGINE_STATE_TRANSITIONS",
    "ACTIVE_ENGINE_STATES",
    "TERMINAL_ENGINE_STATES",
    "EngineOperation",
    "AnalyticsRequestType",
    "PipelineStage",
    "PipelineStatus",
    "ResponseStatus",
    "ScheduleType",
    "EngineHealthStatus",
    "EngineEventType",
    # Exceptions
    "AnalyticsEngineError",
    "AnalyticsEngineNotRunningError",
    "AnalyticsEngineAlreadyRunningError",
    "AnalyticsRequestNotFoundError",
    "AnalyticsRequestValidationError",
    "AnalyticsPipelineError",
    "AnalyticsSessionManagerError",
    "AnalyticsDispatchError",
    "AnalyticsSchedulerError",
    "AnalyticsPublishError",
    # Request/Response
    "AnalyticsRequest",
    "make_analytics_request",
    "AnalyticsResponse",
    "AnalyticsSnapshot",
    "make_analytics_response",
    "make_analytics_snapshot",
    "EngineAnalyticsContext",
    "make_engine_analytics_context",
    # Pipeline
    "AnalyticsPipeline",
    "make_analytics_pipeline",
    # Events
    "EngineAnalyticsEvent",
    "make_analytics_engine_initialized",
    "make_analytics_engine_started",
    "make_analytics_engine_collected",
    "make_analytics_engine_dispatched",
    "make_analytics_engine_completed",
    "make_analytics_engine_published",
    "make_analytics_engine_failed",
    "make_analytics_engine_stopped",
    # Statistics / History
    "EngineAnalyticsStatistics",
    "EngineAnalyticsHistory",
    # Health / Status
    "AnalyticsEngineHealth",
    "assess_engine_health",
    "AnalyticsEngineStatus",
    # Sub-components
    "AnalyticsScheduler",
    "AnalyticsDispatcher",
    "EngineAnalyticsValidationResult",
    "EngineAnalyticsValidator",
]
