"""iios/execution/gateway/brokers/constants.py
==================================================
Constants, enumerations, and defaults for the IIOS
Broker Abstraction Layer.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

BROKER_SYSTEM_ID          = "iios:execution:gateway:brokers"
BROKER_MANAGER_SYSTEM_ID  = "iios:execution:gateway:brokers:manager"
BROKER_REGISTRY_SYSTEM_ID = "iios:execution:gateway:brokers:registry"
BROKER_FACTORY_SYSTEM_ID  = "iios:execution:gateway:brokers:factory"
BROKER_VALIDATOR_SYSTEM_ID = "iios:execution:gateway:brokers:validator"
BROKER_HEALTH_SYSTEM_ID   = "iios:execution:gateway:brokers:health"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_BROKERS               = 100
DEFAULT_MAX_HISTORY               = 5_000
DEFAULT_HEARTBEAT_INTERVAL_SECS   = 30.0
DEFAULT_RECONNECT_DELAY_SECS      = 5.0
DEFAULT_MAX_RECONNECT_ATTEMPTS    = 10
DEFAULT_CONNECTION_TIMEOUT_SECS   = 30.0
DEFAULT_AUTH_TIMEOUT_SECS         = 30.0
DEFAULT_REQUEST_TIMEOUT_SECS      = 10.0
DEFAULT_SESSION_TIMEOUT_SECS      = 3_600.0   # 1 hour
DEFAULT_MAX_RETRIES               = 3

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_BROKER_MANAGER = "iios:execution:gateway:brokers:manager"
ACTOR_BROKER_SYSTEM  = "iios:system"


# ── Broker status ─────────────────────────────────────────────────────────────

class BrokerStatus(str, Enum):
    """Operational status of a broker connection."""
    DISCONNECTED   = "DISCONNECTED"
    CONNECTING     = "CONNECTING"
    AUTHENTICATING = "AUTHENTICATING"
    CONNECTED      = "CONNECTED"
    ACTIVE         = "ACTIVE"
    DEGRADED       = "DEGRADED"
    RECONNECTING   = "RECONNECTING"
    FAILED         = "FAILED"
    STOPPED        = "STOPPED"


ACTIVE_BROKER_STATUSES: frozenset[BrokerStatus] = frozenset({
    BrokerStatus.CONNECTING,
    BrokerStatus.AUTHENTICATING,
    BrokerStatus.CONNECTED,
    BrokerStatus.ACTIVE,
    BrokerStatus.DEGRADED,
    BrokerStatus.RECONNECTING,
})

TERMINAL_BROKER_STATUSES: frozenset[BrokerStatus] = frozenset({
    BrokerStatus.FAILED,
    BrokerStatus.STOPPED,
})

READY_BROKER_STATUSES: frozenset[BrokerStatus] = frozenset({
    BrokerStatus.CONNECTED,
    BrokerStatus.ACTIVE,
    BrokerStatus.DEGRADED,
})


# ── Broker capabilities ───────────────────────────────────────────────────────

class BrokerCapability(str, Enum):
    """Tradeable product and feature capabilities a broker may support."""
    CASH_TRADING       = "CASH_TRADING"
    MARGIN_TRADING     = "MARGIN_TRADING"
    MIS                = "MIS"
    CNC                = "CNC"
    NRML               = "NRML"
    INTRADAY           = "INTRADAY"
    DELIVERY           = "DELIVERY"
    OPTIONS            = "OPTIONS"
    FUTURES            = "FUTURES"
    CURRENCY           = "CURRENCY"
    COMMODITY          = "COMMODITY"
    GTT                = "GTT"
    AMO                = "AMO"
    BRACKET_ORDERS     = "BRACKET_ORDERS"
    COVER_ORDERS       = "COVER_ORDERS"
    PARTIAL_FILL       = "PARTIAL_FILL"
    ORDER_MODIFICATION = "ORDER_MODIFICATION"
    ORDER_CANCELLATION = "ORDER_CANCELLATION"
    WEBSOCKET          = "WEBSOCKET"
    MARKET_DATA        = "MARKET_DATA"


# ── Event types ───────────────────────────────────────────────────────────────

class BrokerEventType(str, Enum):
    """Event types emitted by the Broker Abstraction Layer."""
    BROKER_REGISTERED        = "BROKER_REGISTERED"
    BROKER_CONNECTED         = "BROKER_CONNECTED"
    BROKER_DISCONNECTED      = "BROKER_DISCONNECTED"
    AUTHENTICATION_SUCCEEDED = "AUTHENTICATION_SUCCEEDED"
    AUTHENTICATION_FAILED    = "AUTHENTICATION_FAILED"
    SESSION_EXPIRED          = "SESSION_EXPIRED"
    RECONNECT_STARTED        = "RECONNECT_STARTED"
    RECONNECT_SUCCEEDED      = "RECONNECT_SUCCEEDED"
    BROKER_HEALTH_CHANGED    = "BROKER_HEALTH_CHANGED"


# ── Request type ──────────────────────────────────────────────────────────────

class RequestType(str, Enum):
    """Standardized request types submitted through the abstraction layer."""
    ORDER        = "ORDER"
    MODIFY_ORDER = "MODIFY_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    POSITIONS    = "POSITIONS"
    HOLDINGS     = "HOLDINGS"
    FUNDS        = "FUNDS"
    MARGIN       = "MARGIN"
    STATUS       = "STATUS"
    HEALTH       = "HEALTH"
    PING         = "PING"


# ── Response status ───────────────────────────────────────────────────────────

class ResponseStatus(str, Enum):
    """Standardized response outcome statuses from broker operations."""
    SUCCESS         = "SUCCESS"
    FAILURE         = "FAILURE"
    ERROR           = "ERROR"
    RETRYABLE_ERROR = "RETRYABLE_ERROR"
    AUTH_FAILURE    = "AUTH_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"
    RATE_LIMITED    = "RATE_LIMITED"


TERMINAL_RESPONSE_STATUSES: frozenset[ResponseStatus] = frozenset({
    ResponseStatus.SUCCESS,
    ResponseStatus.FAILURE,
    ResponseStatus.AUTH_FAILURE,
})

RETRYABLE_RESPONSE_STATUSES: frozenset[ResponseStatus] = frozenset({
    ResponseStatus.RETRYABLE_ERROR,
    ResponseStatus.NETWORK_FAILURE,
    ResponseStatus.RATE_LIMITED,
})


# ── Order enums ───────────────────────────────────────────────────────────────

class OrderSide(str, Enum):
    """Direction of an order."""
    BUY  = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Execution type of an order."""
    MARKET = "MARKET"
    LIMIT  = "LIMIT"
    SL     = "SL"
    SL_M   = "SL_M"


class ProductType(str, Enum):
    """SEBI-defined product codes."""
    MIS  = "MIS"
    CNC  = "CNC"
    NRML = "NRML"


class AssetClass(str, Enum):
    """Broad asset classification."""
    EQUITY    = "EQUITY"
    OPTIONS   = "OPTIONS"
    FUTURES   = "FUTURES"
    CURRENCY  = "CURRENCY"
    COMMODITY = "COMMODITY"
