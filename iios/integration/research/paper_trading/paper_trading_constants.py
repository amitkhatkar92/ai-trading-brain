"""paper_trading_constants.py — Enumerations and scalar constants for the Paper Trading & Market Simulation Framework."""
from __future__ import annotations

from enum import Enum


# ── Status enumerations ───────────────────────────────────────────────────────

class SessionStatus(str, Enum):
    IDLE      = "idle"
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    ARCHIVED  = "archived"


class PaperEngineStatus(str, Enum):
    STOPPED      = "stopped"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    STOPPING     = "stopping"
    ERROR        = "error"


class AccountStatus(str, Enum):
    ACTIVE    = "active"
    SUSPENDED = "suspended"
    CLOSED    = "closed"


# ── Order enumerations ────────────────────────────────────────────────────────

class OrderSide(str, Enum):
    BUY  = "buy"
    SELL = "sell"


class PaperOrderType(str, Enum):
    MARKET        = "market"
    LIMIT         = "limit"
    STOP          = "stop"
    STOP_LIMIT    = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class PaperOrderStatus(str, Enum):
    PENDING          = "pending"
    OPEN             = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED           = "filled"
    CANCELLED        = "cancelled"
    REJECTED         = "rejected"
    EXPIRED          = "expired"


class TimeInForce(str, Enum):
    DAY = "day"   # good for the current session only
    GTC = "gtc"   # good till cancelled
    IOC = "ioc"   # immediate or cancel
    FOK = "fok"   # fill or kill
    GTD = "gtd"   # good till date


# ── Position / Trade enumerations ─────────────────────────────────────────────

class PaperPositionSide(str, Enum):
    LONG  = "long"
    SHORT = "short"


# ── Market / exchange enumerations ────────────────────────────────────────────

class ExchangeStatus(str, Enum):
    CLOSED      = "closed"
    PRE_MARKET  = "pre_market"
    OPEN        = "open"
    POST_MARKET = "post_market"
    HALTED      = "halted"


class MarketPhase(str, Enum):
    PRE_MARKET      = "pre_market"
    OPENING_AUCTION = "opening_auction"
    CONTINUOUS      = "continuous"
    CLOSING_AUCTION = "closing_auction"
    POST_MARKET     = "post_market"
    CLOSED          = "closed"


class PTEventType(str, Enum):
    BAR              = "bar"
    CORPORATE_ACTION = "corporate_action"
    SESSION_START    = "session_start"
    SESSION_END      = "session_end"
    HALT             = "halt"
    RESUME           = "resume"
    ORDER_SUBMITTED  = "order_submitted"
    ORDER_FILLED     = "order_filled"
    ORDER_CANCELLED  = "order_cancelled"
    ORDER_EXPIRED    = "order_expired"
    ORDER_REJECTED   = "order_rejected"
    RISK_BREACH      = "risk_breach"


class FillModel(str, Enum):
    NEXT_OPEN  = "next_open"   # fill at the next bar's open (most realistic for EOD)
    CLOSE      = "close"       # fill at current bar's close
    VWAP       = "vwap"        # estimated VWAP = (O+H+L+C) / 4
    WORST_CASE = "worst_case"  # worst of high (for buys) or low (for sells)


# ── Scalar constants ──────────────────────────────────────────────────────────

PAPER_TRADING_ENGINE_VERSION    = "1.0.0"
PT_ERROR_PREFIX                 = "PT"

DEFAULT_INITIAL_CAPITAL         = 1_000_000.0
DEFAULT_COMMISSION_PCT          = 0.001        # 0.1 %
DEFAULT_SLIPPAGE_PCT            = 0.0005       # 0.05 %
DEFAULT_RISK_FREE_RATE          = 0.06
DEFAULT_MAX_SESSIONS            = 10_000
DEFAULT_MAX_ACCOUNTS            = 1_000
TRADING_DAYS_PER_YEAR           = 252
MAX_POSITION_CONCENTRATION      = 0.20         # 20 % per symbol
MIN_CASH_BUFFER                 = 0.02         # 2 % of equity
DEFAULT_BUYING_POWER_MULTIPLIER = 1.0          # no margin by default
DEFAULT_MAX_DRAWDOWN_LIMIT      = 0.20         # 20 %
DEFAULT_DAILY_LOSS_LIMIT        = 0.05         # 5 %
DEFAULT_FILL_MODEL              = FillModel.NEXT_OPEN
DEFAULT_HISTORY_MAX_ENTRIES     = 100_000
DEFAULT_WALK_FORWARD_FOLDS      = 5
