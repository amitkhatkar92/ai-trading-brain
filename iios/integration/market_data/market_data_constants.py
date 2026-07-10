"""iios/integration/market_data/market_data_constants.py

All enumerations and module-level constants for the Market Data Provider Framework.
"""
from __future__ import annotations

from enum import Enum


# ── Instrument ────────────────────────────────────────────────────────────────

class InstrumentType(str, Enum):
    EQUITY        = "equity"
    INDEX         = "index"
    FUTURES       = "futures"
    OPTIONS       = "options"
    CURRENCY      = "currency"
    CRYPTO        = "crypto"
    COMMODITY     = "commodity"
    BOND          = "bond"
    ETF           = "etf"
    MUTUAL_FUND   = "mutual_fund"
    WARRANT       = "warrant"
    UNKNOWN       = "unknown"


class Exchange(str, Enum):
    NSE    = "NSE"
    BSE    = "BSE"
    NYSE   = "NYSE"
    NASDAQ = "NASDAQ"
    MCX    = "MCX"
    NCDEX  = "NCDEX"
    CBOE   = "CBOE"
    CME    = "CME"
    LSE    = "LSE"
    SGX    = "SGX"
    GLOBAL = "GLOBAL"
    CRYPTO = "CRYPTO"
    UNKNOWN = "UNKNOWN"


class TradingSession(str, Enum):
    PRE_MARKET   = "pre_market"
    REGULAR      = "regular"
    POST_MARKET  = "post_market"
    EXTENDED     = "extended"
    CLOSED       = "closed"
    HOLIDAY      = "holiday"
    UNKNOWN      = "unknown"


# ── Data types ────────────────────────────────────────────────────────────────

class MarketDataType(str, Enum):
    TICK        = "tick"
    QUOTE       = "quote"
    TRADE       = "trade"
    CANDLE      = "candle"
    ORDER_BOOK  = "order_book"
    SNAPSHOT    = "snapshot"
    STATISTICS  = "statistics"
    EVENT       = "event"


class CandleInterval(str, Enum):
    S1   = "1s"
    S5   = "5s"
    S15  = "15s"
    S30  = "30s"
    M1   = "1m"
    M3   = "3m"
    M5   = "5m"
    M10  = "10m"
    M15  = "15m"
    M30  = "30m"
    H1   = "1h"
    H2   = "2h"
    H4   = "4h"
    D1   = "1d"
    W1   = "1w"
    MN1  = "1mo"


# ── Provider ──────────────────────────────────────────────────────────────────

class MarketDataProviderStatus(str, Enum):
    DISCONNECTED  = "disconnected"
    CONNECTING    = "connecting"
    CONNECTED     = "connected"
    AUTHENTICATED = "authenticated"
    STREAMING     = "streaming"
    DEGRADED      = "degraded"
    RECONNECTING  = "reconnecting"
    FAILED        = "failed"
    SHUTTING_DOWN = "shutting_down"


class SubscriptionStatus(str, Enum):
    PENDING       = "pending"
    ACTIVE        = "active"
    PAUSED        = "paused"
    UNSUBSCRIBED  = "unsubscribed"
    FAILED        = "failed"


# ── Events ────────────────────────────────────────────────────────────────────

class MarketEventType(str, Enum):
    TICK_RECEIVED        = "tick_received"
    QUOTE_UPDATED        = "quote_updated"
    TRADE_EXECUTED       = "trade_executed"
    CANDLE_OPEN          = "candle_open"
    CANDLE_UPDATED       = "candle_updated"
    CANDLE_CLOSED        = "candle_closed"
    ORDER_BOOK_UPDATED   = "order_book_updated"
    SNAPSHOT_TAKEN       = "snapshot_taken"
    STATISTICS_UPDATED   = "statistics_updated"
    SESSION_OPEN         = "session_open"
    SESSION_CLOSE        = "session_close"
    HALT                 = "halt"
    RESUME               = "resume"
    ADJUSTMENT           = "adjustment"
    PROVIDER_CONNECTED   = "provider_connected"
    PROVIDER_DISCONNECTED = "provider_disconnected"
    PROVIDER_ERROR       = "provider_error"
    SUBSCRIPTION_STARTED = "subscription_started"
    SUBSCRIPTION_ENDED   = "subscription_ended"
    GAP_DETECTED         = "gap_detected"
    ANOMALY_DETECTED     = "anomaly_detected"
    ENGINE_STARTED       = "engine_started"
    ENGINE_STOPPED       = "engine_stopped"


# ── Quality ───────────────────────────────────────────────────────────────────

class DataQuality(str, Enum):
    OFFICIAL   = "official"    # Exchange-certified
    DELAYED    = "delayed"     # 15-min delayed
    INDICATIVE = "indicative"  # Best effort
    SYNTHETIC  = "synthetic"   # Derived/calculated
    STALE      = "stale"       # Too old
    INVALID    = "invalid"     # Failed validation
    UNKNOWN    = "unknown"


class AnomalyType(str, Enum):
    PRICE_SPIKE         = "price_spike"
    VOLUME_SPIKE        = "volume_spike"
    ZERO_PRICE          = "zero_price"
    NEGATIVE_PRICE      = "negative_price"
    STALE_TIMESTAMP     = "stale_timestamp"
    FUTURE_TIMESTAMP    = "future_timestamp"
    SPREAD_INVERSION    = "spread_inversion"
    GAP_IN_SERIES       = "gap_in_series"
    DUPLICATE           = "duplicate"
    BAD_OHLC            = "bad_ohlc"


# ── Engine ────────────────────────────────────────────────────────────────────

class MarketDataEngineStatus(str, Enum):
    STOPPED      = "stopped"
    INITIALIZING = "initializing"
    RUNNING      = "running"
    DEGRADED     = "degraded"
    STOPPING     = "stopping"
    ERROR        = "error"


# ── Module metadata ───────────────────────────────────────────────────────────

MARKET_DATA_ENGINE_VERSION   = "1.0.0"
MARKET_DATA_ENGINE_SYSTEM_ID = "iios:integration:market_data:engine"
MARKET_DATA_ERROR_PREFIX     = "MD"

# Limits
DEFAULT_MAX_PROVIDERS            = 100
DEFAULT_MAX_SUBSCRIPTIONS        = 10_000
DEFAULT_STREAM_BUFFER_SIZE       = 10_000   # events per subscription queue
DEFAULT_MAX_ORDER_BOOK_DEPTH     = 20
DEFAULT_MAX_CANDLE_HISTORY       = 5_000    # candles in rolling cache
DEFAULT_MAX_TICK_HISTORY         = 100_000  # ticks in rolling buffer

# Timeouts
DEFAULT_CONNECT_TIMEOUT_SEC      = 30.0
DEFAULT_FETCH_TIMEOUT_SEC        = 15.0
DEFAULT_HEARTBEAT_INTERVAL_SEC   = 30.0
DEFAULT_RECONNECT_BACKOFF_SEC    = 5.0
DEFAULT_MAX_RECONNECT_ATTEMPTS   = 10
DEFAULT_STALE_QUOTE_SEC          = 60.0     # quote older than this = stale

# Quality thresholds
DEFAULT_MAX_PRICE_DEVIATION_PCT  = 10.0     # 10% spike = anomaly
DEFAULT_MAX_VOLUME_DEVIATION_X   = 20.0     # 20× avg volume = spike
DEFAULT_MAX_GAP_SEC              = 300.0    # 5-min gap = detected
DEFAULT_MIN_QUALITY_SCORE        = 0.70
