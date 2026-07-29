"""
iios.ai.model_management.router
==================================
Model routing for A2 Model Management.
"""
from __future__ import annotations

from .model_router      import ModelRouter
from .routing_context   import RoutingContext
from .routing_decision  import RoutingDecision
from .routing_strategy  import (
    CapabilityFirstStrategy,
    RoundRobinStrategy,
    RoutingStrategy,
    TierPreferenceStrategy,
)

__all__ = [
    "ModelRouter",
    "RoutingContext",
    "RoutingDecision",
    "RoutingStrategy",
    "CapabilityFirstStrategy",
    "TierPreferenceStrategy",
    "RoundRobinStrategy",
]
