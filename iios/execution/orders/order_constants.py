"""iios/execution/orders/order_constants.py"""
from __future__ import annotations

from enum import Enum


class OrderType(str, Enum):
    MARKET        = "market"
    LIMIT         = "limit"
    STOP          = "stop"
    STOP_LIMIT    = "stop_limit"
    TRAILING_STOP = "trailing_stop"
    ICEBERG       = "iceberg"
    BRACKET       = "bracket"
    COVER         = "cover"
    UNKNOWN       = "unknown"


class OrderSide(str, Enum):
    BUY           = "buy"
    SELL          = "sell"
    BUY_TO_COVER  = "buy_to_cover"
    SELL_SHORT    = "sell_short"


class OrderStatus(str, Enum):
    DRAFT            = "draft"
    CREATED          = "created"
    VALIDATED        = "validated"
    APPROVED         = "approved"
    QUEUED           = "queued"
    SUBMITTED        = "submitted"
    ACKNOWLEDGED     = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED           = "filled"
    MODIFIED         = "modified"
    CANCELLED        = "cancelled"
    EXPIRED          = "expired"
    REJECTED         = "rejected"
    FAILED           = "failed"
    ARCHIVED         = "archived"


class TimeInForce(str, Enum):
    DAY      = "day"
    GTC      = "gtc"       # Good Till Cancelled
    IOC      = "ioc"       # Immediate or Cancel
    FOK      = "fok"       # Fill or Kill
    GTD      = "gtd"       # Good Till Date
    AT_OPEN  = "at_open"
    AT_CLOSE = "at_close"


class OrderPriority(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    NORMAL   = "normal"
    LOW      = "low"
    BULK     = "bulk"


# Numeric priority for heapq (lower number = higher priority)
PRIORITY_WEIGHT: dict[str, int] = {
    "critical": 0,
    "high":     1,
    "normal":   2,
    "low":      3,
    "bulk":     4,
}


class OrderMode(str, Enum):
    LIVE       = "live"
    PAPER      = "paper"
    SIMULATION = "simulation"
    BACKTEST   = "backtest"


class OrderAssetClass(str, Enum):
    EQUITY     = "equity"
    DERIVATIVE = "derivative"
    COMMODITY  = "commodity"
    CURRENCY   = "currency"
    DEBT       = "debt"
    ETF        = "etf"
    UNKNOWN    = "unknown"


class FillStatus(str, Enum):
    UNFILLED   = "unfilled"
    PARTIAL    = "partial"
    COMPLETE   = "complete"


class ValidationStatus(str, Enum):
    PENDING  = "pending"
    PASSED   = "passed"
    FAILED   = "failed"
    WARNINGS = "warnings"
    SKIPPED  = "skipped"


class QueueType(str, Enum):
    FIFO        = "fifo"
    PRIORITY    = "priority"
    BATCH       = "batch"
    RETRY       = "retry"
    DELAYED     = "delayed"
    DEAD_LETTER = "dead_letter"


# ── OMS metadata ──────────────────────────────────────────────────────────────

OMS_VERSION   = "1.0.0"
OMS_SYSTEM_ID = "iios:execution:oms"

# ── Capacity ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_ORDERS      = 1_000_000
DEFAULT_MAX_QUEUE_SIZE  = 100_000
DEFAULT_ORDER_TTL_SEC   = 86_400        # 24 hours
DEFAULT_RETRY_LIMIT     = 3
DEFAULT_MAX_HISTORY     = 500           # per order

# ── Validation bounds ─────────────────────────────────────────────────────────

MIN_QUANTITY  = 0.00001
MAX_QUANTITY  = 1_000_000_000.0
MIN_PRICE     = 0.00001
MAX_PRICE     = 1_000_000_000.0

# ── State machine ─────────────────────────────────────────────────────────────

TERMINAL_STATUSES: frozenset[OrderStatus] = frozenset({
    OrderStatus.FILLED,
    OrderStatus.CANCELLED,
    OrderStatus.EXPIRED,
    OrderStatus.REJECTED,
    OrderStatus.FAILED,
    OrderStatus.ARCHIVED,
})

VALID_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.DRAFT:            frozenset({OrderStatus.CREATED,    OrderStatus.CANCELLED}),
    OrderStatus.CREATED:          frozenset({OrderStatus.VALIDATED,  OrderStatus.CANCELLED, OrderStatus.FAILED}),
    OrderStatus.VALIDATED:        frozenset({OrderStatus.APPROVED,   OrderStatus.CANCELLED, OrderStatus.FAILED}),
    OrderStatus.APPROVED:         frozenset({OrderStatus.QUEUED,     OrderStatus.CANCELLED}),
    OrderStatus.QUEUED:           frozenset({OrderStatus.SUBMITTED,  OrderStatus.CANCELLED}),
    OrderStatus.SUBMITTED:        frozenset({OrderStatus.ACKNOWLEDGED, OrderStatus.REJECTED, OrderStatus.FAILED, OrderStatus.CANCELLED}),
    OrderStatus.ACKNOWLEDGED:     frozenset({OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.EXPIRED, OrderStatus.MODIFIED}),
    OrderStatus.PARTIALLY_FILLED: frozenset({OrderStatus.FILLED,    OrderStatus.CANCELLED, OrderStatus.EXPIRED, OrderStatus.MODIFIED}),
    OrderStatus.FILLED:           frozenset({OrderStatus.ARCHIVED}),
    OrderStatus.MODIFIED:         frozenset({OrderStatus.VALIDATED,  OrderStatus.CANCELLED}),
    OrderStatus.CANCELLED:        frozenset({OrderStatus.ARCHIVED}),
    OrderStatus.EXPIRED:          frozenset({OrderStatus.ARCHIVED}),
    OrderStatus.REJECTED:         frozenset({OrderStatus.ARCHIVED}),
    OrderStatus.FAILED:           frozenset({OrderStatus.ARCHIVED,   OrderStatus.QUEUED}),  # retry path
    OrderStatus.ARCHIVED:         frozenset(),
}

# ── Derived sets ─────────────────────────────────────────────────────────────

CANCELLABLE_STATUSES: frozenset[OrderStatus] = frozenset({
    OrderStatus.DRAFT,
    OrderStatus.CREATED,
    OrderStatus.VALIDATED,
    OrderStatus.APPROVED,
    OrderStatus.QUEUED,
    OrderStatus.SUBMITTED,
    OrderStatus.ACKNOWLEDGED,
    OrderStatus.PARTIALLY_FILLED,
    OrderStatus.MODIFIED,
})

ACTIVE_STATUSES: frozenset[OrderStatus] = frozenset({
    OrderStatus.QUEUED,
    OrderStatus.SUBMITTED,
    OrderStatus.ACKNOWLEDGED,
    OrderStatus.PARTIALLY_FILLED,
})

MODIFIABLE_STATUSES: frozenset[OrderStatus] = frozenset({
    OrderStatus.ACKNOWLEDGED,
    OrderStatus.PARTIALLY_FILLED,
})
