"""
constants.py — iios.supervisor.policies
-----------------------------------------
Shared enumerations, constants, and lookup tables for the
AI Governance Policy Framework.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum, IntEnum
from typing import Dict, FrozenSet, Set

# ---------------------------------------------------------------------------
# System identifiers
# ---------------------------------------------------------------------------

AI_GOVERNANCE_SYSTEM_ID:   str = "iios:supervisor:governance"
EVALUATOR_SYSTEM_ID:       str = "iios:supervisor:governance:evaluator"
REGISTRY_SYSTEM_ID:        str = "iios:supervisor:governance:registry"
FACTORY_SYSTEM_ID:         str = "iios:supervisor:governance:factory"
CHAIN_SYSTEM_ID:           str = "iios:supervisor:governance:chain"
AUDIT_SYSTEM_ID:           str = "iios:supervisor:governance:audit"
MANAGER_SYSTEM_ID:         str = "iios:supervisor:governance:manager"

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

VERSION:        str = "1.0.0"
SCHEMA_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Actor labels
# ---------------------------------------------------------------------------

ACTOR_GOVERNANCE_ENGINE: str = "governance_engine"
ACTOR_EVALUATOR:         str = "evaluator"
ACTOR_REGISTRY:          str = "registry"
ACTOR_SYSTEM:            str = "system"
ACTOR_OPERATOR:          str = "operator"
ACTOR_ENTERPRISE:        str = "enterprise"

# ---------------------------------------------------------------------------
# Capacity defaults
# ---------------------------------------------------------------------------

DEFAULT_MAX_POLICIES:         int   = 10_000
DEFAULT_MAX_HISTORY:          int   = 1_000
DEFAULT_EVALUATION_TIMEOUT_S: float = 30.0
DEFAULT_MAX_CHAIN_DEPTH:      int   = 20

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AIGovernancePolicyType(str, Enum):
    """Supported AI governance policy domains."""
    AI_SAFETY              = "ai_safety"
    AUTONOMOUS_OPERATION   = "autonomous_operation"
    DECISION_APPROVAL      = "decision_approval"
    RISK_ESCALATION        = "risk_escalation"
    HUMAN_OVERSIGHT        = "human_oversight"
    EXPLAINABILITY         = "explainability"
    MODEL_USAGE            = "model_usage"
    AGENT_COORDINATION     = "agent_coordination"
    DATA_GOVERNANCE        = "data_governance"
    PRIVACY                = "privacy"
    SECURITY               = "security"
    COMPLIANCE             = "compliance"
    RESOURCE_USAGE         = "resource_usage"
    AUDIT                  = "audit"
    ENTERPRISE_GOVERNANCE  = "enterprise_governance"


class AIGovernancePolicyAction(str, Enum):
    """Actions that governance policies can prescribe."""
    APPROVE                = "approve"
    APPROVE_WITH_CONDITIONS = "approve_with_conditions"
    REJECT                 = "reject"
    BLOCK                  = "block"
    ESCALATE               = "escalate"
    REQUIRE_HUMAN_APPROVAL = "require_human_approval"
    REQUIRE_MANUAL_REVIEW  = "require_manual_review"
    EMERGENCY_STOP         = "emergency_stop"


class PolicyPriority(IntEnum):
    """Policy priority — lower integer = higher priority."""
    CRITICAL      = 1
    HIGH          = 2
    MEDIUM        = 3
    LOW           = 4
    INFORMATIONAL = 5


class EvaluationMode(str, Enum):
    """Policy chain evaluation strategy."""
    SEQUENTIAL  = "sequential"
    PARALLEL    = "parallel"
    COMPOSITE   = "composite"
    NESTED      = "nested"
    CONDITIONAL = "conditional"
    WEIGHTED    = "weighted"


class LogicalOperator(str, Enum):
    """How rule conditions are combined."""
    ALL = "all"  # AND
    ANY = "any"  # OR


class ConditionOperator(str, Enum):
    """Operators for policy condition evaluation."""
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


class ConflictResolutionStrategy(str, Enum):
    """Strategy for resolving contradictory policy outcomes."""
    CRITICAL_OVERRIDES_ALL              = "critical_overrides_all"
    EMERGENCY_STOP_OVERRIDES_ALL        = "emergency_stop_overrides_all"
    HUMAN_APPROVAL_OVERRIDES_AUTOMATION = "human_approval_overrides_automation"
    EXPLICIT_REJECT_OVERRIDES_APPROVAL  = "explicit_reject_overrides_approval"
    BLOCK_OVERRIDES_APPROVAL            = "block_overrides_approval"
    ESCALATION_OVERRIDES_CONDITIONAL    = "escalation_overrides_conditional"


class AIGovernancePolicyEventType(str, Enum):
    """Events emitted by the governance policy framework."""
    EVALUATION_STARTED         = "governance_evaluation_started"
    POLICY_LOADED              = "governance_policy_loaded"
    POLICY_VALIDATED           = "governance_policy_validated"
    APPROVED                   = "governance_approved"
    REJECTED                   = "governance_rejected"
    BLOCKED                    = "governance_blocked"
    HUMAN_APPROVAL_REQUESTED   = "governance_human_approval_requested"
    EMERGENCY_STOP_TRIGGERED   = "governance_emergency_stop_triggered"
    EVALUATION_COMPLETED       = "governance_evaluation_completed"
    POLICY_ENGINE_STARTED      = "governance_engine_started"
    POLICY_ENGINE_STOPPED      = "governance_engine_stopped"


class AIGovernanceValidationCode(str, Enum):
    """Validation check identifiers."""
    REQUEST_COMPLETENESS          = "request_completeness"
    CONTEXT_CONSISTENCY           = "context_consistency"
    POLICY_INTEGRITY              = "policy_integrity"
    RULE_INTEGRITY                = "rule_integrity"
    CONDITION_INTEGRITY           = "condition_integrity"
    CONFLICT_RESOLUTION_INTEGRITY = "conflict_resolution_integrity"
    AUDIT_COMPLETENESS            = "audit_completeness"
    EVALUATION_COMPLETENESS       = "evaluation_completeness"


# ---------------------------------------------------------------------------
# Action severity — higher = more restrictive
# ---------------------------------------------------------------------------

ACTION_SEVERITY: Dict[AIGovernancePolicyAction, int] = {
    AIGovernancePolicyAction.APPROVE:                 0,
    AIGovernancePolicyAction.APPROVE_WITH_CONDITIONS: 1,
    AIGovernancePolicyAction.REQUIRE_MANUAL_REVIEW:   2,
    AIGovernancePolicyAction.ESCALATE:                3,
    AIGovernancePolicyAction.REQUIRE_HUMAN_APPROVAL:  4,
    AIGovernancePolicyAction.REJECT:                  5,
    AIGovernancePolicyAction.BLOCK:                   6,
    AIGovernancePolicyAction.EMERGENCY_STOP:          7,
}

# ---------------------------------------------------------------------------
# Action classification sets
# ---------------------------------------------------------------------------

DENY_ACTIONS: FrozenSet[AIGovernancePolicyAction] = frozenset({
    AIGovernancePolicyAction.REJECT,
    AIGovernancePolicyAction.BLOCK,
    AIGovernancePolicyAction.EMERGENCY_STOP,
})

PERMISSIVE_ACTIONS: FrozenSet[AIGovernancePolicyAction] = frozenset({
    AIGovernancePolicyAction.APPROVE,
    AIGovernancePolicyAction.APPROVE_WITH_CONDITIONS,
})

HUMAN_REVIEW_ACTIONS: FrozenSet[AIGovernancePolicyAction] = frozenset({
    AIGovernancePolicyAction.REQUIRE_HUMAN_APPROVAL,
    AIGovernancePolicyAction.REQUIRE_MANUAL_REVIEW,
})

ESCALATION_ACTIONS: FrozenSet[AIGovernancePolicyAction] = frozenset({
    AIGovernancePolicyAction.ESCALATE,
    AIGovernancePolicyAction.REQUIRE_HUMAN_APPROVAL,
})

STOP_ACTIONS: FrozenSet[AIGovernancePolicyAction] = frozenset({
    AIGovernancePolicyAction.EMERGENCY_STOP,
})

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_GOVERNANCE_ACTION: AIGovernancePolicyAction = AIGovernancePolicyAction.APPROVE
