"""iios/execution/oms/order_router/constants.py
==================================================
Constants, enumerations, and bounds for the IIOS Order Router.

C6 Execution Intelligence — Phase 2, Module 3
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

ROUTER_SYSTEM_ID    = "iios:execution:oms:order_router"
REGISTRY_SYSTEM_ID  = "iios:execution:oms:order_router:registry"
FACTORY_SYSTEM_ID   = "iios:execution:oms:order_router:factory"
VALIDATOR_SYSTEM_ID = "iios:execution:oms:order_router:validator"

VERSION = "1.0.0"

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_SYSTEM    = "iios:system"
ACTOR_ROUTER    = "iios:execution:oms:order_router"
ACTOR_POLICY    = "iios:execution:oms:order_router:policy"
ACTOR_VALIDATOR = "iios:execution:oms:order_router:validator"
ACTOR_USER      = "iios:user"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_HISTORY    = 5_000
DEFAULT_MAX_CANDIDATES = 20
DEFAULT_ROUTING_TTL    = 60.0    # seconds before a routing decision expires


# ── Enumerations ──────────────────────────────────────────────────────────────

class RoutingPolicyType(str, Enum):
    """Named routing policy types."""
    DEFAULT      = "DEFAULT"       # System default: first available
    PRIORITY     = "PRIORITY"      # Ranked broker priority list
    CAPABILITY   = "CAPABILITY"    # Route to broker that supports the capability
    EXCHANGE     = "EXCHANGE"      # Route based on target exchange
    PAPER_TRADE  = "PAPER_TRADE"   # Simulated execution, no real broker
    BACKTEST     = "BACKTEST"      # Historical replay mode
    RECOVERY     = "RECOVERY"      # Recovering failed or stuck orders


class RoutingStatus(str, Enum):
    """Lifecycle status of a routing operation."""
    PENDING   = "PENDING"
    EVALUATING = "EVALUATING"
    SELECTED  = "SELECTED"
    REJECTED  = "REJECTED"
    EXPIRED   = "EXPIRED"
    FAILED    = "FAILED"


# Terminal routing statuses
TERMINAL_ROUTING_STATUSES = frozenset({
    RoutingStatus.SELECTED,
    RoutingStatus.REJECTED,
    RoutingStatus.EXPIRED,
    RoutingStatus.FAILED,
})


class ExecutionMode(str, Enum):
    """Mode under which an order will be executed."""
    LIVE       = "LIVE"
    PAPER      = "PAPER"
    BACKTEST   = "BACKTEST"
    SIMULATION = "SIMULATION"
    RECOVERY   = "RECOVERY"


class BrokerCapability(str, Enum):
    """Capabilities a broker may or may not support."""
    EQUITY        = "EQUITY"
    DERIVATIVES   = "DERIVATIVES"
    OPTIONS       = "OPTIONS"
    FUTURES       = "FUTURES"
    CURRENCY      = "CURRENCY"
    COMMODITY     = "COMMODITY"
    MARKET_ORDER  = "MARKET_ORDER"
    LIMIT_ORDER   = "LIMIT_ORDER"
    STOP_ORDER    = "STOP_ORDER"
    STOP_LIMIT    = "STOP_LIMIT"
    MARGIN        = "MARGIN"
    SHORT_SELLING = "SHORT_SELLING"
    BRACKET_ORDER = "BRACKET_ORDER"
    COVER_ORDER   = "COVER_ORDER"
    AMO           = "AMO"          # After Market Order
    INTRADAY      = "INTRADAY"
    DELIVERY      = "DELIVERY"
    MTF           = "MTF"          # Margin Trading Facility


class CandidateScoreField(str, Enum):
    """Fields contributing to a routing candidate score."""
    PRIORITY      = "PRIORITY"
    AVAILABILITY  = "AVAILABILITY"
    CAPABILITY    = "CAPABILITY"
    EXCHANGE_MATCH = "EXCHANGE_MATCH"
    POLICY_MATCH  = "POLICY_MATCH"
    LATENCY       = "LATENCY"


class RoutingEventType(str, Enum):
    """Events emitted by the Order Router."""
    ROUTING_STARTED   = "ROUTING_STARTED"
    CANDIDATE_EVALUATED = "CANDIDATE_EVALUATED"
    ROUTE_SELECTED    = "ROUTE_SELECTED"
    ROUTING_REJECTED  = "ROUTING_REJECTED"
    ROUTING_COMPLETED = "ROUTING_COMPLETED"


class RoutingValidationCode(str, Enum):
    """Machine-readable routing validation failure codes."""
    MISSING_ORDER_ID   = "MISSING_ORDER_ID"
    NO_CANDIDATES      = "NO_CANDIDATES"
    BROKER_UNAVAILABLE = "BROKER_UNAVAILABLE"
    CAPABILITY_MISSING = "CAPABILITY_MISSING"
    EXCHANGE_UNSUPPORTED = "EXCHANGE_UNSUPPORTED"
    PRODUCT_UNSUPPORTED  = "PRODUCT_UNSUPPORTED"
    ORDER_INCOMPATIBLE   = "ORDER_INCOMPATIBLE"
    POLICY_INVALID       = "POLICY_INVALID"
    ROUTER_NOT_RUNNING   = "ROUTER_NOT_RUNNING"
    REQUEST_EXPIRED      = "REQUEST_EXPIRED"
