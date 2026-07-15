"""iios/investment/workflow/workflow_state.py
WorkflowState — mutable execution state for one pipeline run.
StageRecord — immutable record of a single stage attempt.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.investment.workflow.workflow_types import (
    PIPELINE_STAGES,
    TERMINAL_STAGES,
    StageStatus,
    WorkflowStage,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class StageRecord:
    """
    Immutable audit record for one stage execution attempt.
    Multiple records may exist per stage when retries occur.
    """

    stage:        WorkflowStage
    attempt:      int             # 1-based
    status:       StageStatus
    started_at:   str             # ISO-8601 UTC
    completed_at: Optional[str]   # ISO-8601 UTC; None while running
    duration_ms:  float           # wall-clock ms; 0 while running
    error:        Optional[str]   # last error message if status == FAILED
    snapshot_id:  Optional[str]   # ID of produced snapshot if status == COMPLETED
    metadata:     Dict[str, Any]  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "stage":        self.stage.value,
            "attempt":      self.attempt,
            "status":       self.status.value,
            "started_at":   self.started_at,
            "completed_at": self.completed_at,
            "duration_ms":  round(self.duration_ms, 2),
            "error":        self.error,
            "snapshot_id":  self.snapshot_id,
            "metadata":     self.metadata,
        }


class WorkflowState:
    """
    Thread-safe mutable state for one in-flight workflow execution.

    Tracks current stage, stage timeline, intermediate snapshots, errors,
    and warnings.  The orchestrator updates this as the pipeline progresses.
    """

    def __init__(
        self,
        *,
        workflow_id: str = "",
        request_id:  str = "",
    ) -> None:
        self._lock:          threading.RLock      = threading.RLock()
        self._workflow_id:   str                  = workflow_id or str(uuid.uuid4())
        self._request_id:    str                  = request_id
        self._current_stage: WorkflowStage        = WorkflowStage.INITIALIZED
        self._stage_records: List[StageRecord]    = []
        self._errors:        List[str]            = []
        self._warnings:      List[str]            = []
        self._started_at:    str                  = _now_iso()
        self._completed_at:  Optional[str]        = None

        # Accumulated snapshots per stage (domain objects, not serialised)
        self._snapshots:     Dict[WorkflowStage, Any] = {}

        # Active attempt tracking
        self._active_stage:      Optional[WorkflowStage] = None
        self._active_attempt:    int                     = 0
        self._active_started_ms: float                   = 0.0

        # Retry counters per stage
        self._retries: Dict[WorkflowStage, int] = {s: 0 for s in PIPELINE_STAGES}

        # Cancellation flag
        self._cancelled: bool = False

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def request_id(self) -> str:
        return self._request_id

    # ── Stage navigation ──────────────────────────────────────────────────────

    @property
    def current_stage(self) -> WorkflowStage:
        with self._lock:
            return self._current_stage

    def begin_stage(self, stage: WorkflowStage) -> None:
        """Record that *stage* is beginning its next attempt."""
        with self._lock:
            self._active_stage      = stage
            self._active_attempt    = self._retries.get(stage, 0) + 1
            self._active_started_ms = time.monotonic() * 1_000
            self._current_stage     = stage

    def complete_stage(
        self,
        stage:       WorkflowStage,
        snapshot:    Any             = None,
        snapshot_id: Optional[str]   = None,
        metadata:    Optional[dict]  = None,
    ) -> StageRecord:
        """Mark *stage* as successfully completed; store the produced snapshot."""
        with self._lock:
            elapsed = time.monotonic() * 1_000 - self._active_started_ms
            rec = StageRecord(
                stage        = stage,
                attempt      = self._active_attempt,
                status       = StageStatus.COMPLETED,
                started_at   = _now_iso(),
                completed_at = _now_iso(),
                duration_ms  = elapsed,
                error        = None,
                snapshot_id  = snapshot_id,
                metadata     = metadata or {},
            )
            self._stage_records.append(rec)
            if snapshot is not None:
                self._snapshots[stage] = snapshot
            self._active_stage = None
            return rec

    def fail_stage(
        self,
        stage:  WorkflowStage,
        error:  str,
        *,
        is_retry: bool = False,
    ) -> StageRecord:
        """Record a stage failure; increment retry counter if retrying."""
        with self._lock:
            elapsed = time.monotonic() * 1_000 - self._active_started_ms
            rec = StageRecord(
                stage        = stage,
                attempt      = self._active_attempt,
                status       = StageStatus.FAILED,
                started_at   = _now_iso(),
                completed_at = _now_iso(),
                duration_ms  = elapsed,
                error        = error,
                snapshot_id  = None,
                metadata     = {"is_retry": is_retry},
            )
            self._stage_records.append(rec)
            self._errors.append(f"[{stage.value}] {error}")
            if is_retry:
                self._retries[stage] = self._retries.get(stage, 0) + 1
            self._active_stage = None
            return rec

    def skip_stage(self, stage: WorkflowStage) -> StageRecord:
        """Record a stage as deliberately skipped (by configuration)."""
        with self._lock:
            rec = StageRecord(
                stage        = stage,
                attempt      = 0,
                status       = StageStatus.SKIPPED,
                started_at   = _now_iso(),
                completed_at = _now_iso(),
                duration_ms  = 0.0,
                error        = None,
                snapshot_id  = None,
            )
            self._stage_records.append(rec)
            return rec

    def transition_terminal(self, stage: WorkflowStage) -> None:
        """Move to a terminal stage (PUBLISHED / FAILED / CANCELLED)."""
        with self._lock:
            self._current_stage = stage
            self._completed_at  = _now_iso()

    # ── Cancellation ──────────────────────────────────────────────────────────

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        with self._lock:
            self._cancelled     = True
            self._current_stage = WorkflowStage.CANCELLED
            self._completed_at  = _now_iso()

    # ── Retry info ────────────────────────────────────────────────────────────

    def retry_count(self, stage: WorkflowStage) -> int:
        with self._lock:
            return self._retries.get(stage, 0)

    # ── Snapshots ─────────────────────────────────────────────────────────────

    def get_snapshot(self, stage: WorkflowStage) -> Optional[Any]:
        with self._lock:
            return self._snapshots.get(stage)

    def get_market_snapshot(self) -> Optional[Any]:
        return self.get_snapshot(WorkflowStage.MARKET)

    def get_company_snapshot(self) -> Optional[Any]:
        return self.get_snapshot(WorkflowStage.COMPANY)

    def get_strategy_snapshot(self) -> Optional[Any]:
        return self.get_snapshot(WorkflowStage.STRATEGY)

    def get_decision_snapshot(self) -> Optional[Any]:
        return self.get_snapshot(WorkflowStage.DECISION)

    def get_portfolio_snapshot(self) -> Optional[Any]:
        return self.get_snapshot(WorkflowStage.PORTFOLIO)

    # ── Errors / Warnings ─────────────────────────────────────────────────────

    def add_warning(self, msg: str) -> None:
        with self._lock:
            self._warnings.append(msg)

    @property
    def errors(self) -> List[str]:
        with self._lock:
            return list(self._errors)

    @property
    def warnings(self) -> List[str]:
        with self._lock:
            return list(self._warnings)

    @property
    def has_errors(self) -> bool:
        with self._lock:
            return bool(self._errors)

    # ── Timeline ──────────────────────────────────────────────────────────────

    @property
    def stage_records(self) -> List[StageRecord]:
        with self._lock:
            return list(self._stage_records)

    @property
    def completed_stages(self) -> List[WorkflowStage]:
        with self._lock:
            return [
                r.stage for r in self._stage_records
                if r.status == StageStatus.COMPLETED
            ]

    @property
    def is_terminal(self) -> bool:
        with self._lock:
            return self._current_stage in TERMINAL_STAGES

    @property
    def started_at(self) -> str:
        return self._started_at

    @property
    def completed_at(self) -> Optional[str]:
        with self._lock:
            return self._completed_at

    def total_duration_ms(self) -> float:
        """Wall-clock ms from initialization to now (or completion)."""
        with self._lock:
            return sum(r.duration_ms for r in self._stage_records)

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "workflow_id":       self._workflow_id,
                "request_id":        self._request_id,
                "current_stage":     self._current_stage.value,
                "started_at":        self._started_at,
                "completed_at":      self._completed_at,
                "total_duration_ms": round(self.total_duration_ms(), 2),
                "is_cancelled":      self._cancelled,
                "errors":            list(self._errors),
                "warnings":          list(self._warnings),
                "completed_stages":  [s.value for s in self.completed_stages],
                "stage_records":     [r.to_dict() for r in self._stage_records],
                "retries":           {k.value: v for k, v in self._retries.items()},
            }
