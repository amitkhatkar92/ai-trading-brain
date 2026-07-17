"""iios/execution/gateway/routing/constants.py
==================================================
Constants, enumerations, and defaults for the IIOS
Routing Framework.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

from enum import Enum

# ── System identifiers ────────────────────────────────────────────────────────

ROUTING_SYSTEM_ID          = "iios:execution:gateway:routing"
ROUTING_ENGINE_SYSTEM_ID   = "iios:execution:gateway:routing:engine"
ROUTING_MANAGER_SYSTEM_ID  = "iios:execution:gateway:routing:manager"
ROUTING_REGISTRY_SYSTEM_ID = "iios:execution:gateway:routing:registry"
ROUTING_SELECTOR_SYSTEM_ID = "iios:execution:gateway:routing:selector"

VERSION = "1.0.0"

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_MAX_CANDIDATES       = 500
DEFAULT_MAX_POLICIES         = 200
DEFAULT_MAX_HISTORY          = 5_000
DEFAULT_MIN_HEALTH_SCORE     = 0.0      # minimum health to be considered available
DEFAULT_ROUTING_TIMEOUT_SECS = 5.0
DEFAULT_MAX_FAILOVER_DEPTH   = 3

# ── Actor labels ──────────────────────────────────────────────────────────────

ACTOR_ROUTING_ENGINE  = "iios:execution:gateway:routing:engine"
ACTOR_ROUTING_MANAGER = "iios:execution:gateway:routing:manager"
ACTOR_ROUTING_SYSTEM  = "iios:system"


# ── Routing policy type ───────────────────────────────────────────────────────

class RoutingPolicyType(str, Enum):
    """Supported policy types for broker selection."""
    DEFAULT_BROKER   = "DEFAULT_BROKER"
    PREFERRED_BROKER = "PREFERRED_BROKER"
    CAPABILITY_BASED = "CAPABILITY_BASED"
    INSTRUMENT_BASED = "INSTRUMENT_BASED"
    MARKET_BASED     = "MARKET_BASED"
    EXCHANGE_BASED   = "EXCHANGE_BASED"
    PRODUCT_BASED    = "PRODUCT_BASED"
    PRIORITY_BASED   = "PRIORITY_BASED"
    HEALTH_BASED     = "HEALTH_BASED"
    FAILOVER_ROUTING = "FAILOVER_ROUTING"
    WEIGHTED_ROUTING = "WEIGHTED_ROUTING"
    CUSTOM_POLICY    = "CUSTOM_POLICY"


# ── Routing strategy type ─────────────────────────────────────────────────────

class RoutingStrategyType(str, Enum):
    """Selection algorithm applied to policy-filtered candidates."""
    SINGLE_DESTINATION  = "SINGLE_DESTINATION"   # first available
    PRIORITY_SELECTION  = "PRIORITY_SELECTION"   # highest routing_priority
    WEIGHTED_SELECTION  = "WEIGHTED_SELECTION"   # random weighted by .weight
    CAPABILITY_MATCHING = "CAPABILITY_MATCHING"  # best capability fit
    HEALTH_OPTIMIZED    = "HEALTH_OPTIMIZED"     # highest health_score
    FALLBACK_STRATEGY   = "FALLBACK_STRATEGY"    # first available with fallback


# ── Routing event type ────────────────────────────────────────────────────────

class RoutingEventType(str, Enum):
    """Event types emitted by the Routing Framework."""
    ROUTING_STARTED    = "ROUTING_STARTED"
    ROUTING_COMPLETED  = "ROUTING_COMPLETED"
    BROKER_SELECTED    = "BROKER_SELECTED"
    BROKER_REJECTED    = "BROKER_REJECTED"
    FAILOVER_ACTIVATED = "FAILOVER_ACTIVATED"
    POLICY_APPLIED     = "POLICY_APPLIED"
    ROUTING_FAILED     = "ROUTING_FAILED"


# ── Routing outcome ───────────────────────────────────────────────────────────

class RoutingOutcome(str, Enum):
    """Outcome of a routing decision."""
    ROUTED           = "ROUTED"
    FAILOVER_ROUTED  = "FAILOVER_ROUTED"
    FAILED           = "FAILED"
    NO_CANDIDATES    = "NO_CANDIDATES"
    POLICY_REJECTED  = "POLICY_REJECTED"
    VALIDATION_FAILED = "VALIDATION_FAILED"


# ── Candidate availability ────────────────────────────────────────────────────

class CandidateStatus(str, Enum):
    """Operational status of a routing candidate."""
    AVAILABLE    = "AVAILABLE"
    UNAVAILABLE  = "UNAVAILABLE"
    BLACKLISTED  = "BLACKLISTED"
    DEGRADED     = "DEGRADED"


ROUTED_OUTCOMES: frozenset[RoutingOutcome] = frozenset({
    RoutingOutcome.ROUTED,
    RoutingOutcome.FAILOVER_ROUTED,
})

FAILED_OUTCOMES: frozenset[RoutingOutcome] = frozenset({
    RoutingOutcome.FAILED,
    RoutingOutcome.NO_CANDIDATES,
    RoutingOutcome.POLICY_REJECTED,
    RoutingOutcome.VALIDATION_FAILED,
})
