"""iios/execution/planning/core/execution_statistics.py"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionStatistics:
    """Aggregated planning engine statistics — call .record_*() after each event."""

    plans_created:           int   = 0
    plans_completed:         int   = 0
    plans_failed:            int   = 0
    plans_cancelled:         int   = 0
    plans_archived:          int   = 0
    total_planning_calls:    int   = 0
    total_routing_calls:     int   = 0
    avg_planning_duration_ms: float = 0.0
    min_planning_duration_ms: float = float("inf")
    max_planning_duration_ms: float = 0.0
    avg_cost_bps:            float = 0.0
    avg_route_score:         float = 0.0
    reset_at:                float = field(default_factory=time.time)

    # ── private accumulators ─────────────────────────────────────────────────
    _planning_duration_sum: float = field(default=0.0, repr=False)
    _cost_bps_sum:          float = field(default=0.0, repr=False)
    _route_score_sum:       float = field(default=0.0, repr=False)

    def record_plan_created(self) -> None:
        self.plans_created += 1

    def record_plan_completed(self) -> None:
        self.plans_completed += 1

    def record_plan_failed(self) -> None:
        self.plans_failed += 1

    def record_plan_cancelled(self) -> None:
        self.plans_cancelled += 1

    def record_plan_archived(self) -> None:
        self.plans_archived += 1

    def record_planning_duration(self, duration_ms: float) -> None:
        self.total_planning_calls += 1
        self._planning_duration_sum += duration_ms
        self.avg_planning_duration_ms = self._planning_duration_sum / self.total_planning_calls
        self.min_planning_duration_ms = min(self.min_planning_duration_ms, duration_ms)
        self.max_planning_duration_ms = max(self.max_planning_duration_ms, duration_ms)

    def record_cost_bps(self, cost_bps: float) -> None:
        n = self.plans_completed or 1
        self._cost_bps_sum += cost_bps
        self.avg_cost_bps = self._cost_bps_sum / n

    def record_route_score(self, score: float) -> None:
        self.total_routing_calls += 1
        self._route_score_sum += score
        self.avg_route_score = self._route_score_sum / self.total_routing_calls

    def reset(self) -> None:
        self.plans_created            = 0
        self.plans_completed          = 0
        self.plans_failed             = 0
        self.plans_cancelled          = 0
        self.plans_archived           = 0
        self.total_planning_calls     = 0
        self.total_routing_calls      = 0
        self.avg_planning_duration_ms = 0.0
        self.min_planning_duration_ms = float("inf")
        self.max_planning_duration_ms = 0.0
        self.avg_cost_bps             = 0.0
        self.avg_route_score          = 0.0
        self._planning_duration_sum   = 0.0
        self._cost_bps_sum            = 0.0
        self._route_score_sum         = 0.0
        self.reset_at                 = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "plans_created":            self.plans_created,
            "plans_completed":          self.plans_completed,
            "plans_failed":             self.plans_failed,
            "plans_cancelled":          self.plans_cancelled,
            "plans_archived":           self.plans_archived,
            "total_planning_calls":     self.total_planning_calls,
            "total_routing_calls":      self.total_routing_calls,
            "avg_planning_duration_ms": self.avg_planning_duration_ms,
            "min_planning_duration_ms": self.min_planning_duration_ms
                                        if self.min_planning_duration_ms < float("inf")
                                        else None,
            "max_planning_duration_ms": self.max_planning_duration_ms,
            "avg_cost_bps":             self.avg_cost_bps,
            "avg_route_score":          self.avg_route_score,
            "reset_at":                 self.reset_at,
        }
