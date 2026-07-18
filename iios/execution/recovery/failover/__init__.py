"""
iios/execution/recovery/failover/__init__.py
============================================
Public surface of the Execution Failover Framework (C7 M4).

Primary entry point: FailoverEngine
"""
from .constants import (
    ACTOR_ENGINE,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    DEFAULT_EXECUTION_TIMEOUT_MS,
    DEFAULT_MAX_ACTIVE_SESSIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_SESSIONS,
    ENGINE_ID,
    FACTORY_ID,
    MANAGER_ID,
    REGISTRY_ID,
    SCHEMA_VERSION,
    SYSTEM_ID,
    VERSION,
    ALWAYS_SUCCEEDS,
    NON_OPERATIONAL_ACTIONS,
    STRATEGY_TO_FAILOVER_MAP,
    FailoverAction,
    FailoverEventType,
    FailoverPhase,
    FailoverStatus,
    FailoverType,
    HealthStatus,
    VerificationStatus,
)
from .exceptions import (
    FailoverError,
    FailoverExecutionError,
    FailoverNotRunningError,
    FailoverPlanNotFoundError,
    FailoverRegistryError,
    FailoverResourceUnavailableError,
    FailoverStrategyNotFoundError,
    FailoverTimeoutError,
    FailoverValidationError,
    FailoverVerificationError,
)
from .failover_context import FailoverContext, make_failover_context
from .failover_controller import FailoverController
from .failover_events import (
    FailoverEvent,
    make_failover_completed,
    make_failover_executed,
    make_failover_failed,
    make_failover_prepared,
    make_failover_started,
    make_failover_verified,
    make_fallback_activated,
    make_manual_escalation_requested,
)
from .failover_executor import FailoverExecutor
from .failover_factory import FailoverFactory
from .failover_health_monitor import FailoverHealthMonitor, ResourceAvailabilityReport
from .failover_history import FailoverHistory
from .failover_manager import FailoverManager
from .failover_plan import (
    DEFAULT_PLAN_FACTORIES,
    FailoverPlan,
    make_backup_activation_plan,
    make_broker_failover_plan,
    make_component_restart_plan,
    make_deactivate_primary_plan,
    make_gateway_failover_plan,
    make_graceful_shutdown_plan,
    make_manual_escalation_plan,
    make_resume_plan,
    make_retry_plan,
    make_rollback_plan,
    make_workflow_restart_plan,
)
from .failover_registry import FailoverRegistry
from .failover_request import FailoverRequest, make_failover_request
from .failover_response import (
    FailoverExecutionStep,
    FailoverResponse,
    FailoverResult,
    VerificationCheck,
    VerificationReport,
    make_failover_response,
    make_failover_result,
    make_verification_report,
)
from .failover_statistics import FailoverStatistics
from .failover_strategy_registry import FailoverStrategyRegistry
from .failover_validation import FailoverValidationResult, FailoverValidator
from .failover_verifier import FailoverVerifier

# PRIMARY ENTRY POINT
from .failover_engine import FailoverEngine

__all__ = [
    # Constants
    "SYSTEM_ID", "ENGINE_ID", "MANAGER_ID", "REGISTRY_ID", "FACTORY_ID",
    "VERSION", "SCHEMA_VERSION",
    "DEFAULT_MAX_SESSIONS", "DEFAULT_MAX_HISTORY", "DEFAULT_MAX_ACTIVE_SESSIONS",
    "DEFAULT_EXECUTION_TIMEOUT_MS",
    "ALWAYS_SUCCEEDS", "NON_OPERATIONAL_ACTIONS", "STRATEGY_TO_FAILOVER_MAP",
    # Enums
    "FailoverType", "FailoverAction", "FailoverStatus", "FailoverPhase",
    "VerificationStatus", "HealthStatus", "FailoverEventType",
    # Exceptions
    "FailoverError", "FailoverNotRunningError", "FailoverValidationError",
    "FailoverExecutionError", "FailoverVerificationError",
    "FailoverPlanNotFoundError", "FailoverResourceUnavailableError",
    "FailoverTimeoutError", "FailoverRegistryError", "FailoverStrategyNotFoundError",
    # DTOs
    "FailoverContext", "make_failover_context",
    "FailoverRequest", "make_failover_request",
    "VerificationCheck", "VerificationReport", "make_verification_report",
    "FailoverExecutionStep",
    "FailoverResult", "make_failover_result",
    "FailoverResponse", "make_failover_response",
    "FailoverPlan",
    "make_retry_plan", "make_resume_plan", "make_rollback_plan",
    "make_component_restart_plan", "make_workflow_restart_plan",
    "make_gateway_failover_plan", "make_broker_failover_plan",
    "make_backup_activation_plan", "make_graceful_shutdown_plan",
    "make_manual_escalation_plan", "make_deactivate_primary_plan",
    "DEFAULT_PLAN_FACTORIES",
    "ResourceAvailabilityReport",
    "FailoverEvent",
    "make_failover_started", "make_failover_prepared", "make_failover_executed",
    "make_failover_verified", "make_failover_completed", "make_failover_failed",
    "make_fallback_activated", "make_manual_escalation_requested",
    "FailoverValidationResult",
    # Classes
    "FailoverStatistics",
    "FailoverHistory",
    "FailoverStrategyRegistry",
    "FailoverRegistry",
    "FailoverHealthMonitor",
    "FailoverFactory",
    "FailoverValidator",
    "FailoverVerifier",
    "FailoverExecutor",
    "FailoverController",
    "FailoverManager",
    # PRIMARY ENTRY POINT
    "FailoverEngine",
]
