"""
provider_resolver.py -- iios.ai.foundation.provider
====================================================
ProviderResolver -- capability-based provider discovery.
ProviderSelector -- strategy-based provider routing.

A1 AI Foundation -- Phase 3, Provider Runtime
"""
from __future__ import annotations

import itertools
import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .provider_capabilities import AIProviderCapabilities
from .provider_constants    import ProviderCapabilityType, ProviderSelectionStrategy
from .provider_extensions   import AIProviderExtension
from .provider_registry     import ProviderRegistry

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# ProviderResolver -- capability discovery
# ---------------------------------------------------------------------------

class ProviderResolver:
    """
    Resolves a required capability to a list of candidate providers.

    Resolution is purely capability-based; no cost or load information
    is considered here (that is :class:`ProviderSelector`'s job).

    Usage::

        resolver = ProviderResolver(registry)
        candidates = resolver.resolve(ProviderCapabilityType.CHAT)
    """

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    def resolve(
        self,
        capability: ProviderCapabilityType,
        *,
        active_only: bool = True,
    ) -> List[AIProviderExtension]:
        """
        Return all registered providers that support ``capability``.

        Returns an empty list if no providers match.
        """
        return self._registry.find_for_capability(capability, active_only=active_only)

    def resolve_first(
        self,
        capability: ProviderCapabilityType,
        *,
        active_only: bool = True,
    ) -> Optional[AIProviderExtension]:
        """Return the first matching provider, or None."""
        candidates = self.resolve(capability, active_only=active_only)
        return candidates[0] if candidates else None

    def can_serve(self, capability: ProviderCapabilityType) -> bool:
        """Return True iff at least one active provider supports ``capability``."""
        return len(self.resolve(capability)) > 0

    def available_capabilities(self) -> List[ProviderCapabilityType]:
        """Return the union of all capabilities across all active providers."""
        caps = set()
        for profile in self._registry.all_profiles():
            caps.update(profile.capabilities.capabilities)
        return list(caps)


# ---------------------------------------------------------------------------
# ProviderSelector -- routing strategy
# ---------------------------------------------------------------------------

class ProviderSelector:
    """
    Selects one provider from a candidate list using a
    :class:`ProviderSelectionStrategy`.

    Strategies
    ----------
    FIRST_AVAILABLE :      Return the first candidate (lowest latency).
    ROUND_ROBIN :          Rotate through candidates in order.
    CAPABILITY_BEST_MATCH: Prefer providers whose capability set most
                           closely matches the requested set.
    LEAST_LOADED :         Prefer providers with the fewest recent requests
                           (requires metrics integration; falls back to FIRST_AVAILABLE).

    Usage::

        selector = ProviderSelector(strategy=ProviderSelectionStrategy.ROUND_ROBIN)
        provider = selector.select(capability, candidates)
    """

    def __init__(
        self,
        strategy: ProviderSelectionStrategy = ProviderSelectionStrategy.FIRST_AVAILABLE,
    ) -> None:
        self._strategy = strategy
        self._lock     = threading.Lock()
        self._rr_idx:  Dict[str, itertools.count] = {}  # key -> counter

    def select(
        self,
        capability:  ProviderCapabilityType,
        candidates:  List[AIProviderExtension],
    ) -> Optional[AIProviderExtension]:
        """
        Select one provider from ``candidates`` for ``capability``.

        Returns None if the list is empty.
        """
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        if self._strategy == ProviderSelectionStrategy.ROUND_ROBIN:
            return self._round_robin(capability.value, candidates)

        if self._strategy == ProviderSelectionStrategy.CAPABILITY_BEST_MATCH:
            return self._best_match(capability, candidates)

        # FIRST_AVAILABLE and LEAST_LOADED (no load info -> first)
        return candidates[0]

    # ---- internals --------------------------------------------------------

    def _round_robin(
        self,
        key:        str,
        candidates: List[AIProviderExtension],
    ) -> AIProviderExtension:
        with self._lock:
            if key not in self._rr_idx:
                self._rr_idx[key] = itertools.count()
            idx = next(self._rr_idx[key]) % len(candidates)
        return candidates[idx]

    def _best_match(
        self,
        capability: ProviderCapabilityType,
        candidates: List[AIProviderExtension],
    ) -> AIProviderExtension:
        """Prefer provider whose capability set is the smallest superset."""
        def score(ext: AIProviderExtension) -> int:
            return len(ext.capabilities.capabilities)
        return min(candidates, key=score)
