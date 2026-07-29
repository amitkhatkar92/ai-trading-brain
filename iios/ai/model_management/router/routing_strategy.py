"""
routing_strategy.py -- iios.ai.model_management.router
========================================================
:class:`RoutingStrategy` ABC and three default implementations:
  - :class:`CapabilityFirstStrategy`  — filter by capabilities, first eligible
  - :class:`TierPreferenceStrategy`   — prefers the context's preferred_tier
  - :class:`RoundRobinStrategy`       — cycles through eligible models

No provider-specific logic anywhere in this module.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

import abc
import threading
from typing import List, Optional, Tuple

from ..core.ai_model     import AIModel
from ..core.model_tier   import ModelTier
from ..health.health_monitor import HealthMonitor
from .routing_context    import RoutingContext


class RoutingStrategy(abc.ABC):
    """ABC for all model routing strategies."""
    STRATEGY_NAME: str = "base"

    @abc.abstractmethod
    def select(
        self,
        candidates:     List[AIModel],
        context:        RoutingContext,
        health_monitor: HealthMonitor,
    ) -> Optional[Tuple[AIModel, float]]:
        """
        Select a model from *candidates* given *context*.

        Returns ``(model, score)`` or ``None`` if no eligible model exists.
        ``score`` is a [0.0, 1.0] float — higher is better.
        """
        ...

    def _is_eligible(
        self,
        model:          AIModel,
        context:        RoutingContext,
        health_monitor: HealthMonitor,
    ) -> bool:
        """Shared eligibility filter used by all built-in strategies."""
        if not model.enabled:
            return False
        if model.model_id in context.exclude_model_ids:
            return False
        if not health_monitor.is_healthy(model.model_id):
            return False
        version = model.active_version
        if version is None:
            return False
        if context.required_capabilities:
            if not context.required_capabilities.issubset(version.descriptor.capabilities):
                return False
        return True


class CapabilityFirstStrategy(RoutingStrategy):
    """Returns the first model whose capabilities satisfy all requirements."""
    STRATEGY_NAME = "capability_first"

    def select(self, candidates, context, health_monitor):
        for model in candidates:
            if self._is_eligible(model, context, health_monitor):
                return (model, 1.0)
        return None


class TierPreferenceStrategy(RoutingStrategy):
    """Prefers models in the requested tier; falls back to any eligible model."""
    STRATEGY_NAME = "tier_preference"

    def select(self, candidates, context, health_monitor):
        eligible = [m for m in candidates if self._is_eligible(m, context, health_monitor)]
        if not eligible:
            return None
        if context.preferred_tier is not None:
            preferred = [m for m in eligible if m.metadata.tier == context.preferred_tier]
            if preferred:
                return (preferred[0], 1.0)
        return (eligible[0], 0.5)   # fell back — lower score to signal tier miss


class RoundRobinStrategy(RoutingStrategy):
    """Distributes load evenly across eligible models in registration order."""
    STRATEGY_NAME = "round_robin"

    def __init__(self) -> None:
        self._counter: int            = 0
        self._lock:    threading.Lock = threading.Lock()

    def select(self, candidates, context, health_monitor):
        eligible = [m for m in candidates if self._is_eligible(m, context, health_monitor)]
        if not eligible:
            return None
        with self._lock:
            idx           = self._counter % len(eligible)
            self._counter += 1
        return (eligible[idx], 1.0)
