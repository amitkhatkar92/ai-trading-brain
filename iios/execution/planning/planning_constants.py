"""iios/execution/planning/planning_constants.py"""
from __future__ import annotations

from enum import Enum


class ExecutionPlanStatus(str, Enum):
    DRAFT      = "draft"
    PENDING    = "pending"
    VALIDATED  = "validated"
    OPTIMIZED  = "optimized"
    APPROVED   = "approved"
    ACTIVE     = "active"
    PAUSED     = "paused"
    COMPLETED  = "completed"
    CANCELLED  = "cancelled"
    FAILED     = "failed"
    ARCHIVED   = "archived"


class RoutingStrategy(str, Enum):
    SINGLE_VENUE   = "single_venue"
    MULTI_VENUE    = "multi_venue"
    PRIORITY       = "priority"
    LIQUIDITY      = "liquidity_based"
    COST_BASED     = "cost_based"
    LATENCY_AWARE  = "latency_aware"
    RULE_BASED     = "rule_based"
    AI_ROUTING     = "ai_routing"
    CUSTOM         = "custom"


class ExecutionMode(str, Enum):
    IMMEDIATE    = "immediate"
    SCHEDULED    = "scheduled"
    CONDITIONAL  = "conditional"
    ADAPTIVE     = "adaptive"
    MANUAL       = "manual"


class ExecutionAlgorithm(str, Enum):
    DIRECT         = "direct"
    TWAP_READY     = "twap_ready"
    VWAP_READY     = "vwap_ready"
    ICEBERG_READY  = "iceberg_ready"
    POV_READY      = "pov_ready"
    ADAPTIVE_READY = "adaptive_ready"
    CUSTOM         = "custom"


class OrderSplitType(str, Enum):
    NO_SPLIT    = "no_split"
    EQUAL       = "equal"
    TIME_BASED  = "time_based"
    VOLUME_BASED = "volume_based"
    ADAPTIVE    = "adaptive"
    CUSTOM      = "custom"


class PolicyType(str, Enum):
    IMMEDIATE           = "immediate"
    SCHEDULED           = "scheduled"
    CONDITIONAL         = "conditional"
    RISK_LIMITED        = "risk_limited"
    CAPITAL_LIMITED     = "capital_limited"
    COMPLIANCE_LIMITED  = "compliance_limited"
    CUSTOM              = "custom"


class LiquidityLevel(str, Enum):
    HIGH      = "high"
    MEDIUM    = "medium"
    LOW       = "low"
    VERY_LOW  = "very_low"
    UNKNOWN   = "unknown"


class ExecutionPriority(str, Enum):
    CRITICAL  = "critical"   # 10
    HIGH      = "high"       # 8-9
    NORMAL    = "normal"     # 5-7
    LOW       = "low"        # 2-4
    BULK      = "bulk"       # 1


class PlanningDecision(str, Enum):
    APPROVED   = "approved"
    DEFERRED   = "deferred"
    REJECTED   = "rejected"
    PENDING    = "pending"


# ── Engine metadata ───────────────────────────────────────────────────────────

PLANNING_ENGINE_VERSION   = "1.0.0"
PLANNING_ENGINE_SYSTEM_ID = "iios:execution:planning:engine"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_PLANS          = 100_000
DEFAULT_MAX_HISTORY        = 10_000
DEFAULT_PLAN_TTL_SEC       = 86_400.0   # 24 hours
DEFAULT_MAX_SPLIT_LEGS     = 20
DEFAULT_MAX_VENUES         = 10
DEFAULT_PRIORITY           = 5

# ── Cost / slippage defaults ──────────────────────────────────────────────────

DEFAULT_COMMISSION_RATE    = 0.0003     # 3 bps
DEFAULT_SLIPPAGE_RATE      = 0.0005     # 5 bps
DEFAULT_IMPACT_RATE        = 0.0010     # 10 bps
DEFAULT_OPPORTUNITY_RATE   = 0.0002     # 2 bps

# ── Constraint defaults ───────────────────────────────────────────────────────

DEFAULT_MAX_SLIPPAGE_PCT       = 0.005    # 0.5%
DEFAULT_MAX_IMPACT_PCT         = 0.010    # 1.0%
DEFAULT_MIN_FILL_PROBABILITY   = 0.80
DEFAULT_MAX_EXECUTION_SEC      = 3_600.0

# ── Liquidity ADV thresholds ──────────────────────────────────────────────────

LIQUIDITY_HIGH_THRESHOLD       = 0.01    # < 1% of ADV
LIQUIDITY_MEDIUM_THRESHOLD     = 0.05    # < 5% of ADV
LIQUIDITY_LOW_THRESHOLD        = 0.20    # < 20% of ADV

# ── Terminal plan statuses ────────────────────────────────────────────────────

TERMINAL_PLAN_STATUSES: frozenset[ExecutionPlanStatus] = frozenset({
    ExecutionPlanStatus.COMPLETED,
    ExecutionPlanStatus.CANCELLED,
    ExecutionPlanStatus.FAILED,
    ExecutionPlanStatus.ARCHIVED,
})
