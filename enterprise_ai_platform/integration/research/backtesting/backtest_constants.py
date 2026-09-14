"""backtest_constants.py — Enumerations and scalar constants for the Strategy Backtesting Framework."""
from __future__ import annotations
from enum import Enum


# ── Status enumerations ───────────────────────────────────────────────────────

class BacktestStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    PAUSED    = "paused"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    ARCHIVED  = "archived"


class SimulationStatus(str, Enum):
    IDLE         = "idle"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    PAUSED       = "paused"
    COMPLETED    = "completed"
    FAILED       = "failed"
    ABORTED      = "aborted"


class BacktestEngineStatus(str, Enum):
    STOPPED      = "stopped"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    STOPPING     = "stopping"
    ERROR        = "error"


# ── Order / execution enumerations ────────────────────────────────────────────

class OrderDirection(str, Enum):
    LONG       = "long"
    SHORT      = "short"
    EXIT_LONG  = "exit_long"
    EXIT_SHORT = "exit_short"
    HOLD       = "hold"


class OrderType(str, Enum):
    MARKET     = "market"
    LIMIT      = "limit"
    STOP       = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING   = "pending"
    FILLED    = "filled"
    PARTIAL   = "partial"
    CANCELLED = "cancelled"
    REJECTED  = "rejected"
    EXPIRED   = "expired"


class PositionSide(str, Enum):
    LONG  = "long"
    SHORT = "short"


class ExecutionModel(str, Enum):
    """Determines the fill price model used during simulation."""
    NEXT_OPEN  = "next_open"   # fill at next bar's open (most realistic for EOD)
    CLOSE      = "close"       # fill at current bar's close
    VWAP       = "vwap"        # estimated VWAP = (O+H+L+C)/4
    WORST_CASE = "worst_case"  # worst of high/low


# ── Validation enumerations ───────────────────────────────────────────────────

class ValidationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED  = "passed"
    FAILED  = "failed"
    SKIPPED = "skipped"


# ── Reporting enumerations ────────────────────────────────────────────────────

class ReportFormat(str, Enum):
    DICT = "dict"
    JSON = "json"


# ── Event type enumeration ────────────────────────────────────────────────────

class BacktestEventType(str, Enum):
    BACKTEST_CREATED     = "backtest_created"
    BACKTEST_STARTED     = "backtest_started"
    BACKTEST_COMPLETED   = "backtest_completed"
    BACKTEST_FAILED      = "backtest_failed"
    BACKTEST_CANCELLED   = "backtest_cancelled"
    BACKTEST_ARCHIVED    = "backtest_archived"
    ORDER_SUBMITTED      = "order_submitted"
    ORDER_FILLED         = "order_filled"
    ORDER_REJECTED       = "order_rejected"
    TRADE_OPENED         = "trade_opened"
    TRADE_CLOSED         = "trade_closed"
    VALIDATION_STARTED   = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    REPORT_GENERATED     = "report_generated"


# ── Scalar constants ──────────────────────────────────────────────────────────

BACKTESTING_ENGINE_VERSION = "1.0.0"
BACKTEST_ERROR_PREFIX      = "BT"
DEFAULT_MAX_BACKTESTS      = 10_000
DEFAULT_MAX_CONCURRENT     = 8
DEFAULT_INITIAL_CAPITAL    = 100_000.0
DEFAULT_COMMISSION_PCT     = 0.001        # 0.10 %
DEFAULT_COMMISSION_FIXED   = 0.0
DEFAULT_SLIPPAGE_PCT       = 0.0005       # 0.05 %
DEFAULT_RISK_FREE_RATE     = 0.06         # 6 % annualised (Indian market default)
TRADING_DAYS_PER_YEAR      = 252
DEFAULT_MIN_BARS_REQUIRED  = 30
DEFAULT_WALK_FORWARD_FOLDS = 5
DEFAULT_OOS_SPLIT_RATIO    = 0.3          # 30 % held out for OOS
DEFAULT_BACKTEST_VERSION   = "1.0.0"
