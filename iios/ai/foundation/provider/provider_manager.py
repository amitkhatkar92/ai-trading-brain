"""
provider_manager.py -- iios.ai.foundation.provider
===================================================
ProviderManager -- high-level provider lifecycle orchestrator.
AIProviderRuntime  -- lifecycle-aware provider runtime component.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import time
import threading
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from ..lifecycle.ai_foundation_lifecycle import AILifecycleAwareMixin
from ..lifecycle.constants               import VERSION
from ..events.ai_events                  import (
    ProviderRegisteredEvent, ProviderDeregisteredEvent,
    ProviderHealthChangedEvent, ProviderUnavailableEvent,
)
from ..events.event_bus                  import AIEventBus

from .provider_capabilities  import AIProviderCapabilities, ProviderProfile
from .provider_constants     import ProviderCapabilityType, ProviderStatus, ProviderSelectionStrategy, PROVIDER_SYSTEM_ID
from .provider_extensions    import AIProviderExtension
from .provider_registry      import ProviderRegistry
from .provider_resolver      import ProviderResolver, ProviderSelector

_log = get_logger(__name__)


class ProviderManager:
    """
    High-level provider lifecycle orchestrator.

    Responsibilities
    ----------------
    * Register / deregister providers.
    * Run health probes and update status.
    * Emit lifecycle events on status changes.
    * Provide a unified query interface over the registry.

    Injected into :class:`AIProviderRuntime` at construction time.
    """

    def __init__(
        self,
        registry:  ProviderRegistry,
        event_bus: Optional[AIEventBus] = None,
    ) -> None:
        self._registry  = registry
        self._event_bus = event_bus
        self._lock      = threading.Lock()

    # ---- registration -----------------------------------------------------

    def register(self, extension: AIProviderExtension) -> ProviderProfile:
        """Register a provider and emit a :class:`ProviderRegisteredEvent`."""
        profile = self._registry.register(extension)
        if self._event_bus:
            self._event_bus.publish(
                ProviderRegisteredEvent.create(
                    source_id    = PROVIDER_SYSTEM_ID,
                    provider_id  = extension.provider_id,
                    model_id     = extension.capabilities.model_id,
                    capabilities = tuple(
                        c.value for c in extension.capabilities.capabilities
                    ),
                )
            )
        return profile

    def deregister(self, provider_id: str) -> None:
        """Deregister a provider and emit a :class:`ProviderDeregisteredEvent`."""
        self._registry.deregister(provider_id)
        if self._event_bus:
            self._event_bus.publish(
                ProviderDeregisteredEvent.create(
                    source_id   = PROVIDER_SYSTEM_ID,
                    provider_id = provider_id,
                )
            )

    # ---- health management -----------------------------------------------

    def probe_health(self, provider_id: str) -> bool:
        """
        Run a health probe against ``provider_id`` and update its status.

        Returns True iff the provider is healthy after the probe.
        """
        ext = self._registry.get(provider_id)
        if ext is None:
            return False

        old_status = self._registry.get_status(provider_id)
        try:
            result  = ext.health_check()
            healthy = bool(result.get("healthy", False))
            new_status = ProviderStatus.ACTIVE if healthy else ProviderStatus.DEGRADED
        except Exception as exc:
            _log.warning(f"ProviderManager: health probe failed provider={provider_id!r} err={exc}")
            healthy    = False
            new_status = ProviderStatus.UNAVAILABLE

        self._registry.set_status(provider_id, new_status)

        if self._event_bus and old_status != new_status:
            if new_status == ProviderStatus.UNAVAILABLE:
                self._event_bus.publish(
                    ProviderUnavailableEvent.create(
                        source_id   = PROVIDER_SYSTEM_ID,
                        provider_id = provider_id,
                        reason      = "health_probe_failed",
                    )
                )
            else:
                self._event_bus.publish(
                    ProviderHealthChangedEvent.create(
                        source_id   = PROVIDER_SYSTEM_ID,
                        provider_id = provider_id,
                        old_status  = old_status.value if old_status else "unknown",
                        new_status  = new_status.value,
                    )
                )
        return healthy

    # ---- query ------------------------------------------------------------

    def find_for_capability(
        self,
        capability: ProviderCapabilityType,
    ) -> List[AIProviderExtension]:
        return self._registry.find_for_capability(capability)

    def all_profiles(self) -> List[ProviderProfile]:
        return self._registry.all_profiles()

    def active_count(self) -> int:
        return len(self._registry.active_provider_ids())


# ---------------------------------------------------------------------------
# AIProviderRuntime -- lifecycle-aware wrapper
# ---------------------------------------------------------------------------

class AIProviderRuntime(AILifecycleAwareMixin):
    """
    Lifecycle-aware provider runtime component.

    Wraps :class:`ProviderManager`, :class:`ProviderResolver`, and
    :class:`ProviderSelector` behind the standard AI lifecycle interface.
    All A1/A2 modules that need provider access reference this class.

    Parameters
    ----------
    event_bus :         Optional event bus for lifecycle events.
    selection_strategy: Default routing strategy.
    """

    SYSTEM_ID: str = PROVIDER_SYSTEM_ID
    VERSION:   str = VERSION

    def __init__(
        self,
        event_bus:           Optional[AIEventBus]           = None,
        selection_strategy:  ProviderSelectionStrategy = ProviderSelectionStrategy.FIRST_AVAILABLE,
    ) -> None:
        self._event_bus = event_bus
        self._registry  = ProviderRegistry()
        self._manager   = ProviderManager(self._registry, event_bus)
        self._resolver  = ProviderResolver(self._registry)
        self._selector  = ProviderSelector(selection_strategy)
        self._started_at: Optional[float] = None

    # ---- lifecycle hooks --------------------------------------------------

    def _on_initialize(self) -> None:
        _log.info("AIProviderRuntime: initialized")

    def _on_start(self) -> None:
        self._started_at = time.time()
        _log.info("AIProviderRuntime: started")

    def _on_stop(self) -> None:
        _log.info(
            f"AIProviderRuntime: stopped "
            f"(providers={self._registry.count()})"
        )

    # ---- public API -------------------------------------------------------

    def register_provider(self, extension: AIProviderExtension) -> ProviderProfile:
        return self._manager.register(extension)

    def deregister_provider(self, provider_id: str) -> None:
        self._manager.deregister(provider_id)

    def select_provider(
        self,
        capability: ProviderCapabilityType,
    ) -> Optional[AIProviderExtension]:
        """Resolve and select one provider for ``capability``."""
        candidates = self._resolver.resolve(capability)
        return self._selector.select(capability, candidates)

    def can_serve(self, capability: ProviderCapabilityType) -> bool:
        return self._resolver.can_serve(capability)

    @property
    def manager(self) -> ProviderManager:
        return self._manager

    @property
    def registry(self) -> ProviderRegistry:
        return self._registry

    @property
    def resolver(self) -> ProviderResolver:
        return self._resolver

    def status(self) -> Dict[str, Any]:
        return {
            "system_id":       self.SYSTEM_ID,
            "lifecycle_state": self.lifecycle_state.value,
            "provider_count":  self._registry.count(),
            "active_count":    self._manager.active_count(),
            "profiles":        [p.to_dict() for p in self._manager.all_profiles()],
            "uptime_s":        (time.time() - self._started_at) if self._started_at else 0.0,
        }

    def __repr__(self) -> str:
        return (
            f"<AIProviderRuntime "
            f"state={self.lifecycle_state.value!r} "
            f"providers={self._registry.count()}>"
        )
