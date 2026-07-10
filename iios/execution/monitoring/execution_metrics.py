"""iios/execution/monitoring/execution_metrics.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from iios.execution.execution_constants import ExecutionStatus


@dataclass
class ExecutionMetrics:
    """
    Per-execution timing and step metrics collected by ExecutionMonitor.
    """

    execution_id:     str             = ""
    status:           ExecutionStatus = ExecutionStatus.CREATED

    # ── Timing ─────────────────────────────────────────────────────────────────
    started_at:       float       = field(default_factory=time.time)
    completed_at:     float | None = None
    duration_ms:      float       = 0.0

    # ── Step counters ──────────────────────────────────────────────────────────
    step_count:       int = 0
    steps_completed:  int = 0
    steps_failed:     int = 0
    steps_skipped:    int = 0

    # ── Fill metrics ──────────────────────────────────────────────────────────
    fill_ratio:       float = 0.0
    slippage:         float = 0.0
    commission:       float = 0.0
    volume:           float = 0.0

    # ── Extra ─────────────────────────────────────────────────────────────────
    metadata: dict[str, Any] = field(default_factory=dict)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def mark_complete(self, status: ExecutionStatus) -> None:
        self.completed_at = time.time()
        self.status       = status
        self.duration_ms  = (self.completed_at - self.started_at) * 1_000.0

    def record_step(self, *, success: bool = True, skipped: bool = False) -> None:
        self.step_count += 1
        if skipped:
            self.steps_skipped += 1
        elif success:
            self.steps_completed += 1
        else:
            self.steps_failed += 1

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id":    self.execution_id,
            "status":          self.status.value,
            "started_at":      self.started_at,
            "completed_at":    self.completed_at,
            "duration_ms":     round(self.duration_ms, 2),
            "step_count":      self.step_count,
            "steps_completed": self.steps_completed,
            "steps_failed":    self.steps_failed,
            "steps_skipped":   self.steps_skipped,
            "fill_ratio":      round(self.fill_ratio, 4),
            "slippage":        round(self.slippage, 4),
            "commission":      round(self.commission, 4),
            "volume":          round(self.volume, 4),
            "metadata":        dict(self.metadata),
        }
