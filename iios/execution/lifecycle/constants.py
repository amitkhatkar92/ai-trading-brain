"""iios/execution/lifecycle/constants.py
==================================================
Enumerations and numeric constants for the Order
Lifecycle module.

These are the only definitions of OrderSide, OrderType,
and TimeInForce within iios.execution.lifecycle.
No other module in this package redefines them.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum

# ── System identifiers ─────────────────────────────────────────────────────────
LIFECYCLE_SYSTEM_ID = "iios:execution:lifecycle"
REGISTRY_SYSTEM_ID  = "iios:execution:lifecycle:registry"
FACTORY_SYSTEM_ID   = "iios:execution:lifecycle:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:lifecycle:validator"
VERSION             = "1.0.0"

# ── Registry capacity ──────────────────────────────────────────────────────────
DEFAULT_MAX_ORDERS       = 100_000
DEFAULT_MAX_HISTORY      = 1_000   # max retained history entries per order

# ── Quantity / price guard rails ───────────────────────────────────────────────
MIN_QUANTITY = Decimal("0.000001")
MAX_QUANTITY = Decimal("100_000_000")
MIN_PRICE    = Decimal("0.000001")
MAX_PRICE    = Decimal("1_000_000_000")

# ── Actor labels used in OrderTransition.actor ────────────────────────────────
ACTOR_SYSTEM    = "system"
ACTOR_VALIDATOR = "validator"
ACTOR_BROKER    = "broker"
ACTOR_EXCHANGE  = "exchange"
ACTOR_RISK      = "risk_engine"
ACTOR_SCHEDULER = "scheduler"
ACTOR_USER      = "user"


class OrderSide(str, Enum):
    """Direction of the order."""
    BUY          = "BUY"
    SELL         = "SELL"
    BUY_TO_COVER = "BUY_TO_COVER"
    SELL_SHORT   = "SELL_SHORT"


class OrderType(str, Enum):
    """Execution price type."""
    MARKET     = "MARKET"
    LIMIT      = "LIMIT"
    STOP       = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(str, Enum):
    """Duration for which the order remains active."""
    DAY = "DAY"   # active until end of trading day
    GTC = "GTC"   # good till cancelled
    IOC = "IOC"   # immediate or cancel
    FOK = "FOK"   # fill or kill
    GTD = "GTD"   # good till date (requires expires_at)
    ATO = "ATO"   # at the open
    ATC = "ATC"   # at the close
