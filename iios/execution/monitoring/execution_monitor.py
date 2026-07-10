"""iios/execution/monitoring/execution_monitor.py"""
from __future__ import annotations

import logging
import threading
from typing import Any

from iios.execution.execution_constants import ExecutionStatus
from iios.execution.core.execution_result import ExecutionResult
from iios.execution.monitoring.execution_metrics import ExecutionMetrics

logger = logging.getLogger(__name__)


class ExecutionMonitor:
    """
    Observes execution sessions and accumulates per-execution metrics.

    Provides hooks called by the WorkflowEngine / ExecutionManager at
    lifecycle boundaries.  Thread-safe.
    """

    def __init__(self) -> None:
        self._lock:    threading.RLock                   = threading.RLock()
        self._metrics: dict[str, ExecutionMetrics]       = {}
        self._completed: list[str]                       = []   # ordered execution_ids

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    def on_execution_started(self, execution_id: str) -> None:
        with self._lock:
            self._metrics[execution_id] = ExecutionMetrics(execution_id=execution_id)
        logger.debug("ExecutionMonitor: started %s", execution_id)

    def on_step_completed(
        self, execution_id: str, *, step_name: str, success: bool, skipped: bool = False
    ) -> None:
        with self._lock:
            m = self._metrics.get(execution_id)
            if m:
                m.record_step(success=success, skipped=skipped)

    def on_execution_completed(
        self, execution_id: str, result: ExecutionResult
    ) -> None:
        with self._lock:
            m = self._metrics.get(execution_id)
            if m:
                m.mark_complete(result.status)
                m.fill_ratio   = result.fill_ratio
                m.slippage     = result.slippage
                m.commission   = result.commission
                m.volume       = result.quantity_executed
            self._completed.append(execution_id)
        logger.debug(
            "ExecutionMonitor: completed %s status=%s",
            execution_id,
            result.status.value,
        )

    def on_execution_failed(self, execution_id: str, error: str) -> None:
        with self._lock:
            m = self._metrics.get(execution_id)
            if m:
                m.mark_complete(ExecutionStatus.FAILED)
                m.metadata["error"] = error
            self._completed.append(execution_id)
        logger.debug("ExecutionMonitor: failed %s — %s", execution_id, error)

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_metrics(self, execution_id: str) -> ExecutionMetrics | None:
        with self._lock:
            return self._metrics.get(execution_id)

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for m in self._metrics.values() if not m.is_complete)

    def completed_count(self) -> int:
        with self._lock:
            return len(self._completed)

    def summary(self) -> dict[str, Any]:
        with self._lock:
            total     = len(self._metrics)
            completed = len(self._completed)
            active    = total - completed
            succeeded = sum(
                1 for m in self._metrics.values()
                if m.status == ExecutionStatus.COMPLETED
            )
            failed = sum(
                1 for m in self._metrics.values()
                if m.status == ExecutionStatus.FAILED
            )
            durations = [m.duration_ms for m in self._metrics.values() if m.is_complete]
            avg_ms = (sum(durations) / len(durations)) if durations else 0.0
            return {
                "total":             total,
                "active":            active,
                "completed":         completed,
                "succeeded":         succeeded,
                "failed":            failed,
                "avg_duration_ms":   round(avg_ms, 2),
            }

    def clear(self) -> None:
        with self._lock:
            self._metrics.clear()
            self._completed.clear()
