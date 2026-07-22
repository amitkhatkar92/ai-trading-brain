"""
iios.risk.policies
==================
Institutional Risk Policy Framework — C11 Risk Intelligence, Module 3.

Public exports from this package:

Constants & Enumerations
------------------------
POLICY_SYSTEM_ID, EVALUATOR_SYSTEM_ID, REGISTRY_SYSTEM_ID,
FACTORY_SYSTEM_ID, AUDITOR_SYSTEM_ID, CHAIN_SYSTEM_ID, VERSION
PolicyType, PolicyAction, PolicyPriority, EvaluationMode,
LogicalOperator, ConditionOperator, ConflictResolutionStrategy,
PolicyEventType, ValidationCode

Exceptions
----------
RiskPolicyError, RiskPolicyEngineNotRunningError, RiskPolicyNotFoundError,
RiskPolicyValidationError, RiskPolicyEvaluationError, RiskPolicyConflictError,
RiskPolicyRegistryError, RiskPolicyConfigurationError, RiskPolicyAuditError,
RiskPolicyCapacityError

Value Objects
-------------
RiskPolicyCondition, RiskPolicyRule, RiskPolicy
RiskPolicyContext, RiskPolicyRequest
RiskPolicyResult, RiskEvaluationSummary, RiskPolicyResponse
RiskPolicyAuditReport

Events
------
RiskPolicyEvent
make_evaluation_started, make_policy_loaded, make_policy_validated,
make_policy_approved, make_policy_rejected, make_policy_blocked,
make_policy_escalated, make_immediate_action_triggered,
make_evaluation_completed

Validation
----------
RiskPolicyValidationCheckResult, RiskPolicyValidationResult

Services
--------
RiskPolicyCondition, RiskPolicyEvaluator, RiskPolicyChain,
RiskPolicyRegistry, RiskPolicyValidator, RiskPolicyAuditor,
RiskPolicyStatistics, RiskPolicyHistory, RiskPolicyFactory,
RiskPolicyManager

Engine (primary public interface)
-----------------------------------
RiskPolicyEngine, RiskPolicyEngineStatus
"""
from __future__ import annotations

# ── Constants & enumerations ────────────────────────────────────────────────
from .constants import (
    ACTION_SEVERITY,
    ACTOR_EVALUATOR,
    ACTOR_OPERATOR,
    ACTOR_POLICY_ENGINE,
    ACTOR_REGISTRY,
    ACTOR_SYSTEM,
    AUDITOR_SYSTEM_ID,
    CHAIN_SYSTEM_ID,
    DEFAULT_CONFLICT_RESOLUTION_ORDER,
    DEFAULT_EVALUATION_TIMEOUT_S,
    DEFAULT_MAX_AUDIT_RECORDS,
    DEFAULT_MAX_CHAIN_DEPTH,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    DEFAULT_POLICY_ACTION,
    DENY_ACTIONS,
    EVALUATOR_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    PERMISSIVE_ACTIONS,
    POLICY_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    SCHEMA_VERSION,
    VERSION,
    ConditionOperator,
    ConflictResolutionStrategy,
    EvaluationMode,
    LogicalOperator,
    PolicyAction,
    PolicyEventType,
    PolicyPriority,
    PolicyType,
    ValidationCode,
)

# ── Exceptions ──────────────────────────────────────────────────────────────
from .exceptions import (
    RiskPolicyAuditError,
    RiskPolicyCapacityError,
    RiskPolicyConfigurationError,
    RiskPolicyConflictError,
    RiskPolicyEngineNotRunningError,
    RiskPolicyError,
    RiskPolicyEvaluationError,
    RiskPolicyNotFoundError,
    RiskPolicyRegistryError,
    RiskPolicyValidationError,
)

# ── Value objects ───────────────────────────────────────────────────────────
from .risk_policy import RiskPolicy
from .risk_policy_audit import RiskPolicyAuditReport, RiskPolicyAuditor
from .risk_policy_chain import RiskPolicyChain
from .risk_policy_condition import RiskPolicyCondition
from .risk_policy_context import RiskPolicyContext
from .risk_policy_engine import RiskPolicyEngine, RiskPolicyEngineStatus
from .risk_policy_evaluator import RiskPolicyEvaluator
from .risk_policy_events import (
    RiskPolicyEvent,
    make_evaluation_completed,
    make_evaluation_started,
    make_immediate_action_triggered,
    make_policy_approved,
    make_policy_blocked,
    make_policy_escalated,
    make_policy_loaded,
    make_policy_rejected,
    make_policy_validated,
)
from .risk_policy_factory import RiskPolicyFactory
from .risk_policy_history import RiskPolicyHistory
from .risk_policy_manager import RiskPolicyManager
from .risk_policy_priority import PolicyPriorityResolver
from .risk_policy_registry import RiskPolicyRegistry
from .risk_policy_request import RiskPolicyRequest
from .risk_policy_response import RiskEvaluationSummary, RiskPolicyResponse
from .risk_policy_result import RiskPolicyResult
from .risk_policy_rule import RiskPolicyRule
from .risk_policy_statistics import RiskPolicyStatistics
from .risk_policy_validator import (
    RiskPolicyValidationCheckResult,
    RiskPolicyValidationResult,
    RiskPolicyValidator,
)

__all__ = [
    # ── Constants ───────────────────────────────────────────────────
    "POLICY_SYSTEM_ID",
    "EVALUATOR_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "AUDITOR_SYSTEM_ID",
    "CHAIN_SYSTEM_ID",
    "VERSION",
    "SCHEMA_VERSION",
    "ACTION_SEVERITY",
    "DENY_ACTIONS",
    "PERMISSIVE_ACTIONS",
    "DEFAULT_POLICY_ACTION",
    "DEFAULT_MAX_POLICIES",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_AUDIT_RECORDS",
    "DEFAULT_EVALUATION_TIMEOUT_S",
    "DEFAULT_MAX_CHAIN_DEPTH",
    "DEFAULT_CONFLICT_RESOLUTION_ORDER",
    # ── Actors ──────────────────────────────────────────────────────
    "ACTOR_POLICY_ENGINE",
    "ACTOR_EVALUATOR",
    "ACTOR_REGISTRY",
    "ACTOR_SYSTEM",
    "ACTOR_OPERATOR",
    # ── Enumerations ────────────────────────────────────────────────
    "PolicyType",
    "PolicyAction",
    "PolicyPriority",
    "EvaluationMode",
    "LogicalOperator",
    "ConditionOperator",
    "ConflictResolutionStrategy",
    "PolicyEventType",
    "ValidationCode",
    # ── Exceptions ──────────────────────────────────────────────────
    "RiskPolicyError",
    "RiskPolicyEngineNotRunningError",
    "RiskPolicyNotFoundError",
    "RiskPolicyValidationError",
    "RiskPolicyEvaluationError",
    "RiskPolicyConflictError",
    "RiskPolicyRegistryError",
    "RiskPolicyConfigurationError",
    "RiskPolicyAuditError",
    "RiskPolicyCapacityError",
    # ── Value objects ────────────────────────────────────────────────
    "RiskPolicyCondition",
    "RiskPolicyRule",
    "RiskPolicy",
    "RiskPolicyContext",
    "RiskPolicyRequest",
    "RiskPolicyResult",
    "RiskEvaluationSummary",
    "RiskPolicyResponse",
    "RiskPolicyAuditReport",
    # ── Events ──────────────────────────────────────────────────────
    "RiskPolicyEvent",
    "make_evaluation_started",
    "make_policy_loaded",
    "make_policy_validated",
    "make_policy_approved",
    "make_policy_rejected",
    "make_policy_blocked",
    "make_policy_escalated",
    "make_immediate_action_triggered",
    "make_evaluation_completed",
    # ── Validation ──────────────────────────────────────────────────
    "RiskPolicyValidationCheckResult",
    "RiskPolicyValidationResult",
    # ── Services ────────────────────────────────────────────────────
    "RiskPolicyEvaluator",
    "RiskPolicyChain",
    "RiskPolicyRegistry",
    "RiskPolicyValidator",
    "RiskPolicyAuditor",
    "RiskPolicyStatistics",
    "RiskPolicyHistory",
    "RiskPolicyFactory",
    "RiskPolicyPriorityResolver",  # exported below via alias
    "RiskPolicyManager",
    # ── Engine ──────────────────────────────────────────────────────
    "RiskPolicyEngine",
    "RiskPolicyEngineStatus",
]

# Convenience alias matching naming convention
RiskPolicyPriorityResolver = PolicyPriorityResolver
