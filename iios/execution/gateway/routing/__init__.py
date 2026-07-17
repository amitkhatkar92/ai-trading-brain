"""iios/execution/gateway/routing/__init__.py
==================================================
Public API for the IIOS Routing Framework.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

# ── Constants / enumerations ──────────────────────────────────────────────────
from .constants import (
    ACTOR_ROUTING_ENGINE,
    ACTOR_ROUTING_MANAGER,
    ACTOR_ROUTING_SYSTEM,
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_MAX_FAILOVER_DEPTH,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    DEFAULT_MIN_HEALTH_SCORE,
    DEFAULT_ROUTING_TIMEOUT_SECS,
    FAILED_OUTCOMES,
    ROUTED_OUTCOMES,
    ROUTING_ENGINE_SYSTEM_ID,
    ROUTING_MANAGER_SYSTEM_ID,
    ROUTING_REGISTRY_SYSTEM_ID,
    ROUTING_SELECTOR_SYSTEM_ID,
    ROUTING_SYSTEM_ID,
    CandidateStatus,
    RoutingEventType,
    RoutingOutcome,
    RoutingPolicyType,
    RoutingStrategyType,
    VERSION,
)

# ── Exceptions ────────────────────────────────────────────────────────────────
from .exceptions import (
    CandidateAlreadyRegisteredError,
    CandidateNotFoundError,
    NoBrokersAvailableError,
    PolicyAlreadyRegisteredError,
    RoutingEngineNotRunningError,
    RoutingFrameworkError,
    RoutingPolicyError,
    RoutingPolicyNotFoundError,
    RoutingRegistryCapacityError,
    RoutingRequestError,
    RoutingValidationError,
)

# ── Context ───────────────────────────────────────────────────────────────────
from .routing_context import RoutingContext, make_routing_context

# ── Candidate ─────────────────────────────────────────────────────────────────
from .routing_candidate import RoutingCandidate

# ── Request ───────────────────────────────────────────────────────────────────
from .routing_request import RoutingRequest, make_routing_request

# ── Response (Decision) ───────────────────────────────────────────────────────
from .routing_response import (
    RoutingDecision,
    make_failed_decision,
    make_routed_decision,
)

# ── Events ────────────────────────────────────────────────────────────────────
from .routing_events import (
    RoutingEvent,
    make_broker_rejected_event,
    make_broker_selected_event,
    make_failover_activated_event,
    make_policy_applied_event,
    make_routing_completed_event,
    make_routing_failed_event,
    make_routing_started_event,
)

# ── Policies ──────────────────────────────────────────────────────────────────
from .routing_policy import (
    CapabilityBasedPolicy,
    CustomRoutingPolicy,
    DefaultBrokerPolicy,
    ExchangeBasedPolicy,
    FailoverRoutingPolicy,
    HealthBasedPolicy,
    InstrumentBasedPolicy,
    MarketBasedPolicy,
    PreferredBrokerPolicy,
    PriorityBasedPolicy,
    ProductBasedPolicy,
    RoutingPolicyBase,
    WeightedRoutingPolicy,
)

# ── Strategy + selector ───────────────────────────────────────────────────────
from .routing_strategy  import RoutingStrategySelector
from .routing_selector  import RoutingSelector

# ── Validation ────────────────────────────────────────────────────────────────
from .routing_validation import RoutingValidationResult, RoutingValidator

# ── Statistics + history ──────────────────────────────────────────────────────
from .routing_statistics import RoutingStatistics
from .routing_history    import RoutingHistory

# ── Registry ─────────────────────────────────────────────────────────────────
from .routing_registry import RoutingRegistry

# ── Factory ───────────────────────────────────────────────────────────────────
from .routing_factory import RoutingFactory

# ── Manager + engine (primary API) ───────────────────────────────────────────
from .routing_manager import RoutingManager
from .routing_engine  import RoutingEngine


__all__ = [
    # Constants
    "ROUTING_SYSTEM_ID",
    "ROUTING_ENGINE_SYSTEM_ID",
    "ROUTING_MANAGER_SYSTEM_ID",
    "ROUTING_REGISTRY_SYSTEM_ID",
    "ROUTING_SELECTOR_SYSTEM_ID",
    "ACTOR_ROUTING_ENGINE",
    "ACTOR_ROUTING_MANAGER",
    "ACTOR_ROUTING_SYSTEM",
    "DEFAULT_MAX_CANDIDATES",
    "DEFAULT_MAX_FAILOVER_DEPTH",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_POLICIES",
    "DEFAULT_MIN_HEALTH_SCORE",
    "DEFAULT_ROUTING_TIMEOUT_SECS",
    "FAILED_OUTCOMES",
    "ROUTED_OUTCOMES",
    "VERSION",
    # Enums
    "CandidateStatus",
    "RoutingEventType",
    "RoutingOutcome",
    "RoutingPolicyType",
    "RoutingStrategyType",
    # Exceptions
    "CandidateAlreadyRegisteredError",
    "CandidateNotFoundError",
    "NoBrokersAvailableError",
    "PolicyAlreadyRegisteredError",
    "RoutingEngineNotRunningError",
    "RoutingFrameworkError",
    "RoutingPolicyError",
    "RoutingPolicyNotFoundError",
    "RoutingRegistryCapacityError",
    "RoutingRequestError",
    "RoutingValidationError",
    # Context / request / response
    "RoutingContext",
    "make_routing_context",
    "RoutingCandidate",
    "RoutingRequest",
    "make_routing_request",
    "RoutingDecision",
    "make_failed_decision",
    "make_routed_decision",
    # Events
    "RoutingEvent",
    "make_broker_rejected_event",
    "make_broker_selected_event",
    "make_failover_activated_event",
    "make_policy_applied_event",
    "make_routing_completed_event",
    "make_routing_failed_event",
    "make_routing_started_event",
    # Policies
    "CapabilityBasedPolicy",
    "CustomRoutingPolicy",
    "DefaultBrokerPolicy",
    "ExchangeBasedPolicy",
    "FailoverRoutingPolicy",
    "HealthBasedPolicy",
    "InstrumentBasedPolicy",
    "MarketBasedPolicy",
    "PreferredBrokerPolicy",
    "PriorityBasedPolicy",
    "ProductBasedPolicy",
    "RoutingPolicyBase",
    "WeightedRoutingPolicy",
    # Strategy + selector
    "RoutingStrategySelector",
    "RoutingSelector",
    # Validation
    "RoutingValidationResult",
    "RoutingValidator",
    # Statistics + history
    "RoutingStatistics",
    "RoutingHistory",
    # Registry / manager / engine
    "RoutingRegistry",
    "RoutingFactory",
    "RoutingManager",
    "RoutingEngine",
]
