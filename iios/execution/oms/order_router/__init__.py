"""iios/execution/oms/order_router/__init__.py
==================================================
Public API for the IIOS Order Router.

C6 Execution Intelligence — Phase 2, Module 3
"""
from iios.execution.oms.order_router.constants import (
    ROUTER_SYSTEM_ID,
    REGISTRY_SYSTEM_ID,
    FACTORY_SYSTEM_ID,
    VALIDATOR_SYSTEM_ID,
    VERSION,
    ACTOR_ROUTER,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_ROUTING_TTL,
    BrokerCapability,
    CandidateScoreField,
    ExecutionMode,
    RoutingEventType,
    RoutingPolicyType,
    RoutingStatus,
    RoutingValidationCode,
    TERMINAL_ROUTING_STATUSES,
)
from iios.execution.oms.order_router.exceptions import (
    OrderRouterError,
    DuplicateRoutingError,
    NoCandidatesError,
    RouterCapacityError,
    RouterNotRunning,
    RoutingExpiredError,
    RoutingPolicyError,
    RoutingRejectedError,
    RoutingRequestError,
    RoutingStrategyError,
    RoutingValidationError,
)
from iios.execution.oms.order_router.routing_context import (
    BrokerCapabilities,
    RoutingContext,
)
from iios.execution.oms.order_router.routing_request import RoutingRequest
from iios.execution.oms.order_router.routing_candidate import RoutingCandidate
from iios.execution.oms.order_router.routing_decision import RoutingDecision
from iios.execution.oms.order_router.routing_result import RoutingResult
from iios.execution.oms.order_router.routing_rule import (
    RoutingRule,
    make_availability_rule,
    make_capability_rule,
    make_exchange_rule,
    make_execution_mode_rule,
    make_order_type_rule,
    make_priority_rule,
)
from iios.execution.oms.order_router.routing_policy import (
    RoutingPolicy,
    get_policy,
    make_backtest_policy,
    make_capability_policy,
    make_default_policy,
    make_exchange_policy,
    make_paper_trading_policy,
    make_priority_policy,
    make_recovery_policy,
)
from iios.execution.oms.order_router.routing_strategy import RoutingStrategy
from iios.execution.oms.order_router.routing_events import (
    RoutingEvent,
    make_candidate_evaluated,
    make_route_selected,
    make_routing_completed,
    make_routing_rejected,
    make_routing_started,
)
from iios.execution.oms.order_router.routing_statistics import RoutingStatistics
from iios.execution.oms.order_router.routing_history import RoutingHistory
from iios.execution.oms.order_router.routing_validation import RoutingValidator
from iios.execution.oms.order_router.routing_registry import RoutingRegistry
from iios.execution.oms.order_router.routing_factory import RoutingFactory
from iios.execution.oms.order_router.order_router import OrderRouter

__all__ = [
    # System identifiers
    "ROUTER_SYSTEM_ID",
    "REGISTRY_SYSTEM_ID",
    "FACTORY_SYSTEM_ID",
    "VALIDATOR_SYSTEM_ID",
    "VERSION",
    "ACTOR_ROUTER",
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_MAX_CANDIDATES",
    "DEFAULT_ROUTING_TTL",
    # Enumerations
    "BrokerCapability",
    "CandidateScoreField",
    "ExecutionMode",
    "RoutingEventType",
    "RoutingPolicyType",
    "RoutingStatus",
    "RoutingValidationCode",
    "TERMINAL_ROUTING_STATUSES",
    # Exceptions
    "OrderRouterError",
    "DuplicateRoutingError",
    "NoCandidatesError",
    "RouterCapacityError",
    "RouterNotRunning",
    "RoutingExpiredError",
    "RoutingPolicyError",
    "RoutingRejectedError",
    "RoutingRequestError",
    "RoutingStrategyError",
    "RoutingValidationError",
    # Context & capabilities
    "BrokerCapabilities",
    "RoutingContext",
    # Data models
    "RoutingRequest",
    "RoutingCandidate",
    "RoutingDecision",
    "RoutingResult",
    # Rules
    "RoutingRule",
    "make_availability_rule",
    "make_capability_rule",
    "make_exchange_rule",
    "make_execution_mode_rule",
    "make_order_type_rule",
    "make_priority_rule",
    # Policies
    "RoutingPolicy",
    "get_policy",
    "make_backtest_policy",
    "make_capability_policy",
    "make_default_policy",
    "make_exchange_policy",
    "make_paper_trading_policy",
    "make_priority_policy",
    "make_recovery_policy",
    # Strategy
    "RoutingStrategy",
    # Events
    "RoutingEvent",
    "make_candidate_evaluated",
    "make_route_selected",
    "make_routing_completed",
    "make_routing_rejected",
    "make_routing_started",
    # Infrastructure
    "RoutingStatistics",
    "RoutingHistory",
    "RoutingValidator",
    "RoutingRegistry",
    "RoutingFactory",
    # Primary facade
    "OrderRouter",
]
