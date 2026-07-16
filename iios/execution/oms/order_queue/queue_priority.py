"""iios/execution/oms/order_queue/queue_priority.py
==================================================
Priority helpers — sort-key computation and comparison utilities.

C6 Execution Intelligence — Phase 2, Module 4
"""
from __future__ import annotations

from typing import Any

from iios.execution.oms.order_queue.constants import QueuePolicyType, QueuePriorityLevel
from iios.execution.oms.order_queue.queue_entry import QueueEntry


def priority_sort_key(
    entry: QueueEntry,
    policy: QueuePolicyType = QueuePolicyType.FIFO,
) -> tuple[Any, ...]:
    """
    Return a sort key for a QueueEntry under the given policy.

    Lower tuple value → higher dispatch priority.
    """
    if policy == QueuePolicyType.PRIORITY:
        # Lower priority.value = higher urgency; tiebreak by arrival time
        return (entry.priority.value, entry.queued_at)

    if policy in (QueuePolicyType.SCHEDULED, QueuePolicyType.DELAYED):
        ready = entry.ready_at if entry.ready_at > 0 else entry.queued_at
        return (ready,)

    if policy == QueuePolicyType.RECOVERY:
        # Fewest retries first; tiebreak by next retry time
        return (entry.retry_count, entry.next_retry_at, entry.queued_at)

    # FIFO, PAPER_TRADING, BACKTEST, REPLAY — arrival order
    return (entry.queued_at,)


def compare_priority(a: QueueEntry, b: QueueEntry) -> int:
    """
    Compare two entries by priority level.

    Returns -1 if a is higher priority, 0 if equal, +1 if lower.
    """
    if a.priority.value < b.priority.value:
        return -1
    if a.priority.value > b.priority.value:
        return 1
    # Same priority — earlier arrival wins
    if a.queued_at < b.queued_at:
        return -1
    if a.queued_at > b.queued_at:
        return 1
    return 0


def highest_priority(entries: list[QueueEntry]) -> QueuePriorityLevel:
    """Return the highest (lowest numeric value) priority in a list."""
    if not entries:
        return QueuePriorityLevel.BACKGROUND
    return QueuePriorityLevel(min(e.priority.value for e in entries))


def lowest_priority(entries: list[QueueEntry]) -> QueuePriorityLevel:
    """Return the lowest (highest numeric value) priority in a list."""
    if not entries:
        return QueuePriorityLevel.CRITICAL
    return QueuePriorityLevel(max(e.priority.value for e in entries))
