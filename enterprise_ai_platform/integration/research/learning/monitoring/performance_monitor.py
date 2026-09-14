"""monitoring/performance_monitor.py — System-level performance monitoring."""
from __future__ import annotations

import threading
import time
from typing import Any


class PerformanceMonitor:
    """
    Records engine-level performance counters.

    Updated by the LearningEngine on each major operation.
    """

    def __init__(self) -> None:
        self._lock          = threading.RLock()
        self._job_latencies: list[float] = []
        self._eval_latencies: list[float] = []
        self._deploy_count   = 0
        self._rollback_count = 0
        self._started_at     = time.time()

    def record_job(self, elapsed_sec: float) -> None:
        with self._lock:
            self._job_latencies.append(elapsed_sec)
            if len(self._job_latencies) > 10_000:
                self._job_latencies = self._job_latencies[-10_000:]

    def record_eval(self, elapsed_sec: float) -> None:
        with self._lock:
            self._eval_latencies.append(elapsed_sec)
            if len(self._eval_latencies) > 10_000:
                self._eval_latencies = self._eval_latencies[-10_000:]

    def record_deploy(self) -> None:
        with self._lock:
            self._deploy_count += 1

    def record_rollback(self) -> None:
        with self._lock:
            self._rollback_count += 1

    def _avg(self, lst: list[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "uptime_sec":          time.time() - self._started_at,
                "total_jobs":          len(self._job_latencies),
                "avg_job_sec":         self._avg(self._job_latencies),
                "total_evals":         len(self._eval_latencies),
                "avg_eval_sec":        self._avg(self._eval_latencies),
                "total_deploys":       self._deploy_count,
                "total_rollbacks":     self._rollback_count,
            }
