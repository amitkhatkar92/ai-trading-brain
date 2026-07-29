"""
startup_coordinator.py — iios.ai.platform
==========================================
Resolves platform startup order via topological sort (Kahn's algorithm)
and drives ordered, dependency-safe startup of all registered platforms.

Circular dependency detection is strict: any cycle raises
:class:`CircularDependencyError` before a single platform is started.

F0.1 Critical Architecture Resolution — R-001 Platform Bootstrap
"""
from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any, Dict, List, Set, Tuple

from .platform_registry import PlatformRegistry
from .platform_types import (
    PlatformDescriptor,
    PlatformPhase,
    PlatformStartupResult,
    StartupOrder,
)

__all__ = ["StartupCoordinator", "CircularDependencyError"]

_log = logging.getLogger(__name__)


class CircularDependencyError(RuntimeError):
    """Raised when the platform dependency graph contains a cycle."""


class StartupCoordinator:
    """
    Resolves startup order and performs deterministic platform startup.

    Dependency Resolution
    ---------------------
    Uses Kahn's topological sort on the declared
    ``PlatformDescriptor.dependencies`` graph.  The result is a sequence
    of *batches*; all platforms in batch N are independent of each other
    and may start once all platforms in batch N-1 are running.

    Within each batch platforms are sorted by descending ``priority``
    so high-priority platforms start before low-priority ones.

    Failure Handling
    ----------------
    If a *required* (``optional=False``) platform fails, all platforms
    that directly or transitively depend on it are skipped with a
    "dependency failed" result.

    If an *optional* platform fails, the failure is logged but dependent
    platforms are not blocked.

    Usage::

        coordinator = StartupCoordinator(registry)
        order   = coordinator.resolve_startup_order()
        results = coordinator.start_all()
    """

    def __init__(self, registry: PlatformRegistry) -> None:
        self._registry = registry

    # ── dependency resolution ─────────────────────────────────────────────────

    def resolve_startup_order(self) -> StartupOrder:
        """
        Compute a valid startup order for all registered platforms.

        Returns
        -------
        StartupOrder
            Batches of platform IDs where each batch may run after the
            previous batch has completed.

        Raises
        ------
        CircularDependencyError
            If the dependency graph contains a cycle.
        """
        descriptors: Dict[str, PlatformDescriptor] = {
            pid: self._registry.get_descriptor(pid)
            for pid in self._registry.list_ids()
        }

        # Build in-degree map and reverse adjacency (dependency → dependents)
        in_degree:  Dict[str, int]      = {pid: 0 for pid in descriptors}
        dependents: Dict[str, Set[str]] = {pid: set() for pid in descriptors}

        for pid, desc in descriptors.items():
            for dep_id in desc.dependencies:
                if dep_id not in descriptors:
                    _log.warning(
                        "Platform %r declares unknown dependency %r — ignoring",
                        pid, dep_id,
                    )
                    continue
                in_degree[pid] += 1
                dependents[dep_id].add(pid)

        # Kahn's algorithm — seed with zero-in-degree nodes
        queue: deque = deque(
            sorted(
                (pid for pid, deg in in_degree.items() if deg == 0),
                key=lambda p: -descriptors[p].priority,
            )
        )

        batches:   List[Tuple[str, ...]] = []
        processed: Set[str]              = set()

        while queue:
            # Collect every node currently at in-degree 0 as one batch
            batch_size = len(queue)
            batch: List[str] = []
            for _ in range(batch_size):
                pid = queue.popleft()
                batch.append(pid)
                processed.add(pid)
                for dep_pid in dependents[pid]:
                    in_degree[dep_pid] -= 1
                    if in_degree[dep_pid] == 0:
                        queue.append(dep_pid)

            # Sort batch by descending priority before adding
            batch.sort(key=lambda p: -descriptors[p].priority)
            batches.append(tuple(batch))

        if len(processed) != len(descriptors):
            cycle_pids = [pid for pid in descriptors if pid not in processed]
            raise CircularDependencyError(
                f"Circular dependency detected involving platforms: {cycle_pids}"
            )

        return StartupOrder(batches=tuple(batches), platform_count=len(descriptors))

    # ── startup execution ──────────────────────────────────────────────────────

    def start_all(self) -> List[PlatformStartupResult]:
        """
        Start all registered platforms in resolved dependency order.

        Returns an ordered list of :class:`PlatformStartupResult`.
        """
        order  = self.resolve_startup_order()
        failed : Set[str] = set()          # platforms that failed (non-optional)
        results: List[PlatformStartupResult] = []

        for batch in order.batches:
            for platform_id in batch:
                desc            = self._registry.get_descriptor(platform_id)
                blocking_failed = failed & desc.dependencies

                if blocking_failed:
                    msg = f"Required dependency failed: {blocking_failed}"
                    _log.warning("Skipping platform %r — %s", platform_id, msg)
                    result = PlatformStartupResult.failure(platform_id, 0.0, msg)
                    self._registry.set_phase(platform_id, PlatformPhase.FAILED)
                    results.append(result)
                    if not desc.optional:
                        failed.add(platform_id)
                    continue

                result = self._start_one(platform_id)
                results.append(result)
                if result.failed and not desc.optional:
                    failed.add(platform_id)

        return results

    def _start_one(self, platform_id: str) -> PlatformStartupResult:
        """Attempt to start a single platform and record the outcome."""
        gateway = self._registry.get_gateway(platform_id)
        self._registry.set_phase(platform_id, PlatformPhase.STARTING)
        t0 = time.monotonic()
        try:
            if gateway is not None and hasattr(gateway, "start"):
                gateway.start()
            self._registry.set_phase(platform_id, PlatformPhase.RUNNING)
            elapsed = (time.monotonic() - t0) * 1000
            _log.info("Platform %r started in %.1f ms", platform_id, elapsed)
            return PlatformStartupResult.success(platform_id, elapsed)
        except Exception as exc:
            elapsed = (time.monotonic() - t0) * 1000
            error   = str(exc)
            _log.error("Platform %r failed to start: %s", platform_id, error)
            self._registry.set_phase(platform_id, PlatformPhase.FAILED)
            return PlatformStartupResult.failure(platform_id, elapsed, error)
