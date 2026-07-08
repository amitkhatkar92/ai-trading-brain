"""
iios/decision_policies/policy_constants.py
==========================================
Enumerations and module-level constants for the Decision Policy & Rule Engine.
"""
from __future__ import annotations

from enum import Enum


class RuleStatus(Enum):
    PASS  = "pass"
    FAIL  = "fail"
    WARN  = "warn"
    SKIP  = "skip"
    ERROR = "error"


class RuleType(Enum):
    STATIC      = "static"
    DYNAMIC     = "dynamic"
    CONDITIONAL = "conditional"
    COMPOSITE   = "composite"
    NESTED      = "nested"
    PRIORITY    = "priority"


class GroupOperator(Enum):
    AND      = "and"
    OR       = "or"
    MAJORITY = "majority"


class ConstraintType(Enum):
    HARD      = "hard"
    SOFT      = "soft"
    RISK      = "risk"
    PORTFOLIO = "portfolio"
    CAPITAL   = "capital"
    LIQUIDITY = "liquidity"
    TIME      = "time"
    CUSTOM    = "custom"


class ComplianceCategory(Enum):
    REGULATORY = "regulatory"
    INTERNAL   = "internal"
    MANDATE    = "mandate"
    GOVERNANCE = "governance"
    APPROVAL   = "approval"
    AUDIT      = "audit"


class PolicyVerdict(Enum):
    APPROVE  = "approve"
    REJECT   = "reject"
    ESCALATE = "escalate"
    DEFER    = "defer"
    OVERRIDE = "override"


class EvaluationMode(Enum):
    STRICT  = "strict"   # abort on first hard failure
    LENIENT = "lenient"  # collect all results
    AUDIT   = "audit"    # non-blocking, log-only


class PolicyPriority(Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class ConflictResolution(Enum):
    MOST_RESTRICTIVE  = "most_restrictive"
    LEAST_RESTRICTIVE = "least_restrictive"
    PRIORITY_ORDER    = "priority_order"
    MANUAL            = "manual"


# ── Engine metadata ────────────────────────────────────────────────────────────
POLICY_ENGINE_VERSION   = "1.0.0"
POLICY_ENGINE_SYSTEM_ID = "iios:policy:engine"

# ── Registry limits ────────────────────────────────────────────────────────────
MAX_RULES_PER_GROUP      = 100
MAX_CONSTRAINTS_PER_EVAL = 200
MAX_POLICIES_IN_REGISTRY = 10_000
MAX_EVALUATION_HISTORY   = 50_000

# ── Defaults ───────────────────────────────────────────────────────────────────
DEFAULT_RULE_PRIORITY      = 100
DEFAULT_RULE_TIMEOUT_S     = 5.0
DEFAULT_EVAL_TIMEOUT_S     = 30.0
DEFAULT_MAX_PARALLEL_RULES = 8
DEFAULT_RULE_CACHE_SIZE    = 1_000
