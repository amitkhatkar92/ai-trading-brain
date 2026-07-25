"""
workflow_gateway_statistics.py — iios.workflow.gateway
-------------------------------------------------------
WorkflowGatewayStatistics + WorkflowStatistics —
thread-safe gateway metrics counters and reports.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 6
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class WorkflowStatistics:
    """Immutable gateway statistics report."""
    total_requests:           int
    successful_requests:      int
    failed_requests:          int
    rejected_requests:        int
    workflow_executions:      int
    snapshots_published:      int
    average_response_time_ms: float
    average_processing_time_ms: float
    gateway_availability:     float    # 0.0–1.0
    generated_at:             str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests":             self.total_requests,
            "successful_requests":        self.successful_requests,
            "failed_requests":            self.failed_requests,
            "rejected_requests":          self.rejected_requests,
            "workflow_executions":        self.workflow_executions,
            "snapshots_published":        self.snapshots_published,
            "average_response_time_ms":   self.average_response_time_ms,
            "average_processing_time_ms": self.average_processing_time_ms,
            "gateway_availability":       self.gateway_availability,
            "generated_at":               self.generated_at,
        }


class WorkflowGatewayStatistics:
    """
    Thread-safe gateway metrics tracker.
    """

    def __init__(self) -> None:
        self._lock                 = threading.Lock()
        self._total                = 0
        self._successful           = 0
        self._failed               = 0
        self._rejected             = 0
        self._executions           = 0
        self._snapshots            = 0
        self._total_response_ms    = 0.0
        self._total_processing_ms  = 0.0
        self._available_ticks      = 0
        self._total_ticks          = 0

    def record_request(
        self,
        *,
        success:           bool  = True,
        rejected:          bool  = False,
        response_ms:       float = 0.0,
        processing_ms:     float = 0.0,
    ) -> None:
        with self._lock:
            self._total             += 1
            self._total_response_ms += response_ms
            self._total_processing_ms += processing_ms
            if rejected:
                self._rejected += 1
            elif success:
                self._successful += 1
            else:
                self._failed += 1

    def record_workflow_execution(self) -> None:
        with self._lock:
            self._executions += 1

    def record_snapshot_published(self) -> None:
        with self._lock:
            self._snapshots += 1

    def record_availability_tick(self, available: bool) -> None:
        with self._lock:
            self._total_ticks += 1
            if available:
                self._available_ticks += 1

    def report(self) -> WorkflowStatistics:
        with self._lock:
            total       = self._total
            successful  = self._successful
            failed      = self._failed
            rejected    = self._rejected
            executions  = self._executions
            snapshots   = self._snapshots
            total_rms   = self._total_response_ms
            total_pms   = self._total_processing_ms
            av_ticks    = self._available_ticks
            total_ticks = self._total_ticks

        avg_rms  = round(total_rms  / total, 3) if total       else 0.0
        avg_pms  = round(total_pms  / total, 3) if total       else 0.0
        avail    = round(av_ticks   / total_ticks, 4) if total_ticks else 1.0

        return WorkflowStatistics(
            total_requests             = total,
            successful_requests        = successful,
            failed_requests            = failed,
            rejected_requests          = rejected,
            workflow_executions        = executions,
            snapshots_published        = snapshots,
            average_response_time_ms   = avg_rms,
            average_processing_time_ms = avg_pms,
            gateway_availability       = avail,
            generated_at               = datetime.now(tz=timezone.utc).isoformat(),
        )

    def reset(self) -> None:
        with self._lock:
            self._total               = 0
            self._successful          = 0
            self._failed              = 0
            self._rejected            = 0
            self._executions          = 0
            self._snapshots           = 0
            self._total_response_ms   = 0.0
            self._total_processing_ms = 0.0
            self._available_ticks     = 0
            self._total_ticks         = 0
