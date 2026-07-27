"""
ai_provider_registry.py — iios.ai.foundation.adapters
======================================================
:class:`AIProviderRegistry` — thread-safe registry of active AI provider
adapters.

All AI modules route model calls through the registry rather than holding
direct provider references.  A2 Model Management owns the registry
instance; it is surfaced to other modules via the M6 Gateway.

A1 AI Foundation — Phase 3, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Sequence

from .ai_provider import AIProvider, AIProviderInfo
from .constants    import AICapability, AIProviderHealth
from .exceptions   import AIProviderNotFoundError, AICapabilityNotSupportedError


class AIProviderRegistry:
    """
    Thread-safe registry of :class:`AIProvider` instances.

    Responsibilities
    ----------------
    * Register / deregister provider adapters.
    * Look up providers by ID or by required capability.
    * Filter providers by health status.

    This registry is the single source of truth for which AI providers
    are available at any given moment.
    """

    def __init__(self) -> None:
        self._lock:      threading.Lock              = threading.Lock()
        self._providers: Dict[str, AIProvider]       = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, provider: AIProvider) -> None:
        """Register a provider, replacing any existing entry with the same ID."""
        with self._lock:
            self._providers[provider.provider_id] = provider

    def deregister(self, provider_id: str) -> None:
        """Remove the provider identified by ``provider_id`` (no-op if absent)."""
        with self._lock:
            self._providers.pop(provider_id, None)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, provider_id: str) -> AIProvider:
        """
        Return the provider for ``provider_id``.

        Raises
        ------
        AIProviderNotFoundError
            If the provider is not registered.
        """
        with self._lock:
            provider = self._providers.get(provider_id)
        if provider is None:
            raise AIProviderNotFoundError(provider_id)
        return provider

    def find(self, provider_id: str) -> Optional[AIProvider]:
        """Return the provider for ``provider_id``, or ``None`` if not found."""
        with self._lock:
            return self._providers.get(provider_id)

    # ── Capability routing ────────────────────────────────────────────────────

    def providers_for(
        self,
        capability: AICapability,
        *,
        healthy_only: bool = True,
    ) -> List[AIProvider]:
        """
        Return all registered providers that support ``capability``.

        Parameters
        ----------
        capability :   Required capability.
        healthy_only : If ``True`` (default), exclude providers whose
                       ``health()`` returns ``UNHEALTHY``.

        Returns
        -------
        List[AIProvider]
            Providers in registration order.
        """
        with self._lock:
            candidates = list(self._providers.values())

        result = []
        for p in candidates:
            if not p.info.supports(capability):
                continue
            if healthy_only and p.health() == AIProviderHealth.UNHEALTHY:
                continue
            result.append(p)
        return result

    def first_for(
        self,
        capability: AICapability,
        *,
        healthy_only: bool = True,
    ) -> AIProvider:
        """
        Return the first healthy provider that supports ``capability``.

        Raises
        ------
        AICapabilityNotSupportedError
            If no qualifying provider is available.
        """
        providers = self.providers_for(capability, healthy_only=healthy_only)
        if not providers:
            raise AICapabilityNotSupportedError(
                provider_id = "(none)",
                capability  = capability.value,
            )
        return providers[0]

    # ── Introspection ─────────────────────────────────────────────────────────

    def all_providers(self) -> List[AIProvider]:
        with self._lock:
            return list(self._providers.values())

    def provider_ids(self) -> List[str]:
        with self._lock:
            return list(self._providers.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._providers)

    def all_info(self) -> List[AIProviderInfo]:
        """Return the :class:`AIProviderInfo` for every registered provider."""
        with self._lock:
            return [p.info for p in self._providers.values()]

    def __repr__(self) -> str:
        return f"<AIProviderRegistry providers={self.count()}>"
