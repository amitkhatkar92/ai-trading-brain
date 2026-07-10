"""iios/integration/research/workflow/research_workflow.py

DAG-based research workflow for sequencing experiments with dependencies.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from iios.integration.research.core.research_experiment import ResearchExperiment
from iios.integration.research.core.research_result     import ResearchResult
from iios.integration.research.research_constants        import WorkflowStatus
from iios.integration.research.research_exceptions       import (
    WorkflowStateError,
    WorkflowStepNotFoundError,
    WorkflowValidationError,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """One step in a research workflow."""
    step_id:       str       = field(default_factory=lambda: str(uuid.uuid4()))
    name:          str       = ""
    experiment_id: str       = ""
    depends_on:    list[str] = field(default_factory=list)   # step_ids
    status:        str       = "pending"   # pending | running | completed | failed | skipped
    result_id:     str       = ""
    started_at:    float | None = None
    completed_at:  float | None = None

    def is_complete(self) -> bool:
        return self.status in ("completed", "failed", "skipped")

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id":       self.step_id,
            "name":          self.name,
            "experiment_id": self.experiment_id,
            "depends_on":    list(self.depends_on),
            "status":        self.status,
        }


class ResearchWorkflow:
    """
    Directed Acyclic Graph (DAG) of experiment steps.

    Steps can declare dependencies; only steps whose dependencies
    are all completed will be returned by ``next_runnable_steps()``.
    """

    def __init__(
        self,
        project_id:  str = "",
        name:        str = "",
        description: str = "",
    ) -> None:
        self.workflow_id  = str(uuid.uuid4())
        self.project_id   = project_id
        self.name         = name
        self.description  = description
        self.status       = WorkflowStatus.PENDING
        self.created_at   = time.time()
        self._steps: dict[str, WorkflowStep] = {}

    # ── Step management ───────────────────────────────────────────────────────

    def add_step(self, step: WorkflowStep) -> None:
        """Add a step. Raises WorkflowValidationError on dependency cycle."""
        if step.step_id in self._steps:
            raise WorkflowValidationError(f"Step '{step.step_id}' already in workflow.")
        # Validate dependencies exist
        for dep in step.depends_on:
            if dep not in self._steps:
                raise WorkflowValidationError(
                    f"Dependency '{dep}' not found in workflow (add dependencies first)."
                )
        self._steps[step.step_id] = step

    def get_step(self, step_id: str) -> WorkflowStep:
        s = self._steps.get(step_id)
        if s is None:
            raise WorkflowStepNotFoundError(f"Step '{step_id}' not found.")
        return s

    def remove_step(self, step_id: str) -> None:
        self._steps.pop(step_id, None)

    def step_count(self) -> int:
        return len(self._steps)

    # ── Execution planning ────────────────────────────────────────────────────

    def next_runnable_steps(self) -> list[WorkflowStep]:
        """
        Return steps that are pending and whose dependencies are all completed.
        """
        completed_ids = {s.step_id for s in self._steps.values() if s.status == "completed"}
        return [
            s for s in self._steps.values()
            if s.status == "pending"
            and all(dep in completed_ids for dep in s.depends_on)
        ]

    def is_complete(self) -> bool:
        return all(s.is_complete() for s in self._steps.values())

    def has_failures(self) -> bool:
        return any(s.status == "failed" for s in self._steps.values())

    # ── Execution ─────────────────────────────────────────────────────────────

    async def execute(
        self,
        experiments:   dict[str, ResearchExperiment],
        runner_fn:     Any,   # async callable: (experiment) -> ResearchResult
    ) -> dict[str, ResearchResult]:
        """
        Execute workflow steps in dependency order.
        Returns a dict mapping step_id -> ResearchResult.
        """
        if self.status == WorkflowStatus.RUNNING:
            raise WorkflowStateError("Workflow is already running.")

        self.status = WorkflowStatus.RUNNING
        results: dict[str, ResearchResult] = {}

        try:
            while True:
                runnable = self.next_runnable_steps()
                if not runnable:
                    break   # nothing more to run

                # Run all runnable steps (could parallelize; sequential for safety)
                for step in runnable:
                    exp = experiments.get(step.experiment_id)
                    if exp is None:
                        step.status = "failed"
                        continue
                    step.status     = "running"
                    step.started_at = time.time()
                    try:
                        result = await runner_fn(exp)
                        step.status       = "completed"
                        step.result_id    = result.result_id
                        step.completed_at = time.time()
                        results[step.step_id] = result
                    except Exception as exc:
                        step.status       = "failed"
                        step.completed_at = time.time()
                        logger.error("[Workflow] Step '%s' failed: %s", step.name, exc)

                if self.is_complete():
                    break

            self.status = WorkflowStatus.FAILED if self.has_failures() else WorkflowStatus.COMPLETED

        except Exception as exc:
            self.status = WorkflowStatus.FAILED
            logger.error("[Workflow] '%s' failed: %s", self.name, exc)
            raise

        return results

    # ── Info ──────────────────────────────────────────────────────────────────

    def all_steps(self) -> list[WorkflowStep]:
        return list(self._steps.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "project_id":  self.project_id,
            "name":        self.name,
            "status":      self.status.value,
            "steps":       [s.to_dict() for s in self._steps.values()],
            "created_at":  self.created_at,
        }
