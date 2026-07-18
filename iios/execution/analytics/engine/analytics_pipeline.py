"""
iios/execution/analytics/engine/analytics_pipeline.py
=====================================================
AnalyticsPipeline — mutable descriptor for a single analytics pipeline
execution.

A pipeline coordinates delegation of analytics work to downstream frameworks:
  - Performance Analytics Framework (M3)
  - Predictive Intelligence Framework (M4)

The pipeline performs NO calculations — it orchestrates delegation only.

C8 Execution Analytics & Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION, PipelineStage, PipelineStatus


@dataclass
class AnalyticsPipeline:
    """
    Mutable descriptor for a single analytics pipeline execution.

    Tracks pipeline state, timing, and delegation results from M3/M4.

    Fields
    ------
    pipeline_id:        Unique pipeline identifier.
    request_id:         Parent AnalyticsRequest ID.
    session_id:         Analytics lifecycle session ID.
    status:             Overall pipeline status.
    stage:              Current pipeline stage.
    has_performance:    Whether M3 Performance Analytics should be invoked.
    has_predictive:     Whether M4 Predictive Intelligence should be invoked.
    performance_result: Delegation result from M3 (opaque; set by dispatcher).
    predictive_result:  Delegation result from M4 (opaque; set by dispatcher).
    created_at:         Wall-time of pipeline creation.
    started_at:         Wall-time when processing started.
    completed_at:       Wall-time of completion.
    error_message:      Error description on failure.
    metadata:           Supplementary data.
    framework_version:  Framework version.
    """

    pipeline_id:        str
    request_id:         str
    session_id:         str
    status:             PipelineStatus  = PipelineStatus.PENDING
    stage:              PipelineStage   = PipelineStage.CREATED
    has_performance:    bool            = True
    has_predictive:     bool            = False
    performance_result: Optional[Any]   = None
    predictive_result:  Optional[Any]   = None
    created_at:         float           = field(default_factory=time.time)
    started_at:         Optional[float] = None
    completed_at:       Optional[float] = None
    error_message:      str             = ""
    metadata:           Dict[str, Any]  = field(default_factory=dict)
    framework_version:  str             = VERSION

    @property
    def is_pending(self) -> bool:
        return self.status == PipelineStatus.PENDING

    @property
    def is_active(self) -> bool:
        return self.status == PipelineStatus.ACTIVE

    @property
    def is_completed(self) -> bool:
        return self.status == PipelineStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status == PipelineStatus.FAILED

    @property
    def is_cancelled(self) -> bool:
        return self.status == PipelineStatus.CANCELLED

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at) * 1000.0

    def start(self) -> None:
        """Mark the pipeline as active and record start time."""
        self.status     = PipelineStatus.ACTIVE
        self.stage      = PipelineStage.COLLECTING
        self.started_at = time.time()

    def advance_to(self, stage: PipelineStage) -> None:
        """Advance the pipeline to the specified stage."""
        self.stage = stage

    def complete(self) -> None:
        """Mark the pipeline as completed."""
        self.status       = PipelineStatus.COMPLETED
        self.stage        = PipelineStage.COMPLETED
        self.completed_at = time.time()

    def fail(self, reason: str = "") -> None:
        """Mark the pipeline as failed."""
        self.status        = PipelineStatus.FAILED
        self.stage         = PipelineStage.FAILED
        self.error_message = reason
        self.completed_at  = time.time()

    def cancel(self) -> None:
        """Mark the pipeline as cancelled."""
        self.status       = PipelineStatus.CANCELLED
        self.stage        = PipelineStage.CANCELLED
        self.completed_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id":       self.pipeline_id,
            "request_id":        self.request_id,
            "session_id":        self.session_id,
            "status":            self.status.value,
            "stage":             self.stage.value,
            "has_performance":   self.has_performance,
            "has_predictive":    self.has_predictive,
            "created_at":        self.created_at,
            "started_at":        self.started_at,
            "completed_at":      self.completed_at,
            "duration_ms":       self.duration_ms,
            "error_message":     self.error_message,
            "framework_version": self.framework_version,
        }


def make_analytics_pipeline(
    request_id:  str,
    session_id:  str,
    *,
    pipeline_id:     Optional[str]           = None,
    has_performance: bool                    = True,
    has_predictive:  bool                    = False,
    metadata:        Optional[Dict[str, Any]]= None,
) -> AnalyticsPipeline:
    """Create a new AnalyticsPipeline descriptor."""
    return AnalyticsPipeline(
        pipeline_id     = pipeline_id or str(uuid.uuid4()),
        request_id      = request_id,
        session_id      = session_id,
        has_performance = has_performance,
        has_predictive  = has_predictive,
        metadata        = metadata or {},
    )
