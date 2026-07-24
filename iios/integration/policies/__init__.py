"""
iios/integration/policies/__init__.py
---------------------------------------
Public API for the Integration Governance Policy Framework.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from .constants import (
    ACTION_PRECEDENCE,
    ACTION_TO_STATUS,
    DEFAULT_ENGINE_ID,
    DEFAULT_MAX_AUDIT,
    DEFAULT_MAX_CONDITIONS_PER_RULE,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    DEFAULT_MAX_RULES_PER_POLICY,
    DEFAULT_PRIORITY,
    MANAGER_SYSTEM_ID,
    PIPELINE_STAGES,
    POLICY_SYSTEM_ID,
    PRIORITY_RANK,
    VERSION,
    ConditionOperator,
    ConflictResolutionStrategy,
    PolicyAction,
    PolicyChainMode,
    PolicyDomain,
    PolicyEvaluationMode,
    PolicyEventType,
    PolicyPriority,
    PolicyResultStatus,
    PolicyType,
)
from .exceptions import (
    IntegrationPolicyError,
    PolicyChainError,
    PolicyConditionError,
    PolicyConflictError,
    PolicyEngineNotReadyError,
    PolicyEvaluationError,
    PolicyNotFoundError,
    PolicyRegistrationError,
    PolicyRuleError,
    PolicyValidationError,
)
from .integration_policy import IntegrationPolicy
from .integration_policy_audit import (
    IntegrationAuditEntry,
    IntegrationAuditReport,
    IntegrationPolicyAudit,
)
from .integration_policy_chain import ChainExecution, IntegrationPolicyChain
from .integration_policy_condition import IntegrationPolicyCondition
from .integration_policy_context import IntegrationPolicyContext
from .integration_policy_engine import IntegrationPolicyEngine
from .integration_policy_evaluator import IntegrationPolicyEvaluator
from .integration_policy_events import IntegrationPolicyEvent, IntegrationPolicyEventBus
from .integration_policy_factory import IntegrationPolicyFactory
from .integration_policy_history import IntegrationPolicyHistory
from .integration_policy_manager import IntegrationPolicyManager
from .integration_policy_priority import IntegrationPolicyPriority
from .integration_policy_registry import IntegrationPolicyRegistry
from .integration_policy_request import IntegrationPolicyRequest
from .integration_policy_response import IntegrationPolicyResponse
from .integration_policy_result import GovernanceDecision, IntegrationPolicyResult
from .integration_policy_rule import IntegrationPolicyRule
from .integration_policy_statistics import (
    IntegrationPolicyStatistics,
    IntegrationPolicyStatisticsReport,
)
from .integration_policy_validator import (
    IntegrationPolicyValidator,
    PolicyValidationReport,
    PolicyValidationResult,
)

__all__ = [
    # ── constants & enums ──────────────────────────────────────────────
    "PolicyType",
    "PolicyAction",
    "PolicyPriority",
    "PolicyDomain",
    "PolicyChainMode",
    "ConflictResolutionStrategy",
    "ConditionOperator",
    "PolicyEvaluationMode",
    "PolicyEventType",
    "PolicyResultStatus",
    "ACTION_PRECEDENCE",
    "ACTION_TO_STATUS",
    "PRIORITY_RANK",
    "PIPELINE_STAGES",
    "POLICY_SYSTEM_ID",
    "MANAGER_SYSTEM_ID",
    "VERSION",
    "DEFAULT_ENGINE_ID",
    "DEFAULT_MAX_POLICIES",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_AUDIT",
    "DEFAULT_MAX_RULES_PER_POLICY",
    "DEFAULT_MAX_CONDITIONS_PER_RULE",
    "DEFAULT_PRIORITY",
    # ── exceptions ────────────────────────────────────────────────────
    "IntegrationPolicyError",
    "PolicyEngineNotReadyError",
    "PolicyNotFoundError",
    "PolicyRuleError",
    "PolicyConditionError",
    "PolicyValidationError",
    "PolicyConflictError",
    "PolicyEvaluationError",
    "PolicyRegistrationError",
    "PolicyChainError",
    # ── data objects ──────────────────────────────────────────────────
    "IntegrationPolicyCondition",
    "IntegrationPolicyRule",
    "IntegrationPolicy",
    "IntegrationPolicyContext",
    "IntegrationPolicyRequest",
    "IntegrationPolicyResult",
    "GovernanceDecision",
    "IntegrationPolicyResponse",
    # ── subsystems ────────────────────────────────────────────────────
    "IntegrationPolicyEvaluator",
    "IntegrationPolicyPriority",
    "IntegrationPolicyValidator",
    "PolicyValidationResult",
    "PolicyValidationReport",
    "IntegrationPolicyRegistry",
    "IntegrationPolicyChain",
    "ChainExecution",
    "IntegrationPolicyFactory",
    # ── audit ─────────────────────────────────────────────────────────
    "IntegrationAuditEntry",
    "IntegrationAuditReport",
    "IntegrationPolicyAudit",
    # ── statistics ────────────────────────────────────────────────────
    "IntegrationPolicyStatistics",
    "IntegrationPolicyStatisticsReport",
    # ── history ───────────────────────────────────────────────────────
    "IntegrationPolicyHistory",
    # ── events ────────────────────────────────────────────────────────
    "IntegrationPolicyEvent",
    "IntegrationPolicyEventBus",
    # ── engine & manager ──────────────────────────────────────────────
    "IntegrationPolicyEngine",
    "IntegrationPolicyManager",
]
