"""iios/execution/planning/core/execution_schedule.py"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import ExecutionMode


@dataclass
class ExecutionSchedule:
    schedule_id:          str           = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id:              str           = ""
    execution_mode:       ExecutionMode = ExecutionMode.IMMEDIATE
    start_time:           float | None  = None
    end_time:             float | None  = None
    execution_window_sec: float         = 0.0
    slices:               int           = 1
    slice_interval_sec:   float         = 0.0
    conditions:           list[str]     = field(default_factory=list)
    is_active:            bool          = True
    created_at:           float         = field(default_factory=time.time)
    metadata:             dict          = field(default_factory=dict)

    def is_immediate(self) -> bool:
        return self.execution_mode == ExecutionMode.IMMEDIATE

    def is_expired(self, now: float | None = None) -> bool:
        now = now or time.time()
        return self.end_time is not None and now > self.end_time

    def window_remaining_sec(self, now: float | None = None) -> float:
        if self.end_time is None:
            return float("inf")
        now = now or time.time()
        return max(0.0, self.end_time - now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id":          self.schedule_id,
            "plan_id":              self.plan_id,
            "execution_mode":       self.execution_mode.value,
            "start_time":           self.start_time,
            "end_time":             self.end_time,
            "execution_window_sec": self.execution_window_sec,
            "slices":               self.slices,
            "slice_interval_sec":   self.slice_interval_sec,
            "conditions":           list(self.conditions),
            "is_active":            self.is_active,
        }
