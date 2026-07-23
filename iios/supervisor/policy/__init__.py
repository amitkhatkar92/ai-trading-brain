"""
iios.supervisor.policy — AI Governance Policy Framework
========================================================

Public surface for the C13 AI Governance Policy Framework.
All stable exports are listed in ``__all__``.
"""
from .constants import (
    ACTION_SEVERITY,
    DEFAULT_MAX_CHAIN_DEPTH,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    DEFAULT_POLICY_ACTION,
    POLICY_SYSTEM_ID,
    VERSION,
    ConditionOperator,
    ConflictResolutionStrategy,
    EvaluationMode,
    GovernancePolicyEventType,
    GovernancePolicyType,
    GovernanceValidationCode,
    LogicalOperator,
    PolicyAction,
    PolicyPriority,
)
from .exceptions import (
    GovernancePolicyCapacityError,
    GovernancePolicyConditionError,
    GovernancePolicyEngineNotRunningError,
    GovernancePolicyError,
    GovernancePolicyEvaluationError,
    GovernancePolicyHistoryError,
    GovernancePolicyNotFoundError,
    GovernancePolicyRegistryError,
    GovernancePolicyRuleError,
    GovernancePolicyValidationError,
)
from .governance_policy import GovernancePolicy
from .governance_policy_chain import GovernancePolicyChain
from .governance_policy_condition import GovernancePolicyCondition
from .governance_policy_context import GovernancePolicyContext
from .governance_policy_engine import GovernancePolicyEngine
from .governance_policy_evaluator import GovernancePolicyEvaluator
from .governance_policy_events import (
    GovernancePolicyEvent,
    make_conflict_resolved_event,
    make_engine_started_event,
    make_engine_stopped_event,
    make_evaluation_completed_event,
    make_evaluation_failed_event,
    make_evaluation_started_event,
    make_policy_registered_event,
    make_policy_unregistered_event,
)
from .governance_policy_factory import GovernancePolicyFactory
from .governance_policy_history import GovernancePolicyHistory
from .governance_policy_manager import GovernancePolicyManager
from .governance_policy_registry import GovernancePolicyRegistry
from .governance_policy_request import GovernancePolicyRequest
from .governance_policy_response import (
    GovernanceEvaluationSummary,
    GovernancePolicyResponse,
)
from .governance_policy_result import GovernancePolicyResult
from .governance_policy_rule import GovernancePolicyRule
from .governance_policy_statistics import GovernancePolicyStatistics
from .governance_policy_validation import (
    GovernancePolicyValidator,
    GovernanceValidationCheckResult,
    GovernanceValidationResult,
)

__all__ = [
    # Constants
    "ACTION_SEVERITY",
    "DEFAULT_MAX_CHAIN_DEPTH",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_POLICIES",
    "DEFAULT_POLICY_ACTION",
    "POLICY_SYSTEM_ID",
    "VERSION",
    # Enumerations
    "ConditionOperator",
    "ConflictResolutionStrategy",
    "EvaluationMode",
    "GovernancePolicyEventType",
    "GovernancePolicyType",
    "GovernanceValidationCode",
    "LogicalOperator",
    "PolicyAction",
    "PolicyPriority",
    # Exceptions
    "GovernancePolicyCapacityError",
    "GovernancePolicyConditionError",
    "GovernancePolicyEngineNotRunningError",
    "GovernancePolicyError",
    "GovernancePolicyEvaluationError",
    "GovernancePolicyHistoryError",
    "GovernancePolicyNotFoundError",
    "GovernancePolicyRegistryError",
    "GovernancePolicyRuleError",
    "GovernancePolicyValidationError",
    # Value objects
    "GovernancePolicy",
    "GovernancePolicyCondition",
    "GovernancePolicyContext",
    "GovernancePolicyRequest",
    "GovernancePolicyResponse",
    "GovernancePolicyResult",
    "GovernancePolicyRule",
    "GovernanceEvaluationSummary",
    # Events
    "GovernancePolicyEvent",
    "make_conflict_resolved_event",
    "make_engine_started_event",
    "make_engine_stopped_event",
    "make_evaluation_completed_event",
    "make_evaluation_failed_event",
    "make_evaluation_started_event",
    "make_policy_registered_event",
    "make_policy_unregistered_event",
    # Validation
    "GovernancePolicyValidator",
    "GovernanceValidationCheckResult",
    "GovernanceValidationResult",
    # Subsystems
    "GovernancePolicyChain",
    "GovernancePolicyEvaluator",
    "GovernancePolicyFactory",
    "GovernancePolicyHistory",
    "GovernancePolicyManager",
    "GovernancePolicyRegistry",
    "GovernancePolicyStatistics",
    # Engine (primary interface)
    "GovernancePolicyEngine",
]
