"""
constants.py — iios.supervisor.policy
=======================================
Enumerations, identifiers, and defaults for the AI Governance Policy Framework.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet, Set

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
POLICY_SYSTEM_ID:    str = "iios:supervisor:policy"
EVALUATOR_SYSTEM_ID: str = "iios:supervisor:policy:evaluator"
REGISTRY_SYSTEM_ID:  str = "iios:supervisor:policy:registry"
FACTORY_SYSTEM_ID:   str = "iios:supervisor:policy:factory"
CHAIN_SYSTEM_ID:     str = "iios:supervisor:policy:chain"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------
ACTOR_POLICY_ENGINE: str = "iios:supervisor:policy:engine"
ACTOR_EVALUATOR:     str = "iios:supervisor:policy:evaluator"
ACTOR_REGISTRY:      str = "iios:supervisor:policy:registry"
ACTOR_SYSTEM:        str = "iios:system"
ACTOR_OPERATOR:      str = "operator"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_POLICIES:         int   = 10_000
DEFAULT_MAX_HISTORY:          int   = 1_000
DEFAULT_EVALUATION_TIMEOUT_S: float = 30.0
DEFAULT_MAX_CHAIN_DEPTH:      int   = 20


# ---------------------------------------------------------------------------
# GovernancePolicyType — 12 supported governance domains
# ---------------------------------------------------------------------------
class GovernancePolicyType(str, Enum):
    """Classification of enterprise governance policy domains."""
    HEALTH_GOVERNANCE       = "health_governance"
    RISK_GOVERNANCE         = "risk_governance"
    OPERATIONAL_GOVERNANCE  = "operational_governance"
    COMPLIANCE_GOVERNANCE   = "compliance_governance"
    ESCALATION_GOVERNANCE   = "escalation_governance"
    PERFORMANCE_GOVERNANCE  = "performance_governance"
    AVAILABILITY_GOVERNANCE = "availability_governance"
    LIFECYCLE_GOVERNANCE    = "lifecycle_governance"
    SUPERVISION_GOVERNANCE  = "supervision_governance"
    ENTERPRISE_GOVERNANCE   = "enterprise_governance"
    SAFETY_GOVERNANCE       = "safety_governance"
    REGULATORY_GOVERNANCE   = "regulatory_governance"


# ---------------------------------------------------------------------------
# PolicyAction — 7 possible outcomes
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
    SEQUENTIAL  = "sequential"
    PARALLEL    = "parallel"
    COMPOSITE   = "composite"
    NESTED      = "nested"
    CONDITIONAL = "conditional"
    WEIGHTED    = "weighted"


# ---------------------------------------------------------------------------
# LogicalOperator
# ---------------------------------------------------------------------------
class LogicalOperator(str, Enum):
    """Logical combination of conditions."""
    ALL = "all"
    ANY = "any"


# ---------------------------------------------------------------------------
# ConditionOperator
# ---------------------------------------------------------------------------
class ConditionOperator(str, Enum):
    """Operator used to evaluate a condition."""
    GT         = "gt"
    GTE        = "gte"
    LT         = "lt"
    LTE        = "lte"
    EQ         = "eq"
    NEQ        = "neq"
    IN         = "in"
    NOT_IN     = "not_in"
    EXISTS     = "exists"
    NOT_EXISTS = "not_exists"
    IS_TRUE    = "is_true"
    IS_FALSE   = "is_false"


# ---------------------------------------------------------------------------
# ConflictResolutionStrategy
# ---------------------------------------------------------------------------
class ConflictResolutionStrategy(str, Enum):
    """How conflicting policy outcomes are resolved."""
    HIGHEST_PRIORITY_WINS            = "highest_priority_wins"
    CRITICAL_OVERRIDES               = "critical_overrides"
    EXPLICIT_DENY_OVERRIDES          = "explicit_deny_overrides"
    ESCALATION_OVERRIDES_CONDITIONAL = "escalation_overrides_conditional"
    BLOCK_OVERRIDES_ALL              = "block_overrides_all"


# ---------------------------------------------------------------------------
# GovernancePolicyEventType — 8 events
# ---------------------------------------------------------------------------
class GovernancePolicyEventType(str, Enum):
    """Event types emitted by the governance policy framework."""
    POLICY_REGISTERED        = "governance_policy_registered"
    POLICY_UNREGISTERED      = "governance_policy_unregistered"
    EVALUATION_STARTED       = "governance_evaluation_started"
    EVALUATION_COMPLETED     = "governance_evaluation_completed"
    EVALUATION_FAILED        = "governance_evaluation_failed"
    POLICY_ENGINE_STARTED    = "governance_policy_engine_started"
    POLICY_ENGINE_STOPPED    = "governance_policy_engine_stopped"
    CONFLICT_RESOLVED        = "governance_conflict_resolved"


# ---------------------------------------------------------------------------
# GovernanceValidationCode
# ---------------------------------------------------------------------------
class GovernanceValidationCode(str, Enum):
    """Validation check identifiers."""
    REQUEST_COMPLETENESS  = "request_completeness"
    CONTEXT_CONSISTENCY   = "context_consistency"
    POLICY_INTEGRITY      = "policy_integrity"
    RULE_INTEGRITY        = "rule_integrity"
    CONDITION_INTEGRITY   = "condition_integrity"


# ---------------------------------------------------------------------------
# Semantic sets
# ---------------------------------------------------------------------------
DENY_ACTIONS: FrozenSet[PolicyAction] = frozenset({
    PolicyAction.REJECT,
    PolicyAction.BLOCK,
})

PERMISSIVE_ACTIONS: FrozenSet[PolicyAction] = frozenset({
    PolicyAction.APPROVE,
    PolicyAction.APPROVE_WITH_CONDITIONS,
})

ESCALATION_ACTIONS: FrozenSet[PolicyAction] = frozenset({
    PolicyAction.ESCALATE,
    PolicyAction.REQUIRE_MANUAL_REVIEW,
})

# ---------------------------------------------------------------------------
# Action severity (higher = more restrictive)
# ---------------------------------------------------------------------------
ACTION_SEVERITY: Dict[PolicyAction, int] = {
    PolicyAction.APPROVE:                 0,
    PolicyAction.APPROVE_WITH_CONDITIONS: 1,
    PolicyAction.DEFER:                   2,
    PolicyAction.REQUIRE_MANUAL_REVIEW:   3,
    PolicyAction.ESCALATE:                4,
    PolicyAction.REJECT:                  5,
    PolicyAction.BLOCK:                   6,
}

# Default action when no rule matches
DEFAULT_POLICY_ACTION: PolicyAction = PolicyAction.APPROVE
