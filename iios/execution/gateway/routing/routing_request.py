"""iios/execution/gateway/routing/routing_request.py
==================================================
RoutingRequest — wrapper around RoutingContext for a single
routing evaluation pass.

C6 Execution Intelligence — Phase 5, Module 4
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import RoutingStrategyType, VERSION
from .routing_context import RoutingContext


@dataclass(frozen=True)
class RoutingRequest:
    """
    Immutable routing request submitted to RoutingEngine.route().

    Wraps a RoutingContext with an explicit policy selection and
    strategy override.
    """

    request_id:  str
    context:     RoutingContext
    policy_id:   Optional[str]          # None → use default policy
    strategy:    RoutingStrategyType
    created_at:  float
    version:     str                    = VERSION
    metadata:    Dict[str, Any]         = field(default_factory=dict, compare=False)

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def routing_id(self) -> str:
        return self.context.routing_id

    @property
    def execution_id(self) -> str:
        return self.context.execution_id

    @property
    def order_id(self) -> str:
        return self.context.order_id

    @property
    def portfolio_id(self) -> str:
        return self.context.portfolio_id

    @property
    def strategy_id(self) -> str:
        return self.context.strategy_id

    @property
    def has_explicit_policy(self) -> bool:
        return self.policy_id is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":  self.request_id,
            "context":     self.context.to_dict(),
            "policy_id":   self.policy_id,
            "strategy":    self.strategy.value,
            "created_at":  self.created_at,
            "version":     self.version,
            "metadata":    dict(self.metadata),
        }


# ── Factory function ──────────────────────────────────────────────────────────

def make_routing_request(
    context:   RoutingContext,
    *,
    policy_id: Optional[str] = None,
    strategy:  RoutingStrategyType = RoutingStrategyType.PRIORITY_SELECTION,
    metadata:  Optional[Dict[str, Any]] = None,
) -> RoutingRequest:
    """Create a RoutingRequest from a RoutingContext."""
    return RoutingRequest(
        request_id=str(uuid.uuid4()),
        context=context,
        policy_id=policy_id,
        strategy=strategy,
        created_at=time.time(),
        metadata=dict(metadata or {}),
    )
