"""
workflow_statistics.py — iios.workflow.engine
----------------------------------------------
8-counter rolling statistics for the Workflow Engine.

Statistics:
  1. workflows_executed          — total workflows processed
  2. workflows_completed         — successfully completed
  3. workflows_failed            — failed workflows
  4. queued_workflows            — current queue depth (snapshot)
  5. average_runtime_ms          — avg RUNNING → terminal duration
  6. average_queue_time_ms       — avg time from enqueue to dispatch
  7. average_processing_time_ms  — avg pipeline processing duration
  8. workflow_availability       — rolling success ratio (0.0–1.0)

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class WorkflowEngineStatisticsReport:
    """Point-in-time statistics snapshot for the Workflow Engine."""
    workflows_executed:         int
    workflows_completed:        int
    workflows_failed:           int
    queued_workflows:           int
    average_runtime_ms:         float
    average_queue_time_ms:      float
    average_processing_time_ms: float
    workflow_availability:      float
    captured_at:                str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflows_executed":         self.workflows_executed,
            "workflows_completed":        self.workflows_completed,
            "workflows_failed":           self.workflows_failed,
            "queued_workflows":           self.queued_workflows,
            "average_runtime_ms":         self.average_runtime_ms,
            "average_queue_time_ms":      self.average_queue_time_ms,
            "average_processing_time_ms": self.average_processing_time_ms,
            "workflow_availability":      self.workflow_availability,
            "captured_at":                self.captured_at,
        }


class WorkflowEngineStatistics:
    """Thread-safe rolling statistics for the Workflow Engine."""

    def __init__(self) -> None:
        self._lock                    = threading.Lock()
        self._executed                = 0
        self._completed               = 0
        self._failed                  = 0
        self._total_runtime_ms        = 0.0
        self._runtime_count           = 0
        self._total_queue_ms          = 0.0
        self._queue_count             = 0
        self._total_processing_ms     = 0.0
        self._processing_count        = 0
        self._availability_ticks      = 0
        self._availability_ok         = 0

    # ----------------------------------------------------------------
    # Increment
    # ----------------------------------------------------------------

    def record_executed(self) -> None:
        with self._lock:
            self._executed += 1

    def record_completed(self, runtime_ms: float = 0.0) -> None:
        with self._lock:
            self._completed += 1
            self._availability_ticks += 1
            self._availability_ok    += 1
            if runtime_ms > 0:
                self._total_runtime_ms += runtime_ms
                self._runtime_count    += 1

    def record_failed(self) -> None:
        with self._lock:
            self._failed             += 1
            self._availability_ticks += 1

    def record_queue_time(self, ms: float) -> None:
        with self._lock:
            self._total_queue_ms += ms
            self._queue_count    += 1

    def record_processing_time(self, ms: float) -> None:
        with self._lock:
            self._total_processing_ms += ms
            self._processing_count    += 1

    # ----------------------------------------------------------------
    # Report
    # ----------------------------------------------------------------

    def report(self, current_queue_size: int = 0) -> WorkflowEngineStatisticsReport:
        with self._lock:
            avg_rt  = (
                self._total_runtime_ms / self._runtime_count
                if self._runtime_count > 0 else 0.0
            )
            avg_qt  = (
                self._total_queue_ms / self._queue_count
                if self._queue_count > 0 else 0.0
            )
            avg_pt  = (
                self._total_processing_ms / self._processing_count
                if self._processing_count > 0 else 0.0
            )
            avail   = (
                self._availability_ok / self._availability_ticks
                if self._availability_ticks > 0 else 1.0
            )
            return WorkflowEngineStatisticsReport(
                workflows_executed         = self._executed,
                workflows_completed        = self._completed,
                workflows_failed           = self._failed,
                queued_workflows           = current_queue_size,
                average_runtime_ms         = round(avg_rt, 3),
                average_queue_time_ms      = round(avg_qt, 3),
                average_processing_time_ms = round(avg_pt, 3),
                workflow_availability      = round(avail, 6),
                captured_at                = datetime.now(tz=timezone.utc).isoformat(),
            )

    def reset(self) -> None:
        with self._lock:
            self._executed            = 0
            self._completed           = 0
            self._failed              = 0
            self._total_runtime_ms    = 0.0
            self._runtime_count       = 0
            self._total_queue_ms      = 0.0
            self._queue_count         = 0
            self._total_processing_ms = 0.0
            self._processing_count    = 0
            self._availability_ticks  = 0
            self._availability_ok     = 0
