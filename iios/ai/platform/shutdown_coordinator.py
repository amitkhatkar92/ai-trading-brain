"""
shutdown_coordinator.py — iios.ai.platform
==========================================
Performs deterministic, best-effort shutdown of all registered platforms
in REVERSE startup order.

Shutdown is best-effort: a failure to stop one platform is logged and
recorded but does not prevent other platforms from shutting down.

F0.1 Critical Architecture Resolution — R-001 Platform Bootstrap
"""
from __future__ import annotations

import logging
import time
from typing import List

from .platform_registry import PlatformRegistry
from .platform_types import PlatformPhase, PlatformStartupResult
from .startup_coordinator import CircularDependencyError, StartupCoordinator

__all__ = ["ShutdownCoordinator"]

_log = logging.getLogger(__name__)


class ShutdownCoordinator:
    """
    Stops all registered platforms in reverse startup order.

    Shutdown is best-effort — exceptions from individual gateway.stop()
    calls are caught, logged, and returned as failure results, but do
    not abort the remaining shutdown sequence.

    Usage::

        coordinator = ShutdownCoordinator(registry)
        results = coordinator.stop_all()
    """

    def __init__(self, registry: PlatformRegistry) -> None:
        self._registry           = registry
        self._startup_coordinator = StartupCoordinator(registry)

    def stop_all(self) -> List[PlatformStartupResult]:
        """
        Stop all running platforms in reverse dependency order.

        Returns a list of :class:`PlatformStartupResult` in shutdown order
        (reverse of the startup batches).
        """
        try:
            order = self._startup_coordinator.resolve_startup_order()
            # Reverse batch list — within each reversed batch keep priority order
            shutdown_batches = list(reversed(order.batches))
        except (CircularDependencyError, Exception) as exc:
            # Fallback: stop in reverse registration order if resolution fails
            _log.warning(
                "Could not resolve startup order for shutdown (%s) — "
                "using reverse-registration order",
                exc,
            )
            all_ids = list(reversed(self._registry.list_ids()))
            shutdown_batches = [tuple(all_ids)]

        results: List[PlatformStartupResult] = []
        for batch in shutdown_batches:
            for platform_id in batch:
                phase = self._registry.get_phase(platform_id)
                if phase.is_terminal():
                    # Already stopped/failed — record without calling gateway
                    results.append(
                        PlatformStartupResult.stopped(platform_id, 0.0)
                    )
                    continue
                results.append(self._stop_one(platform_id))

        return results

    def _stop_one(self, platform_id: str) -> PlatformStartupResult:
        """Attempt to stop a single platform and record the outcome."""
        gateway = self._registry.get_gateway(platform_id)
        self._registry.set_phase(platform_id, PlatformPhase.STOPPING)
        t0 = time.monotonic()
        try:
            if gateway is not None and hasattr(gateway, "stop"):
                gateway.stop()
            self._registry.set_phase(platform_id, PlatformPhase.STOPPED)
            elapsed = (time.monotonic() - t0) * 1000
            _log.info("Platform %r stopped in %.1f ms", platform_id, elapsed)
            return PlatformStartupResult.stopped(platform_id, elapsed)
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            error   = str(exc)
            _log.error("Platform %r failed to stop cleanly: %s", platform_id, error)
            self._registry.set_phase(platform_id, PlatformPhase.FAILED)
            return PlatformStartupResult.failure(platform_id, elapsed, error)
