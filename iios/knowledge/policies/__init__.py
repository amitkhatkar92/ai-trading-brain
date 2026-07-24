"""
__init__.py — iios.knowledge.policies
----------------------------------------
Public API surface of the Knowledge Governance Policy Framework.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from .constants import (
    ACTOR_GOVERNANCE,
    ACTOR_EVALUATOR,
    ACTOR_AUDITOR,
    ACTOR_OPERATOR,
    ACTOR_SYSTEM,
    AUDIT_SYSTEM_ID,
    CHAIN_SYSTEM_ID,
    DEFAULT_MAX_AUDIT_ENTRIES,
    DEFAULT_MAX_CHAIN_DEPTH,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    EVALUATOR_SYSTEM_ID,
    GOVERNANCE_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    SCHEMA_VERSION,
    VERSION,
    ConditionOperator,
    EvaluationStatus,
    GovernanceDecision,
    GovernanceEngineState,
    GovernanceEventType,
    PolicyAction,
    PolicyChainMode,
    PolicyDomain,
    PolicyPriority,
    PolicyStatus,
    PolicyType,
    PolicyValidationCode,
)
from .exceptions import (
    AuditError,
    GovernanceCapacityError,
    GovernanceNotRunningError,
    GovernanceValidationError,
    KnowledgeGovernanceError,
    PolicyChainError,
    PolicyConflictError,
    PolicyEvaluationError,
    PolicyLoadError,
    PolicyNotFoundError,
)
from .knowledge_policy import KnowledgePolicy
from .knowledge_policy_audit import KnowledgePolicyAudit, PolicyAuditEntry
from .knowledge_policy_chain import ChainResult, KnowledgePolicyChain
from .knowledge_policy_condition import PolicyCondition
from .knowledge_policy_context import GovernancePolicyContext
from .knowledge_policy_engine import KnowledgeGovernancePolicyEngine
from .knowledge_policy_evaluator import KnowledgePolicyEvaluator
from .knowledge_policy_events import (
    GovernancePolicyEvent,
    GovernancePolicyEventBus,
    make_governance_completed,
    make_governance_started,
    make_knowledge_approved,
    make_knowledge_blocked,
    make_knowledge_escalated,
    make_knowledge_rejected,
    make_policy_loaded,
    make_policy_validated,
    make_review_requested,
)
from .knowledge_policy_factory import KnowledgePolicyFactory
from .knowledge_policy_history import KnowledgeGovernanceHistory
from .knowledge_policy_manager import KnowledgePolicyWorkflowManager
from .knowledge_policy_priority import PolicyPriorityResolver
from .knowledge_policy_registry import KnowledgePolicyRegistry
from .knowledge_policy_request import KnowledgePolicyRequest
from .knowledge_policy_response import GovernanceDecisionRecord, KnowledgePolicyResponse
from .knowledge_policy_result import PolicyEvaluationResult, PolicyRuleResult
from .knowledge_policy_rule import PolicyRule
from .knowledge_policy_statistics import KnowledgeGovernanceStatistics
from .knowledge_policy_validator import GovernanceValidationResult, KnowledgeGovernanceValidator

__all__ = [
    # Constants / enums
    "VERSION", "SCHEMA_VERSION",
    "GOVERNANCE_SYSTEM_ID", "EVALUATOR_SYSTEM_ID", "REGISTRY_SYSTEM_ID",
    "CHAIN_SYSTEM_ID", "AUDIT_SYSTEM_ID",
    "ACTOR_GOVERNANCE", "ACTOR_EVALUATOR", "ACTOR_AUDITOR",
    "ACTOR_OPERATOR", "ACTOR_SYSTEM",
    "DEFAULT_MAX_POLICIES", "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_AUDIT_ENTRIES", "DEFAULT_MAX_CHAIN_DEPTH",
    "GovernanceEngineState", "PolicyType", "PolicyAction",
    "PolicyPriority", "PolicyDomain", "PolicyStatus",
    "GovernanceDecision", "EvaluationStatus", "PolicyChainMode",
    "ConditionOperator", "GovernanceEventType", "PolicyValidationCode",
    # Exceptions
    "KnowledgeGovernanceError", "GovernanceNotRunningError",
    "GovernanceValidationError", "PolicyLoadError", "PolicyEvaluationError",
    "PolicyConflictError", "PolicyNotFoundError", "GovernanceCapacityError",
    "AuditError", "PolicyChainError",
    # Value objects
    "GovernancePolicyContext", "KnowledgePolicyRequest",
    "KnowledgePolicyResponse", "GovernanceDecisionRecord",
    "PolicyEvaluationResult", "PolicyRuleResult",
    # Domain objects
    "KnowledgePolicy", "PolicyRule", "PolicyCondition",
    # Infrastructure
    "KnowledgePolicyRegistry", "KnowledgePolicyEvaluator",
    "PolicyPriorityResolver", "KnowledgePolicyWorkflowManager",
    "KnowledgeGovernanceStatistics", "KnowledgeGovernanceHistory",
    "KnowledgePolicyAudit", "PolicyAuditEntry",
    "KnowledgePolicyChain", "ChainResult",
    "KnowledgePolicyFactory",
    "KnowledgeGovernanceValidator", "GovernanceValidationResult",
    # Events
    "GovernancePolicyEvent", "GovernancePolicyEventBus",
    "make_policy_loaded", "make_policy_validated", "make_governance_started",
    "make_knowledge_approved", "make_knowledge_rejected", "make_knowledge_blocked",
    "make_knowledge_escalated", "make_review_requested", "make_governance_completed",
    # Primary façade
    "KnowledgeGovernancePolicyEngine",
]
