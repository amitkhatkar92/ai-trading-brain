"""iios/execution/oms/order_queue/queue_scheduler.py
==================================================
QueueScheduler — determines entry eligibility without executing anything.

All methods are pure time-based computations.
No threads. No I/O. No broker communication.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

import time
from typing import Optional

from iios.execution.oms.order_queue.constants import (
    DEFAULT_RETRY_DELAY_SEC,
    QueueEntryState,
    QueuePolicyType,
)
from iios.execution.oms.order_queue.queue_entry import QueueEntry


class QueueScheduler:
    """
    Stateless scheduler: checks timestamps to determine whether
    a QueueEntry should transition to READY.

    Also computes retry-at timestamps using exponential back-off.
    """

    __slots__ = ("_base_retry_delay",)

    def __init__(self, base_retry_delay: float = DEFAULT_RETRY_DELAY_SEC) -> None:
        self._base_retry_delay = base_retry_delay

    # ── Eligibility checks ────────────────────────────────────────────────────

    def is_ready(self, entry: QueueEntry, now: Optional[float] = None) -> bool:
        """
        Return True if the entry should be READY right now.

        WAITING entries become ready when their ready_at has elapsed.
        RETRY_PENDING entries become ready when next_retry_at has elapsed.
        READY entries are always ready.
        All other states return False.
        """
        t = now if now is not None else time.time()
        if entry.state == QueueEntryState.READY:
            return True
        if entry.state == QueueEntryState.WAITING:
            ready = entry.ready_at if entry.ready_at > 0 else entry.queued_at
            return ready <= t
        if entry.state == QueueEntryState.RETRY_PENDING:
            return entry.next_retry_at <= t
        if entry.state == QueueEntryState.QUEUED:
            # Immediately-eligible entries that haven't been promoted yet
            return entry.ready_at <= 0 or entry.ready_at <= t
        return False

    def should_expire(self, entry: QueueEntry, now: Optional[float] = None) -> bool:
        """Return True if the entry has exceeded its TTL."""
        t = now if now is not None else time.time()
        return (t - entry.queued_at) > entry.ttl_sec

    def needs_promotion(self, entry: QueueEntry, now: Optional[float] = None) -> bool:
        """
        True if the entry is WAITING/RETRY_PENDING and its time has come.
        Used by OrderQueue.tick() to bulk-advance states.
        """
        t = now if now is not None else time.time()
        if entry.state == QueueEntryState.WAITING:
            ready = entry.ready_at if entry.ready_at > 0 else entry.queued_at
            return ready <= t
        if entry.state == QueueEntryState.RETRY_PENDING:
            return entry.next_retry_at > 0 and entry.next_retry_at <= t
        return False

    # ── Retry scheduling ──────────────────────────────────────────────────────

    def compute_retry_at(
        self,
        entry: QueueEntry,
        base_delay: Optional[float] = None,
        now: Optional[float] = None,
    ) -> float:
        """
        Compute the next retry timestamp using exponential back-off.

        Formula: now + base_delay * 2^retry_count
        Capped at base_delay * 32 to avoid unbounded delays.
        """
        t   = now if now is not None else time.time()
        bd  = base_delay if base_delay is not None else self._base_retry_delay
        exp = min(entry.retry_count, 5)   # 2^5 = 32 cap
        return t + bd * (2 ** exp)

    def remaining_ttl(self, entry: QueueEntry, now: Optional[float] = None) -> float:
        """Seconds remaining before this entry expires. Negative means expired."""
        t = now if now is not None else time.time()
        return entry.ttl_sec - (t - entry.queued_at)

    def get_ready_entries(
        self,
        entries: list[QueueEntry],
        now: Optional[float] = None,
    ) -> list[QueueEntry]:
        """Filter list to those currently eligible for dispatch."""
        t = now if now is not None else time.time()
        return [e for e in entries if self.is_ready(e, t)]

    def get_promotable_entries(
        self,
        entries: list[QueueEntry],
        now: Optional[float] = None,
    ) -> list[QueueEntry]:
        """Filter WAITING/RETRY_PENDING entries whose time has come."""
        t = now if now is not None else time.time()
        return [e for e in entries if self.needs_promotion(e, t)]

    def get_expired_entries(
        self,
        entries: list[QueueEntry],
        now: Optional[float] = None,
    ) -> list[QueueEntry]:
        """Filter active entries that have exceeded their TTL."""
        from iios.execution.oms.order_queue.constants import ACTIVE_ENTRY_STATES
        t = now if now is not None else time.time()
        return [
            e for e in entries
            if e.state in ACTIVE_ENTRY_STATES and self.should_expire(e, t)
        ]
