"""
iios/execution/recovery/engine/recovery_pipeline.py
===================================================
RecoveryPipeline — tracks the ordered execution of recovery workflow stages.

The pipeline does NOT execute stages; the RecoveryManager drives execution.
The pipeline records stage status, timing, and results.

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    PIPELINE_STAGES_ORDERED,
    VERSION,
    PipelineStage,
    PipelineStageStatus,
)
from .exceptions import RecoveryPipelineError
from .recovery_context import RecoveryContext
from .recovery_request import RecoveryRequest


@dataclass
class PipelineStageRecord:
    """Mutable record of a single pipeline stage execution."""

    stage:        PipelineStage
    status:       PipelineStageStatus = PipelineStageStatus.PENDING
    started_at:   Optional[float]     = None
    completed_at: Optional[float]     = None
    result:       Any                 = None
    error:        str                 = ""

    @property
    def duration_ms(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return (end - self.started_at) * 1000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage":        self.stage.value,
            "status":       self.status.value,
            "started_at":   self.started_at,
            "completed_at": self.completed_at,
            "duration_ms":  self.duration_ms,
            "error":        self.error,
        }


class RecoveryPipeline:
    """
    Tracks the ordered execution of recovery pipeline stages.

    Thread-safe via an internal RLock.
    """

    def __init__(
        self,
        request_id: str,
        session_id: str,
        stages:     Tuple[PipelineStage, ...] = PIPELINE_STAGES_ORDERED,
    ) -> None:
        self._request_id = request_id
        self._session_id = session_id
        self._stages     = stages
        self._records: Dict[PipelineStage, PipelineStageRecord] = {
            s: PipelineStageRecord(stage=s) for s in stages
        }
        self._stage_order: List[PipelineStage] = list(stages)
        self._current_idx: int = 0
        self._lock = threading.RLock()
        self._created_at = time.time()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def current_stage(self) -> Optional[PipelineStage]:
        with self._lock:
            if self._current_idx < len(self._stage_order):
                return self._stage_order[self._current_idx]
            return None

    @property
    def is_complete(self) -> bool:
        with self._lock:
            return all(
                r.status == PipelineStageStatus.COMPLETED
                or r.status == PipelineStageStatus.SKIPPED
                for r in self._records.values()
            )

    @property
    def is_failed(self) -> bool:
        with self._lock:
            return any(
                r.status == PipelineStageStatus.FAILED
                for r in self._records.values()
            )

    @property
    def stages_completed(self) -> int:
        with self._lock:
            return sum(
                1 for r in self._records.values()
                if r.status in (PipelineStageStatus.COMPLETED, PipelineStageStatus.SKIPPED)
            )

    @property
    def stages_total(self) -> int:
        return len(self._stages)

    @property
    def failed_stage(self) -> Optional[PipelineStage]:
        with self._lock:
            for stage in self._stage_order:
                if self._records[stage].status == PipelineStageStatus.FAILED:
                    return stage
            return None

    @property
    def completed_stage_names(self) -> List[str]:
        with self._lock:
            return [
                r.stage.value
                for r in self._records.values()
                if r.status in (PipelineStageStatus.COMPLETED, PipelineStageStatus.SKIPPED)
            ]

    # ── Stage lifecycle ───────────────────────────────────────────────────────

    def start_stage(self, stage: PipelineStage) -> None:
        """Mark a stage as running."""
        with self._lock:
            if stage not in self._records:
                raise RecoveryPipelineError(
                    f"Unknown pipeline stage: {stage!r}", stage=stage.value
                )
            rec = self._records[stage]
            if rec.status not in (PipelineStageStatus.PENDING, PipelineStageStatus.RUNNING):
                raise RecoveryPipelineError(
                    f"Cannot start stage {stage!r} from status {rec.status!r}",
                    stage=stage.value,
                )
            rec.status     = PipelineStageStatus.RUNNING
            rec.started_at = time.time()

    def complete_stage(self, stage: PipelineStage, result: Any = None) -> None:
        """Mark a stage as successfully completed."""
        with self._lock:
            if stage not in self._records:
                raise RecoveryPipelineError(
                    f"Unknown pipeline stage: {stage!r}", stage=stage.value
                )
            rec = self._records[stage]
            rec.status       = PipelineStageStatus.COMPLETED
            rec.completed_at = time.time()
            rec.result       = result
            # Advance the current index past this stage
            if stage in self._stage_order:
                idx = self._stage_order.index(stage)
                if self._current_idx <= idx:
                    self._current_idx = idx + 1

    def fail_stage(self, stage: PipelineStage, error: str) -> None:
        """Mark a stage as failed."""
        with self._lock:
            if stage not in self._records:
                raise RecoveryPipelineError(
                    f"Unknown pipeline stage: {stage!r}", stage=stage.value
                )
            rec = self._records[stage]
            rec.status       = PipelineStageStatus.FAILED
            rec.completed_at = time.time()
            rec.error        = error

    def skip_stage(self, stage: PipelineStage) -> None:
        """Mark a stage as skipped (not required for this workflow)."""
        with self._lock:
            if stage not in self._records:
                raise RecoveryPipelineError(
                    f"Unknown pipeline stage: {stage!r}", stage=stage.value
                )
            rec = self._records[stage]
            rec.status       = PipelineStageStatus.SKIPPED
            rec.completed_at = time.time()
            # Advance past skipped stage
            if stage in self._stage_order:
                idx = self._stage_order.index(stage)
                if self._current_idx <= idx:
                    self._current_idx = idx + 1

    def get_stage_record(self, stage: PipelineStage) -> Optional[PipelineStageRecord]:
        with self._lock:
            return self._records.get(stage)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "request_id":    self._request_id,
                "session_id":    self._session_id,
                "is_complete":   self.is_complete,
                "is_failed":     self.is_failed,
                "stages_completed": self.stages_completed,
                "stages_total":  self.stages_total,
                "current_stage": self.current_stage.value if self.current_stage else None,
                "failed_stage":  self.failed_stage.value if self.failed_stage else None,
                "stages": [r.to_dict() for r in self._records.values()],
            }
