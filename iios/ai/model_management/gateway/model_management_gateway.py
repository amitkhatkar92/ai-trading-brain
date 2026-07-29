"""
model_management_gateway.py -- iios.ai.model_management.gateway
=================================================================
:class:`ModelManagementGateway` — the single public entry point for the
A2 Model Management module.

All external AI Platform modules (A3-A10, orchestration, agents) interact
with A2 exclusively through this gateway.  No external code should import
from ``iios.ai.model_management.registry``, ``.router``, ``.health``, etc.

Design
------
* Inherits ``AILifecycleAwareMixin`` (via A1) — full lifecycle management.
* Owns a :class:`ModelManagementContainer` — DI composition root.
* Exposes a minimal, stable public API — this is the V1 contract for A2.

A2 Model Management — Phase 3, Module 2  |  M6 Gateway
"""
from __future__ import annotations

import time
from typing import Any, Dict, FrozenSet, List, Optional, Tuple, Type

from iios.common.logging.logging_manager import get_logger

from ..capabilities.capability_type          import ModelCapabilityType
from ..container.model_management_container  import ModelManagementContainer
from ..core.ai_model                          import AIModel
from ..core.model_category                    import ModelCategory
from ..core.model_tier                        import ModelTier
from ..core.model_version                     import AIModelVersion
from ..events.event_bus                       import ModelEventBus
from ..health.health_report                   import HealthReport
from ..lifecycle import AILifecycleAwareMixin, AILifecycleState
from ..router.routing_context                 import RoutingContext
from ..router.routing_decision                import RoutingDecision
from ..snapshot.model_management_snapshot     import ModelManagementSnapshot

_log = get_logger(__name__)

SYSTEM_ID = "iios:ai:model_management:gateway"
VERSION   = "1.0.0"


class ModelManagementGateway(AILifecycleAwareMixin):
    """
    Single public entry point for the A2 Model Management module.

    Usage::

        from iios.ai.model_management.gateway import ModelManagementGateway
        from iios.ai.model_management.capabilities import ModelCapabilityType
        from iios.ai.model_management.core import ModelCategory

        gw = ModelManagementGateway()
        gw.initialize()
        gw.start()

        gw.register_model(
            "gpt-abstract", ModelCategory.LANGUAGE_MODEL,
            frozenset({ModelCapabilityType.CHAT, ModelCapabilityType.STREAMING}),
        )
        ctx = RoutingContext.for_capability(ModelCapabilityType.CHAT)
        decision = gw.route_request(ctx)
    """

    SYSTEM_ID  : str = SYSTEM_ID
    VERSION    : str = VERSION
    MODULE_ID  : str = "A2"
    MODULE_NAME: str = "Model Management"
    API_VERSION: str = "v1"
    DESCRIPTION: str = "AI model registry, routing, capability management and health monitoring"
    STATUS     : str = "stable"

    def __init__(self, container: Optional[ModelManagementContainer] = None) -> None:
        self._container:  ModelManagementContainer = container or ModelManagementContainer()
        self._started_at: Optional[float]           = None

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    def _on_initialize(self) -> None:
        self._container.build()
        _log.info("ModelManagementGateway: container built")

    def _on_start(self) -> None:
        self._started_at = time.time()
        _log.info(f"ModelManagementGateway: started (v{self.VERSION})")

    def _on_stop(self) -> None:
        _log.info(
            f"ModelManagementGateway: stopped "
            f"(models={len(self._container.registry)})"
        )

    # ── Model Registry API ────────────────────────────────────────────────────

    def register_model(
        self,
        name:         str,
        category:     ModelCategory,
        capabilities: FrozenSet[ModelCapabilityType],
        *,
        tier:                ModelTier          = ModelTier.STANDARD,
        provider_id:         str                = "",
        description:         str                = "",
        tags:                Tuple[str, ...]    = (),
        owner:               str                = "",
        context_window:      int                = 4_096,
        max_output_tokens:   int                = 1_024,
        parameters_billions: float              = 0.0,
    ) -> AIModel:
        """Register a new model with its initial (active) version."""
        return self._container.registry.register(
            name, category, frozenset(capabilities),
            tier=tier, provider_id=provider_id, description=description,
            tags=tags, owner=owner,
            context_window=context_window,
            max_output_tokens=max_output_tokens,
            parameters_billions=parameters_billions,
        )

    def remove_model(self, model_id: str) -> None:
        """Permanently deregister a model."""
        self._container.registry.deregister(model_id)

    def enable_model(self, model_id: str) -> None:
        self._container.registry.enable(model_id)

    def disable_model(self, model_id: str) -> None:
        self._container.registry.disable(model_id)

    def get_model(self, model_id: str) -> AIModel:
        """Fetch by model_id; raises :class:`AIModelNotFoundError` if missing."""
        return self._container.registry.get(model_id)

    def find_model(self, name: str) -> Optional[AIModel]:
        """Fetch by name; returns ``None`` if not found."""
        return self._container.registry.find_by_name(name)

    def list_models(
        self,
        *,
        category:     Optional[ModelCategory]       = None,
        capability:   Optional[ModelCapabilityType] = None,
        tier:         Optional[ModelTier]            = None,
        enabled_only: bool                          = False,
    ) -> List[AIModel]:
        """List/search registered models."""
        return self._container.registry.search(
            category=category, capability=capability,
            tier=tier, enabled_only=enabled_only,
        )

    # ── Version Management API ────────────────────────────────────────────────

    def add_version(
        self,
        model_id:     str,
        capabilities: FrozenSet[ModelCapabilityType],
        *,
        context_window:      int   = 4_096,
        max_output_tokens:   int   = 1_024,
        parameters_billions: float = 0.0,
        activate:            bool  = True,
    ) -> AIModelVersion:
        return self._container.registry.add_version(
            model_id, frozenset(capabilities),
            context_window=context_window,
            max_output_tokens=max_output_tokens,
            parameters_billions=parameters_billions,
            activate=activate,
        )

    def activate_version(self, model_id: str, version_id: str) -> AIModelVersion:
        return self._container.registry.activate_version(model_id, version_id)

    def rollback(self, model_id: str, version_id: str) -> AIModelVersion:
        return self._container.registry.rollback(model_id, version_id)

    def version_history(self, model_id: str) -> List[AIModelVersion]:
        return self.get_model(model_id).history()

    # ── Capability Discovery ──────────────────────────────────────────────────

    def list_capabilities(self) -> List[ModelCapabilityType]:
        """Return all defined capability types (static catalogue)."""
        return list(ModelCapabilityType)

    # ── Routing API ───────────────────────────────────────────────────────────

    def route_request(self, context: RoutingContext) -> RoutingDecision:
        """
        Route to the best available model for *context*.

        Raises
        ------
        AINoModelAvailableError
            If no eligible, healthy model can be found.
        """
        return self._container.router.route(context)

    # ── Health API ────────────────────────────────────────────────────────────

    def get_health(self, model_id: str) -> HealthReport:
        """Return the current health report for *model_id*."""
        return self._container.health_monitor.get_report(model_id)

    def record_success(self, model_id: str) -> None:
        """Record a successful call outcome for *model_id*."""
        self._container.health_monitor.record_success(model_id)

    def record_failure(self, model_id: str) -> None:
        """Record a failed call outcome for *model_id*."""
        self._container.health_monitor.record_failure(model_id)

    def all_health(self) -> Dict[str, HealthReport]:
        """Return health reports for all tracked models."""
        return self._container.health_monitor.all_reports()

    # ── Observability ─────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        models = self._container.registry.list_all()
        state  = self.lifecycle_state
        return {
            "module_id":             self.SYSTEM_ID,
            "state":                 state.value,
            "is_running":            (state == AILifecycleState.RUNNING),
            "model_count":           len(models),
            "enabled_model_count":   sum(1 for m in models if m.enabled),
            "version":               self.VERSION,
        }

    def status(self) -> Dict[str, Any]:
        h = self.health()
        h["events_published"] = self._container.event_bus.published_count
        h["healthy_models"]   = sum(
            1 for m in self._container.registry.list_all()
            if self._container.health_monitor.is_healthy(m.model_id)
        )
        return h

    def snapshot(self) -> ModelManagementSnapshot:
        """Return an immutable :class:`ModelManagementSnapshot`."""
        return ModelManagementSnapshot.capture(
            self._container.registry,
            self._container.health_monitor,
            self._container.event_bus,
        )

    # ── Shared infrastructure access ──────────────────────────────────────────

    @property
    def event_bus(self) -> ModelEventBus:
        return self._container.event_bus

    @property
    def container(self) -> ModelManagementContainer:
        return self._container
