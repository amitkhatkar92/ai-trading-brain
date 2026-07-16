"""iios/execution/brokers/constants.py
==================================================
Constants, enumerations, and bounds for the
IIOS Broker Abstraction Layer.

C6 Execution Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

BROKER_SYSTEM_ID    = "iios:execution:brokers"
MANAGER_SYSTEM_ID   = "iios:execution:brokers:manager"
REGISTRY_SYSTEM_ID  = "iios:execution:brokers:registry"
FACTORY_SYSTEM_ID   = "iios:execution:brokers:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:brokers:validator"
HEALTH_SYSTEM_ID    = "iios:execution:brokers:health"

VERSION = "1.0.0"

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_BROKER    = "iios:execution:brokers"
ACTOR_MANAGER   = "iios:execution:brokers:manager"
ACTOR_REGISTRY  = "iios:execution:brokers:registry"
ACTOR_FACTORY   = "iios:execution:brokers:factory"
ACTOR_VALIDATOR = "iios:execution:brokers:validator"
ACTOR_USER      = "iios:user"

# ── Capacity defaults ─────────────────────────────────────────────────────────

DEFAULT_MAX_BROKERS          = 500
DEFAULT_MAX_REQUESTS_HISTORY = 10_000
DEFAULT_HEARTBEAT_INTERVAL   = 30.0   # seconds

# ── Timing thresholds (seconds) ───────────────────────────────────────────────

DEFAULT_CONNECT_TIMEOUT  = 30.0
DEFAULT_REQUEST_TIMEOUT  = 10.0
DEFAULT_HEALTH_TIMEOUT   = 5.0
MAX_RESPONSE_TIMEOUT     = 300.0

# ── Enumerations ──────────────────────────────────────────────────────────────


class BrokerMode(str, Enum):
    """Operational mode of the broker connection."""
    LIVE       = "LIVE"
    PAPER      = "PAPER"
    SIMULATION = "SIMULATION"
    BACKTEST   = "BACKTEST"


class BrokerHealthStatus(str, Enum):
    """Overall health of a registered broker."""
    HEALTHY     = "HEALTHY"
    DEGRADED    = "DEGRADED"
    UNHEALTHY   = "UNHEALTHY"
    UNKNOWN     = "UNKNOWN"
    INITIALISING = "INITIALISING"


class BrokerConnectionState(str, Enum):
    """Current connectivity state of a broker."""
    DISCONNECTED  = "DISCONNECTED"
    CONNECTING    = "CONNECTING"
    CONNECTED     = "CONNECTED"
    RECONNECTING  = "RECONNECTING"
    DISCONNECTING = "DISCONNECTING"
    FAILED        = "FAILED"


class BrokerRequestType(str, Enum):
    """Classification of a broker request."""
    CONNECTION  = "CONNECTION"
    ORDER       = "ORDER"
    MODIFY      = "MODIFY"
    CANCEL      = "CANCEL"
    POSITION    = "POSITION"
    BALANCE     = "BALANCE"
    HEARTBEAT   = "HEARTBEAT"
    HEALTH      = "HEALTH"


class BrokerResponseStatus(str, Enum):
    """Outcome of a broker request."""
    SUCCESS     = "SUCCESS"
    FAILURE     = "FAILURE"
    PENDING     = "PENDING"
    REJECTED    = "REJECTED"
    TIMEOUT     = "TIMEOUT"
    UNSUPPORTED = "UNSUPPORTED"


class BrokerCapabilityCode(str, Enum):
    """Standard capability identifiers for a broker."""
    # Order types
    MARKET_ORDER  = "MARKET_ORDER"
    LIMIT_ORDER   = "LIMIT_ORDER"
    STOP_ORDER    = "STOP_ORDER"
    STOP_LIMIT    = "STOP_LIMIT"
    BRACKET_ORDER = "BRACKET_ORDER"
    COVER_ORDER   = "COVER_ORDER"
    # Execution features
    AMO           = "AMO"           # After-Market Order
    GTT           = "GTT"           # Good-Till-Triggered
    ICEBERG       = "ICEBERG"
    BASKET        = "BASKET"
    # Fill behaviour
    PARTIAL_FILL  = "PARTIAL_FILL"
    # Margin
    MARGIN        = "MARGIN"
    INTRADAY      = "INTRADAY"
    # Operational modes
    PAPER_TRADING = "PAPER_TRADING"
    BACKTEST      = "BACKTEST"
    # Market data
    STREAMING     = "STREAMING"
    HISTORICAL    = "HISTORICAL"
    # Multi-account
    MULTI_ACCOUNT = "MULTI_ACCOUNT"


class TimeInForce(str, Enum):
    """Standard time-in-force values."""
    DAY   = "DAY"
    IOC   = "IOC"    # Immediate-or-Cancel
    FOK   = "FOK"    # Fill-or-Kill
    GTC   = "GTC"    # Good-Till-Cancelled
    GTT   = "GTT"    # Good-Till-Triggered
    AT_OPEN  = "AT_OPEN"
    AT_CLOSE = "AT_CLOSE"


class Exchange(str, Enum):
    """Exchanges supported by the abstraction layer."""
    NSE    = "NSE"
    BSE    = "BSE"
    NFO    = "NFO"    # NSE F&O
    BFO    = "BFO"    # BSE F&O
    MCX    = "MCX"
    CDS    = "CDS"    # Currency Derivatives NSE
    NYSE   = "NYSE"
    NASDAQ = "NASDAQ"
    CME    = "CME"
    BINANCE = "BINANCE"
    UNKNOWN = "UNKNOWN"


class ProductType(str, Enum):
    """Product classifications."""
    CNC    = "CNC"    # Cash-and-Carry (delivery)
    MIS    = "MIS"    # Margin Intraday
    NRML   = "NRML"   # Normal (F&O carry-forward)
    CO     = "CO"     # Cover Order
    BO     = "BO"     # Bracket Order
    MTF    = "MTF"    # Margin Trade Funding
    UNKNOWN = "UNKNOWN"


class BrokerValidationCode(str, Enum):
    """Machine-readable codes for validation failures."""
    MISSING_BROKER_ID      = "MISSING_BROKER_ID"
    MISSING_BROKER_NAME    = "MISSING_BROKER_NAME"
    MISSING_REQUEST_ID     = "MISSING_REQUEST_ID"
    MISSING_OPERATION      = "MISSING_OPERATION"
    BROKER_NOT_REGISTERED  = "BROKER_NOT_REGISTERED"
    BROKER_NOT_CONNECTED   = "BROKER_NOT_CONNECTED"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    UNSUPPORTED_EXCHANGE   = "UNSUPPORTED_EXCHANGE"
    UNSUPPORTED_PRODUCT    = "UNSUPPORTED_PRODUCT"
    UNSUPPORTED_ORDER_TYPE = "UNSUPPORTED_ORDER_TYPE"
    INVALID_REQUEST_TYPE   = "INVALID_REQUEST_TYPE"
    REGISTRY_CAPACITY      = "REGISTRY_CAPACITY"
    DUPLICATE_BROKER_ID    = "DUPLICATE_BROKER_ID"
