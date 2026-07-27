"""
provider_registry.py -- iios.ai.foundation.provider
====================================================
ProviderRegistry -- thread-safe registry of active provider extensions.

Separate from adapters/ai_provider_registry.py which holds raw AIProvider
adapters. This registry holds ProviderExtension instances (the richer
runtime interface used by ExecutionRuntime).

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import time
import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .provider_capabilities  import AIProviderCapabilities, ProviderProfile
from .provider_constants     import ProviderCapabilityType, ProviderStatus, SCHEMA_VER
from .provider_extensions    import AIProviderExtension

_log = get_logger(__name__)


class ProviderEntry:
    """Mutable runtime entry in the provider registry."""

    def __init__(self, extension: AIProviderExtension) -> None:
        self.extension     = extension
        self.status        = ProviderStatus.REGISTERED
        self.registered_at = time.time()
        self.last_health   = time.time()
        self._lock         = threading.Lock()

    @property
    def provider_id(self) -> str:
        return self.extension.provider_id

    def set_status(self, status: ProviderStatus) -> None:
        with self._lock:
            self.status = status

    def profile(self) -> ProviderProfile:
        return ProviderProfile(
            provider_id   = self.provider_id,
            display_name  = self.provider_id,
            capabilities  = self.extension.capabilities,
            registered_at = self.registered_at,
        )


class ProviderRegistry:
    """
    Thread-safe registry of :class:`AIProviderExtension` instances.

    Responsibilities
    ----------------
    * Register / deregister provider extensions.
    * Look up by ID or capability.
    * Track provider status (ACTIVE / DEGRADED / UNAVAILABLE).
    * Return :class:`ProviderProfile` for observability.
    """

    def __init__(self) -> None:
        self._lock:      threading.Lock              = threading.Lock()
        self._entries:   Dict[str, ProviderEntry]    = {}

    # ---- registration -----------------------------------------------------

    def register(
        self,
        extension:    AIProviderExtension,
        activate:     bool = True,
    ) -> ProviderProfile:
        """
        Register a provider extension.

        Parameters
        ----------
        extension : Provider extension instance.
        activate :  If True, immediately set status to ACTIVE.

        Returns
        -------
        ProviderProfile
            Immutable profile of the registered provider.
        """
        entry = ProviderEntry(extension)
        if activate:
            entry.status = ProviderStatus.ACTIVE
        with self._lock:
            self._entries[extension.provider_id] = entry
        _log.info(
            f"ProviderRegistry: registered provider_id={extension.provider_id!r} "
            f"status={entry.status.value!r}"
        )
        return entry.profile()

    def deregister(self, provider_id: str) -> None:
        """Remove a provider from the registry."""
        with self._lock:
            entry = self._entries.pop(provider_id, None)
        if entry:
            _log.info(f"ProviderRegistry: deregistered provider_id={provider_id!r}")

    # ---- status management -----------------------------------------------

    def set_status(self, provider_id: str, status: ProviderStatus) -> None:
        """Update the runtime status of a registered provider."""
        with self._lock:
            entry = self._entries.get(provider_id)
        if entry:
            old = entry.status
            entry.set_status(status)
            if old != status:
                _log.info(
                    f"ProviderRegistry: status change "
                    f"provider_id={provider_id!r} {old.value}->{status.value}"
                )

    def get_status(self, provider_id: str) -> Optional[ProviderStatus]:
        with self._lock:
            entry = self._entries.get(provider_id)
        return entry.status if entry else None

    # ---- lookup -----------------------------------------------------------

    def get(self, provider_id: str) -> Optional[AIProviderExtension]:
        """Return the extension for ``provider_id``, or None."""
        with self._lock:
            entry = self._entries.get(provider_id)
        return entry.extension if entry else None

    def find_for_capability(
        self,
        capability:   ProviderCapabilityType,
        *,
        active_only:  bool = True,
    ) -> List[AIProviderExtension]:
        """
        Return all providers supporting ``capability``.

        Parameters
        ----------
        capability :  Required capability type.
        active_only : If True, exclude UNAVAILABLE providers.
        """
        with self._lock:
            entries = list(self._entries.values())
        result = []
        for e in entries:
            if active_only and e.status == ProviderStatus.UNAVAILABLE:
                continue
            if e.extension.capabilities.supports(capability):
                result.append(e.extension)
        return result

    def all_profiles(self) -> List[ProviderProfile]:
        with self._lock:
            return [e.profile() for e in self._entries.values()]

    def active_provider_ids(self) -> List[str]:
        with self._lock:
            return [
                pid for pid, e in self._entries.items()
                if e.status == ProviderStatus.ACTIVE
            ]

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def __repr__(self) -> str:
        return f"<ProviderRegistry providers={self.count()}>"
