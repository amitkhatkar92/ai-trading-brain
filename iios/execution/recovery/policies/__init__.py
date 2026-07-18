"""
iios/execution/recovery/policies/__init__.py
============================================
Public surface of the Execution Recovery Policy Framework (C7 M3).

Primary entry point: RecoveryPolicyEngine
M2 bridge:          RecoveryPolicyEngineAdapter
"""
from .constants import (
    CONFIDENCE_EMERGENCY_SHUTDOWN,
    CONFIDENCE_FAILOVER,
    CONFIDENCE_MANUAL,
    CONFIDENCE_RESTART,
    CONFIDENCE_RESUME,
    CONFIDENCE_RETRY,
    CONFIDENCE_ROLLBACK,
    ENGINE_ID,
    FACTORY_ID,
    MANAGER_ID,
    REGISTRY_ID,
    SCHEMA_VERSION,
    SEVERITY_PRIORITY_MAP,
    SYSTEM_ID,
    VERSION,
    FailureCategory,
    FailureSeverity,
    PolicyEventType,
    PolicyPriority,
    RecoveryRecommendation,
    RecoveryStrategyType,
    RuleConditionOperator,
    TRANSIENT_FAILURE_CATEGORIES,
    FAILOVER_ELIGIBLE_CATEGORIES,
    SAFETY_CRITICAL_CATEGORIES,
)
from .exceptions import (
    RecoveryPolicyConflictError,
    RecoveryPolicyError,
    RecoveryPolicyEvaluationError,
    RecoveryPolicyNotFoundError,
    RecoveryPolicyNotRunningError,
    RecoveryPolicyRegistryError,
    RecoveryPolicyValidationError,
    RecoveryRuleValidationError,
    RecoveryStrategyNotFoundError,
)
from .recovery_context import (
    PolicyEvaluationContext,
    make_policy_evaluation_context,
)
from .recovery_events import (
    RecoveryPolicyEvent,
    make_decision_published,
    make_engine_started,
    make_engine_stopped,
    make_fallback_policy_selected,
    make_policy_evaluated,
    make_policy_evaluation_failed,
    make_policy_evaluation_started,
    make_strategy_selected,
)
from .recovery_factory import RecoveryPolicyFactory
from .recovery_history import RecoveryPolicyHistory
from .recovery_policy import (
    CompositePolicy,
    EmergencyShutdownPolicy,
    FailoverPolicy,
    ManualInterventionPolicy,
    PolicyEvaluationResult,
    RecoveryPolicy,
    RestartPolicy,
    ResumePolicy,
    RetryPolicy,
    RollbackPolicy,
)
from .recovery_policy_engine import (
    RecoveryPolicyEngine,
    RecoveryPolicyEngineAdapter,
)
from .recovery_policy_manager import RecoveryPolicyManager
from .recovery_policy_registry import RecoveryPolicyRegistry
from .recovery_priority import PriorityScore, RecoveryPriorityEvaluator
from .recovery_request import (
    PolicyEvaluationRequest,
    make_policy_evaluation_request,
)
from .recovery_response import (
    PolicyEvaluationReport,
    RecoveryPolicyDecision,
    make_policy_decision,
)
from .recovery_rule import RuleCondition, RecoveryRule, make_rule
from .recovery_statistics import RecoveryPolicyStatistics
from .recovery_strategy import (
    RecoveryStrategy,
    make_emergency_shutdown_strategy,
    make_failover_strategy,
    make_manual_intervention_strategy,
    make_restart_strategy,
    make_resume_strategy,
    make_retry_strategy,
    make_rollback_strategy,
    make_strategy,
)
from .recovery_validation import PolicyEvaluationValidator, PolicyValidationResult

__all__ = [
    # Constants
    "SYSTEM_ID", "ENGINE_ID", "MANAGER_ID", "REGISTRY_ID", "FACTORY_ID",
    "VERSION", "SCHEMA_VERSION",
    "CONFIDENCE_EMERGENCY_SHUTDOWN", "CONFIDENCE_FAILOVER", "CONFIDENCE_MANUAL",
    "CONFIDENCE_RESTART", "CONFIDENCE_RESUME", "CONFIDENCE_RETRY", "CONFIDENCE_ROLLBACK",
    "SEVERITY_PRIORITY_MAP",
    "TRANSIENT_FAILURE_CATEGORIES", "FAILOVER_ELIGIBLE_CATEGORIES",
    "SAFETY_CRITICAL_CATEGORIES",
    # Enums
    "FailureCategory", "FailureSeverity", "PolicyEventType", "PolicyPriority",
    "RecoveryRecommendation", "RecoveryStrategyType", "RuleConditionOperator",
    # Exceptions
    "RecoveryPolicyError", "RecoveryPolicyNotRunningError",
    "RecoveryPolicyNotFoundError", "RecoveryPolicyValidationError",
    "RecoveryRuleValidationError", "RecoveryStrategyNotFoundError",
    "RecoveryPolicyEvaluationError", "RecoveryPolicyConflictError",
    "RecoveryPolicyRegistryError",
    # DTOs
    "PolicyEvaluationContext", "make_policy_evaluation_context",
    "PolicyEvaluationRequest", "make_policy_evaluation_request",
    "RecoveryPolicyDecision", "PolicyEvaluationReport", "make_policy_decision",
    "RecoveryPolicyEvent",
    "RuleCondition", "RecoveryRule", "make_rule",
    "RecoveryStrategy",
    "make_retry_strategy", "make_resume_strategy", "make_rollback_strategy",
    "make_restart_strategy", "make_failover_strategy",
    "make_manual_intervention_strategy", "make_emergency_shutdown_strategy",
    "make_strategy",
    "PriorityScore",
    "PolicyEvaluationResult",
    "PolicyValidationResult",
    # Classes
    "RecoveryPolicy", "RetryPolicy", "ResumePolicy", "RollbackPolicy",
    "RestartPolicy", "FailoverPolicy", "ManualInterventionPolicy",
    "EmergencyShutdownPolicy", "CompositePolicy",
    "RecoveryPriorityEvaluator",
    "PolicyEvaluationValidator",
    "RecoveryPolicyStatistics",
    "RecoveryPolicyHistory",
    "RecoveryPolicyFactory",
    "RecoveryPolicyRegistry",
    "RecoveryPolicyManager",
    # PRIMARY ENTRY POINT
    "RecoveryPolicyEngine",
    # M2 bridge
    "RecoveryPolicyEngineAdapter",
    # Event factories
    "make_policy_evaluation_started", "make_policy_evaluated",
    "make_strategy_selected", "make_decision_published",
    "make_fallback_policy_selected", "make_policy_evaluation_failed",
    "make_engine_started", "make_engine_stopped",
]
