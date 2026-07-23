"""
constants.py — iios.market.policies
=====================================
Enumerations, identifiers, and defaults for the Market Policy Framework.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
POLICY_SYSTEM_ID:    str = "iios:market:policies"
EVALUATOR_SYSTEM_ID: str = "iios:market:policies:evaluator"
REGISTRY_SYSTEM_ID:  str = "iios:market:policies:registry"
FACTORY_SYSTEM_ID:   str = "iios:market:policies:factory"
AUDITOR_SYSTEM_ID:   str = "iios:market:policies:auditor"
CHAIN_SYSTEM_ID:     str = "iios:market:policies:chain"

# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------
VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------
ACTOR_POLICY_ENGINE: str = "iios:market:policies:engine"
ACTOR_EVALUATOR:     str = "iios:market:policies:evaluator"
ACTOR_REGISTRY:      str = "iios:market:policies:registry"
ACTOR_SYSTEM:        str = "iios:system"
ACTOR_OPERATOR:      str = "operator"

# ---------------------------------------------------------------------------
# Default limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_POLICIES:         int   = 10_000
DEFAULT_MAX_HISTORY:          int   = 1_000
DEFAULT_MAX_AUDIT_RECORDS:    int   = 10_000
DEFAULT_EVALUATION_TIMEOUT_S: float = 30.0
DEFAULT_MAX_CHAIN_DEPTH:      int   = 20


# ---------------------------------------------------------------------------
# MarketPolicyType — 15 supported policy domains
# ---------------------------------------------------------------------------
class MarketPolicyType(str, Enum):
    """Classification of market governance policy domains."""
    MARKET_DATA_POLICY        = "market_data_policy"
    EXCHANGE_ACCESS_POLICY    = "exchange_access_policy"
    TRADING_SESSION_POLICY    = "trading_session_policy"
    MARKET_HOURS_POLICY       = "market_hours_policy"
    ECONOMIC_EVENT_POLICY     = "economic_event_policy"
    CORPORATE_ACTION_POLICY   = "corporate_action_policy"
    DATA_FRESHNESS_POLICY     = "data_freshness_policy"
    MARKET_REGIME_POLICY      = "market_regime_policy"
    VOLATILITY_POLICY         = "volatility_policy"
    SECTOR_COVERAGE_POLICY    = "sector_coverage_policy"
    INDEX_COVERAGE_POLICY     = "index_coverage_policy"
    BREADTH_COVERAGE_POLICY   = "breadth_coverage_policy"
    MARKET_HEALTH_POLICY      = "market_health_policy"
    REGULATORY_POLICY         = "regulatory_policy"
    ENTERPRISE_GOVERNANCE_POLICY = "enterprise_governance_policy"


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
# PolicyEventType — 8 events
# ---------------------------------------------------------------------------
class PolicyEventType(str, Enum):
    """Events emitted by the Market Policy Framework."""
    EVALUATION_STARTED   = "market_policy_evaluation_started"
    POLICY_LOADED        = "market_policy_loaded"
    POLICY_VALIDATED     = "market_policy_validated"
    POLICY_APPROVED      = "market_policy_approved"
    POLICY_REJECTED      = "market_policy_rejected"
    POLICY_BLOCKED       = "market_policy_blocked"
    POLICY_ESCALATED     = "market_policy_escalated"
    EVALUATION_COMPLETED = "market_policy_evaluation_completed"


# ---------------------------------------------------------------------------
# ValidationCode
# ---------------------------------------------------------------------------
class ValidationCode(str, Enum):
    """Validation check identifiers."""
    POLICY_CONSISTENCY            = "policy_consistency"
    RULE_CONSISTENCY              = "rule_consistency"
    CONDITION_VALIDITY            = "condition_validity"
    PRIORITY_INTEGRITY            = "priority_integrity"
    CONFLICT_RESOLUTION_INTEGRITY = "conflict_resolution_integrity"
    EVALUATION_COMPLETENESS       = "evaluation_completeness"
    AUDIT_COMPLETENESS            = "audit_completeness"
    REQUEST_VALIDITY              = "request_validity"


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
}

# Deny actions that override approval
DENY_ACTIONS: FrozenSet[PolicyAction] = frozenset({
    PolicyAction.REJECT,
    PolicyAction.BLOCK,
})

# Permissive actions
PERMISSIVE_ACTIONS: FrozenSet[PolicyAction] = frozenset({
    PolicyAction.APPROVE,
    PolicyAction.APPROVE_WITH_CONDITIONS,
})

# Default resolution order
DEFAULT_CONFLICT_RESOLUTION_ORDER = (
    ConflictResolutionStrategy.BLOCK_OVERRIDES_ALL,
    ConflictResolutionStrategy.CRITICAL_OVERRIDES,
    ConflictResolutionStrategy.EXPLICIT_DENY_OVERRIDES,
    ConflictResolutionStrategy.ESCALATION_OVERRIDES_CONDITIONAL,
    ConflictResolutionStrategy.HIGHEST_PRIORITY_WINS,
)

# Default action when no policies match
DEFAULT_POLICY_ACTION: PolicyAction = PolicyAction.APPROVE
