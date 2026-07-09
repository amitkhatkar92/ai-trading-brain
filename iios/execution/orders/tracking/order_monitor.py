"""iios/execution/orders/tracking/order_monitor.py

Real-time monitoring summary combining OrderTracker, StatusTracker
and ExecutionTracker into a single snapshot.
"""
from __future__ import annotations

import time
from typing import Any

from ..queue.queue_manager import QueueManager
from .execution_tracker import ExecutionTracker
from .order_tracker import OrderTracker
from .status_tracker import StatusTracker


class OrderMonitor:
    """Aggregates all tracking subsystems into a single monitoring facade."""

    def __init__(
        self,
        order_tracker:     OrderTracker,
        status_tracker:    StatusTracker,
        execution_tracker: ExecutionTracker,
        queue_manager:     QueueManager,
    ) -> None:
        self._ot = order_tracker
        self._st = status_tracker
        self._et = execution_tracker
        self._qm = queue_manager

    def snapshot(self) -> dict[str, Any]:
        return {
            "timestamp":   time.time(),
            "orders":      self._ot.to_dict(),
            "status":      self._st.to_dict(),
            "executions":  self._et.to_dict(),
            "queues":      self._qm.stats(),
        }

    def is_healthy(self) -> bool:
        """Simple health check — dead-letter queue should be empty for a healthy OMS."""
        dl = self._qm.stats().get("dead_letter", {})
        return dl.get("size", 0) == 0

    def active_count(self) -> int:
        return len(self._ot.active_order_ids())

    def to_dict(self) -> dict[str, Any]:
        return self.snapshot()
