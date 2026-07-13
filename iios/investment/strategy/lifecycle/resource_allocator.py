"""iios/investment/strategy/lifecycle/resource_allocator.py
Resource allocation tickets and admission control.
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from iios.investment.strategy.lifecycle.resource_limits import ResourceLimits


class AllocationError(Exception):
    """Raised when resources cannot be allocated due to limit enforcement."""


@dataclass
class AllocationTicket:
    """
    Token representing a granted resource allocation for one strategy execution.

    Must be released (via ResourceAllocator.release()) after execution
    completes, whether it succeeds or fails.
    """

    ticket_id: str = field(
        default_factory=lambda: f"tkt-{uuid.uuid4().hex[:8]}"
    )
    strategy_id: str = ""
    allocated_threads: int = 1
    cpu_weight: float = 0.0
    granted_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    released_at: Optional[datetime] = None

    @property
    def is_released(self) -> bool:
        return self.released_at is not None

    def release(self) -> None:
        if not self.is_released:
            self.released_at = datetime.now(timezone.utc)


class ResourceAllocator:
    """
    Grants and releases resource allocation tickets.

    Enforces:
      - max_concurrent_strategies: ceiling on simultaneous executions
      - admission_threshold: fraction of total_workers considered "full"
      - cpu_weight_limit: aggregate CPU weight ceiling (0 = unlimited)
    """

    def __init__(self, limits: ResourceLimits) -> None:
        self._limits = limits
        self._lock = threading.RLock()
        self._active_tickets: Dict[str, AllocationTicket] = {}
        self._total_workers = max(limits.max_thread_pool_workers, 1)

    def request(
        self,
        strategy_id: str,
        threads: int = 1,
        cpu_weight: float = 0.0,
    ) -> AllocationTicket:
        """
        Request a resource allocation ticket.

        Raises AllocationError if any limit would be exceeded.
        """
        with self._lock:
            active = len(self._active_tickets)

            # Concurrent strategies ceiling
            max_conc = self._limits.max_concurrent_strategies
            if max_conc and active >= max_conc:
                raise AllocationError(
                    f"Max concurrent strategies ({max_conc}) reached "
                    f"(active={active})"
                )

            # Admission threshold
            util = active / self._total_workers
            if util >= self._limits.admission_threshold:
                raise AllocationError(
                    f"Admission threshold ({self._limits.admission_threshold:.0%}) "
                    f"reached — current utilisation {util:.0%}"
                )

            # CPU weight ceiling
            cpu_limit = self._limits.cpu_weight_limit
            if cpu_limit > 0:
                current_weight = sum(
                    t.cpu_weight for t in self._active_tickets.values()
                )
                if current_weight + cpu_weight > cpu_limit:
                    raise AllocationError(
                        f"CPU weight limit ({cpu_limit}) would be exceeded "
                        f"(current={current_weight:.2f}, requested={cpu_weight:.2f})"
                    )

            ticket = AllocationTicket(
                strategy_id=strategy_id,
                allocated_threads=threads,
                cpu_weight=cpu_weight,
            )
            self._active_tickets[ticket.ticket_id] = ticket
            return ticket

    def release(self, ticket: AllocationTicket) -> None:
        """Release a previously granted ticket and free the slot."""
        with self._lock:
            ticket.release()
            self._active_tickets.pop(ticket.ticket_id, None)

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active_tickets)

    @property
    def utilization(self) -> float:
        with self._lock:
            return len(self._active_tickets) / self._total_workers

    def active_tickets(self) -> List[AllocationTicket]:
        with self._lock:
            return list(self._active_tickets.values())

    def is_strategy_allocated(self, strategy_id: str) -> bool:
        with self._lock:
            return any(
                t.strategy_id == strategy_id
                for t in self._active_tickets.values()
            )
