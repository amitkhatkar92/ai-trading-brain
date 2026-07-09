"""iios/execution/planning/planning_manager.py
Orchestrates the full execution planning pipeline.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from iios.execution.planning.planning_constants import ExecutionPlanStatus
from iios.execution.planning.planning_exceptions import (
    PlanNotFoundError,
    PlanTerminalError,
)
from iios.execution.planning.core.execution_plan import ExecutionPlan
from iios.execution.planning.core.execution_statistics import ExecutionStatistics
from iios.execution.planning.planning_registry import (
    PlanningRegistry,
    get_planning_registry,
)
from iios.execution.planning.planning_factory import PlanningFactory
from iios.execution.planning.planner.order_planner import OrderPlanner, PlanRequest, PlanResult
from iios.execution.planning.planner.order_splitter import OrderSplitter, SplitConfig, SplitResult
from iios.execution.planning.planner.order_merger import OrderMerger, MergeResult
from iios.execution.planning.planner.execution_batch import ExecutionBatch
from iios.execution.planning.routing.routing_engine import RoutingEngine
from iios.execution.planning.routing.route_registry import VenueInfo
from iios.execution.planning.policies.execution_policy import (
    ExecutionPolicy,
    PolicyRegistry,
    PolicyEvaluation,
)


@dataclass
class PlanningManagerStats:
    plans_created:     int   = 0
    plans_approved:    int   = 0
    plans_completed:   int   = 0
    plans_cancelled:   int   = 0
    plans_failed:      int   = 0
    avg_duration_ms:   float = 0.0
    uptime_sec:        float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "plans_created":   self.plans_created,
            "plans_approved":  self.plans_approved,
            "plans_completed": self.plans_completed,
            "plans_cancelled": self.plans_cancelled,
            "plans_failed":    self.plans_failed,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "uptime_sec":      round(self.uptime_sec, 2),
        }


class PlanningManager:
    """
    Central coordinator for Execution Planning & Smart Routing.

    Responsibilities:
    - Accept PlanRequests and generate ExecutionPlans
    - Manage plan lifecycle (approve / cancel / complete / fail)
    - Support split / merge / batch operations
    - Evaluate plans against registered policies
    - Maintain history and statistics
    """

    def __init__(
        self,
        registry:          PlanningRegistry    | None = None,
        planner:           OrderPlanner        | None = None,
        splitter:          OrderSplitter       | None = None,
        merger:            OrderMerger         | None = None,
        routing_engine:    RoutingEngine       | None = None,
        policy_registry:   PolicyRegistry      | None = None,
        max_recent:        int                 = 1_000,
    ) -> None:
        self._lock             = threading.RLock()
        self._registry         = registry       or get_planning_registry()
        self._planner          = planner        or OrderPlanner()
        self._splitter         = splitter       or OrderSplitter()
        self._merger           = merger         or OrderMerger()
        self._routing          = routing_engine or RoutingEngine()
        self._policies         = policy_registry or PolicyRegistry()
        self._recent:          deque[ExecutionPlan] = deque(maxlen=max_recent)
        self._batches:         dict[str, ExecutionBatch] = {}
        self._stats            = PlanningManagerStats()
        self._started_at       = time.time()
        self._total_dur_ms     = 0.0

    # ── plan creation ─────────────────────────────────────────────────────────

    def create_plan(self, req: PlanRequest) -> PlanResult:
        """Generate, register, and return an ExecutionPlan."""
        t0     = time.time()
        result = self._planner.plan(req)
        plan   = result.plan

        with self._lock:
            self._registry.register(plan)
            self._recent.append(plan)
            self._stats.plans_created += 1
            dur = (time.time() - t0) * 1_000
            self._total_dur_ms += dur
            self._stats.avg_duration_ms = (
                self._total_dur_ms / self._stats.plans_created
            )

        return result

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def get_plan(self, plan_id: str) -> ExecutionPlan:
        return self._registry.get(plan_id)

    def approve_plan(self, plan_id: str) -> ExecutionPlan:
        plan = self._registry.get(plan_id)
        plan.transition_to(ExecutionPlanStatus.APPROVED)
        with self._lock:
            self._stats.plans_approved += 1
        return plan

    def activate_plan(self, plan_id: str) -> ExecutionPlan:
        plan = self._registry.get(plan_id)
        plan.transition_to(ExecutionPlanStatus.ACTIVE)
        return plan

    def complete_plan(self, plan_id: str) -> ExecutionPlan:
        plan = self._registry.get(plan_id)
        plan.transition_to(ExecutionPlanStatus.COMPLETED)
        with self._lock:
            self._stats.plans_completed += 1
        return plan

    def cancel_plan(self, plan_id: str, reason: str = "") -> ExecutionPlan:
        plan = self._registry.get(plan_id)
        plan.transition_to(ExecutionPlanStatus.CANCELLED, reason=reason or "cancelled by manager")
        with self._lock:
            self._stats.plans_cancelled += 1
        return plan

    def fail_plan(self, plan_id: str, reason: str = "") -> ExecutionPlan:
        plan = self._registry.get(plan_id)
        plan.transition_to(ExecutionPlanStatus.FAILED, reason=reason or "failed")
        with self._lock:
            self._stats.plans_failed += 1
        return plan

    def archive_plan(self, plan_id: str) -> ExecutionPlan:
        plan = self._registry.get(plan_id)
        plan.transition_to(ExecutionPlanStatus.ARCHIVED)
        return plan

    # ── split / merge / batch ─────────────────────────────────────────────────

    def split_plan(self, plan_id: str, config: SplitConfig | None = None) -> SplitResult:
        parent = self._registry.get(plan_id)
        result = self._splitter.split(parent, config)
        with self._lock:
            for child in result.child_plans:
                self._registry.register(child)
        return result

    def merge_plans(self, plan_ids: list[str]) -> MergeResult:
        plans  = [self._registry.get(pid) for pid in plan_ids]
        result = self._merger.merge(plans)
        with self._lock:
            self._registry.register(result.merged_plan)
        return result

    def create_batch(
        self,
        plan_ids:    list[str] = (),
        name:        str       = "",
        portfolio_id: str      = "",
        strategy_id: str       = "",
    ) -> ExecutionBatch:
        batch = ExecutionBatch(
            name         = name,
            plan_ids     = list(plan_ids),
            portfolio_id = portfolio_id,
            strategy_id  = strategy_id,
        )
        with self._lock:
            self._batches[batch.batch_id] = batch
        return batch

    def get_batch(self, batch_id: str) -> ExecutionBatch:
        with self._lock:
            if batch_id not in self._batches:
                raise KeyError(f"Batch not found: {batch_id!r}")
            return self._batches[batch_id]

    # ── policy evaluation ─────────────────────────────────────────────────────

    def register_policy(self, policy: ExecutionPolicy, *, overwrite: bool = False) -> None:
        self._policies.register(policy, overwrite=overwrite)

    def evaluate_policies(self, plan_id: str) -> list[PolicyEvaluation]:
        plan = self._registry.get(plan_id)
        return self._policies.evaluate_all(plan)

    # ── venue management ──────────────────────────────────────────────────────

    def register_venue(self, info: VenueInfo, *, overwrite: bool = False) -> None:
        self._routing.register_venue(info, overwrite=overwrite)

    # ── retrieval ─────────────────────────────────────────────────────────────

    def recent(self, n: int = 10) -> list[ExecutionPlan]:
        with self._lock:
            items = list(self._recent)
            return items[-n:] if len(items) >= n else items

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            self._stats.uptime_sec = time.time() - self._started_at
            return self._stats.to_dict()

    def stats_object(self) -> PlanningManagerStats:
        with self._lock:
            self._stats.uptime_sec = time.time() - self._started_at
            return self._stats


# ── singleton ─────────────────────────────────────────────────────────────────

_manager_lock:     threading.Lock             = threading.Lock()
_manager_instance: PlanningManager | None     = None


def get_planning_manager() -> PlanningManager:
    global _manager_instance
    with _manager_lock:
        if _manager_instance is None:
            _manager_instance = PlanningManager()
        return _manager_instance


def reset_planning_manager() -> None:
    global _manager_instance
    with _manager_lock:
        _manager_instance = None
