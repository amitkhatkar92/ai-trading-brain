"""iios/investment/strategy/lifecycle/resource_manager.py
Resource management facade — allocation + utilisation tracking.

Usage:
    with resource_manager.allocate("strat-id") as ticket:
        run_strategy()   # ticket released automatically on exit
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from iios.investment.strategy.lifecycle.resource_allocator import (
    AllocationError,
    AllocationTicket,
    ResourceAllocator,
)
from iios.investment.strategy.lifecycle.resource_limits import ResourceLimits
from iios.investment.strategy.lifecycle.resource_statistics import (
    ResourceSnapshot,
    ResourceStatistics,
)

logger = logging.getLogger(__name__)


class ResourceManager:
    """
    Manages resource allocation and utilisation tracking.

    Combines ResourceAllocator (admission control + tickets) and
    ResourceStatistics (rolling usage snapshots) under one API.
    """

    def __init__(self, limits: Optional[ResourceLimits] = None) -> None:
        self._limits = limits or ResourceLimits.standard()
        self._allocator = ResourceAllocator(self._limits)
        self._statistics = ResourceStatistics()

    # ── Context-manager allocation ────────────────────────────────────────────

    @contextmanager
    def allocate(
        self,
        strategy_id: str,
        threads: int = 1,
        cpu_weight: float = 0.0,
    ) -> Generator[AllocationTicket, None, None]:
        """
        Grant and automatically release a resource allocation ticket.

        Raises AllocationError if resource limits are exhausted.
        """
        ticket = self._allocator.request(strategy_id, threads, cpu_weight)
        self._record_snapshot()
        try:
            yield ticket
        finally:
            self._allocator.release(ticket)
            self._record_snapshot()

    # ── Admission probe ───────────────────────────────────────────────────────

    def can_allocate(self) -> bool:
        """Return True if a new strategy can be admitted right now."""
        try:
            probe = self._allocator.request("__probe__", threads=0, cpu_weight=0.0)
            self._allocator.release(probe)
            return True
        except AllocationError:
            return False

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def active_count(self) -> int:
        return self._allocator.active_count

    @property
    def utilization(self) -> float:
        return self._allocator.utilization

    @property
    def limits(self) -> ResourceLimits:
        return self._limits

    @property
    def statistics(self) -> ResourceStatistics:
        return self._statistics

    @property
    def allocator(self) -> ResourceAllocator:
        """Direct access to the allocator (for engine internals)."""
        return self._allocator

    def snapshot(self) -> ResourceSnapshot:
        """Return a point-in-time resource snapshot."""
        return ResourceSnapshot(
            thread_count=self._allocator.active_count,
            active_strategies=self._allocator.active_count,
            total_workers=self._limits.max_thread_pool_workers or 64,
        )

    # ── Internal ──────────────────────────────────────────────────────────────

    def _record_snapshot(self) -> None:
        snap = self.snapshot()
        self._statistics.record(snap)
