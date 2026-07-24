"""
workflow_statistics.py — iios.workflow.lifecycle
-------------------------------------------------
Thread-safe statistics for the Workflow Lifecycle module.

7 metrics:
  1. workflows_created
  2. workflows_running          (peak concurrency counter)
  3. workflows_completed
  4. workflows_failed
  5. workflows_cancelled
  6. average_runtime_ms         (RUNNING → terminal duration)
  7. average_lifecycle_duration_ms (CREATED → terminal duration)

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class WorkflowLifecycleStatisticsReport:
    """Point-in-time statistics snapshot for the workflow lifecycle system."""
    workflows_created:              int
    workflows_running:              int
    workflows_completed:            int
    workflows_failed:               int
    workflows_cancelled:            int
    average_runtime_ms:             float
    average_lifecycle_duration_ms:  float
    captured_at:                    str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflows_created":             self.workflows_created,
            "workflows_running":             self.workflows_running,
            "workflows_completed":           self.workflows_completed,
            "workflows_failed":              self.workflows_failed,
            "workflows_cancelled":           self.workflows_cancelled,
            "average_runtime_ms":            self.average_runtime_ms,
            "average_lifecycle_duration_ms": self.average_lifecycle_duration_ms,
            "captured_at":                   self.captured_at,
        }


class WorkflowLifecycleStatistics:
    """Thread-safe rolling statistics for the workflow lifecycle system."""

    def __init__(self) -> None:
        self._lock                        = threading.Lock()
        self._workflows_created           = 0
        self._workflows_running           = 0    # current concurrency
        self._workflows_completed         = 0
        self._workflows_failed            = 0
        self._workflows_cancelled         = 0
        # runtime = RUNNING → terminal
        self._total_runtime_ms            = 0.0
        self._runtime_count               = 0
        # lifecycle = CREATED → terminal
        self._total_lifecycle_duration_ms = 0.0
        self._lifecycle_count             = 0

    # ----------------------------------------------------------------
    # Increment
    # ----------------------------------------------------------------

    def record_created(self) -> None:
        with self._lock:
            self._workflows_created += 1

    def record_started(self) -> None:
        """Increment the running concurrency counter."""
        with self._lock:
            self._workflows_running += 1

    def record_completed(
        self,
        runtime_ms:            float = 0.0,
        lifecycle_duration_ms: float = 0.0,
    ) -> None:
        with self._lock:
            self._workflows_completed += 1
            self._workflows_running   = max(0, self._workflows_running - 1)
            if runtime_ms > 0:
                self._total_runtime_ms += runtime_ms
                self._runtime_count    += 1
            if lifecycle_duration_ms > 0:
                self._total_lifecycle_duration_ms += lifecycle_duration_ms
                self._lifecycle_count             += 1

    def record_failed(
        self,
        lifecycle_duration_ms: float = 0.0,
    ) -> None:
        with self._lock:
            self._workflows_failed  += 1
            self._workflows_running  = max(0, self._workflows_running - 1)
            if lifecycle_duration_ms > 0:
                self._total_lifecycle_duration_ms += lifecycle_duration_ms
                self._lifecycle_count             += 1

    def record_cancelled(
        self,
        lifecycle_duration_ms: float = 0.0,
    ) -> None:
        with self._lock:
            self._workflows_cancelled += 1
            self._workflows_running    = max(0, self._workflows_running - 1)
            if lifecycle_duration_ms > 0:
                self._total_lifecycle_duration_ms += lifecycle_duration_ms
                self._lifecycle_count             += 1

    # ----------------------------------------------------------------
    # Report
    # ----------------------------------------------------------------

    def report(self) -> WorkflowLifecycleStatisticsReport:
        with self._lock:
            avg_rt = (
                self._total_runtime_ms / self._runtime_count
                if self._runtime_count > 0 else 0.0
            )
            avg_lc = (
                self._total_lifecycle_duration_ms / self._lifecycle_count
                if self._lifecycle_count > 0 else 0.0
            )
            return WorkflowLifecycleStatisticsReport(
                workflows_created             = self._workflows_created,
                workflows_running             = self._workflows_running,
                workflows_completed           = self._workflows_completed,
                workflows_failed              = self._workflows_failed,
                workflows_cancelled           = self._workflows_cancelled,
                average_runtime_ms            = round(avg_rt, 3),
                average_lifecycle_duration_ms = round(avg_lc, 3),
                captured_at                   = datetime.now(tz=timezone.utc).isoformat(),
            )

    def reset(self) -> None:
        with self._lock:
            self._workflows_created           = 0
            self._workflows_running           = 0
            self._workflows_completed         = 0
            self._workflows_failed            = 0
            self._workflows_cancelled         = 0
            self._total_runtime_ms            = 0.0
            self._runtime_count               = 0
            self._total_lifecycle_duration_ms = 0.0
            self._lifecycle_count             = 0
