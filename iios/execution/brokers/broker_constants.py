"""iios/execution/brokers/broker_constants.py"""
from __future__ import annotations

from enum import Enum


class BrokerStatus(str, Enum):
    ACTIVE       = "active"
    INACTIVE     = "inactive"
    CONNECTING   = "connecting"
    CONNECTED    = "connected"
    DISCONNECTED = "disconnected"
    ERROR        = "error"
    MAINTENANCE  = "maintenance"
    UNKNOWN      = "unknown"


class BrokerEnvironment(str, Enum):
    LIVE    = "live"
    PAPER   = "paper"
    SANDBOX = "sandbox"
    TEST    = "test"


class AuthMethod(str, Enum):
    API_KEY       = "api_key"
    OAUTH         = "oauth"
    JWT           = "jwt"
    SESSION_TOKEN = "session_token"
    TOTP          = "totp"
    NONE          = "none"


class ConnectionStatus(str, Enum):
    CONNECTED    = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING   = "connecting"
    RECONNECTING = "reconnecting"
    FAILED       = "failed"
    TIMEOUT      = "timeout"
    UNKNOWN      = "unknown"


class BrokerCapabilityType(str, Enum):
    CASH_EQUITY       = "cash_equity"
    DERIVATIVES       = "derivatives"
    FUTURES           = "futures"
    OPTIONS           = "options"
    CURRENCY          = "currency"
    COMMODITY         = "commodity"
    CRYPTO            = "crypto"
    MARGIN            = "margin"
    BRACKET_ORDER     = "bracket_order"
    COVER_ORDER       = "cover_order"
    GTT               = "gtt"
    MARKET_ORDER      = "market_order"
    LIMIT_ORDER       = "limit_order"
    STOP_ORDER        = "stop_order"
    STOP_LIMIT_ORDER  = "stop_limit_order"
    ICEBERG_ORDER     = "iceberg_order"
    STREAMING         = "streaming"
    HISTORICAL_DATA   = "historical_data"
    PAPER_TRADING     = "paper_trading"
    MULTI_ACCOUNT     = "multi_account"
    BASKET_ORDER      = "basket_order"
    AMO               = "amo"          # After-Market Order
    CO                = "co"           # Cover Order


class RetryPolicy(str, Enum):
    NONE        = "none"
    LINEAR      = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI   = "fibonacci"


class BrokerRegion(str, Enum):
    IN   = "india"
    US   = "united_states"
    EU   = "europe"
    ASIA = "asia"
    GLOB = "global"
    UNKNOWN = "unknown"


# ── Engine metadata ───────────────────────────────────────────────────────────

BROKER_FRAMEWORK_VERSION   = "1.0.0"
BROKER_FRAMEWORK_SYSTEM_ID = "iios:execution:brokers:framework"

# ── Timeouts & limits ─────────────────────────────────────────────────────────

DEFAULT_CONNECT_TIMEOUT_SEC     = 30.0
DEFAULT_REQUEST_TIMEOUT_SEC     = 10.0
DEFAULT_HEARTBEAT_INTERVAL_SEC  = 30.0
DEFAULT_MAX_RETRIES             = 3
DEFAULT_RETRY_DELAY_SEC         = 1.0
DEFAULT_RETRY_BACKOFF_FACTOR    = 2.0
DEFAULT_MAX_CONNECTIONS         = 100
DEFAULT_MAX_BROKERS             = 500
DEFAULT_SESSION_TTL_SEC         = 86_400.0   # 24 hours
DEFAULT_TOKEN_TTL_SEC           = 3_600.0    # 1 hour
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
CIRCUIT_BREAKER_RECOVERY_SEC    = 60.0
