"""iios/execution/gateway/routing/routing_factory.py
==================================================
RoutingFactory — static factory helpers for Routing Framework objects.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, FrozenSet, List, Optional

from iios.execution.gateway.brokers.broker_capabilities import BrokerCapabilities
from iios.execution.gateway.brokers.constants import BrokerCapability, ProductType

from .constants import (
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_POLICIES,
    DEFAULT_MAX_CANDIDATES,
    RoutingStrategyType,
)
from .routing_candidate import RoutingCandidate
from .routing_context import RoutingContext, make_routing_context
from .routing_history import RoutingHistory
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
from .routing_request import RoutingRequest, make_routing_request
from .routing_statistics import RoutingStatistics


class RoutingFactory:
    """All-static factory for Routing Framework objects."""

    # ── Context / request ─────────────────────────────────────────────────────

    @staticmethod
    def create_context(
        execution_id: str,
        order_id:     str,
        portfolio_id: str,
        strategy_id:  str,
        **kwargs: Any,
    ) -> RoutingContext:
        """Create a RoutingContext with sensible defaults."""
        return make_routing_context(
            execution_id=execution_id,
            order_id=order_id,
            portfolio_id=portfolio_id,
            strategy_id=strategy_id,
            **kwargs,
        )

    @staticmethod
    def create_request(
        context:   RoutingContext,
        *,
        policy_id: Optional[str] = None,
        strategy:  RoutingStrategyType = RoutingStrategyType.PRIORITY_SELECTION,
        metadata:  Optional[Dict[str, Any]] = None,
    ) -> RoutingRequest:
        """Create a RoutingRequest from a RoutingContext."""
        return make_routing_request(
            context=context,
            policy_id=policy_id,
            strategy=strategy,
            metadata=metadata,
        )

    # ── Candidate ─────────────────────────────────────────────────────────────

    @staticmethod
    def create_candidate(
        broker_id:           str,
        broker_name:         str,
        capabilities:        BrokerCapabilities,
        *,
        is_connected:        bool                   = True,
        is_authenticated:    bool                   = True,
        health_score:        float                  = 1.0,
        routing_priority:    int                    = 0,
        weight:              float                  = 1.0,
        supported_exchanges: FrozenSet[str]         = frozenset(),
        supported_products:  FrozenSet[ProductType] = frozenset(),
    ) -> RoutingCandidate:
        """Create a pre-connected RoutingCandidate."""
        return RoutingCandidate(
            broker_id=broker_id,
            broker_name=broker_name,
            capabilities=capabilities,
            is_connected=is_connected,
            is_authenticated=is_authenticated,
            health_score=health_score,
            routing_priority=routing_priority,
            weight=weight,
            supported_exchanges=supported_exchanges,
            supported_products=supported_products,
        )

    # ── Statistics / history ──────────────────────────────────────────────────

    @staticmethod
    def create_statistics() -> RoutingStatistics:
        return RoutingStatistics()

    @staticmethod
    def create_history(
        max_decisions: int = DEFAULT_MAX_HISTORY,
        max_events:    int = DEFAULT_MAX_HISTORY,
    ) -> RoutingHistory:
        return RoutingHistory(max_decisions=max_decisions, max_events=max_events)

    # ── Policies ──────────────────────────────────────────────────────────────

    @staticmethod
    def create_default_broker_policy(
        policy_id:         str,
        default_broker_id: str,
        policy_name:       str = "",
    ) -> DefaultBrokerPolicy:
        return DefaultBrokerPolicy(policy_id, default_broker_id, policy_name)

    @staticmethod
    def create_preferred_broker_policy(
        policy_id:          str,
        *,
        fallback_broker_id: Optional[str] = None,
        policy_name:        str = "",
    ) -> PreferredBrokerPolicy:
        return PreferredBrokerPolicy(
            policy_id,
            fallback_broker_id=fallback_broker_id,
            policy_name=policy_name,
        )

    @staticmethod
    def create_capability_policy(
        policy_id:             str,
        required_capabilities: FrozenSet[BrokerCapability] = frozenset(),
        policy_name:           str = "",
    ) -> CapabilityBasedPolicy:
        return CapabilityBasedPolicy(
            policy_id,
            required_capabilities=required_capabilities,
            policy_name=policy_name,
        )

    @staticmethod
    def create_health_policy(
        policy_id:        str,
        min_health_score: float = 0.5,
        policy_name:      str = "",
    ) -> HealthBasedPolicy:
        return HealthBasedPolicy(policy_id, min_health_score, policy_name)

    @staticmethod
    def create_priority_policy(
        policy_id:    str,
        min_priority: int = 0,
        policy_name:  str = "",
    ) -> PriorityBasedPolicy:
        return PriorityBasedPolicy(policy_id, min_priority, policy_name)

    @staticmethod
    def create_failover_policy(
        policy_id:           str,
        primary_broker_id:   str,
        secondary_broker_id: str,
        policy_name:         str = "",
    ) -> FailoverRoutingPolicy:
        return FailoverRoutingPolicy(
            policy_id,
            primary_broker_id,
            secondary_broker_id,
            policy_name,
        )

    @staticmethod
    def create_weighted_policy(
        policy_id:   str,
        policy_name: str = "",
    ) -> WeightedRoutingPolicy:
        return WeightedRoutingPolicy(policy_id, policy_name)

    @staticmethod
    def create_custom_policy(
        policy_id:   str,
        evaluator:   Callable,
        policy_name: str = "",
    ) -> CustomRoutingPolicy:
        return CustomRoutingPolicy(policy_id, evaluator, policy_name)

    @staticmethod
    def create_exchange_policy(
        policy_id:   str,
        policy_name: str = "",
    ) -> ExchangeBasedPolicy:
        return ExchangeBasedPolicy(policy_id, policy_name)

    @staticmethod
    def create_product_policy(
        policy_id:   str,
        policy_name: str = "",
    ) -> ProductBasedPolicy:
        return ProductBasedPolicy(policy_id, policy_name)

    @staticmethod
    def create_instrument_policy(
        policy_id:       str,
        *,
        allowed_symbols: FrozenSet[str] = frozenset(),
        blocked_symbols: FrozenSet[str] = frozenset(),
        symbol_broker_map: Optional[Dict[str, List[str]]] = None,
        policy_name:     str = "",
    ) -> InstrumentBasedPolicy:
        return InstrumentBasedPolicy(
            policy_id,
            allowed_symbols=allowed_symbols,
            blocked_symbols=blocked_symbols,
            symbol_broker_map=symbol_broker_map,
            policy_name=policy_name,
        )

    @staticmethod
    def create_market_policy(
        policy_id:         str,
        market_broker_map: Optional[Dict[str, List[str]]] = None,
        policy_name:       str = "",
    ) -> MarketBasedPolicy:
        return MarketBasedPolicy(policy_id, market_broker_map, policy_name)
