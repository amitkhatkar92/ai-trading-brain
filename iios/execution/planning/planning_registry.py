"""iios/execution/planning/planning_registry.py
Thread-safe registry of execution plans and metadata.
"""
from __future__ import annotations

import threading
from typing import Any

from iios.execution.planning.planning_constants import DEFAULT_MAX_PLANS
from iios.execution.planning.planning_exceptions import (
    PlanAlreadyExistsError,
    PlanNotFoundError,
    PlanningRegistryOverflowError,
)
from iios.execution.planning.core.execution_plan import ExecutionPlan


class PlanningRegistry:
    """Thread-safe store of active execution plans keyed by plan_id."""

    def __init__(self, max_plans: int = DEFAULT_MAX_PLANS) -> None:
        self._lock:      threading.RLock        = threading.RLock()
        self._max        = max_plans
        self._plans:     dict[str, ExecutionPlan] = {}

    # ── plans ─────────────────────────────────────────────────────────────────

    def register(self, plan: ExecutionPlan, *, overwrite: bool = False) -> None:
        with self._lock:
            if plan.plan_id in self._plans and not overwrite:
                raise PlanAlreadyExistsError(plan_id=plan.plan_id)
            if len(self._plans) >= self._max and plan.plan_id not in self._plans:
                raise PlanningRegistryOverflowError(
                    capacity=self._max, current=len(self._plans)
                )
            self._plans[plan.plan_id] = plan

    def get(self, plan_id: str) -> ExecutionPlan:
        with self._lock:
            if plan_id not in self._plans:
                raise PlanNotFoundError(plan_id=plan_id)
            return self._plans[plan_id]

    def has(self, plan_id: str) -> bool:
        with self._lock:
            return plan_id in self._plans

    def remove(self, plan_id: str) -> None:
        with self._lock:
            self._plans.pop(plan_id, None)

    def all_plans(self) -> list[str]:
        with self._lock:
            return list(self._plans.keys())

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {
                "registered_plans": len(self._plans),
                "max_plans":        self._max,
            }


# ── singleton ─────────────────────────────────────────────────────────────────

_registry_lock:     threading.Lock              = threading.Lock()
_registry_instance: PlanningRegistry | None     = None


def get_planning_registry() -> PlanningRegistry:
    global _registry_instance
    with _registry_lock:
        if _registry_instance is None:
            _registry_instance = PlanningRegistry()
        return _registry_instance


def reset_planning_registry() -> None:
    global _registry_instance
    with _registry_lock:
        _registry_instance = None
