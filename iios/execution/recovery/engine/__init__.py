"""
iios/execution/recovery/engine/__init__.py
==========================================
Public surface for C7 Execution Recovery Engine.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

# ── Primary entry point ───────────────────────────────────────────────────────
from .execution_recovery_engine import ExecutionRecoveryEngine  # noqa: F401

# ── Constants ─────────────────────────────────────────────────────────────────
from .constants import (  # noqa: F401
    SYSTEM_ID,
    ENGINE_ID,
    MANAGER_ID,
    SCHEDULER_ID,
    DISPATCHER_ID,
    PIPELINE_ID,
    SESSION_MGR_ID,
    REGISTRY_ID,
    FACTORY_ID,
    VERSION,
    SCHEMA_VERSION,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_QUEUE_SIZE,
    ACTOR_ENGINE,
    ACTOR_MANAGER,
    ACTOR_SCHEDULER,
    ACTOR_DISPATCHER,
    ACTOR_PIPELINE,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    ACTOR_POLICY,
    ACTOR_WATCHDOG,
    RecoveryEngineState,
    ACTIVE_ENGINE_STATES,
    TERMINAL_ENGINE_STATES,
    RecoveryRequestType,
    RecoveryRequestPriority,
    RecoveryResponseStatus,
    RecoveryOutcome,
    RecoveryEngineEventType,
    PipelineStage,
    PIPELINE_STAGES_ORDERED,
    PipelineStageStatus,
    SchedulerMode,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (  # noqa: F401
    RecoveryEngineError,
    RecoveryEngineNotRunningError,
    RecoveryEngineAlreadyRunningError,
    RecoveryRequestNotFoundError,
    RecoveryRequestValidationError,
    RecoveryDispatchError,
    RecoverySchedulerError,
    RecoveryPipelineError,
    RecoverySessionManagerError,
    RecoverySnapshotError,
    RecoveryContextValidationError,
)

# ── Domain objects ────────────────────────────────────────────────────────────
from .recovery_context import (  # noqa: F401
    ExecutionMonitoringSnapshot,
    ExecutionGatewaySnapshot,
    ExecutionRiskSnapshot,
    FailureContext,
    RecoveryContext,
    make_failure_context,
    make_recovery_context,
)
from .recovery_request import RecoveryRequest, make_recovery_request  # noqa: F401
from .recovery_response import (  # noqa: F401
    RecoveryResponse,
    make_recovery_response,
    make_success_response,
    make_failure_response,
)
from .recovery_events import (  # noqa: F401
    RecoveryEngineEvent,
    make_recovery_initialized,
    make_recovery_started,
    make_failure_detected,
    make_recovery_dispatched,
    make_recovery_verified,
    make_recovery_completed,
    make_recovery_failed,
    make_recovery_stopped,
    make_engine_started,
    make_engine_stopped,
)
from .recovery_snapshot import RecoverySnapshot, make_recovery_snapshot  # noqa: F401
from .recovery_validation import (  # noqa: F401
    RecoveryEngineValidationResult,
    RecoveryEngineValidator,
)
from .recovery_statistics import RecoveryEngineStatistics  # noqa: F401
from .recovery_history import RecoveryEngineHistory  # noqa: F401
from .recovery_pipeline import RecoveryPipeline, PipelineStageRecord  # noqa: F401
from .recovery_scheduler import RecoveryScheduler  # noqa: F401
from .recovery_dispatcher import (  # noqa: F401
    PolicyDecision,
    FailoverResult,
    DispatchResult,
    PolicyFrameworkPort,
    FailoverFrameworkPort,
    NullPolicyFramework,
    NullFailoverFramework,
    RecoveryDispatcher,
)
from .recovery_session_manager import RecoverySessionManager  # noqa: F401
from .recovery_registry import RecoveryRegistry  # noqa: F401
from .recovery_factory import RecoveryFactory  # noqa: F401
from .recovery_manager import RecoveryManager  # noqa: F401
