"""iios/integration/providers/provider_manager.py

Manages provider lifecycle: init, activate, deactivate, shutdown.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from iios.integration.integration_constants import ProviderStatus
from iios.integration.integration_exceptions import ProviderInitializationError, ProviderNotFoundError
from iios.integration.providers.base_provider import BaseProvider
from iios.integration.providers.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class ProviderManager:
    """
    Wraps ProviderRegistry with lifecycle management.

    Responsible for calling initialize() / shutdown() on providers
    and maintaining a consistent status picture.
    """

    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self._registry = registry or ProviderRegistry()
        self._lock     = threading.RLock()

    # ── Registration ──────────────────────────────────────────────────────────

    async def register(self, provider: BaseProvider) -> None:
        self._registry.register(provider)
        logger.info("ProviderManager: registered '%s'", provider.provider_id)

    async def unregister(self, provider_id: str) -> None:
        p = self._registry.get(provider_id)
        if p.is_active():
            await self.deactivate(provider_id)
        self._registry.unregister(provider_id)
        logger.info("ProviderManager: unregistered '%s'", provider_id)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def activate(self, provider_id: str) -> None:
        p = self._registry.get(provider_id)
        try:
            await p.initialize()
            logger.info("ProviderManager: activated '%s'", provider_id)
        except Exception as exc:
            raise ProviderInitializationError(
                f"Provider '{provider_id}' failed to initialize: {exc}"
            ) from exc

    async def deactivate(self, provider_id: str) -> None:
        p = self._registry.get(provider_id)
        await p.shutdown()
        logger.info("ProviderManager: deactivated '%s'", provider_id)

    async def activate_all(self) -> dict[str, str]:
        """Activate all registered providers. Returns {provider_id: error|'ok'}."""
        results: dict[str, str] = {}
        for p in self._registry.all_providers():
            try:
                await self.activate(p.provider_id)
                results[p.provider_id] = "ok"
            except Exception as exc:
                results[p.provider_id] = str(exc)
        return results

    async def shutdown_all(self) -> None:
        tasks = []
        for p in self._registry.active_providers():
            tasks.append(self.deactivate(p.provider_id))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # ── Delegation ────────────────────────────────────────────────────────────

    @property
    def registry(self) -> ProviderRegistry:
        return self._registry

    def get(self, provider_id: str) -> BaseProvider:
        return self._registry.get(provider_id)

    def has(self, provider_id: str) -> bool:
        return self._registry.has(provider_id)

    def all_providers(self) -> list[BaseProvider]:
        return self._registry.all_providers()

    def active_providers(self) -> list[BaseProvider]:
        return self._registry.active_providers()

    def providers_for_category(self, category: str, frequency: str | None = None) -> list[BaseProvider]:
        return self._registry.providers_for_category(category, frequency)

    def statistics(self) -> dict[str, Any]:
        return self._registry.statistics()
