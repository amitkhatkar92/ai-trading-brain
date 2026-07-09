"""iios/execution/planning/execution_planning_engine.py
Top-level facade for the Execution Planning & Smart Routing Engine.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from iios.execution.planning.planning_constants import (
    PLANNING_ENGINE_SYSTEM_ID,
    PLANNING_ENGINE_VERSION,
)
from iios.execution.planning.planning_exceptions import (
    PlanningEngineAlreadyRunningError,
    PlanningEngineNotInitializedError,
)
from iios.execution.planning.planning_manager import (
    PlanningManager,
    get_planning_manager,
    reset_planning_manager,
)
from iios.execution.planning.planning_registry import (
    PlanningRegistry,
    get_planning_registry,
    reset_planning_registry,
)
from iios.execution.planning.core.execution_plan import ExecutionPlan
from iios.execution.planning.planner.order_planner import PlanRequest, PlanResult
from iios.execution.planning.planner.order_splitter import SplitConfig, SplitResult
from iios.execution.planning.planner.order_merger import MergeResult
from iios.execution.planning.planner.execution_batch import ExecutionBatch
from iios.execution.planning.routing.route_registry import VenueInfo
from iios.execution.planning.policies.execution_policy import (
    ExecutionPolicy,
    PolicyEvaluation,
)


class ExecutionPlanningEngine:
    """
    Top-level facade for the Execution Planning & Smart Routing Engine.

    Public API consumed by the Execution Engine and higher IIOS layers.
    """

    VERSION   = PLANNING_ENGINE_VERSION
    SYSTEM_ID = PLANNING_ENGINE_SYSTEM_ID

    def __init__(self) -> None:
        self._lock:     threading.RLock          = threading.RLock()
        self._running:  bool                     = False
        self._manager:  PlanningManager | None   = None
        self._registry: PlanningRegistry | None  = None

    # ── lifecycle ────────────────────────────────────────────────────────────

    def initialize(
        self,
        manager:  PlanningManager  | None = None,
        registry: PlanningRegistry | None = None,
    ) -> None:
        with self._lock:
            if self._running:
                raise PlanningEngineAlreadyRunningError()
            self._registry = registry or get_planning_registry()
            self._manager  = manager  or get_planning_manager()
            self._running  = True

    def shutdown(self) -> None:
        with self._lock:
            self._running  = False
            self._manager  = None
            self._registry = None

    @property
    def is_running(self) -> bool:
        return self._running

    # ── planning API ─────────────────────────────────────────────────────────

    def create_plan(self, req: PlanRequest) -> PlanResult:
        self._require_running()
        return self._manager.create_plan(req)

    async def create_plan_async(self, req: PlanRequest) -> PlanResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.create_plan(req))

    def get_plan(self, plan_id: str) -> ExecutionPlan:
        self._require_running()
        return self._manager.get_plan(plan_id)

    def approve_plan(self, plan_id: str) -> ExecutionPlan:
        self._require_running()
        return self._manager.approve_plan(plan_id)

    def activate_plan(self, plan_id: str) -> ExecutionPlan:
        self._require_running()
        return self._manager.activate_plan(plan_id)

    def complete_plan(self, plan_id: str) -> ExecutionPlan:
        self._require_running()
        return self._manager.complete_plan(plan_id)

    def cancel_plan(self, plan_id: str, reason: str = "") -> ExecutionPlan:
        self._require_running()
        return self._manager.cancel_plan(plan_id, reason)

    def fail_plan(self, plan_id: str, reason: str = "") -> ExecutionPlan:
        self._require_running()
        return self._manager.fail_plan(plan_id, reason)

    def archive_plan(self, plan_id: str) -> ExecutionPlan:
        self._require_running()
        return self._manager.archive_plan(plan_id)

    # ── advanced operations ───────────────────────────────────────────────────

    def split_plan(self, plan_id: str, config: SplitConfig | None = None) -> SplitResult:
        self._require_running()
        return self._manager.split_plan(plan_id, config)

    def merge_plans(self, plan_ids: list[str]) -> MergeResult:
        self._require_running()
        return self._manager.merge_plans(plan_ids)

    def create_batch(self, plan_ids: list[str] = (), **kwargs: Any) -> ExecutionBatch:
        self._require_running()
        return self._manager.create_batch(plan_ids, **kwargs)

    def get_batch(self, batch_id: str) -> ExecutionBatch:
        self._require_running()
        return self._manager.get_batch(batch_id)

    # ── venue / policy management ─────────────────────────────────────────────

    def register_venue(self, info: VenueInfo, *, overwrite: bool = False) -> None:
        self._require_running()
        self._manager.register_venue(info, overwrite=overwrite)

    def register_policy(self, policy: ExecutionPolicy, *, overwrite: bool = False) -> None:
        self._require_running()
        self._manager.register_policy(policy, overwrite=overwrite)

    def evaluate_policies(self, plan_id: str) -> list[PolicyEvaluation]:
        self._require_running()
        return self._manager.evaluate_policies(plan_id)

    # ── monitoring ────────────────────────────────────────────────────────────

    def recent(self, n: int = 10) -> list[ExecutionPlan]:
        self._require_running()
        return self._manager.recent(n)

    def health(self) -> dict[str, Any]:
        return {
            "status":    "running" if self._running else "stopped",
            "version":   self.VERSION,
            "system_id": self.SYSTEM_ID,
        }

    def stats(self) -> dict[str, Any]:
        self._require_running()
        return self._manager.statistics()

    # ── internal ─────────────────────────────────────────────────────────────

    def _require_running(self) -> None:
        if not self._running or self._manager is None:
            raise PlanningEngineNotInitializedError(
                "ExecutionPlanningEngine is not initialized. Call initialize() first."
            )


# ── module-level singleton ────────────────────────────────────────────────────

_engine_lock:     threading.Lock                      = threading.Lock()
_engine_instance: ExecutionPlanningEngine | None      = None


def get_planning_engine() -> ExecutionPlanningEngine:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = ExecutionPlanningEngine()
        return _engine_instance


def reset_planning_engine() -> None:
    global _engine_instance
    with _engine_lock:
        if _engine_instance is not None:
            _engine_instance.shutdown()
        _engine_instance = None
