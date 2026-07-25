"""
workflow_snapshot_statistics.py — iios.workflow.snapshot
---------------------------------------------------------
WorkflowSnapshotStatisticsReport + WorkflowSnapshotStatistics —
snapshot publication and quality metrics.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import ExecutionStatus


@dataclass(frozen=True)
class WorkflowSnapshotStatisticsReport:
    """Immutable statistics snapshot."""
    total_snapshots:        int
    published_snapshots:    int
    superseded_snapshots:   int
    invalid_snapshots:      int
    successful_executions:  int
    failed_executions:      int
    total_steps:            int
    total_retries:          int
    total_compensations:    int
    average_duration_ms:    float
    success_rate:           float
    failure_rate:           float
    generated_at:           str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_snapshots":       self.total_snapshots,
            "published_snapshots":   self.published_snapshots,
            "superseded_snapshots":  self.superseded_snapshots,
            "invalid_snapshots":     self.invalid_snapshots,
            "successful_executions": self.successful_executions,
            "failed_executions":     self.failed_executions,
            "total_steps":           self.total_steps,
            "total_retries":         self.total_retries,
            "total_compensations":   self.total_compensations,
            "average_duration_ms":   self.average_duration_ms,
            "success_rate":          self.success_rate,
            "failure_rate":          self.failure_rate,
            "generated_at":          self.generated_at,
        }


class WorkflowSnapshotStatistics:
    """
    Thread-safe snapshot publication metrics tracker.
    """

    def __init__(self) -> None:
        self._lock               = threading.Lock()
        self._total              = 0
        self._published          = 0
        self._superseded         = 0
        self._invalid            = 0
        self._successful         = 0
        self._failed             = 0
        self._total_steps        = 0
        self._total_retries      = 0
        self._total_compensations = 0
        self._total_duration_ms  = 0.0

    def record_snapshot(
        self,
        execution_status:   ExecutionStatus,
        duration_ms:        float,
        steps:              int  = 0,
        retries:            int  = 0,
        compensations:      int  = 0,
        *,
        published:          bool = True,
        superseded:         bool = False,
        valid:              bool = True,
    ) -> None:
        with self._lock:
            self._total             += 1
            self._total_duration_ms += duration_ms
            self._total_steps       += steps
            self._total_retries     += retries
            self._total_compensations += compensations
            if published:
                self._published += 1
            if superseded:
                self._superseded += 1
            if not valid:
                self._invalid += 1
            if execution_status == ExecutionStatus.COMPLETED:
                self._successful += 1
            elif execution_status in (ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT):
                self._failed += 1

    def report(self) -> WorkflowSnapshotStatisticsReport:
        with self._lock:
            total      = self._total
            published  = self._published
            superseded = self._superseded
            invalid    = self._invalid
            successful = self._successful
            failed     = self._failed
            steps      = self._total_steps
            retries    = self._total_retries
            comps      = self._total_compensations
            total_dur  = self._total_duration_ms

        avg_dur      = round(total_dur / total, 3) if total else 0.0
        success_rate = round(successful / total, 4) if total else 0.0
        failure_rate = round(failed     / total, 4) if total else 0.0

        return WorkflowSnapshotStatisticsReport(
            total_snapshots        = total,
            published_snapshots    = published,
            superseded_snapshots   = superseded,
            invalid_snapshots      = invalid,
            successful_executions  = successful,
            failed_executions      = failed,
            total_steps            = steps,
            total_retries          = retries,
            total_compensations    = comps,
            average_duration_ms    = avg_dur,
            success_rate           = success_rate,
            failure_rate           = failure_rate,
            generated_at           = datetime.now(tz=timezone.utc).isoformat(),
        )

    def reset(self) -> None:
        with self._lock:
            self._total              = 0
            self._published          = 0
            self._superseded         = 0
            self._invalid            = 0
            self._successful         = 0
            self._failed             = 0
            self._total_steps        = 0
            self._total_retries      = 0
            self._total_compensations = 0
            self._total_duration_ms  = 0.0
