"""
iios.market.policies
=====================
Institutional Market Policy Framework — C12 Market Intelligence, Module 3.

Public exports from this package:

Constants & Enumerations
------------------------
POLICY_SYSTEM_ID, EVALUATOR_SYSTEM_ID, REGISTRY_SYSTEM_ID,
FACTORY_SYSTEM_ID, AUDITOR_SYSTEM_ID, CHAIN_SYSTEM_ID, VERSION
MarketPolicyType, PolicyAction, PolicyPriority, EvaluationMode,
LogicalOperator, ConditionOperator, ConflictResolutionStrategy,
PolicyEventType, ValidationCode

Exceptions
----------
MarketPolicyError, MarketPolicyEngineNotRunningError,
MarketPolicyNotFoundError, MarketPolicyValidationError,
MarketPolicyEvaluationError, MarketPolicyConflictError,
MarketPolicyRegistryError, MarketPolicyConfigurationError,
MarketPolicyAuditError, MarketPolicyCapacityError

Value Objects
-------------
MarketPolicyCondition, MarketPolicyRule, MarketPolicy
MarketPolicyContext, MarketPolicyRequest
MarketPolicyResult, MarketEvaluationSummary, MarketPolicyResponse
MarketPolicyAuditReport

Events
------
MarketPolicyEvent
make_market_policy_evaluation_started, make_market_policy_loaded,
make_market_policy_validated, make_market_policy_approved,
make_market_policy_rejected, make_market_policy_blocked,
make_market_policy_escalated, make_market_policy_evaluation_completed

Validation
----------
MarketPolicyValidationCheckResult, MarketPolicyValidationResult

Services
--------
MarketPolicyEvaluator, MarketPolicyChain, MarketPolicyRegistry,
MarketPolicyValidator, MarketPolicyAuditor, MarketPolicyStatistics,
MarketPolicyHistory, MarketPolicyFactory, MarketPolicyManager
MarketPolicyPriorityResolver

Engine (primary public interface)
----------------------------------
MarketPolicyEngine, MarketPolicyEngineStatus
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
    MarketPolicyType,
    PolicyAction,
    PolicyEventType,
    PolicyPriority,
    ValidationCode,
)

# ── Exceptions ──────────────────────────────────────────────────────────────
from .exceptions import (
    MarketPolicyAuditError,
    MarketPolicyCapacityError,
    MarketPolicyConfigurationError,
    MarketPolicyConflictError,
    MarketPolicyEngineNotRunningError,
    MarketPolicyError,
    MarketPolicyEvaluationError,
    MarketPolicyNotFoundError,
    MarketPolicyRegistryError,
    MarketPolicyValidationError,
)

# ── Value objects ───────────────────────────────────────────────────────────
from .market_policy import MarketPolicy
from .market_policy_audit import MarketPolicyAuditReport, MarketPolicyAuditor
from .market_policy_chain import MarketPolicyChain
from .market_policy_condition import MarketPolicyCondition
from .market_policy_context import MarketPolicyContext
from .market_policy_engine import MarketPolicyEngine, MarketPolicyEngineStatus
from .market_policy_evaluator import MarketPolicyEvaluator
from .market_policy_events import (
    MarketPolicyEvent,
    make_market_policy_approved,
    make_market_policy_blocked,
    make_market_policy_escalated,
    make_market_policy_evaluation_completed,
    make_market_policy_evaluation_started,
    make_market_policy_loaded,
    make_market_policy_rejected,
    make_market_policy_validated,
)
from .market_policy_factory import MarketPolicyFactory
from .market_policy_history import MarketPolicyHistory
from .market_policy_manager import MarketPolicyManager
from .market_policy_priority import MarketPolicyPriorityResolver
from .market_policy_registry import MarketPolicyRegistry
from .market_policy_request import MarketPolicyRequest
from .market_policy_response import MarketEvaluationSummary, MarketPolicyResponse
from .market_policy_result import MarketPolicyResult
from .market_policy_rule import MarketPolicyRule
from .market_policy_statistics import MarketPolicyStatistics
from .market_policy_validator import (
    MarketPolicyValidationCheckResult,
    MarketPolicyValidationResult,
    MarketPolicyValidator,
)

__all__ = [
    # Constants
    "ACTION_SEVERITY",
    "ACTOR_EVALUATOR",
    "ACTOR_OPERATOR",
    "ACTOR_POLICY_ENGINE",
    "ACTOR_REGISTRY",
    "ACTOR_SYSTEM",
    "AUDITOR_SYSTEM_ID",
    "CHAIN_SYSTEM_ID",
    "DEFAULT_CONFLICT_RESOLUTION_ORDER",
    "DEFAULT_EVALUATION_TIMEOUT_S",
    "DEFAULT_MAX_AUDIT_RECORDS",
    "DEFAULT_MAX_CHAIN_DEPTH",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_POLICIES",
    "DEFAULT_POLICY_ACTION",
    "DENY_ACTIONS",
    "EVALUATOR_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "PERMISSIVE_ACTIONS",
    "POLICY_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "SCHEMA_VERSION",
    "VERSION",
    # Enumerations
    "ConditionOperator",
    "ConflictResolutionStrategy",
    "EvaluationMode",
    "LogicalOperator",
    "MarketPolicyType",
    "PolicyAction",
    "PolicyEventType",
    "PolicyPriority",
    "ValidationCode",
    # Exceptions
    "MarketPolicyAuditError",
    "MarketPolicyCapacityError",
    "MarketPolicyConfigurationError",
    "MarketPolicyConflictError",
    "MarketPolicyEngineNotRunningError",
    "MarketPolicyError",
    "MarketPolicyEvaluationError",
    "MarketPolicyNotFoundError",
    "MarketPolicyRegistryError",
    "MarketPolicyValidationError",
    # Value objects
    "MarketPolicy",
    "MarketPolicyAuditReport",
    "MarketPolicyAuditor",
    "MarketPolicyChain",
    "MarketPolicyCondition",
    "MarketPolicyContext",
    "MarketEvaluationSummary",
    "MarketPolicyEvent",
    "MarketPolicyFactory",
    "MarketPolicyHistory",
    "MarketPolicyManager",
    "MarketPolicyPriorityResolver",
    "MarketPolicyRegistry",
    "MarketPolicyRequest",
    "MarketPolicyResponse",
    "MarketPolicyResult",
    "MarketPolicyRule",
    "MarketPolicyStatistics",
    "MarketPolicyValidationCheckResult",
    "MarketPolicyValidationResult",
    "MarketPolicyValidator",
    # Engine
    "MarketPolicyEngine",
    "MarketPolicyEngineStatus",
    # Event factories
    "make_market_policy_approved",
    "make_market_policy_blocked",
    "make_market_policy_escalated",
    "make_market_policy_evaluation_completed",
    "make_market_policy_evaluation_started",
    "make_market_policy_loaded",
    "make_market_policy_rejected",
    "make_market_policy_validated",
]
