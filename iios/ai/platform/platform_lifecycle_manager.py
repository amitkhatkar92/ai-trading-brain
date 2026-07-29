"""
platform_lifecycle_manager.py — iios.ai.platform
=================================================
Unified lifecycle façade over all registered platforms.

Provides single-platform and bulk operations:
  start_all()         — ordered startup of all platforms
  stop_all()          — ordered shutdown of all platforms
  start_platform()    — start a single platform
  stop_platform()     — stop a single platform
  restart_platform()  — stop then start a single platform
  health()            — aggregated health dict
  status()            — PlatformStatus snapshot

F0.1 Critical Architecture Resolution — R-001 Platform Bootstrap
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from .health_coordinator      import HealthCoordinator
from .platform_registry       import PlatformRegistry
from .platform_types          import PlatformPhase, PlatformStartupResult, PlatformStatus
from .shutdown_coordinator    import ShutdownCoordinator
from .startup_coordinator     import StartupCoordinator

__all__ = ["PlatformLifecycleManager"]

_log = logging.getLogger(__name__)


class PlatformLifecycleManager:
    """
    Unified lifecycle façade over the :class:`PlatformRegistry`.

    Delegates startup ordering to :class:`StartupCoordinator`, shutdown
    ordering to :class:`ShutdownCoordinator`, and health aggregation to
    :class:`HealthCoordinator`.

    Usage::

        registry = PlatformRegistry()
        registry.register(PlatformDescriptor.create("A1:foundation"), gw_a1)
        registry.register(
            PlatformDescriptor.create(
                "A2:model_management",
                dependencies=frozenset(["A1:foundation"]),
            ),
            gw_a2,
        )

        mgr     = PlatformLifecycleManager(registry)
        results = mgr.start_all()
        status  = mgr.status()
        mgr.stop_all()
    """

    def __init__(self, registry: PlatformRegistry) -> None:
        self._registry             = registry
        self._startup              = StartupCoordinator(registry)
        self._shutdown             = ShutdownCoordinator(registry)
        self._health               = HealthCoordinator(registry)
        self._last_startup_results : List[PlatformStartupResult] = []

    # ── bulk operations ───────────────────────────────────────────────────────

    def start_all(self) -> List[PlatformStartupResult]:
        """Start all registered platforms in dependency order."""
        results = self._startup.start_all()
        self._last_startup_results = list(results)
        return results

    def stop_all(self) -> List[PlatformStartupResult]:
        """Stop all platforms in reverse dependency order."""
        return self._shutdown.stop_all()

    # ── single-platform operations ────────────────────────────────────────────

    def start_platform(self, platform_id: str) -> PlatformStartupResult:
        """Start a single registered platform."""
        return self._startup._start_one(platform_id)

    def stop_platform(self, platform_id: str) -> PlatformStartupResult:
        """Stop a single registered platform."""
        return self._shutdown._stop_one(platform_id)

    def restart_platform(self, platform_id: str) -> PlatformStartupResult:
        """Stop then re-start a single platform."""
        self._shutdown._stop_one(platform_id)
        return self._startup._start_one(platform_id)

    # ── observability ─────────────────────────────────────────────────────────

    def status(self) -> PlatformStatus:
        """Return a :class:`PlatformStatus` snapshot of the current state."""
        phases = self._registry.all_phases()
        return PlatformStatus.create(phases=phases, results=self._last_startup_results)

    def health(self) -> Dict[str, Any]:
        """Return aggregated health for all registered platforms."""
        individual = self._health.check_all()
        aggregate  = self._health.aggregate_status()
        return {
            "aggregate": aggregate,
            "platforms": individual,
        }
