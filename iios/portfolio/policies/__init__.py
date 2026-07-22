"""
iios/portfolio/policies/__init__.py
====================================
Public API for the Institutional Portfolio Policy Framework.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

# Constants / enums
from .constants import (
    ACTION_SEVERITY,
    ACTION_SEVERITY_ORDER,
    ACTOR_ENGINE,
    ACTOR_EVALUATOR,
    ACTOR_MANAGER,
    ACTOR_POLICY,
    APPROVAL_ACTIONS,
    BLOCKING_ACTIONS,
    DEFAULT_MAX_CHAIN_SIZE,
    DEFAULT_MAX_EVALUATIONS,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    ESCALATION_ACTIONS,
    POLICY_SYSTEM_ID,
    VERSION,
    PolicyAction,
    PolicyChainMode,
    PolicyConflictResolution,
    PolicyEvaluationStatus,
    PolicyEventType,
    PolicyPriority,
    PolicyStatus,
    PolicyType,
)

# Exceptions
from .exceptions import (
    PortfolioPolicyAuditError,
    PortfolioPolicyCapacityError,
    PortfolioPolicyChainError,
    PortfolioPolicyConfigurationError,
    PortfolioPolicyConflictError,
    PortfolioPolicyError,
    PortfolioPolicyEvaluationError,
    PortfolioPolicyNotFoundError,
    PortfolioPolicyNotRunningError,
    PortfolioPolicyValidationError,
)

# Context / request
from .portfolio_policy_context import PolicyContext
from .portfolio_policy_request import PortfolioPolicyRequest

# Domain objects
from .portfolio_policy_condition import PolicyCondition, PolicyConditionResult
from .portfolio_policy_rule import PolicyRule, PolicyRuleResult
from .portfolio_policy import PolicyOutcome, PortfolioPolicy
from .portfolio_policy_priority import PolicyPriorityResolver

# Result / response
from .portfolio_policy_result import PolicyEvaluationSummary, PortfolioPolicyResult
from .portfolio_policy_response import PortfolioPolicyResponse

# Audit
from .portfolio_policy_audit import PolicyAuditEntry, PortfolioPolicyAuditReport

# Events
from .portfolio_policy_events import (
    PolicyEngineEvent,
    make_policy_approved,
    make_policy_blocked,
    make_policy_escalated,
    make_policy_evaluation_completed,
    make_policy_evaluation_started,
    make_policy_loaded,
    make_policy_rejected,
    make_policy_validated,
)

# Statistics / history
from .portfolio_policy_statistics import PortfolioPolicyStatistics
from .portfolio_policy_history import PortfolioPolicyHistory

# Chain / evaluator / validator
from .portfolio_policy_chain import PolicyChain
from .portfolio_policy_evaluator import PortfolioPolicyEvaluator
from .portfolio_policy_validator import (
    PolicyValidationCheckResult,
    PolicyValidationResult,
    PortfolioPolicyValidator,
)

# Registry / factory
from .portfolio_policy_registry import PortfolioPolicyRegistry
from .portfolio_policy_factory import PortfolioPolicyFactory

# Manager / Engine (primary interfaces)
from .portfolio_policy_manager import PortfolioPolicyManager
from .portfolio_policy_engine import PolicyEngineStatus, PortfolioPolicyEngine

__all__ = [
    # Constants
    "ACTION_SEVERITY",
    "ACTION_SEVERITY_ORDER",
    "ACTOR_ENGINE",
    "ACTOR_EVALUATOR",
    "ACTOR_MANAGER",
    "ACTOR_POLICY",
    "APPROVAL_ACTIONS",
    "BLOCKING_ACTIONS",
    "DEFAULT_MAX_CHAIN_SIZE",
    "DEFAULT_MAX_EVALUATIONS",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_POLICIES",
    "ESCALATION_ACTIONS",
    "POLICY_SYSTEM_ID",
    "VERSION",
    "PolicyAction",
    "PolicyChainMode",
    "PolicyConflictResolution",
    "PolicyEvaluationStatus",
    "PolicyEventType",
    "PolicyPriority",
    "PolicyStatus",
    "PolicyType",
    # Exceptions
    "PortfolioPolicyAuditError",
    "PortfolioPolicyCapacityError",
    "PortfolioPolicyChainError",
    "PortfolioPolicyConfigurationError",
    "PortfolioPolicyConflictError",
    "PortfolioPolicyError",
    "PortfolioPolicyEvaluationError",
    "PortfolioPolicyNotFoundError",
    "PortfolioPolicyNotRunningError",
    "PortfolioPolicyValidationError",
    # Context / request
    "PolicyContext",
    "PortfolioPolicyRequest",
    # Domain objects
    "PolicyCondition",
    "PolicyConditionResult",
    "PolicyRule",
    "PolicyRuleResult",
    "PolicyOutcome",
    "PortfolioPolicy",
    "PolicyPriorityResolver",
    # Result / response
    "PolicyEvaluationSummary",
    "PortfolioPolicyResult",
    "PortfolioPolicyResponse",
    # Audit
    "PolicyAuditEntry",
    "PortfolioPolicyAuditReport",
    # Events
    "PolicyEngineEvent",
    "make_policy_approved",
    "make_policy_blocked",
    "make_policy_escalated",
    "make_policy_evaluation_completed",
    "make_policy_evaluation_started",
    "make_policy_loaded",
    "make_policy_rejected",
    "make_policy_validated",
    # Statistics / history
    "PortfolioPolicyStatistics",
    "PortfolioPolicyHistory",
    # Chain / evaluator / validator
    "PolicyChain",
    "PortfolioPolicyEvaluator",
    "PolicyValidationCheckResult",
    "PolicyValidationResult",
    "PortfolioPolicyValidator",
    # Registry / factory
    "PortfolioPolicyRegistry",
    "PortfolioPolicyFactory",
    # Manager / engine
    "PortfolioPolicyManager",
    "PolicyEngineStatus",
    "PortfolioPolicyEngine",
]
