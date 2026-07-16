"""iios/execution/positions/risk/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS
Position Risk State — execution-time risk tracking per position.

C6 Execution Intelligence — Phase 3, Module 4
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

RISK_SYSTEM_ID      = "iios:execution:positions:risk"
MANAGER_SYSTEM_ID   = "iios:execution:positions:risk:manager"
REGISTRY_SYSTEM_ID  = "iios:execution:positions:risk:registry"
MONITOR_SYSTEM_ID   = "iios:execution:positions:risk:monitor"
FACTORY_SYSTEM_ID   = "iios:execution:positions:risk:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:positions:risk:validator"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_POSITIONS  = 10_000
DEFAULT_MAX_HISTORY    = 500
DEFAULT_SNAPSHOT_LIMIT = 200

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_RISK     = "iios:execution:positions:risk"
ACTOR_MANAGER  = "iios:execution:positions:risk:manager"
ACTOR_MONITOR  = "iios:execution:positions:risk:monitor"
ACTOR_SYSTEM   = "iios:system"

# ── Default thresholds (decimal fractions) ────────────────────────────────────

DEFAULT_WATCH_DRAWDOWN_PCT       = Decimal("0.25")
DEFAULT_WARNING_DRAWDOWN_PCT     = Decimal("0.50")
DEFAULT_CRITICAL_DRAWDOWN_PCT    = Decimal("0.75")
DEFAULT_LIQUIDATION_DRAWDOWN_PCT = Decimal("0.90")

DEFAULT_WATCH_MARGIN_PCT         = Decimal("0.70")
DEFAULT_WARNING_MARGIN_PCT       = Decimal("0.85")
DEFAULT_CRITICAL_MARGIN_PCT      = Decimal("0.95")
DEFAULT_LIQUIDATION_MARGIN_PCT   = Decimal("1.00")

# Default max loss (absolute, in currency units)
DEFAULT_MAX_LOSS = Decimal("10000")

# Default max exposure (position market value cap)
DEFAULT_MAX_EXPOSURE = Decimal("0")   # 0 = no limit


# ── Risk level ────────────────────────────────────────────────────────────────

class RiskLevel(str, Enum):
    """
    Execution-time risk level for a single position.

    NORMAL              — all metrics within acceptable limits
    WATCH               — approaching a threshold, monitoring intensified
    WARNING             — threshold crossed, action recommended
    CRITICAL            — critical threshold breached, action required
    LIQUIDATION_PENDING — liquidation has been triggered, awaiting execution
    LIQUIDATED          — position has been liquidated
    RECOVERING          — risk metrics improving after a critical event
    RECOVERED           — fully recovered to acceptable levels
    """
    NORMAL              = "NORMAL"
    WATCH               = "WATCH"
    WARNING             = "WARNING"
    CRITICAL            = "CRITICAL"
    LIQUIDATION_PENDING = "LIQUIDATION_PENDING"
    LIQUIDATED          = "LIQUIDATED"
    RECOVERING          = "RECOVERING"
    RECOVERED           = "RECOVERED"


# ── Active / terminal risk levels ─────────────────────────────────────────────

ACTIVE_RISK_LEVELS = frozenset({
    RiskLevel.NORMAL,
    RiskLevel.WATCH,
    RiskLevel.WARNING,
    RiskLevel.CRITICAL,
    RiskLevel.RECOVERING,
    RiskLevel.RECOVERED,
})

ELEVATED_RISK_LEVELS = frozenset({
    RiskLevel.WARNING,
    RiskLevel.CRITICAL,
    RiskLevel.LIQUIDATION_PENDING,
})

TERMINAL_RISK_LEVELS = frozenset({
    RiskLevel.LIQUIDATED,
})


# ── Risk event types ──────────────────────────────────────────────────────────

class RiskEventType(str, Enum):
    """Domain events emitted by the Position Risk module."""
    RISK_EVALUATED         = "RISK_EVALUATED"
    RISK_UPDATED           = "RISK_UPDATED"
    RISK_WARNING           = "RISK_WARNING"
    RISK_CRITICAL          = "RISK_CRITICAL"
    STOP_LOSS_TRIGGERED    = "STOP_LOSS_TRIGGERED"
    TAKE_PROFIT_TRIGGERED  = "TAKE_PROFIT_TRIGGERED"
    LIQUIDATION_WARNING    = "LIQUIDATION_WARNING"
    RISK_RECOVERED         = "RISK_RECOVERED"


# ── Risk operation types ──────────────────────────────────────────────────────

class RiskOperationType(str, Enum):
    """Types of operations performed by the risk manager."""
    REGISTER   = "REGISTER"
    UPDATE     = "UPDATE"
    EVALUATE   = "EVALUATE"
    UNREGISTER = "UNREGISTER"
    SNAPSHOT   = "SNAPSHOT"
    VALIDATE   = "VALIDATE"
