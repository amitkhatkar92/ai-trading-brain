"""
ai_foundation_gateway.py — iios.ai.foundation.gateway
======================================================
:class:`AIFoundationGateway` — the single public entry point for the
entire A1 AI Foundation module.

All AI modules (A2–A10) interact with the AI Platform exclusively through
this gateway.  No AI module imports from ``iios.ai.foundation.lifecycle``,
``iios.ai.foundation.adapters``, or any other internal A1 sub-package.

Design
------
* Inherits :class:`AILifecycleAwareMixin` — full lifecycle management.
* Owns the :class:`AIProviderRegistry` — provider registration lives here.
* Owns the :class:`AIEventBus` — all inter-module events flow through it.
* Holds the active :class:`AIConfiguration` — loaded once on initialisation.
* Exposes a minimal, stable public API — this is the V1 contract for A1.

Public API (stable, V1 contract)
---------------------------------
``initialize()`` / ``start()`` / ``stop()`` / ``restart()``  — lifecycle
``health()``     — structured health dict
``status()``     — structured status dict
``statistics()`` — execution counters
``snapshot()``   — immutable :class:`FoundationSnapshot`
``register_provider(provider)``   — register an AI provider
``deregister_provider(pid)``      — remove a provider
``event_bus``    — access the event bus (publish / subscribe)
``configuration`` — access the active configuration
``provider_registry`` — access the provider registry

A1 AI Foundation — Phase 3, Module 1  |  M6 Gateway
"""
from __future__ import annotations

import time
import threading
from typing import Any, Dict, Optional

from iios.common.logging.logging_manager import get_logger

from ..lifecycle.ai_foundation_lifecycle import AILifecycleAwareMixin
from ..lifecycle.constants               import AILifecycleState, VERSION
from ..adapters.ai_provider              import AIProvider
from ..adapters.ai_provider_registry     import AIProviderRegistry
from ..adapters.ai_configuration         import (
    AIConfiguration,
    AIConfigurationProvider,
    EnvironmentAIConfigurationProvider,
)
from ..adapters.ai_event_bus             import AIEventBus, LocalAIEventBus
from ..snapshot.foundation_snapshot      import (
    FoundationSnapshot,
    ProviderStatusEntry,
)

_log = get_logger(__name__)


class AIFoundationGateway(AILifecycleAwareMixin):
    """
    Single public entry point for the A1 AI Foundation module.

    All A2–A10 modules that need AI model access, configuration, or
    inter-module events must obtain them through this gateway.

    Intended use
    ------------
    One singleton instance is created at system startup and shared::

        from iios.ai.foundation.gateway import AIFoundationGateway
        gateway = AIFoundationGateway()
        gateway.initialize()
        gateway.start()

        # Register a provider (done by A2 Model Management)
        gateway.register_provider(my_openai_adapter)

        # Publish an event (done by any AI module)
        gateway.event_bus.emit("ai.model.selected", source_id="a2", payload={...})

    Parameters
    ----------
    config_provider : Optional :class:`AIConfigurationProvider`.
        Defaults to :class:`EnvironmentAIConfigurationProvider`.
    event_bus :       Optional :class:`AIEventBus`.
        Defaults to a :class:`LocalAIEventBus` instance.
    """

    SYSTEM_ID  : str = "iios:ai:foundation:gateway"
    VERSION    : str = VERSION
    MODULE_ID  : str = "A1"
    MODULE_NAME: str = "AI Foundation"
    API_VERSION: str = "v1"
    DESCRIPTION: str = "AI Platform foundation — lifecycle management, provider abstraction, events, configuration"
    STATUS     : str = "stable"

    def __init__(
        self,
        config_provider: Optional[AIConfigurationProvider] = None,
        event_bus:       Optional[AIEventBus]              = None,
    ) -> None:
        self._config_provider: AIConfigurationProvider = (
            config_provider or EnvironmentAIConfigurationProvider()
        )
        self._event_bus: AIEventBus       = event_bus or LocalAIEventBus()
        self._registry:  AIProviderRegistry = AIProviderRegistry()
        self._config:    Optional[AIConfiguration] = None
        self._started_at: Optional[float] = None
        self._lock:      threading.Lock   = threading.Lock()

        # Cumulative counters
        self._total_requests: int = 0
        self._total_errors:   int = 0

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    def _on_initialize(self) -> None:
        _log.info(f"AIFoundationGateway._on_initialize: loading configuration")
        self._config = self._config_provider.load()
        _log.info(
            f"AIFoundationGateway: configuration loaded "
            f"(env={self._config.environment!r}, "
            f"providers={list(self._config.credentials.keys())})"
        )

    def _on_start(self) -> None:
        self._started_at = time.time()
        _log.info(f"AIFoundationGateway: started (v{self.VERSION})")

    def _on_stop(self) -> None:
        _log.info(
            f"AIFoundationGateway: stopped "
            f"(total_requests={self._total_requests}, "
            f"total_errors={self._total_errors})"
        )

    def _on_pause(self) -> None:
        _log.info("AIFoundationGateway: paused")

    def _on_resume(self) -> None:
        _log.info("AIFoundationGateway: resumed")

    # ── Provider management ───────────────────────────────────────────────────

    def register_provider(self, provider: AIProvider) -> None:
        """
        Register an AI provider adapter.

        Typically called by A2 Model Management during its initialization.
        """
        self._registry.register(provider)
        _log.info(
            f"AIFoundationGateway: registered provider "
            f"provider_id={provider.provider_id!r} "
            f"model_id={provider.model_id!r}"
        )

    def deregister_provider(self, provider_id: str) -> None:
        """Remove a provider from the registry."""
        self._registry.deregister(provider_id)
        _log.info(f"AIFoundationGateway: deregistered provider {provider_id!r}")

    # ── Public properties ─────────────────────────────────────────────────────

    @property
    def event_bus(self) -> AIEventBus:
        """The AI Platform event bus (publish / subscribe)."""
        return self._event_bus

    @property
    def configuration(self) -> Optional[AIConfiguration]:
        """The active :class:`AIConfiguration`, or ``None`` before initialization."""
        return self._config

    @property
    def provider_registry(self) -> AIProviderRegistry:
        """The :class:`AIProviderRegistry` containing all registered providers."""
        return self._registry

    # ── Observability ─────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """
        Return a structured health dictionary.

        Suitable for health-check endpoints and monitoring dashboards.
        """
        state = self.lifecycle_state
        providers = self._registry.all_providers()
        provider_health = {
            p.provider_id: p.health().value
            for p in providers
        }
        return {
            "module_id":      self.SYSTEM_ID,
            "state":          state.value,
            "is_running":     (state == AILifecycleState.RUNNING),
            "provider_count": len(providers),
            "provider_health": provider_health,
            "total_requests": self._total_requests,
            "total_errors":   self._total_errors,
            "uptime_s":       self._uptime_s(),
            "version":        self.VERSION,
        }

    def status(self) -> Dict[str, Any]:
        """Return a verbose status dictionary (superset of health)."""
        h = self.health()
        h["configuration"] = (
            self._config.to_dict() if self._config else None
        )
        h["providers"] = [
            p.info.to_dict()
            for p in self._registry.all_providers()
        ]
        return h

    def statistics(self) -> Dict[str, Any]:
        """Return cumulative execution counters."""
        return {
            "total_requests": self._total_requests,
            "total_errors":   self._total_errors,
            "error_rate": (
                round(self._total_errors / self._total_requests, 4)
                if self._total_requests > 0 else 0.0
            ),
            "uptime_s": self._uptime_s(),
        }

    def snapshot(self) -> FoundationSnapshot:
        """Return an immutable :class:`FoundationSnapshot`."""
        providers = [
            ProviderStatusEntry(
                provider_id  = p.info.provider_id,
                model_id     = p.info.model_id,
                health       = p.health(),
                capabilities = tuple(c.value for c in p.info.capabilities),
            )
            for p in self._registry.all_providers()
        ]
        return FoundationSnapshot.create(
            module_id       = self.SYSTEM_ID,
            lifecycle_state = self.lifecycle_state,
            providers       = providers,
            active_sessions = 0,  # populated by M1 registry in full impl
            total_requests  = self._total_requests,
            total_errors    = self._total_errors,
            uptime_s        = self._uptime_s(),
            governance_tier = (
                self._config.governance_tier if self._config else "unknown"
            ),
            environment     = (
                self._config.environment     if self._config else "unknown"
            ),
        )

    # ── Counter helpers ───────────────────────────────────────────────────────

    def record_request(self, *, error: bool = False) -> None:
        """Increment request and optional error counters (called by pipeline)."""
        with self._lock:
            self._total_requests += 1
            if error:
                self._total_errors += 1

    # ── Internals ──────────────────────────────────────────────────────────────

    def _uptime_s(self) -> float:
        if self._started_at is None:
            return 0.0
        return time.time() - self._started_at

    def __repr__(self) -> str:
        return (
            f"<AIFoundationGateway "
            f"state={self.lifecycle_state.value!r} "
            f"providers={self._registry.count()} "
            f"requests={self._total_requests}>"
        )
