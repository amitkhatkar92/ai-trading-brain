"""
planning_engine.py -- iios.ai.orchestrator.engine
===================================================
:class:`PlanningEngine` — decomposes objectives into executable plans.

A10 Enterprise AI Orchestrator — Phase 3, Module 10
"""
from __future__ import annotations

import threading
from collections import defaultdict, deque
from typing import Dict, FrozenSet, List, Optional, Tuple

from ..core.orchestration_types import PlanStatus
from ..core.plan_types import (
    ExecutionPlan,
    PlanDependency,
    PlanningContext,
    PlanStep,
)
from ..exceptions.orchestrator_exceptions import (
    AIPlanDependencyError,
    AIPlanGenerationError,
    AIPlanNotFoundError,
    AIReplanningError,
)


class PlanningEngine:
    """
    Decomposes objectives into structured, dependency-aware execution plans.

    Decomposition strategy
    ----------------------
    - Objective contains ``|`` → each part becomes a **parallel** step.
    - Objective contains ``;`` → each part becomes a **sequential** step
      (each depends on the previous).
    - Otherwise → single step.

    Steps can be added dynamically via :meth:`add_step`.
    Plans are validated via :meth:`validate_plan` (DAG check).
    Execution order is computed via :meth:`get_execution_order` (topological batches).
    """

    def __init__(self) -> None:
        self._lock:  threading.Lock           = threading.Lock()
        self._plans: Dict[str, ExecutionPlan] = {}

    # ── plan creation ─────────────────────────────────────────────────────────

    def create_plan(self, context: PlanningContext) -> ExecutionPlan:
        """Decompose *context.objective* and return a READY :class:`ExecutionPlan`."""
        try:
            steps, deps = self._decompose(context.objective, context.constraints)
            plan = ExecutionPlan.create(
                objective    = context.objective,
                steps        = tuple(steps),
                dependencies = tuple(deps),
            ).with_status(PlanStatus.READY)

            with self._lock:
                self._plans[plan.plan_id] = plan

            return plan
        except Exception as exc:
            raise AIPlanGenerationError(f"Plan generation failed: {exc}") from exc

    def _decompose(
        self,
        objective:   str,
        constraints: FrozenSet[str],
    ) -> Tuple[List[PlanStep], List[PlanDependency]]:
        steps: List[PlanStep]        = []
        deps:  List[PlanDependency]  = []

        if "|" in objective:
            for part in (p.strip() for p in objective.split("|") if p.strip()):
                steps.append(PlanStep.create(
                    name        = part[:64],
                    action      = "execute",
                    description = part,
                    parallel    = True,
                ))
        elif ";" in objective:
            prev_id: Optional[str] = None
            for part in (p.strip() for p in objective.split(";") if p.strip()):
                dep_set = frozenset({prev_id}) if prev_id else frozenset()
                step = PlanStep.create(
                    name         = part[:64],
                    action       = "execute",
                    description  = part,
                    dependencies = dep_set,
                )
                if prev_id:
                    deps.append(PlanDependency.create(from_step=prev_id, to_step=step.step_id))
                steps.append(step)
                prev_id = step.step_id
        else:
            steps.append(PlanStep.create(
                name        = objective[:64],
                action      = "execute",
                description = objective,
            ))

        return steps, deps

    # ── plan management ───────────────────────────────────────────────────────

    def add_step(self, plan: ExecutionPlan, step: PlanStep) -> ExecutionPlan:
        """Return a new plan with *step* appended.  Updates the store."""
        new_plan = plan.with_steps(plan.steps + (step,))
        with self._lock:
            self._plans[new_plan.plan_id] = new_plan
        return new_plan

    def get_plan(self, plan_id: str) -> ExecutionPlan:
        with self._lock:
            plan = self._plans.get(plan_id)
        if plan is None:
            raise AIPlanNotFoundError(f"Plan '{plan_id}' not found")
        return plan

    def validate_plan(self, plan: ExecutionPlan) -> bool:
        """
        Return True if the plan's dependency graph is acyclic (DAG).
        Raises :class:`AIPlanDependencyError` on cycle or unknown step reference.
        """
        step_ids = {s.step_id for s in plan.steps}

        for dep in plan.dependencies:
            if dep.from_step not in step_ids or dep.to_step not in step_ids:
                raise AIPlanDependencyError(
                    f"Dependency references unknown step: {dep.from_step} → {dep.to_step}"
                )

        in_degree: Dict[str, int]        = defaultdict(int)
        graph:     Dict[str, List[str]]  = defaultdict(list)

        for dep in plan.dependencies:
            graph[dep.from_step].append(dep.to_step)
            in_degree[dep.to_step] += 1

        for step in plan.steps:
            for dep_id in step.dependencies:
                if dep_id in step_ids:
                    graph[dep_id].append(step.step_id)
                    in_degree[step.step_id] += 1

        queue   = deque(s for s in step_ids if in_degree[s] == 0)
        visited = 0
        while queue:
            node = queue.popleft()
            visited += 1
            for child in graph[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if visited != len(step_ids):
            raise AIPlanDependencyError("Plan contains a dependency cycle")
        return True

    def get_execution_order(self, plan: ExecutionPlan) -> List[List[str]]:
        """
        Return topologically-sorted batches of step_ids.

        Each inner list contains steps that may run in parallel.
        Batch N must complete before batch N+1 begins.
        """
        step_ids = {s.step_id for s in plan.steps}
        in_degree: Dict[str, int]       = defaultdict(int)
        graph:     Dict[str, List[str]] = defaultdict(list)

        for dep in plan.dependencies:
            graph[dep.from_step].append(dep.to_step)
            in_degree[dep.to_step] += 1

        for step in plan.steps:
            for dep_id in step.dependencies:
                if dep_id in step_ids:
                    graph[dep_id].append(step.step_id)
                    in_degree[step.step_id] += 1

        batches: List[List[str]] = []
        queue = deque(s for s in step_ids if in_degree[s] == 0)
        while queue:
            batch = list(queue)
            queue.clear()
            batches.append(batch)
            for node in batch:
                for child in graph[node]:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        queue.append(child)

        return batches

    def replan(self, plan: ExecutionPlan, failed_step_id: str) -> ExecutionPlan:
        """
        Generate a recovery plan by removing the failed step and its transitive
        dependants.  The new plan is stored and returned.
        """
        step_ids = {s.step_id for s in plan.steps}
        if failed_step_id not in step_ids:
            raise AIReplanningError(f"Failed step '{failed_step_id}' not in plan")

        try:
            graph: Dict[str, List[str]] = defaultdict(list)
            for dep in plan.dependencies:
                graph[dep.from_step].append(dep.to_step)
            for step in plan.steps:
                for dep_id in step.dependencies:
                    graph[dep_id].append(step.step_id)

            removed: set = {failed_step_id}
            queue: deque = deque([failed_step_id])
            while queue:
                node = queue.popleft()
                for child in graph[node]:
                    if child not in removed:
                        removed.add(child)
                        queue.append(child)

            new_steps = tuple(s for s in plan.steps if s.step_id not in removed)
            new_deps  = tuple(
                d for d in plan.dependencies
                if d.from_step not in removed and d.to_step not in removed
            )
            new_plan = ExecutionPlan.create(
                objective    = plan.objective,
                steps        = new_steps,
                dependencies = new_deps,
            ).with_status(PlanStatus.READY)

            with self._lock:
                self._plans[new_plan.plan_id] = new_plan
            return new_plan

        except AIReplanningError:
            raise
        except Exception as exc:
            raise AIReplanningError(f"Replanning failed: {exc}") from exc

    # ── stats ─────────────────────────────────────────────────────────────────

    def plan_count(self) -> int:
        with self._lock:
            return len(self._plans)
