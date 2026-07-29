"""
iios_bootstrap.py — iios.ai.platform
======================================
:class:`IIOSBootstrap` — single entry point for bootstrapping the IIOS
AI Platform.

Resolves Enterprise Design Review finding R-001:
  "No platform-level bootstrap or lifecycle manager — ten gateways must
   be individually started with no dependency order enforcement."

Architecture Layer Order (from the Enterprise Design Review):
  Layer 0 — Core Trading Platform  (external; must be running before
                                    AI Platform starts)
  Layer 1 — AI Foundation          (A1 — no AI-platform dependencies)
  Layer 2 — AI Capabilities        (A2–A9 — each depends on A1)
  Layer 3 — AI Orchestrator        (A10 — depends on A1 and optionally
                                    uses A2–A9 via handler registration)
  Layer 4 — Future Enterprise Services
  Layer 5 — Applications
  Layer 6 — External Interfaces

Dependency declaration is the responsibility of the caller.  Register
each platform with the dependency list it requires, and
:class:`IIOSBootstrap` will resolve the correct start/stop order
automatically.

F0.1 Critical Architecture Resolution — R-001 Platform Bootstrap
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .platform_lifecycle_manager import PlatformLifecycleManager
from .platform_registry          import PlatformRegistry
from .platform_types             import (
    PlatformDescriptor,
    PlatformPhase,
    PlatformStatus,
)

__all__ = ["IIOSBootstrap"]

_log = logging.getLogger(__name__)

BOOTSTRAP_VERSION = "1.0.0"


class IIOSBootstrap:
    """
    Single entry point for bootstrapping all platforms in the IIOS AI
    Platform.

    Responsibilities
    ----------------
    - Discover registered platforms via :class:`PlatformRegistry`
    - Resolve startup dependency order (topological sort, circular-dependency
      detection) via :class:`StartupCoordinator`
    - Perform deterministic startup via :class:`StartupCoordinator`
    - Perform deterministic shutdown in reverse order via
      :class:`ShutdownCoordinator`
    - Execute health validation via :class:`HealthCoordinator`
    - Handle startup failures (optional platforms skip dependents;
      required failures abort dependents)
    - Produce :class:`PlatformStatus` snapshots

    Usage::

        bootstrap = IIOSBootstrap()

        # Register in any order — startup order is auto-resolved
        bootstrap.register(
            PlatformDescriptor.create("A1:foundation"),
            ai_foundation_gateway,
        )
        bootstrap.register(
            PlatformDescriptor.create(
                "A2:model_management",
                dependencies=frozenset(["A1:foundation"]),
            ),
            model_gateway,
        )
        bootstrap.register(
            PlatformDescriptor.create(
                "A10:orchestrator",
                dependencies=frozenset(["A1:foundation"]),
                priority=90,
            ),
            orchestrator_gateway,
        )

        # Start all in dependency order
        status = bootstrap.start()
        assert status.is_fully_operational

        # Health check
        health = bootstrap.health()

        # Graceful shutdown (reverse order)
        bootstrap.stop()
    """

    VERSION = BOOTSTRAP_VERSION

    def __init__(self) -> None:
        self._registry = PlatformRegistry()
        self._manager  = PlatformLifecycleManager(self._registry)
        self._started  = False

    # ── registration ──────────────────────────────────────────────────────────

    def register(
        self,
        descriptor: PlatformDescriptor,
        gateway:    Any = None,
    ) -> None:
        """Register a platform and its optional live gateway object.

        Must be called before :meth:`start`.  To add a platform after
        startup, call :meth:`stop`, register, then :meth:`start` again.
        """
        self._registry.register(descriptor, gateway)
        _log.debug(
            "Registered platform %r v%s (deps=%s optional=%s)",
            descriptor.platform_id,
            descriptor.version,
            sorted(descriptor.dependencies) or "none",
            descriptor.optional,
        )

    def deregister(self, platform_id: str) -> None:
        """Remove a platform from the registry."""
        self._registry.deregister(platform_id)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> PlatformStatus:
        """
        Start all registered platforms in dependency order.

        Raises :class:`~startup_coordinator.CircularDependencyError` if
        the dependency graph contains a cycle — before any platform starts.

        Returns a :class:`PlatformStatus` reflecting post-startup state.
        """
        count = len(self._registry.list_ids())
        _log.info(
            "IIOSBootstrap v%s — starting %d platform(s)", self.VERSION, count
        )

        self._manager.start_all()
        self._started = True

        status = self._manager.status()
        _log.info(
            "Startup complete — running=%d failed=%d stopped=%d",
            status.running_platforms,
            status.failed_platforms,
            status.stopped_platforms,
        )
        return status

    def stop(self) -> PlatformStatus:
        """
        Stop all running platforms in reverse dependency order.

        Returns a :class:`PlatformStatus` reflecting post-shutdown state.
        """
        _log.info("IIOSBootstrap — shutting down all platforms")
        self._manager.stop_all()
        self._started = False

        status = self._manager.status()
        _log.info(
            "Shutdown complete — stopped=%d failed=%d",
            status.stopped_platforms,
            status.failed_platforms,
        )
        return status

    def restart(self) -> PlatformStatus:
        """Stop all platforms then start them again in dependency order."""
        self.stop()
        return self.start()

    # ── observability ─────────────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """Return aggregated health report for all registered platforms.

        Returns a dict with:
        - ``"aggregate"`` — overall platform health string
        - ``"platforms"`` — per-platform health dicts
        """
        return self._manager.health()

    def status(self) -> PlatformStatus:
        """Return a :class:`PlatformStatus` snapshot of the current state."""
        return self._manager.status()

    # ── properties ────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        """True after :meth:`start` has been called and :meth:`stop` has not."""
        return self._started

    @property
    def platform_count(self) -> int:
        """Number of registered platforms."""
        return len(self._registry.list_ids())
