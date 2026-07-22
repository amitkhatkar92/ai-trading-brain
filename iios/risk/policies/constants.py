"""
constants.py — iios.risk.policies
====================================
Enumerations, identifiers, and defaults for the Risk Policy Framework.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet, Tuple

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
POLICY_SYSTEM_ID:    str = "iios:risk:policies"
EVALUATOR_SYSTEM_ID: str = "iios:risk:policies:evaluator"
REGISTRY_SYSTEM_ID:  str = "iios:risk:policies:registry"
FACTORY_SYSTEM_ID:   str = "iios:risk:policies:factory"
AUDITOR_SYSTEM_ID:   str = "iios:risk:policies:auditor"
CHAIN_SYSTEM_ID:     str = "iios:risk:policies:chain"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------
ACTOR_POLICY_ENGINE:    str = "iios:risk:policies:engine"
ACTOR_EVALUATOR:        str = "iios:risk:policies:evaluator"
ACTOR_REGISTRY:         str = "iios:risk:policies:registry"
ACTOR_SYSTEM:           str = "iios:system"
ACTOR_OPERATOR:         str = "operator"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_POLICIES:         int = 10_000
DEFAULT_MAX_HISTORY:          int = 1_000
DEFAULT_MAX_AUDIT_RECORDS:    int = 10_000
DEFAULT_EVALUATION_TIMEOUT_S: float = 30.0
DEFAULT_MAX_CHAIN_DEPTH:      int = 20


# ---------------------------------------------------------------------------
# PolicyType — 15 supported policy domains
# ---------------------------------------------------------------------------
class PolicyType(str, Enum):
    """Classification of risk governance policy domains."""
    MARKET_RISK          = "market_risk"
    PORTFOLIO_RISK       = "portfolio_risk"
    POSITION_RISK        = "position_risk"
    CREDIT_RISK          = "credit_risk"
    LIQUIDITY_RISK       = "liquidity_risk"
    COUNTERPARTY_RISK    = "counterparty_risk"
    OPERATIONAL_RISK     = "operational_risk"
    INFRASTRUCTURE_RISK  = "infrastructure_risk"
    CYBER_RISK           = "cyber_risk"
    CONCENTRATION_RISK   = "concentration_risk"
    EXPOSURE_RISK        = "exposure_risk"
    STRESS_TESTING       = "stress_testing"
    SCENARIO_ANALYSIS    = "scenario_analysis"
    REGULATORY_RISK      = "regulatory_risk"
    ENTERPRISE_GOVERNANCE = "enterprise_governance"


# ---------------------------------------------------------------------------
# PolicyAction — 8 possible outcomes
# ---------------------------------------------------------------------------
class PolicyAction(str, Enum):
    """Governance outcome determined by policy evaluation."""
    APPROVE                 = "approve"
    APPROVE_WITH_CONDITIONS = "approve_with_conditions"
    REJECT                  = "reject"
    BLOCK                   = "block"
    ESCALATE                = "escalate"
    DEFER                   = "defer"
    REQUIRE_MANUAL_REVIEW   = "require_manual_review"
    REQUIRE_IMMEDIATE_ACTION = "require_immediate_action"


# ---------------------------------------------------------------------------
# PolicyPriority — 5 levels
# ---------------------------------------------------------------------------
class PolicyPriority(IntEnum):
    """Policy severity — lower integer = higher priority."""
    CRITICAL      = 1
    HIGH          = 2
    MEDIUM        = 3
    LOW           = 4
    INFORMATIONAL = 5


# ---------------------------------------------------------------------------
# EvaluationMode
# ---------------------------------------------------------------------------
class EvaluationMode(str, Enum):
    """How rules within a policy are evaluated."""
    SEQUENTIAL  = "sequential"   # first matching rule wins
    PARALLEL    = "parallel"     # all rules evaluated; conflicts resolved
    COMPOSITE   = "composite"    # policy is a composition of sub-policies
    NESTED      = "nested"       # policy contains nested sub-policies
    CONDITIONAL = "conditional"  # evaluation depends on prior outcomes
    WEIGHTED    = "weighted"     # rules have numeric weights; highest score wins


# ---------------------------------------------------------------------------
# LogicalOperator — how conditions combine within a rule
# ---------------------------------------------------------------------------
class LogicalOperator(str, Enum):
    """Logical combination of conditions."""
    ALL = "all"   # all conditions must pass (AND)
    ANY = "any"   # any condition must pass (OR)


# ---------------------------------------------------------------------------
# ConditionOperator — comparison operators
# ---------------------------------------------------------------------------
class ConditionOperator(str, Enum):
    """Operator used to evaluate a condition."""
    GT        = "gt"         # >
    GTE       = "gte"        # >=
    LT        = "lt"         # <
    LTE       = "lte"        # <=
    EQ        = "eq"         # ==
    NEQ       = "neq"        # !=
    IN        = "in"         # value in collection
    NOT_IN    = "not_in"     # value not in collection
    EXISTS    = "exists"     # key present in inputs
    NOT_EXISTS = "not_exists" # key not present
    IS_TRUE   = "is_true"    # value is truthy
    IS_FALSE  = "is_false"   # value is falsy


# ---------------------------------------------------------------------------
# ConflictResolutionStrategy
# ---------------------------------------------------------------------------
class ConflictResolutionStrategy(str, Enum):
    """How conflicting policy outcomes are resolved."""
    HIGHEST_PRIORITY_WINS           = "highest_priority_wins"
    CRITICAL_OVERRIDES              = "critical_overrides"
    EXPLICIT_DENY_OVERRIDES         = "explicit_deny_overrides"
    ESCALATION_OVERRIDES_CONDITIONAL = "escalation_overrides_conditional"
    IMMEDIATE_ACTION_OVERRIDES_ALL  = "immediate_action_overrides_all"


# ---------------------------------------------------------------------------
# PolicyEventType — 9 events
# ---------------------------------------------------------------------------
class PolicyEventType(str, Enum):
    """Events emitted by the Risk Policy Framework."""
    EVALUATION_STARTED           = "risk_policy_evaluation_started"
    POLICY_LOADED                = "risk_policy_loaded"
    POLICY_VALIDATED             = "risk_policy_validated"
    POLICY_APPROVED              = "risk_policy_approved"
    POLICY_REJECTED              = "risk_policy_rejected"
    POLICY_BLOCKED               = "risk_policy_blocked"
    POLICY_ESCALATED             = "risk_policy_escalated"
    IMMEDIATE_ACTION_TRIGGERED   = "risk_immediate_action_triggered"
    EVALUATION_COMPLETED         = "risk_policy_evaluation_completed"


# ---------------------------------------------------------------------------
# ValidationCode
# ---------------------------------------------------------------------------
class ValidationCode(str, Enum):
    """Validation check identifiers."""
    POLICY_CONSISTENCY        = "policy_consistency"
    RULE_CONSISTENCY          = "rule_consistency"
    CONDITION_VALIDITY        = "condition_validity"
    PRIORITY_INTEGRITY        = "priority_integrity"
    CONFLICT_RESOLUTION_INTEGRITY = "conflict_resolution_integrity"
    EVALUATION_COMPLETENESS   = "evaluation_completeness"
    AUDIT_COMPLETENESS        = "audit_completeness"
    REQUEST_VALIDITY          = "request_validity"


# ---------------------------------------------------------------------------
# Action severity ordering (for conflict resolution)
# Higher value = more severe
# ---------------------------------------------------------------------------
ACTION_SEVERITY: Dict[PolicyAction, int] = {
    PolicyAction.APPROVE:                 0,
    PolicyAction.APPROVE_WITH_CONDITIONS: 1,
    PolicyAction.DEFER:                   2,
    PolicyAction.REQUIRE_MANUAL_REVIEW:   3,
    PolicyAction.ESCALATE:                4,
    PolicyAction.REJECT:                  5,
    PolicyAction.BLOCK:                   6,
    PolicyAction.REQUIRE_IMMEDIATE_ACTION: 7,
}

# Deny actions that override approval
DENY_ACTIONS: FrozenSet[PolicyAction] = frozenset({
    PolicyAction.REJECT,
    PolicyAction.BLOCK,
    PolicyAction.REQUIRE_IMMEDIATE_ACTION,
})

# Actions that allow the workflow to proceed
PERMISSIVE_ACTIONS: FrozenSet[PolicyAction] = frozenset({
    PolicyAction.APPROVE,
    PolicyAction.APPROVE_WITH_CONDITIONS,
})

# Default conflict resolution ordering
DEFAULT_CONFLICT_RESOLUTION_ORDER: Tuple[ConflictResolutionStrategy, ...] = (
    ConflictResolutionStrategy.IMMEDIATE_ACTION_OVERRIDES_ALL,
    ConflictResolutionStrategy.CRITICAL_OVERRIDES,
    ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES,
    ConflictResolutionStrategy.ESCALATION_OVERRIDES_CONDITIONAL,
    ConflictResolutionStrategy.HIGHEST_PRIORITY_WINS,
)

# Default action when no policies are registered
DEFAULT_POLICY_ACTION: PolicyAction = PolicyAction.APPROVE
