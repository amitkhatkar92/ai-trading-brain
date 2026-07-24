"""
constants.py — iios.integration.policies
-----------------------------------------
Enums, type definitions, and constants for the
Integration Governance Policy Framework.

C15 Enterprise Integration & Connectivity — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List


# ════════════════════════════════════════════════════════════════════════
# Policy Types  (20)
# ════════════════════════════════════════════════════════════════════════


class PolicyType(str, Enum):
    """20 enterprise governance policy types."""
    CONNECTOR_GOVERNANCE    = "connector_governance"
    ADAPTER_GOVERNANCE      = "adapter_governance"
    PROTOCOL_GOVERNANCE     = "protocol_governance"
    ENDPOINT_GOVERNANCE     = "endpoint_governance"
    AUTHENTICATION          = "authentication"
    AUTHORIZATION           = "authorization"
    CREDENTIAL_MANAGEMENT   = "credential_management"
    SECRET_MANAGEMENT       = "secret_management"
    CERTIFICATE             = "certificate"
    NETWORK_SECURITY        = "network_security"
    TRANSPORT_SECURITY      = "transport_security"
    ENCRYPTION              = "encryption"
    MESSAGE_ROUTING         = "message_routing"
    RETRY                   = "retry"
    RATE_LIMITING           = "rate_limiting"
    TIMEOUT                 = "timeout"
    FAILOVER                = "failover"
    COMPLIANCE              = "compliance"
    AUDIT                   = "audit"
    ENTERPRISE_INTEGRATION  = "enterprise_integration"


# ════════════════════════════════════════════════════════════════════════
# Policy Actions  (8)
# ════════════════════════════════════════════════════════════════════════


class PolicyAction(str, Enum):
    """8 governance actions a policy may produce."""
    APPROVE                   = "approve"
    APPROVE_WITH_CONDITIONS   = "approve_with_conditions"
    REJECT                    = "reject"
    BLOCK                     = "block"
    ESCALATE                  = "escalate"
    REQUIRE_MANUAL_REVIEW     = "require_manual_review"
    REQUIRE_SECURITY_APPROVAL = "require_security_approval"
    EMERGENCY_STOP            = "emergency_stop"


# ════════════════════════════════════════════════════════════════════════
# Policy Priority  (5)
# ════════════════════════════════════════════════════════════════════════


class PolicyPriority(str, Enum):
    """5 priority levels for governance policies."""
    CRITICAL      = "critical"
    HIGH          = "high"
    MEDIUM        = "medium"
    LOW           = "low"
    INFORMATIONAL = "informational"


# Numeric rank — higher = more authoritative
PRIORITY_RANK: Dict[PolicyPriority, int] = {
    PolicyPriority.CRITICAL:      5,
    PolicyPriority.HIGH:          4,
    PolicyPriority.MEDIUM:        3,
    PolicyPriority.LOW:           2,
    PolicyPriority.INFORMATIONAL: 1,
}


# ════════════════════════════════════════════════════════════════════════
# Policy Domains  (13)
# ════════════════════════════════════════════════════════════════════════


class PolicyDomain(str, Enum):
    """13 governance domains."""
    CONNECTOR_GOVERNANCE = "connector_governance"
    ADAPTER_GOVERNANCE   = "adapter_governance"
    PROTOCOL_GOVERNANCE  = "protocol_governance"
    API_GOVERNANCE       = "api_governance"
    AUTHENTICATION       = "authentication"
    AUTHORIZATION        = "authorization"
    SECURITY             = "security"
    ENCRYPTION           = "encryption"
    MESSAGING            = "messaging"
    NETWORK              = "network"
    COMPLIANCE           = "compliance"
    AUDIT                = "audit"
    ENTERPRISE           = "enterprise"


# ════════════════════════════════════════════════════════════════════════
# Policy Chain Mode  (6)
# ════════════════════════════════════════════════════════════════════════


class PolicyChainMode(str, Enum):
    """6 modes for policy chain evaluation."""
    SEQUENTIAL  = "sequential"
    PARALLEL    = "parallel"
    COMPOSITE   = "composite"
    NESTED      = "nested"
    CONDITIONAL = "conditional"
    PRIORITY    = "priority"


# ════════════════════════════════════════════════════════════════════════
# Conflict Resolution Strategy
# ════════════════════════════════════════════════════════════════════════


class ConflictResolutionStrategy(str, Enum):
    """Strategies for resolving conflicting policy actions."""
    MOST_RESTRICTIVE             = "most_restrictive"
    MOST_PERMISSIVE              = "most_permissive"
    CRITICAL_OVERRIDES_ALL       = "critical_overrides_all"
    EMERGENCY_STOP_OVERRIDES_ALL = "emergency_stop_overrides_all"
    PRIORITY_WINS                = "priority_wins"


# ════════════════════════════════════════════════════════════════════════
# Condition Operators  (10)
# ════════════════════════════════════════════════════════════════════════


class ConditionOperator(str, Enum):
    """10 operators for policy condition evaluation."""
    EQUALS       = "equals"
    NOT_EQUALS   = "not_equals"
    IN           = "in"
    NOT_IN       = "not_in"
    CONTAINS     = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN    = "less_than"
    EXISTS       = "exists"
    NOT_EXISTS   = "not_exists"


# ════════════════════════════════════════════════════════════════════════
# Policy Evaluation Mode  (3)
# ════════════════════════════════════════════════════════════════════════


class PolicyEvaluationMode(str, Enum):
    """How conditions within a rule are combined."""
    ALL_MUST_PASS  = "all_must_pass"    # AND semantics
    ANY_MUST_PASS  = "any_must_pass"    # OR  semantics
    NONE_MUST_PASS = "none_must_pass"   # NOR semantics


# ════════════════════════════════════════════════════════════════════════
# Policy Event Types  (9)
# ════════════════════════════════════════════════════════════════════════


class PolicyEventType(str, Enum):
    """9 governance lifecycle event types."""
    POLICY_LOADED               = "policy_loaded"
    POLICY_VALIDATED            = "policy_validated"
    GOVERNANCE_STARTED          = "governance_started"
    INTEGRATION_APPROVED        = "integration_approved"
    INTEGRATION_REJECTED        = "integration_rejected"
    INTEGRATION_BLOCKED         = "integration_blocked"
    SECURITY_APPROVAL_REQUESTED = "security_approval_requested"
    EMERGENCY_STOP_TRIGGERED    = "emergency_stop_triggered"
    GOVERNANCE_COMPLETED        = "governance_completed"


# ════════════════════════════════════════════════════════════════════════
# Policy Result Status
# ════════════════════════════════════════════════════════════════════════


class PolicyResultStatus(str, Enum):
    """Outcome status derived from a PolicyAction."""
    APPROVED             = "approved"
    APPROVED_CONDITIONAL = "approved_with_conditions"
    REJECTED             = "rejected"
    BLOCKED              = "blocked"
    ESCALATED            = "escalated"
    MANUAL_REVIEW        = "manual_review"
    SECURITY_REVIEW      = "security_review"
    EMERGENCY_STOP       = "emergency_stop"


# ════════════════════════════════════════════════════════════════════════
# Conflict resolution — action precedence
# Higher index in this list = higher override power (more restrictive).
#
# Conflict resolution rules (applied via this list):
#   EMERGENCY_STOP   overrides all
#   BLOCK            overrides approval actions
#   REJECT           overrides approval actions
#   SECURITY_APPROVAL overrides automation
#   ESCALATE         overrides conditional approval
#   APPROVE_WITH_CONDITIONS overrides plain approve
#   APPROVE          is the default (lowest precedence)
# ════════════════════════════════════════════════════════════════════════

ACTION_PRECEDENCE: List[PolicyAction] = [
    PolicyAction.APPROVE,
    PolicyAction.APPROVE_WITH_CONDITIONS,
    PolicyAction.ESCALATE,
    PolicyAction.REQUIRE_MANUAL_REVIEW,
    PolicyAction.REQUIRE_SECURITY_APPROVAL,
    PolicyAction.REJECT,
    PolicyAction.BLOCK,
    PolicyAction.EMERGENCY_STOP,
]

# Maps PolicyAction → PolicyResultStatus
ACTION_TO_STATUS: Dict[PolicyAction, PolicyResultStatus] = {
    PolicyAction.APPROVE:                   PolicyResultStatus.APPROVED,
    PolicyAction.APPROVE_WITH_CONDITIONS:   PolicyResultStatus.APPROVED_CONDITIONAL,
    PolicyAction.REJECT:                    PolicyResultStatus.REJECTED,
    PolicyAction.BLOCK:                     PolicyResultStatus.BLOCKED,
    PolicyAction.ESCALATE:                  PolicyResultStatus.ESCALATED,
    PolicyAction.REQUIRE_MANUAL_REVIEW:     PolicyResultStatus.MANUAL_REVIEW,
    PolicyAction.REQUIRE_SECURITY_APPROVAL: PolicyResultStatus.SECURITY_REVIEW,
    PolicyAction.EMERGENCY_STOP:            PolicyResultStatus.EMERGENCY_STOP,
}

# ════════════════════════════════════════════════════════════════════════
# System identifiers & defaults
# ════════════════════════════════════════════════════════════════════════

POLICY_SYSTEM_ID  = "iios:integration:policies"
MANAGER_SYSTEM_ID = "iios:integration:policy-manager"
VERSION           = "1.0.0"

DEFAULT_ENGINE_ID               = "iios-policy-engine-default"
DEFAULT_MAX_POLICIES            = 500
DEFAULT_MAX_HISTORY             = 2_000
DEFAULT_MAX_AUDIT               = 10_000
DEFAULT_MAX_RULES_PER_POLICY    = 50
DEFAULT_MAX_CONDITIONS_PER_RULE = 20
DEFAULT_PRIORITY                = PolicyPriority.MEDIUM

PIPELINE_STAGES: List[str] = [
    "load_policies",
    "validate_configuration",
    "evaluate_rules",
    "resolve_conflicts",
    "apply_priorities",
    "generate_decision",
    "generate_audit",
]
