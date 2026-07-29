"""
model_router.py -- iios.ai.model_management.router
====================================================
:class:`ModelRouter` — routes a :class:`RoutingContext` to the best
available :class:`AIModel` using a pluggable :class:`RoutingStrategy`.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from typing import Optional

from ..events.event_bus   import ModelEventBus
from ..events.model_events import RoutingCompletedEvent
from ..exceptions          import AINoModelAvailableError
from ..health.health_monitor import HealthMonitor
from ..registry.model_registry import AIModelRegistry
from .routing_context      import RoutingContext
from .routing_decision     import RoutingDecision
from .routing_strategy     import CapabilityFirstStrategy, RoutingStrategy

SYSTEM_ID = "iios:ai:model_management:router"


class ModelRouter:
    """Routes a :class:`RoutingContext` to the best available model."""

    def __init__(
        self,
        registry:       AIModelRegistry,
        health_monitor: HealthMonitor,
        *,
        strategy:       Optional[RoutingStrategy] = None,
        event_bus:      Optional[ModelEventBus]   = None,
    ) -> None:
        self._registry:       AIModelRegistry     = registry
        self._health_monitor: HealthMonitor        = health_monitor
        self._strategy:       RoutingStrategy      = strategy or CapabilityFirstStrategy()
        self._event_bus:      Optional[ModelEventBus] = event_bus

    def route(self, context: RoutingContext) -> RoutingDecision:
        """
        Select a model for *context*.

        Raises
        ------
        AINoModelAvailableError
            If no eligible model is available.
        """
        candidates = self._registry.list_all()
        result     = self._strategy.select(candidates, context, self._health_monitor)

        if result is None:
            raise AINoModelAvailableError(
                f"No model satisfies context requirements "
                f"(capabilities={set(context.required_capabilities)})."
            )

        model, score = result

        # Collect up to 3 alternatives (eligible but not selected)
        alternatives = tuple(
            m.model_id
            for m in candidates
            if m.model_id != model.model_id
            and m.enabled
            and m.active_version is not None
        )[:3]

        decision = RoutingDecision.create(
            model_id      = model.model_id,
            model_name    = model.metadata.name,
            strategy_used = self._strategy.STRATEGY_NAME,
            score         = score,
            alternatives  = alternatives,
        )

        if self._event_bus:
            self._event_bus.publish(
                RoutingCompletedEvent.create(
                    SYSTEM_ID,
                    model.model_id,
                    self._strategy.STRATEGY_NAME,
                    score,
                    len(alternatives),
                )
            )
        return decision

    @property
    def strategy(self) -> RoutingStrategy:
        return self._strategy

    def with_strategy(self, strategy: RoutingStrategy) -> "ModelRouter":
        """Return a new router using *strategy*."""
        return ModelRouter(
            self._registry, self._health_monitor,
            strategy=strategy, event_bus=self._event_bus
        )
