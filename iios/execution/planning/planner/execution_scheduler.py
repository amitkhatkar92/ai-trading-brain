"""iios/execution/planning/planner/execution_scheduler.py
Assigns scheduling windows to execution plans.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.core.execution_plan import ExecutionPlan
from iios.execution.planning.core.execution_schedule import ExecutionSchedule


@dataclass
class ScheduleRequest:
    """Input to the scheduler."""

    plan_id:            str   = ""
    start_offset_sec:   float = 0.0      # seconds from now to start
    window_sec:         float = 3_600.0  # total execution window
    urgency:            str   = "normal" # "immediate" | "normal" | "bulk"
    metadata:           dict[str, Any] = field(default_factory=dict)


class ExecutionScheduler:
    """
    Assigns ExecutionSchedule objects to plans.

    "immediate" urgency: start_time = now
    "normal"   urgency: start_time = now + start_offset_sec
    "bulk"     urgency: start_time = now + 1 hour + start_offset_sec
    """

    URGENCY_OFFSET = {
        "immediate": 0.0,
        "normal":    0.0,
        "bulk":      3_600.0,
    }

    def schedule(self, plan: ExecutionPlan, req: ScheduleRequest | None = None) -> ExecutionSchedule:
        r = req or ScheduleRequest(plan_id=plan.plan_id)
        now    = time.time()
        base   = self.URGENCY_OFFSET.get(r.urgency, 0.0)
        start  = now + base + r.start_offset_sec
        end    = start + r.window_sec

        sched = ExecutionSchedule(
            plan_id              = plan.plan_id,
            start_time           = start,
            end_time             = end,
            execution_window_sec = r.window_sec,
            execution_mode       = plan.execution_mode,
        )
        plan.schedule    = sched
        plan.updated_at  = now
        return sched
