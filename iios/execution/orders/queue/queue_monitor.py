"""iios/execution/orders/queue/queue_monitor.py

Observability for QueueManager — exposes metrics snapshots.
"""
from __future__ import annotations

import time
from typing import Any

from .queue_manager import QueueManager


class QueueMonitor:
    """Lightweight metrics collector for all queues in QueueManager."""

    def __init__(self, queue_manager: QueueManager) -> None:
        self._qm           = queue_manager
        self._last_snapshot: dict[str, Any] = {}
        self._sample_time:  float           = 0.0

    def snapshot(self) -> dict[str, Any]:
        self._last_snapshot = {
            "timestamp":     time.time(),
            "total_pending": self._qm.total_pending(),
            "queues":        self._qm.stats(),
        }
        self._sample_time = self._last_snapshot["timestamp"]
        return self._last_snapshot

    def is_congested(self, threshold_pct: float = 0.80) -> bool:
        """True if any queue exceeds threshold_pct of its max capacity."""
        stats = self._qm.stats()
        for q_stats in stats.values():
            if isinstance(q_stats, dict):
                size     = q_stats.get("size", 0)
                max_size = q_stats.get("max_size", 1)
                if size / max(max_size, 1) >= threshold_pct:
                    return True
        return False

    def dead_letter_count(self) -> int:
        stats = self._qm.stats()
        dl = stats.get("dead_letter", {})
        return dl.get("size", 0)

    def retry_count(self) -> int:
        stats = self._qm.stats()
        r = stats.get("retry", {})
        return r.get("size", 0)
