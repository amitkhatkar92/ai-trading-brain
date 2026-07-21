"""
constants.py — iios.decision.policies
======================================
Policy types, actions, priorities, and configuration constants.

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum, IntEnum

# ── Identity ─────────────────────────────────────────────────────────────────

POLICIES_SYSTEM_ID = "iios:decision:policies"
VERSION             = "1.0.0"
SCHEMA_VERSION      = "1.0"

# ── Actors ───────────────────────────────────────────────────────────────────

ACTOR_ENGINE    = "iios:policy:engine"
ACTOR_MANAGER   = "iios:policy:manager"
ACTOR_EVALUATOR = "iios:policy:evaluator"
ACTOR_VALIDATOR = "iios:policy:validator"
ACTOR_SYSTEM    = "iios:policy:system"
ACTOR_OPERATOR  = "iios:policy:operator"

# ── Capacity Defaults ─────────────────────────────────────────────────────────

DEFAULT_MAX_POLICIES        = 500
DEFAULT_MAX_HISTORY         = 2_000
DEFAULT_MAX_CHAIN           = 50
DEFAULT_EVALUATION_TIMEOUT  = 30.0
EMA_ALPHA                   = 0.1
THROUGHPUT_WINDOW_S         = 60.0

# ── Policy Types (15) ─────────────────────────────────────────────────────────

class PolicyType(str, Enum):
    RISK                  = "risk"
    COMPLIANCE            = "compliance"
    CAPITAL               = "capital"
    EXPOSURE              = "exposure"
    POSITION              = "position"
    PORTFOLIO             = "portfolio"
    MARKET                = "market"
    LIQUIDITY             = "liquidity"
    VOLATILITY            = "volatility"
    TRADING_SESSION       = "trading_session"
    INFRASTRUCTURE        = "infrastructure"
    OPERATIONAL           = "operational"
    RECOVERY              = "recovery"
    MONITORING            = "monitoring"
    ENTERPRISE_GOVERNANCE = "enterprise_governance"

# ── Policy Actions (7) ────────────────────────────────────────────────────────

class PolicyAction(str, Enum):
    APPROVE                 = "approve"
    APPROVE_WITH_CONDITIONS = "approve_with_conditions"
    REJECT                  = "reject"
    BLOCK                   = "block"
    ESCALATE                = "escalate"
    DEFER                   = "defer"
    REQUIRE_MANUAL_REVIEW   = "require_manual_review"

# ── Policy Priority (IntEnum — lower integer = higher urgency) ────────────────

class PolicyPriority(IntEnum):
    CRITICAL      = 1
    HIGH          = 2
    MEDIUM        = 3
    LOW           = 4
    INFORMATIONAL = 5

# ── Policy Status ─────────────────────────────────────────────────────────────

class PolicyStatus(str, Enum):
    ACTIVE     = "active"
    INACTIVE   = "inactive"
    DRAFT      = "draft"
    DEPRECATED = "deprecated"

# ── Policy Chain Mode (6) ─────────────────────────────────────────────────────

class PolicyChainMode(str, Enum):
    SEQUENTIAL  = "sequential"
    PARALLEL    = "parallel"
    COMPOSITE   = "composite"
    NESTED      = "nested"
    CONDITIONAL = "conditional"
    WEIGHTED    = "weighted"

# ── Conflict Resolution Strategy ─────────────────────────────────────────────

class ConflictResolutionStrategy(str, Enum):
    HIGHEST_PRIORITY_WINS   = "highest_priority_wins"
    EXPLICIT_DENY_OVERRIDES = "explicit_deny_overrides"
    ESCALATION_OVERRIDES    = "escalation_overrides"

# ── Condition Operators ───────────────────────────────────────────────────────

class PolicyConditionOperator(str, Enum):
    LT         = "lt"
    LTE        = "lte"
    GT         = "gt"
    GTE        = "gte"
    EQ         = "eq"
    NE         = "ne"
    IN         = "in"
    NOT_IN     = "not_in"
    EXISTS     = "exists"
    NOT_EXISTS = "not_exists"

# ── Rule Logic ────────────────────────────────────────────────────────────────

class PolicyRuleLogic(str, Enum):
    AND = "and"
    OR  = "or"
    NOT = "not"

# ── Evaluation Status ─────────────────────────────────────────────────────────

class PolicyEvaluationStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"

# ── Validation Codes (6) ─────────────────────────────────────────────────────

class PolicyValidationCode(str, Enum):
    POLICY_IDENTITY    = "policy_identity"
    RULE_CONSISTENCY   = "rule_consistency"
    CONDITION_VALIDITY = "condition_validity"
    PRIORITY_INTEGRITY = "priority_integrity"
    CONFLICT_INTEGRITY = "conflict_integrity"
    AUDIT_COMPLETENESS = "audit_completeness"

# ── Events (8) ───────────────────────────────────────────────────────────────

class PolicyEventType(str, Enum):
    POLICY_EVALUATION_STARTED   = "policy_evaluation_started"
    POLICY_LOADED               = "policy_loaded"
    POLICY_VALIDATED            = "policy_validated"
    POLICY_APPROVED             = "policy_approved"
    POLICY_REJECTED             = "policy_rejected"
    POLICY_BLOCKED              = "policy_blocked"
    POLICY_ESCALATED            = "policy_escalated"
    POLICY_EVALUATION_COMPLETED = "policy_evaluation_completed"

# ── Action Precedence (lower int = wins conflict) ─────────────────────────────

ACTION_PRECEDENCE: dict[PolicyAction, int] = {
    PolicyAction.BLOCK:                   1,
    PolicyAction.REJECT:                  2,
    PolicyAction.ESCALATE:                3,
    PolicyAction.REQUIRE_MANUAL_REVIEW:   4,
    PolicyAction.DEFER:                   5,
    PolicyAction.APPROVE_WITH_CONDITIONS: 6,
    PolicyAction.APPROVE:                 7,
}

DENY_ACTIONS: frozenset[PolicyAction] = frozenset({
    PolicyAction.BLOCK,
    PolicyAction.REJECT,
})

ESCALATION_ACTIONS: frozenset[PolicyAction] = frozenset({
    PolicyAction.ESCALATE,
    PolicyAction.REQUIRE_MANUAL_REVIEW,
})

APPROVAL_ACTIONS: frozenset[PolicyAction] = frozenset({
    PolicyAction.APPROVE,
    PolicyAction.APPROVE_WITH_CONDITIONS,
})
