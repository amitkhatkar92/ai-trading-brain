"""iios/execution/gateway/routing/routing_policy.py
==================================================
RoutingPolicyBase and concrete routing policy implementations.

Every policy filters and ranks RoutingCandidates given a
RoutingContext.  Policies NEVER execute orders or call broker APIs.

Supported policies
------------------
DefaultBrokerPolicy
PreferredBrokerPolicy
CapabilityBasedPolicy
InstrumentBasedPolicy
MarketBasedPolicy
ExchangeBasedPolicy
ProductBasedPolicy
PriorityBasedPolicy
HealthBasedPolicy
FailoverRoutingPolicy
WeightedRoutingPolicy
CustomRoutingPolicy

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Set

from iios.execution.gateway.brokers.constants import BrokerCapability, ProductType

from .constants import RoutingPolicyType
from .routing_candidate import RoutingCandidate
from .routing_context import RoutingContext


# ── Abstract base ─────────────────────────────────────────────────────────────

class RoutingPolicyBase(ABC):
    """
    Abstract base for all routing policies.

    A policy evaluates a list of candidates against a routing context
    and returns an ordered subset.  The first candidate in the returned
    list is the most preferred selection.

    Policies are stateless with respect to execution — they may not
    store mutable request state between calls.
    """

    policy_type:       RoutingPolicyType
    supports_failover: bool = False

    def __init__(
        self,
        policy_id:   str,
        policy_name: str = "",
        *,
        metadata:    Optional[Dict[str, Any]] = None,
    ) -> None:
        self._policy_id   = policy_id
        self._policy_name = policy_name or policy_id
        self._metadata    = dict(metadata or {})

    @property
    def policy_id(self) -> str:
        return self._policy_id

    @property
    def policy_name(self) -> str:
        return self._policy_name

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    @abstractmethod
    def evaluate(
        self,
        candidates: List[RoutingCandidate],
        context:    RoutingContext,
    ) -> List[RoutingCandidate]:
        """
        Filter and rank candidates.

        Parameters
        ----------
        candidates:
            All available (connected, authenticated, non-blacklisted)
            candidates to evaluate.
        context:
            The routing context for this request.

        Returns
        -------
        List[RoutingCandidate]
            Ordered subset.  Empty list means no suitable broker found.
            The strategy selector will pick from this list.
        """

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id":        self._policy_id,
            "policy_name":      self._policy_name,
            "policy_type":      self.policy_type.value,
            "supports_failover": self.supports_failover,
            "metadata":         self._metadata,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"policy_id={self._policy_id!r}, "
            f"type={self.policy_type.value!r}"
            f")"
        )


# ── DefaultBrokerPolicy ───────────────────────────────────────────────────────

class DefaultBrokerPolicy(RoutingPolicyBase):
    """Always route to the configured default broker."""

    policy_type = RoutingPolicyType.DEFAULT_BROKER

    def __init__(
        self,
        policy_id:         str,
        default_broker_id: str,
        policy_name:       str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or f"default:{default_broker_id}", **kwargs)
        self._default_broker_id = default_broker_id

    @property
    def default_broker_id(self) -> str:
        return self._default_broker_id

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        return [c for c in candidates if c.broker_id == self._default_broker_id]


# ── PreferredBrokerPolicy ─────────────────────────────────────────────────────

class PreferredBrokerPolicy(RoutingPolicyBase):
    """
    Try the context's preferred_broker_id first, then fall back to
    the configured default_broker_id, then all available candidates.
    """

    policy_type = RoutingPolicyType.PREFERRED_BROKER

    def __init__(
        self,
        policy_id:          str,
        *,
        fallback_broker_id: Optional[str] = None,
        policy_name:        str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or "preferred-broker", **kwargs)
        self._fallback_broker_id = fallback_broker_id

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        result: List[RoutingCandidate] = []
        seen:   Set[str] = set()

        # 1. context preferred broker
        if context.preferred_broker_id:
            preferred = [c for c in candidates if c.broker_id == context.preferred_broker_id]
            for c in preferred:
                result.append(c)
                seen.add(c.broker_id)

        # 2. configured fallback
        if self._fallback_broker_id and self._fallback_broker_id not in seen:
            fallback = [c for c in candidates if c.broker_id == self._fallback_broker_id]
            for c in fallback:
                result.append(c)
                seen.add(c.broker_id)

        # 3. all others (sorted by priority desc)
        others = sorted(
            [c for c in candidates if c.broker_id not in seen],
            key=lambda c: c.routing_priority,
            reverse=True,
        )
        result.extend(others)
        return result


# ── CapabilityBasedPolicy ─────────────────────────────────────────────────────

class CapabilityBasedPolicy(RoutingPolicyBase):
    """Filter candidates to those supporting all required capabilities."""

    policy_type = RoutingPolicyType.CAPABILITY_BASED

    def __init__(
        self,
        policy_id:             str,
        required_capabilities: FrozenSet[BrokerCapability] = frozenset(),
        policy_name:           str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or "capability-based", **kwargs)
        self._required_capabilities = required_capabilities

    @property
    def required_capabilities(self) -> FrozenSet[BrokerCapability]:
        return self._required_capabilities

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        caps = self._required_capabilities | context.required_capabilities
        if not caps:
            return list(candidates)
        return [c for c in candidates if c.capabilities.supports_all(*caps)]


# ── InstrumentBasedPolicy ─────────────────────────────────────────────────────

class InstrumentBasedPolicy(RoutingPolicyBase):
    """
    Route based on instrument symbol.

    If allowed_symbols is non-empty, only candidates that have the
    symbol in the allowed set will be returned.
    If blocked_symbols is non-empty, candidates are dropped for
    those symbols.
    """

    policy_type = RoutingPolicyType.INSTRUMENT_BASED

    def __init__(
        self,
        policy_id:       str,
        *,
        allowed_symbols: FrozenSet[str] = frozenset(),
        blocked_symbols: FrozenSet[str] = frozenset(),
        symbol_broker_map: Optional[Dict[str, List[str]]] = None,
        policy_name:     str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or "instrument-based", **kwargs)
        self._allowed_symbols  = allowed_symbols
        self._blocked_symbols  = blocked_symbols
        self._symbol_broker_map: Dict[str, List[str]] = symbol_broker_map or {}

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        symbol = context.symbol

        # Symbol-specific broker mapping
        if symbol in self._symbol_broker_map:
            allowed_ids = set(self._symbol_broker_map[symbol])
            return [c for c in candidates if c.broker_id in allowed_ids]

        # Block check
        if symbol in self._blocked_symbols:
            return []

        # Allow check
        if self._allowed_symbols and symbol not in self._allowed_symbols:
            return []

        return list(candidates)


# ── MarketBasedPolicy ─────────────────────────────────────────────────────────

class MarketBasedPolicy(RoutingPolicyBase):
    """Route based on market (asset_class) to brokers that support it."""

    policy_type = RoutingPolicyType.MARKET_BASED

    def __init__(
        self,
        policy_id:         str,
        market_broker_map: Optional[Dict[str, List[str]]] = None,
        policy_name:       str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or "market-based", **kwargs)
        self._market_broker_map: Dict[str, List[str]] = market_broker_map or {}

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        market = context.asset_class
        if market in self._market_broker_map:
            allowed_ids = set(self._market_broker_map[market])
            return [c for c in candidates if c.broker_id in allowed_ids]
        return list(candidates)


# ── ExchangeBasedPolicy ───────────────────────────────────────────────────────

class ExchangeBasedPolicy(RoutingPolicyBase):
    """Route to brokers that support the context's exchange."""

    policy_type = RoutingPolicyType.EXCHANGE_BASED

    def __init__(
        self,
        policy_id:    str,
        policy_name:  str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or "exchange-based", **kwargs)

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        return [c for c in candidates if c.supports_exchange(context.exchange)]


# ── ProductBasedPolicy ────────────────────────────────────────────────────────

class ProductBasedPolicy(RoutingPolicyBase):
    """Route to brokers that support the context's product type."""

    policy_type = RoutingPolicyType.PRODUCT_BASED

    def __init__(
        self,
        policy_id:   str,
        policy_name: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or "product-based", **kwargs)

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        try:
            product = ProductType(context.product)
        except ValueError:
            return list(candidates)
        return [c for c in candidates if c.supports_product(product)]


# ── PriorityBasedPolicy ───────────────────────────────────────────────────────

class PriorityBasedPolicy(RoutingPolicyBase):
    """Sort candidates by routing_priority descending."""

    policy_type = RoutingPolicyType.PRIORITY_BASED

    def __init__(
        self,
        policy_id:       str,
        min_priority:    int = 0,
        policy_name:     str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or "priority-based", **kwargs)
        self._min_priority = min_priority

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        filtered = [c for c in candidates if c.routing_priority >= self._min_priority]
        return sorted(filtered, key=lambda c: c.routing_priority, reverse=True)


# ── HealthBasedPolicy ─────────────────────────────────────────────────────────

class HealthBasedPolicy(RoutingPolicyBase):
    """Filter by minimum health score and sort by health descending."""

    policy_type = RoutingPolicyType.HEALTH_BASED

    def __init__(
        self,
        policy_id:       str,
        min_health_score: float = 0.5,
        policy_name:     str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or "health-based", **kwargs)
        self._min_health_score = max(0.0, min(1.0, min_health_score))

    @property
    def min_health_score(self) -> float:
        return self._min_health_score

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        filtered = [c for c in candidates if c.health_score >= self._min_health_score]
        return sorted(filtered, key=lambda c: c.health_score, reverse=True)


# ── FailoverRoutingPolicy ─────────────────────────────────────────────────────

class FailoverRoutingPolicy(RoutingPolicyBase):
    """
    Try primary broker first; automatically fall back to secondary
    if the primary is unavailable.
    """

    policy_type        = RoutingPolicyType.FAILOVER_ROUTING
    supports_failover  = True

    def __init__(
        self,
        policy_id:           str,
        primary_broker_id:   str,
        secondary_broker_id: str,
        policy_name:         str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or "failover", **kwargs)
        self._primary_broker_id   = primary_broker_id
        self._secondary_broker_id = secondary_broker_id

    @property
    def primary_broker_id(self) -> str:
        return self._primary_broker_id

    @property
    def secondary_broker_id(self) -> str:
        return self._secondary_broker_id

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        primary   = [c for c in candidates if c.broker_id == self._primary_broker_id]
        secondary = [c for c in candidates if c.broker_id == self._secondary_broker_id]
        # Return primary first; secondary acts as failover
        return primary + secondary


# ── WeightedRoutingPolicy ─────────────────────────────────────────────────────

class WeightedRoutingPolicy(RoutingPolicyBase):
    """
    Include candidates with positive weight.

    The WeightedSelection strategy will use each candidate's .weight
    for probabilistic selection.
    """

    policy_type = RoutingPolicyType.WEIGHTED_ROUTING

    def __init__(
        self,
        policy_id:   str,
        policy_name: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or "weighted", **kwargs)

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        return [c for c in candidates if c.weight > 0.0]


# ── CustomRoutingPolicy ───────────────────────────────────────────────────────

class CustomRoutingPolicy(RoutingPolicyBase):
    """
    Policy backed by a user-provided evaluation callable.

    The evaluator receives the same arguments as evaluate() and must
    return a list of RoutingCandidate objects.
    """

    policy_type = RoutingPolicyType.CUSTOM_POLICY

    def __init__(
        self,
        policy_id:   str,
        evaluator:   Callable[[List[RoutingCandidate], RoutingContext], List[RoutingCandidate]],
        policy_name: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(policy_id, policy_name or "custom", **kwargs)
        self._evaluator = evaluator

    def evaluate(
        self, candidates: List[RoutingCandidate], context: RoutingContext
    ) -> List[RoutingCandidate]:
        return self._evaluator(candidates, context)
