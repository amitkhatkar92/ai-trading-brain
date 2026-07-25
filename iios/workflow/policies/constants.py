"""
constants.py — iios.workflow.policies
--------------------------------------
Enums, policy types, actions, priorities, and constants for the
Workflow Governance Policy Framework.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List


# ════════════════════════════════════════════════════════════════════════
# Policy Types (14)
# ════════════════════════════════════════════════════════════════════════


class PolicyType(str, Enum):
    """14 governance policy types."""
    WORKFLOW_GOVERNANCE   = "workflow_governance"
    EXECUTION_APPROVAL    = "execution_approval"
    SCHEDULING            = "scheduling"
    RESOURCE_ALLOCATION   = "resource_allocation"
    PRIORITY              = "priority"
    DEPENDENCY            = "dependency"
    SECURITY              = "security"
    COMPLIANCE            = "compliance"
    RISK                  = "risk"
    HUMAN_APPROVAL        = "human_approval"
    SLA                   = "sla"
    AUDIT                 = "audit"
    RETENTION             = "retention"
    ENTERPRISE_WORKFLOW   = "enterprise_workflow"


# ════════════════════════════════════════════════════════════════════════
# Policy Actions (8)
# ════════════════════════════════════════════════════════════════════════


class PolicyAction(str, Enum):
    """8 governance policy actions."""
    APPROVE                    = "approve"
    APPROVE_WITH_CONDITIONS    = "approve_with_conditions"
    REJECT                     = "reject"
    BLOCK                      = "block"
    ESCALATE                   = "escalate"
    REQUIRE_MANUAL_APPROVAL    = "require_manual_approval"
    REQUIRE_EXECUTIVE_APPROVAL = "require_executive_approval"
    EMERGENCY_STOP             = "emergency_stop"


# Action precedence — lower value = higher authority
ACTION_PRECEDENCE: Dict[str, int] = {
    PolicyAction.EMERGENCY_STOP:              0,
    PolicyAction.BLOCK:                        1,
    PolicyAction.REJECT:                       2,
    PolicyAction.REQUIRE_EXECUTIVE_APPROVAL:   3,
    PolicyAction.ESCALATE:                     4,
    PolicyAction.REQUIRE_MANUAL_APPROVAL:      5,
    PolicyAction.APPROVE_WITH_CONDITIONS:      6,
    PolicyAction.APPROVE:                      7,
}


def higher_authority(a: PolicyAction, b: PolicyAction) -> PolicyAction:
    """Return the action with higher governance authority."""
    return a if ACTION_PRECEDENCE[a] <= ACTION_PRECEDENCE[b] else b


# ════════════════════════════════════════════════════════════════════════
# Governance Decision
# ════════════════════════════════════════════════════════════════════════


class GovernanceDecision(str, Enum):
    """Final governance decision after policy chain evaluation."""
    APPROVED                   = "approved"
    APPROVED_WITH_CONDITIONS   = "approved_with_conditions"
    REJECTED                   = "rejected"
    BLOCKED                    = "blocked"
    ESCALATED                  = "escalated"
    REQUIRES_MANUAL_APPROVAL   = "requires_manual_approval"
    REQUIRES_EXECUTIVE_APPROVAL = "requires_executive_approval"
    EMERGENCY_STOPPED          = "emergency_stopped"
    PENDING                    = "pending"


ACTION_TO_DECISION: Dict[str, str] = {
    PolicyAction.APPROVE:                    GovernanceDecision.APPROVED,
    PolicyAction.APPROVE_WITH_CONDITIONS:    GovernanceDecision.APPROVED_WITH_CONDITIONS,
    PolicyAction.REJECT:                     GovernanceDecision.REJECTED,
    PolicyAction.BLOCK:                      GovernanceDecision.BLOCKED,
    PolicyAction.ESCALATE:                   GovernanceDecision.ESCALATED,
    PolicyAction.REQUIRE_MANUAL_APPROVAL:    GovernanceDecision.REQUIRES_MANUAL_APPROVAL,
    PolicyAction.REQUIRE_EXECUTIVE_APPROVAL: GovernanceDecision.REQUIRES_EXECUTIVE_APPROVAL,
    PolicyAction.EMERGENCY_STOP:             GovernanceDecision.EMERGENCY_STOPPED,
}


def action_to_decision(action: PolicyAction) -> GovernanceDecision:
    """Map a PolicyAction to its GovernanceDecision."""
    return GovernanceDecision(ACTION_TO_DECISION.get(action, GovernanceDecision.PENDING))


# ════════════════════════════════════════════════════════════════════════
# Policy Priority (int enum — lower = higher urgency)
# ════════════════════════════════════════════════════════════════════════


class PolicyPriorityLevel(int, Enum):
    """Numeric priority levels for governance policies."""
    CRITICAL      = 0
    HIGH          = 1
    MEDIUM        = 2
    LOW           = 3
    INFORMATIONAL = 4


# ════════════════════════════════════════════════════════════════════════
# Policy Domains (12)
# ════════════════════════════════════════════════════════════════════════


class PolicyDomain(str, Enum):
    """12 governance policy domains."""
    WORKFLOW_GOVERNANCE   = "workflow_governance"
    SCHEDULING_GOVERNANCE = "scheduling_governance"
    EXECUTION_GOVERNANCE  = "execution_governance"
    SECURITY_GOVERNANCE   = "security_governance"
    COMPLIANCE_GOVERNANCE = "compliance_governance"
    RISK_GOVERNANCE       = "risk_governance"
    RESOURCE_GOVERNANCE   = "resource_governance"
    APPROVAL_GOVERNANCE   = "approval_governance"
    DEPENDENCY_GOVERNANCE = "dependency_governance"
    SLA_GOVERNANCE        = "sla_governance"
    AUDIT_GOVERNANCE      = "audit_governance"
    ENTERPRISE_GOVERNANCE = "enterprise_governance"


# ════════════════════════════════════════════════════════════════════════
# Policy Chain Mode
# ════════════════════════════════════════════════════════════════════════


class PolicyChainMode(str, Enum):
    """How policies in a chain are evaluated."""
    SEQUENTIAL  = "sequential"
    PARALLEL    = "parallel"
    COMPOSITE   = "composite"


# ════════════════════════════════════════════════════════════════════════
# Policy Condition Operators
# ════════════════════════════════════════════════════════════════════════


class ConditionOperator(str, Enum):
    """Operators for policy condition evaluation."""
    EQUALS                  = "equals"
    NOT_EQUALS              = "not_equals"
    GREATER_THAN            = "greater_than"
    LESS_THAN               = "less_than"
    GREATER_THAN_OR_EQUAL   = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL      = "less_than_or_equal"
    IN                      = "in"
    NOT_IN                  = "not_in"
    CONTAINS                = "contains"
    NOT_CONTAINS            = "not_contains"
    IS_NULL                 = "is_null"
    IS_NOT_NULL             = "is_not_null"
    STARTS_WITH             = "starts_with"
    ENDS_WITH               = "ends_with"
    MATCHES                 = "matches"   # regex


# ════════════════════════════════════════════════════════════════════════
# Policy Event Types (9)
# ════════════════════════════════════════════════════════════════════════


class PolicyEventType(str, Enum):
    """9 event types emitted by the governance framework."""
    WORKFLOW_POLICY_LOADED          = "workflow_policy_loaded"
    WORKFLOW_POLICY_VALIDATED       = "workflow_policy_validated"
    WORKFLOW_GOVERNANCE_STARTED     = "workflow_governance_started"
    WORKFLOW_APPROVED               = "workflow_approved"
    WORKFLOW_REJECTED               = "workflow_rejected"
    WORKFLOW_BLOCKED                = "workflow_blocked"
    APPROVAL_REQUESTED              = "approval_requested"
    EMERGENCY_STOP_TRIGGERED        = "emergency_stop_triggered"
    WORKFLOW_GOVERNANCE_COMPLETED   = "workflow_governance_completed"


# ════════════════════════════════════════════════════════════════════════
# Module constants
# ════════════════════════════════════════════════════════════════════════

VERSION        = "1.0.0"
BUILD_VERSION  = "c16-m3"
DEFAULT_POLICY_ID      = "default-governance-policy"
DEFAULT_POLICY_CHAIN   = "default-chain"
DEFAULT_MAX_HISTORY    = 50_000
DEFAULT_MAX_POLICIES   = 10_000
DEFAULT_RULE_LIMIT     = 1_000
ACTOR_POLICY_ENGINE    = "policy-engine"
ACTOR_EVALUATOR        = "policy-evaluator"
ACTOR_AUDIT            = "policy-audit"
ACTOR_CHAIN            = "policy-chain"
