"""
model_management_container.py -- iios.ai.model_management.container
=====================================================================
:class:`ModelManagementContainer` — DI composition root wiring every
A2 component: registry, router, health monitor, configuration loader,
and policies.  Mirrors the ``AIContainer`` / ``PromptContextContainer``
pattern from A1/A3.

A2 Model Management — Phase 3, Module 2
"""
from __future__ import annotations

from typing import Optional

from ..configuration.configuration_loader import ConfigurationLoader
from ..events.event_bus                   import ModelEventBus
from ..health.health_monitor              import HealthMonitor
from ..policy.policies                    import (
    AllowAllCostPolicy,
    CapabilityBasedSelectionPolicy,
    CostPolicy,
    FailoverPolicy,
    SelectionPolicy,
    SimpleFailoverPolicy,
    StrictCapabilityPolicy,
    CapabilityPolicy,
    PermissiveLatencyPolicy,
    LatencyPolicy,
)
from ..registry.model_registry            import AIModelRegistry
from ..router.model_router                import ModelRouter
from ..router.routing_strategy            import CapabilityFirstStrategy, RoutingStrategy


class ModelManagementContainer:
    """
    DI composition root for the A2 Model Management module.

    Usage::

        container = ModelManagementContainer()
        container.build()
        container.registry.register(...)
    """

    def __init__(
        self,
        routing_strategy:    Optional[RoutingStrategy]    = None,
        selection_policy:    Optional[SelectionPolicy]    = None,
        failover_policy:     Optional[FailoverPolicy]     = None,
        cost_policy:         Optional[CostPolicy]         = None,
        latency_policy:      Optional[LatencyPolicy]      = None,
        capability_policy:   Optional[CapabilityPolicy]   = None,
    ) -> None:
        self._event_bus:          ModelEventBus         = ModelEventBus()
        self._registry:           AIModelRegistry       = AIModelRegistry(self._event_bus)
        self._health_monitor:     HealthMonitor         = HealthMonitor(self._event_bus)
        self._configuration_loader: ConfigurationLoader = ConfigurationLoader()

        self._routing_strategy:   RoutingStrategy       = routing_strategy or CapabilityFirstStrategy()
        self._router:             ModelRouter            = ModelRouter(
            self._registry, self._health_monitor,
            strategy=self._routing_strategy, event_bus=self._event_bus,
        )

        # Policies
        self._selection_policy:   SelectionPolicy       = selection_policy or CapabilityBasedSelectionPolicy()
        self._failover_policy:    FailoverPolicy        = failover_policy or SimpleFailoverPolicy()
        self._cost_policy:        CostPolicy            = cost_policy or AllowAllCostPolicy()
        self._latency_policy:     LatencyPolicy         = latency_policy or PermissiveLatencyPolicy()
        self._capability_policy:  CapabilityPolicy      = capability_policy or StrictCapabilityPolicy()

        self._built = False

    def build(self) -> "ModelManagementContainer":
        """Finalize wiring.  Idempotent — safe to call multiple times."""
        self._built = True
        return self

    @property
    def is_built(self) -> bool:
        return self._built

    # ── Component accessors ───────────────────────────────────────────────────

    @property
    def event_bus(self) -> ModelEventBus:
        return self._event_bus

    @property
    def registry(self) -> AIModelRegistry:
        return self._registry

    @property
    def health_monitor(self) -> HealthMonitor:
        return self._health_monitor

    @property
    def router(self) -> ModelRouter:
        return self._router

    @property
    def configuration_loader(self) -> ConfigurationLoader:
        return self._configuration_loader

    @property
    def selection_policy(self) -> SelectionPolicy:
        return self._selection_policy

    @property
    def failover_policy(self) -> FailoverPolicy:
        return self._failover_policy

    @property
    def cost_policy(self) -> CostPolicy:
        return self._cost_policy

    @property
    def latency_policy(self) -> LatencyPolicy:
        return self._latency_policy

    @property
    def capability_policy(self) -> CapabilityPolicy:
        return self._capability_policy

    def __repr__(self) -> str:
        return (
            f"<ModelManagementContainer built={self._built} "
            f"models={len(self._registry)}>"
        )
