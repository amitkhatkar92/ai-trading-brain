"""
workflow_validator.py — iios.workflow.orchestration
----------------------------------------------------
WorkflowValidator — validates workflow definitions before execution.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .exceptions import WorkflowValidationError
from .workflow_definition import WorkflowDefinition
from .workflow_dependency_engine import WorkflowDependencyEngine

_log = get_logger(__name__)


@dataclass(frozen=True)
class ValidationResult:
    definition_id: str
    valid:         bool
    issues:        tuple   # Tuple[str, ...]

    @property
    def issue_list(self) -> List[str]:
        return list(self.issues)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "definition_id": self.definition_id,
            "valid":         self.valid,
            "issues":        self.issue_list,
        }


class WorkflowValidator:
    """
    Validates workflow definitions for structural correctness.

    Thread-safe — stateless.
    """

    def __init__(self) -> None:
        self._dep_engine = WorkflowDependencyEngine()

    def validate(self, definition: WorkflowDefinition) -> ValidationResult:
        issues: List[str] = []

        if not definition.definition_id:
            issues.append("definition_id is empty")

        if not definition.name:
            issues.append("definition name is empty")

        if definition.step_count == 0:
            issues.append("definition has no steps")

        if definition.entry_step_id and definition.entry_step_id not in definition.step_ids:
            issues.append(
                f"entry_step_id {definition.entry_step_id!r} not in steps"
            )

        # Validate each step
        seen_ids: set = set()
        for step in definition.steps:
            if not step.step_id:
                issues.append("Step has empty step_id")
            if not step.name:
                issues.append(f"Step {step.step_id!r} has empty name")
            if not step.handler:
                issues.append(f"Step {step.step_id!r} has empty handler")
            if step.step_id in seen_ids:
                issues.append(f"Duplicate step_id {step.step_id!r}")
            seen_ids.add(step.step_id)

        # Validate dependency graph (no cycles)
        if not issues:
            if not self._dep_engine.validate_no_cycles(definition):
                issues.append("Circular dependency detected in step graph")

        valid  = len(issues) == 0
        result = ValidationResult(
            definition_id = definition.definition_id,
            valid         = valid,
            issues        = tuple(issues),
        )
        if not valid:
            _log.warning(
                f"Validator: definition={definition.definition_id!r} "
                f"failed with {len(issues)} issues"
            )
        return result

    def validate_or_raise(self, definition: WorkflowDefinition) -> None:
        result = self.validate(definition)
        if not result.valid:
            raise WorkflowValidationError(
                f"Definition {definition.definition_id!r} failed validation",
                issues=result.issue_list,
            )
