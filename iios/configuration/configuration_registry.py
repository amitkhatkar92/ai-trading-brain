"""
iios/configuration/configuration_registry.py
==============================================
Registry of configuration providers, ordered by priority.

``ConfigurationRegistry`` stores all active providers, loads them in
priority order, and returns a merged dict ready for validation.

Architecture Reference: IIOS-CIS-001 INFRA-CFG-001
"""

from __future__ import annotations

import logging
from typing import Optional

from .configuration_exception import ConfigurationProviderError
from .configuration_merger import ConfigurationMerger
from .configuration_provider import ConfigurationProvider

logger = logging.getLogger(__name__)

__all__ = [
    "ConfigurationRegistry",
]


class ConfigurationRegistry:
    """Ordered collection of ``ConfigurationProvider`` instances.

    Providers are stored sorted by ascending priority — when ``load_all()``
    is called they are merged in order (lowest priority → highest priority),
    so higher-priority providers win on conflicts.
    """

    def __init__(
        self,
        merger: Optional[ConfigurationMerger] = None,
    ) -> None:
        self._providers: list[ConfigurationProvider] = []
        self._merger = merger or ConfigurationMerger()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, provider: ConfigurationProvider) -> "ConfigurationRegistry":
        """Add a provider. Duplicate names are replaced silently."""
        self._providers = [p for p in self._providers if p.name != provider.name]
        self._providers.append(provider)
        self._providers.sort(key=lambda p: p.priority)
        logger.debug("Registered provider %r (priority=%d)", provider.name, provider.priority)
        return self  # Fluent

    def unregister(self, name: str) -> bool:
        """Remove a provider by name. Returns True if it was present."""
        before = len(self._providers)
        self._providers = [p for p in self._providers if p.name != name]
        removed = len(self._providers) < before
        if removed:
            logger.debug("Unregistered provider %r", name)
        return removed

    def get_provider(self, name: str) -> Optional[ConfigurationProvider]:
        """Return the provider with the given name, or None."""
        for p in self._providers:
            if p.name == name:
                return p
        return None

    def has_provider(self, name: str) -> bool:
        return self.get_provider(name) is not None

    @property
    def providers(self) -> list[ConfigurationProvider]:
        """Providers ordered by ascending priority."""
        return list(self._providers)

    @property
    def provider_names(self) -> list[str]:
        return [p.name for p in self._providers]

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_all(
        self,
        skip_errors: bool = True,
    ) -> dict:
        """Load all enabled providers and merge their results.

        Providers are called in ascending priority order; later (higher
        priority) providers override earlier ones on conflict.

        Args:
            skip_errors: If True, providers that raise are skipped with a
                         warning. If False, errors propagate immediately.

        Returns:
            Merged configuration dict.
        """
        sources = []
        loaded_names: list[str] = []

        for provider in self._providers:
            if not provider.enabled:
                continue
            try:
                data = provider.load()
                sources.append(data)
                loaded_names.append(provider.name)
            except ConfigurationProviderError as exc:
                if not skip_errors:
                    raise
                logger.warning("Provider %r skipped: %s", provider.name, exc)
            except Exception as exc:
                if not skip_errors:
                    raise ConfigurationProviderError(
                        f"Unexpected error from provider {provider.name!r}: {exc}",
                        provider=provider.name,
                    ) from exc
                logger.warning("Provider %r unexpected error (skipped): %s", provider.name, exc)

        merged = self._merger.merge(sources)
        logger.debug(
            "Registry loaded %d providers: %s",
            len(loaded_names),
            ", ".join(loaded_names),
        )
        return merged

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def describe(self) -> list[dict]:
        """Return a list of provider info dicts for diagnostics."""
        return [
            {
                "name": p.name,
                "priority": p.priority,
                "enabled": p.enabled,
                "type": type(p).__name__,
                "description": p.description,
            }
            for p in self._providers
        ]

    def __len__(self) -> int:
        return len(self._providers)

    def __repr__(self) -> str:
        return (
            f"ConfigurationRegistry("
            f"providers=[{', '.join(self.provider_names)}])"
        )
