"""
iios/execution/recovery/policies/constants.py
=============================================
Constants, enumerations, and runtime limits for the Execution Recovery
Policy Framework.

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Tuple

# ── System identifiers ────────────────────────────────────────────────────────

SYSTEM_ID      = "iios:execution:recovery:policies"
ENGINE_ID      = "iios:execution:recovery:policies:engine"
MANAGER_ID     = "iios:execution:recovery:policies:manager"
REGISTRY_ID    = "iios:execution:recovery:policies:registry"
FACTORY_ID     = "iios:execution:recovery:policies:factory"

VERSION        = "1.0.0"
SCHEMA_VERSION = "1.0"

# ── Runtime limits ────────────────────────────────────────────────────────────

DEFAULT_MAX_POLICIES = 256
DEFAULT_MAX_HISTORY  = 2_000
DEFAULT_MAX_EVENTS   = 20_000
DEFAULT_MAX_RULES    = 1_024

# ── Actors ────────────────────────────────────────────────────────────────────

ACTOR_ENGINE    = "policy_engine"
ACTOR_MANAGER   = "policy_manager"
ACTOR_REGISTRY  = "policy_registry"
ACTOR_EVALUATOR = "policy_evaluator"
ACTOR_SYSTEM    = "system"
ACTOR_OPERATOR  = "operator"

# ── Failure categories ────────────────────────────────────────────────────────

class FailureCategory(str, Enum):
    """Execution failure categories for policy selection."""
    EXECUTION_FAILURE     = "execution_failure"
    BROKER_FAILURE        = "broker_failure"
    GATEWAY_FAILURE       = "gateway_failure"
    NETWORK_FAILURE       = "network_failure"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    DATA_INTEGRITY_FAILURE = "data_integrity_failure"
    TIMEOUT               = "timeout"
    RISK_VIOLATION        = "risk_violation"
    UNKNOWN_FAILURE       = "unknown_failure"


# Failure categories treated as transient (retry-eligible)
TRANSIENT_FAILURE_CATEGORIES: FrozenSet[FailureCategory] = frozenset({
    FailureCategory.TIMEOUT,
    FailureCategory.GATEWAY_FAILURE,
    FailureCategory.NETWORK_FAILURE,
})

# Failure categories that require failover consideration
FAILOVER_ELIGIBLE_CATEGORIES: FrozenSet[FailureCategory] = frozenset({
    FailureCategory.BROKER_FAILURE,
    FailureCategory.GATEWAY_FAILURE,
    FailureCategory.INFRASTRUCTURE_FAILURE,
})

# Failure categories that are safety-critical
SAFETY_CRITICAL_CATEGORIES: FrozenSet[FailureCategory] = frozenset({
    FailureCategory.RISK_VIOLATION,
    FailureCategory.DATA_INTEGRITY_FAILURE,
})

# ── Failure severity ──────────────────────────────────────────────────────────

class FailureSeverity(str, Enum):
    UNKNOWN  = "unknown"
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"

# ── Recovery strategy types ───────────────────────────────────────────────────

class RecoveryStrategyType(str, Enum):
    """Recovery strategy types — the engine selects one per decision."""
    RETRY                = "retry"
    RESUME               = "resume"
    ROLLBACK             = "rollback"
    RESTART              = "restart"
    FAILOVER             = "failover"
    MANUAL_INTERVENTION  = "manual_intervention"
    EMERGENCY_SHUTDOWN   = "emergency_shutdown"
    COMPOSITE            = "composite"

# ── Policy priority ───────────────────────────────────────────────────────────

class PolicyPriority(int, Enum):
    """Evaluation priority for policies.  Higher value = evaluated first."""
    LOW       = 1
    NORMAL    = 2
    HIGH      = 3
    CRITICAL  = 4
    EMERGENCY = 5

# ── Recovery recommendation ───────────────────────────────────────────────────

class RecoveryRecommendation(str, Enum):
    RETRY                = "retry"
    RESUME               = "resume"
    ROLLBACK             = "rollback"
    RESTART              = "restart"
    FAILOVER             = "failover"
    MANUAL_INTERVENTION  = "manual_intervention"
    EMERGENCY_SHUTDOWN   = "emergency_shutdown"
    NO_ACTION            = "no_action"
    DEGRADE              = "degrade"

# ── Events ────────────────────────────────────────────────────────────────────

class PolicyEventType(str, Enum):
    POLICY_EVALUATION_STARTED  = "policy_evaluation_started"
    POLICY_EVALUATED           = "policy_evaluated"
    STRATEGY_SELECTED          = "strategy_selected"
    DECISION_PUBLISHED         = "decision_published"
    FALLBACK_POLICY_SELECTED   = "fallback_policy_selected"
    POLICY_EVALUATION_FAILED   = "policy_evaluation_failed"
    ENGINE_STARTED             = "engine_started"
    ENGINE_STOPPED             = "engine_stopped"

# ── Rule condition operators ──────────────────────────────────────────────────

class RuleConditionOperator(str, Enum):
    EQUALS         = "equals"
    NOT_EQUALS     = "not_equals"
    LESS_THAN      = "less_than"
    LESS_EQUALS    = "less_equals"
    GREATER_THAN   = "greater_than"
    GREATER_EQUALS = "greater_equals"
    IN             = "in"
    NOT_IN         = "not_in"
    IS_TRUE        = "is_true"
    IS_FALSE       = "is_false"
    CONTAINS       = "contains"

# ── Confidence thresholds ────────────────────────────────────────────────────

CONFIDENCE_EMERGENCY_SHUTDOWN = 0.95
CONFIDENCE_FAILOVER           = 0.90
CONFIDENCE_ROLLBACK           = 0.85
CONFIDENCE_RETRY              = 0.80
CONFIDENCE_RESTART            = 0.75
CONFIDENCE_RESUME             = 0.70
CONFIDENCE_MANUAL             = 0.50
CONFIDENCE_FALLBACK           = 0.40

# ── Severity → priority map ──────────────────────────────────────────────────

SEVERITY_PRIORITY_MAP = {
    FailureSeverity.UNKNOWN:  PolicyPriority.LOW,
    FailureSeverity.LOW:      PolicyPriority.LOW,
    FailureSeverity.MEDIUM:   PolicyPriority.NORMAL,
    FailureSeverity.HIGH:     PolicyPriority.HIGH,
    FailureSeverity.CRITICAL: PolicyPriority.EMERGENCY,
}
