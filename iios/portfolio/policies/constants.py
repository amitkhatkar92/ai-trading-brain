"""
constants.py — iios.portfolio.policies
=======================================
Enumerations, conflict resolution rules, severity ordering, and default
limits for the Institutional Portfolio Policy Framework.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------
POLICY_SYSTEM_ID: str = "iios:portfolio:policies"
VERSION:          str = "1.0.0"

ACTOR_POLICY:    str = "iios:portfolio:policy"
ACTOR_EVALUATOR: str = "iios:portfolio:policy:evaluator"
ACTOR_ENGINE:    str = "iios:portfolio:policy:engine"
ACTOR_MANAGER:   str = "iios:portfolio:policy:manager"

# ---------------------------------------------------------------------------
# Default capacity limits
# ---------------------------------------------------------------------------
DEFAULT_MAX_POLICIES:    int = 500
DEFAULT_MAX_HISTORY:     int = 1_000
DEFAULT_MAX_EVALUATIONS: int = 10_000
DEFAULT_MAX_CHAIN_SIZE:  int = 50


# ---------------------------------------------------------------------------
# PolicyAction — seven possible outcomes from policy evaluation
# ---------------------------------------------------------------------------
class PolicyAction(str, Enum):
    """
    Outcome of evaluating a portfolio operation against an institutional policy.

    Severity order (most restrictive first):
        BLOCK > REJECT > ESCALATE > REQUIRE_MANUAL_REVIEW > DEFER
        > APPROVE_WITH_CONDITIONS > APPROVE
    """
    APPROVE                = "approve"
    APPROVE_WITH_CONDITIONS = "approve_with_conditions"
    REJECT                 = "reject"
    BLOCK                  = "block"
    ESCALATE               = "escalate"
    DEFER                  = "defer"
    REQUIRE_MANUAL_REVIEW  = "require_manual_review"


# ---------------------------------------------------------------------------
# PolicyType — fifteen institutional policy domains
# ---------------------------------------------------------------------------
class PolicyType(str, Enum):
    CAPITAL_ALLOCATION    = "capital_allocation"
    EXPOSURE              = "exposure"
    DIVERSIFICATION       = "diversification"
    POSITION_SIZE         = "position_size"
    SECTOR_ALLOCATION     = "sector_allocation"
    INDUSTRY_ALLOCATION   = "industry_allocation"
    ASSET_ALLOCATION      = "asset_allocation"
    LIQUIDITY             = "liquidity"
    RISK                  = "risk"
    LEVERAGE              = "leverage"
    CASH_RESERVE          = "cash_reserve"
    REBALANCING           = "rebalancing"
    CONCENTRATION         = "concentration"
    COMPLIANCE            = "compliance"
    ENTERPRISE_GOVERNANCE = "enterprise_governance"


# ---------------------------------------------------------------------------
# PolicyPriority — five levels (IntEnum so sorting works naturally)
# Lower integer → higher institutional priority
# ---------------------------------------------------------------------------
class PolicyPriority(IntEnum):
    CRITICAL      = 0
    HIGH          = 1
    MEDIUM        = 2
    LOW           = 3
    INFORMATIONAL = 4


# ---------------------------------------------------------------------------
# PolicyStatus — lifecycle of a registered policy
# ---------------------------------------------------------------------------
class PolicyStatus(str, Enum):
    ACTIVE     = "active"
    INACTIVE   = "inactive"
    DEPRECATED = "deprecated"
    DRAFT      = "draft"


# ---------------------------------------------------------------------------
# PolicyEventType — eight lifecycle events
# ---------------------------------------------------------------------------
class PolicyEventType(str, Enum):
    POLICY_EVALUATION_STARTED   = "portfolio_policy_evaluation_started"
    POLICY_LOADED               = "portfolio_policy_loaded"
    POLICY_VALIDATED            = "portfolio_policy_validated"
    POLICY_APPROVED             = "portfolio_policy_approved"
    POLICY_REJECTED             = "portfolio_policy_rejected"
    POLICY_BLOCKED              = "portfolio_policy_blocked"
    POLICY_ESCALATED            = "portfolio_policy_escalated"
    POLICY_EVALUATION_COMPLETED = "portfolio_policy_evaluation_completed"


# ---------------------------------------------------------------------------
# PolicyEvaluationStatus — lifecycle of one evaluation run
# ---------------------------------------------------------------------------
class PolicyEvaluationStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# PolicyChainMode — how policies within a chain are evaluated
# ---------------------------------------------------------------------------
class PolicyChainMode(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL   = "parallel"
    COMPOSITE  = "composite"


# ---------------------------------------------------------------------------
# PolicyConflictResolution — strategy used when multiple policies conflict
# ---------------------------------------------------------------------------
class PolicyConflictResolution(str, Enum):
    DENY_OVERRIDES        = "deny_overrides"
    PRIORITY_WINS         = "priority_wins"
    ESCALATION_OVERRIDES  = "escalation_overrides"


# ---------------------------------------------------------------------------
# Action severity map — lower integer → more restrictive
# Used by conflict resolution to find the "most restrictive" action
# ---------------------------------------------------------------------------
ACTION_SEVERITY: Dict[PolicyAction, int] = {
    PolicyAction.BLOCK:                   0,
    PolicyAction.REJECT:                  1,
    PolicyAction.ESCALATE:                2,
    PolicyAction.REQUIRE_MANUAL_REVIEW:   3,
    PolicyAction.DEFER:                   4,
    PolicyAction.APPROVE_WITH_CONDITIONS: 5,
    PolicyAction.APPROVE:                 6,
}

# Severity order list (most → least restrictive)
ACTION_SEVERITY_ORDER: tuple = (
    PolicyAction.BLOCK,
    PolicyAction.REJECT,
    PolicyAction.ESCALATE,
    PolicyAction.REQUIRE_MANUAL_REVIEW,
    PolicyAction.DEFER,
    PolicyAction.APPROVE_WITH_CONDITIONS,
    PolicyAction.APPROVE,
)

# ---------------------------------------------------------------------------
# Action family sets — used in conflict resolution and response properties
# ---------------------------------------------------------------------------
BLOCKING_ACTIONS: FrozenSet[PolicyAction] = frozenset({
    PolicyAction.BLOCK,
    PolicyAction.REJECT,
})

APPROVAL_ACTIONS: FrozenSet[PolicyAction] = frozenset({
    PolicyAction.APPROVE,
    PolicyAction.APPROVE_WITH_CONDITIONS,
})

ESCALATION_ACTIONS: FrozenSet[PolicyAction] = frozenset({
    PolicyAction.ESCALATE,
    PolicyAction.REQUIRE_MANUAL_REVIEW,
})
