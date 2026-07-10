"""iios/integration/research/monitoring/research_monitor.py

Runtime health monitor for the research framework.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from iios.integration.research.research_constants import DEFAULT_EXPERIMENT_TIMEOUT_SEC

logger = logging.getLogger(__name__)


class ResearchMonitor:
    """
    Tracks experiment execution health and produces alerts.

    Records when experiments start and end.
    Computes averages and detects long-running experiments.
    """

    def __init__(
        self,
        timeout_sec: float = DEFAULT_EXPERIMENT_TIMEOUT_SEC,
    ) -> None:
        self._timeout  = timeout_sec
        self._lock     = threading.RLock()
        self._running:   dict[str, float]  = {}   # experiment_id -> start_wall_ts
        self._durations: list[float]       = []
        self._completed  = 0
        self._failed     = 0
        self._cancelled  = 0

    def record_start(self, experiment_id: str) -> None:
        with self._lock:
            self._running[experiment_id] = time.time()

    def record_end(self, experiment_id: str, status: str) -> None:
        with self._lock:
            start = self._running.pop(experiment_id, None)
            if start is not None:
                self._durations.append(time.time() - start)
            if status == "completed":
                self._completed += 1
            elif status == "failed":
                self._failed += 1
            elif status == "cancelled":
                self._cancelled += 1

    def alerts(self) -> list[str]:
        """Return a list of alert messages for experiments exceeding timeout."""
        now    = time.time()
        msgs   = []
        with self._lock:
            for eid, start in self._running.items():
                elapsed = now - start
                if elapsed > self._timeout:
                    msgs.append(
                        f"Experiment '{eid}' has been running for "
                        f"{elapsed:.0f}s (timeout={self._timeout:.0f}s)."
                    )
        return msgs

    def is_any_running(self) -> bool:
        with self._lock:
            return bool(self._running)

    def running_count(self) -> int:
        with self._lock:
            return len(self._running)

    def avg_duration_sec(self) -> float:
        with self._lock:
            if not self._durations:
                return 0.0
            return sum(self._durations) / len(self._durations)

    def success_rate(self) -> float:
        with self._lock:
            total = self._completed + self._failed
            if total == 0:
                return 0.0
            return self._completed / total

    def health(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running":          len(self._running),
                "completed":        self._completed,
                "failed":           self._failed,
                "cancelled":        self._cancelled,
                "avg_duration_sec": self.avg_duration_sec(),
                "success_rate":     self.success_rate(),
                "alerts":           self.alerts(),
            }
