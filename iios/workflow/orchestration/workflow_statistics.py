"""
workflow_statistics.py — iios.workflow.orchestration
-----------------------------------------------------
OrchestrationStatisticsReport + WorkflowStatistics — execution metrics.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .constants import WorkflowStatus


@dataclass(frozen=True)
class OrchestrationStatisticsReport:
    """Immutable snapshot of orchestration metrics."""
    workflows_executed:    int
    workflows_succeeded:   int
    workflows_failed:      int
    workflows_compensated: int
    steps_executed:        int
    steps_succeeded:       int
    steps_failed:          int
    retries:               int
    compensations:         int
    checkpoints:           int
    total_duration_ms:     float
    average_duration_ms:   float
    average_steps_per_wf:  float
    throughput_per_minute: float
    generated_at:          str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflows_executed":    self.workflows_executed,
            "workflows_succeeded":   self.workflows_succeeded,
            "workflows_failed":      self.workflows_failed,
            "workflows_compensated": self.workflows_compensated,
            "steps_executed":        self.steps_executed,
            "steps_succeeded":       self.steps_succeeded,
            "steps_failed":          self.steps_failed,
            "retries":               self.retries,
            "compensations":         self.compensations,
            "checkpoints":           self.checkpoints,
            "total_duration_ms":     self.total_duration_ms,
            "average_duration_ms":   self.average_duration_ms,
            "average_steps_per_wf":  self.average_steps_per_wf,
            "throughput_per_minute": self.throughput_per_minute,
            "generated_at":          self.generated_at,
        }


class WorkflowStatistics:
    """Thread-safe orchestration execution metrics tracker."""

    def __init__(self) -> None:
        self._lock             = threading.Lock()
        self._executed         = 0
        self._succeeded        = 0
        self._failed           = 0
        self._compensated      = 0
        self._steps_executed   = 0
        self._steps_succeeded  = 0
        self._steps_failed     = 0
        self._retries          = 0
        self._compensations    = 0
        self._checkpoints      = 0
        self._total_duration   = 0.0
        self._first_ts: float  = 0.0
        self._last_ts:  float  = 0.0

    def record_execution(
        self,
        status:         WorkflowStatus,
        duration_ms:    float,
        steps_executed: int  = 0,
        steps_succeeded: int = 0,
        steps_failed:   int  = 0,
        retries:        int  = 0,
        compensations:  int  = 0,
        checkpoints:    int  = 0,
    ) -> None:
        import time
        now = time.monotonic()
        with self._lock:
            self._executed       += 1
            self._total_duration += duration_ms
            self._steps_executed += steps_executed
            self._steps_succeeded += steps_succeeded
            self._steps_failed   += steps_failed
            self._retries        += retries
            self._compensations  += compensations
            self._checkpoints    += checkpoints
            if status == WorkflowStatus.COMPLETED:
                self._succeeded += 1
            else:
                self._failed += 1
            if compensations > 0:
                self._compensated += 1
            if self._first_ts == 0.0:
                self._first_ts = now
            self._last_ts = now

    def report(self) -> OrchestrationStatisticsReport:
        import time
        with self._lock:
            executed    = self._executed
            succeeded   = self._succeeded
            failed      = self._failed
            compensated = self._compensated
            steps_ex    = self._steps_executed
            steps_suc   = self._steps_succeeded
            steps_fail  = self._steps_failed
            retries     = self._retries
            comp        = self._compensations
            chk         = self._checkpoints
            total_dur   = self._total_duration
            first_ts    = self._first_ts
            last_ts     = self._last_ts

        avg_dur  = round(total_dur / executed, 3) if executed else 0.0
        avg_step = round(steps_ex  / executed, 2) if executed else 0.0

        elapsed_min = (last_ts - first_ts) / 60.0 if last_ts > first_ts else 0.0
        throughput  = round(executed / elapsed_min, 2) if elapsed_min > 0 else 0.0

        return OrchestrationStatisticsReport(
            workflows_executed    = executed,
            workflows_succeeded   = succeeded,
            workflows_failed      = failed,
            workflows_compensated = compensated,
            steps_executed        = steps_ex,
            steps_succeeded       = steps_suc,
            steps_failed          = steps_fail,
            retries               = retries,
            compensations         = comp,
            checkpoints           = chk,
            total_duration_ms     = round(total_dur, 3),
            average_duration_ms   = avg_dur,
            average_steps_per_wf  = avg_step,
            throughput_per_minute = throughput,
            generated_at          = datetime.now(tz=timezone.utc).isoformat(),
        )

    def reset(self) -> None:
        with self._lock:
            self._executed        = 0
            self._succeeded       = 0
            self._failed          = 0
            self._compensated     = 0
            self._steps_executed  = 0
            self._steps_succeeded = 0
            self._steps_failed    = 0
            self._retries         = 0
            self._compensations   = 0
            self._checkpoints     = 0
            self._total_duration  = 0.0
            self._first_ts        = 0.0
            self._last_ts         = 0.0
