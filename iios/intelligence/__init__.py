"""iios/intelligence/__init__.py — Public API for the IIOS Intelligence Layer."""

# Constants
from .intelligence_constants import (
    EngineType, EngineStatus, WorkflowType, StepType, StepStatus,
    SessionStatus, ExecutionStatus, Priority, PolicyType, EventType,
    CheckpointStatus, RecoveryMode, ScheduleType, OrchestratorStatus,
    MAX_CONCURRENT_SESSIONS, MAX_CONCURRENT_WORKFLOWS, MAX_WORKFLOW_STEPS,
    MAX_NESTING_DEPTH, MAX_RETRY_ATTEMPTS, SESSION_TTL_SECONDS,
    WORKFLOW_TIMEOUT_MS, STEP_TIMEOUT_MS, DEFAULT_THREAD_POOL_SIZE,
    INTELLIGENCE_ENGINE_VERSION, SYSTEM_ACTOR, WILDCARD_ENGINE,
    WF_FULL_ANALYSIS, WF_RISK_CHECK, WF_STRATEGY_CYCLE, WF_LEARNING_CYCLE,
)

# Exceptions
from .intelligence_exceptions import (
    IntelligenceError,
    EngineError, EngineNotFoundError, EngineAlreadyRegisteredError,
    EngineExecutionError, EngineTimeoutError, EngineNotInitializedError,
    EngineUnavailableError,
    SessionError, SessionNotFoundError, SessionExpiredError,
    SessionAlreadyActiveError, SessionRecoveryError, SessionCapacityError,
    WorkflowError, WorkflowNotFoundError, WorkflowExecutionError,
    WorkflowStepError, WorkflowTimeoutError, WorkflowCancelledError,
    CircularDependencyError, CheckpointError, WorkflowAlreadyRegisteredError,
    OrchestratorError, OrchestratorNotInitializedError, PolicyViolationError,
    SchedulerError, SchedulerNotRunningError,
)

# Context
from .intelligence_context import (
    IntelligenceDiagnostic,
    IntelligenceContext,
    get_intelligence_context,
    reset_intelligence_context,
    intelligence_execution,
    workflow_scope,
    step_scope,
)

# Sessions
from .sessions import (
    IntelligenceSession,
    SessionResult,
    SessionManager,
    get_session_manager,
    reset_session_manager,
)

# Registry
from .registry import (
    EngineDescriptor,
    AIEngine,
    EngineRegistry,
    get_engine_registry,
    reset_engine_registry,
)

# Execution policies
from .execution import (
    RetryPolicy,
    TimeoutPolicy,
    FallbackPolicy,
    DependencyPolicy,
    ResourcePolicy,
    CancellationToken,
    ExecutionPolicy,
    DEFAULT_POLICY,
)

# Workflow
from .workflow import (
    WorkflowStep,
    WorkflowDefinition,
    WorkflowBuilder,
    WorkflowRegistry,  get_workflow_registry,  reset_workflow_registry,
    StepRunResult, WorkflowRunResult,
    WorkflowExecutor,  get_workflow_executor,  reset_workflow_executor,
    ScheduledWorkflow,
    WorkflowScheduler, get_workflow_scheduler, reset_workflow_scheduler,
    WorkflowEngine,    get_workflow_engine,    reset_workflow_engine,
)

# Manager
from .intelligence_manager import (
    IntelligenceStats,
    IntelligenceManager,
    get_intelligence_manager,
    reset_intelligence_manager,
)

# Orchestrator
from .intelligence_orchestrator import (
    IntelligenceOrchestrator,
    get_intelligence_orchestrator,
    reset_intelligence_orchestrator,
)

__all__ = [
    # constants
    "EngineType", "EngineStatus", "WorkflowType", "StepType", "StepStatus",
    "SessionStatus", "ExecutionStatus", "Priority", "PolicyType", "EventType",
    "CheckpointStatus", "RecoveryMode", "ScheduleType", "OrchestratorStatus",
    "MAX_CONCURRENT_SESSIONS", "MAX_CONCURRENT_WORKFLOWS", "MAX_WORKFLOW_STEPS",
    "MAX_NESTING_DEPTH", "MAX_RETRY_ATTEMPTS", "SESSION_TTL_SECONDS",
    "WORKFLOW_TIMEOUT_MS", "STEP_TIMEOUT_MS", "DEFAULT_THREAD_POOL_SIZE",
    "INTELLIGENCE_ENGINE_VERSION", "SYSTEM_ACTOR", "WILDCARD_ENGINE",
    "WF_FULL_ANALYSIS", "WF_RISK_CHECK", "WF_STRATEGY_CYCLE", "WF_LEARNING_CYCLE",
    # exceptions
    "IntelligenceError",
    "EngineError", "EngineNotFoundError", "EngineAlreadyRegisteredError",
    "EngineExecutionError", "EngineTimeoutError", "EngineNotInitializedError",
    "EngineUnavailableError",
    "SessionError", "SessionNotFoundError", "SessionExpiredError",
    "SessionAlreadyActiveError", "SessionRecoveryError", "SessionCapacityError",
    "WorkflowError", "WorkflowNotFoundError", "WorkflowExecutionError",
    "WorkflowStepError", "WorkflowTimeoutError", "WorkflowCancelledError",
    "CircularDependencyError", "CheckpointError", "WorkflowAlreadyRegisteredError",
    "OrchestratorError", "OrchestratorNotInitializedError", "PolicyViolationError",
    "SchedulerError", "SchedulerNotRunningError",
    # context
    "IntelligenceDiagnostic", "IntelligenceContext",
    "get_intelligence_context", "reset_intelligence_context",
    "intelligence_execution", "workflow_scope", "step_scope",
    # sessions
    "IntelligenceSession", "SessionResult",
    "SessionManager", "get_session_manager", "reset_session_manager",
    # registry
    "EngineDescriptor", "AIEngine",
    "EngineRegistry", "get_engine_registry", "reset_engine_registry",
    # execution policies
    "RetryPolicy", "TimeoutPolicy", "FallbackPolicy", "DependencyPolicy",
    "ResourcePolicy", "CancellationToken", "ExecutionPolicy", "DEFAULT_POLICY",
    # workflow
    "WorkflowStep", "WorkflowDefinition", "WorkflowBuilder",
    "WorkflowRegistry",  "get_workflow_registry",  "reset_workflow_registry",
    "StepRunResult", "WorkflowRunResult",
    "WorkflowExecutor",  "get_workflow_executor",  "reset_workflow_executor",
    "ScheduledWorkflow",
    "WorkflowScheduler", "get_workflow_scheduler", "reset_workflow_scheduler",
    "WorkflowEngine",    "get_workflow_engine",    "reset_workflow_engine",
    # manager
    "IntelligenceStats", "IntelligenceManager",
    "get_intelligence_manager", "reset_intelligence_manager",
    # orchestrator
    "IntelligenceOrchestrator",
    "get_intelligence_orchestrator", "reset_intelligence_orchestrator",
]
