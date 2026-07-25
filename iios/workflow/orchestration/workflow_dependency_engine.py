"""
workflow_dependency_engine.py — iios.workflow.orchestration
------------------------------------------------------------
WorkflowDependencyEngine — resolves step execution order via
Kahn's topological sort algorithm.

Returns execution waves: each wave is a group of steps whose
dependencies are all satisfied by previous waves.  Steps within
a wave can run in parallel.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Set

from iios.common.logging.logging_manager import get_logger

from .exceptions import WorkflowDependencyError
from .workflow_definition import WorkflowDefinition

_log = get_logger(__name__)


class WorkflowDependencyEngine:
    """
    Resolves workflow step dependencies and produces execution waves.

    Thread-safe — stateless.
    """

    def get_execution_waves(self, definition: WorkflowDefinition) -> List[List[str]]:
        """
        Return a list of execution waves.

        Each wave is a list of step_ids that can execute in parallel
        (all their dependencies are satisfied by previous waves).

        Raises WorkflowDependencyError on circular dependencies.
        """
        steps    = list(definition.steps)
        step_ids = {s.step_id for s in steps}

        # Build in-degree count and adjacency list
        in_degree: Dict[str, int] = {s.step_id: 0 for s in steps}
        adjacency: Dict[str, List[str]] = {s.step_id: [] for s in steps}

        for step in steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    raise WorkflowDependencyError(
                        f"Step {step.step_id!r} depends on unknown step {dep!r}"
                    )
                adjacency[dep].append(step.step_id)
                in_degree[step.step_id] += 1

        # Kahn's algorithm — group by wave
        waves:   List[List[str]] = []
        current_wave = [sid for sid, deg in in_degree.items() if deg == 0]

        while current_wave:
            waves.append(sorted(current_wave))   # sorted for determinism
            next_wave: List[str] = []
            for sid in current_wave:
                for neighbour in adjacency[sid]:
                    in_degree[neighbour] -= 1
                    if in_degree[neighbour] == 0:
                        next_wave.append(neighbour)
            current_wave = next_wave

        processed = sum(len(w) for w in waves)
        if processed != len(steps):
            raise WorkflowDependencyError(
                f"Circular dependency detected in definition {definition.definition_id!r}"
            )

        _log.debug(
            f"DependencyEngine: {len(waves)} waves, "
            f"{len(steps)} steps for {definition.definition_id!r}"
        )
        return waves

    def get_execution_order(self, definition: WorkflowDefinition) -> List[str]:
        """
        Return a flat topological ordering of step_ids.
        """
        waves = self.get_execution_waves(definition)
        return [sid for wave in waves for sid in wave]

    def validate_no_cycles(self, definition: WorkflowDefinition) -> bool:
        """Return True if the definition has no circular dependencies."""
        try:
            self.get_execution_waves(definition)
            return True
        except WorkflowDependencyError:
            return False

    def get_dependents(
        self,
        step_id:    str,
        definition: WorkflowDefinition,
    ) -> List[str]:
        """Return step_ids that directly depend on step_id."""
        return [
            s.step_id for s in definition.steps
            if step_id in s.dependencies
        ]

    def get_dependencies_satisfied(
        self,
        step_id:         str,
        definition:      WorkflowDefinition,
        completed_steps: Set[str],
    ) -> bool:
        """Return True if all dependencies of step_id are in completed_steps."""
        step = definition.get_step(step_id)
        if step is None:
            return False
        return all(dep in completed_steps for dep in step.dependencies)
