"""
workflow_definition.py — iios.workflow.orchestration
------------------------------------------------------
WorkflowDefinition — immutable description of a workflow.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 4
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_WORKFLOW_TIMEOUT,
    PREFIX_DEFINITION,
    WorkflowType,
)
from .workflow_step import WorkflowStep


@dataclass(frozen=True)
class WorkflowDefinition:
    """
    Immutable workflow definition.

    Describes the structure, steps, and configuration of an enterprise
    workflow.  All execution behaviour is driven by this definition and
    registered handlers — no business logic is embedded here.
    """
    definition_id:         str
    name:                  str
    description:           str
    workflow_type:         WorkflowType
    steps:                 tuple              # Tuple[WorkflowStep, ...]
    entry_step_id:         str                # first step to execute
    exit_step_ids:         tuple              # Tuple[str, ...]  — terminal steps
    version:               str
    max_retries:           int                # workflow-level default
    timeout_seconds:       float             # 0 = no workflow-level timeout
    enable_checkpointing:  bool
    enable_compensation:   bool
    metadata:              Dict[str, Any]
    created_at:            str

    @classmethod
    def create(
        cls,
        name:          str,
        steps:         List[WorkflowStep],
        *,
        workflow_type:         WorkflowType           = WorkflowType.SEQUENTIAL,
        entry_step_id:         Optional[str]          = None,
        exit_step_ids:         Optional[List[str]]    = None,
        description:           str                    = "",
        version:               str                    = "1.0.0",
        max_retries:           int                    = DEFAULT_MAX_RETRIES,
        timeout_seconds:       float                  = DEFAULT_WORKFLOW_TIMEOUT,
        enable_checkpointing:  bool                   = True,
        enable_compensation:   bool                   = True,
        metadata:              Optional[Dict[str, Any]] = None,
        definition_id:         Optional[str]          = None,
    ) -> "WorkflowDefinition":
        step_ids = [s.step_id for s in steps]
        # Default entry = first step; default exits = steps with no outgoing deps
        if entry_step_id is None and step_ids:
            entry_step_id = step_ids[0]
        if exit_step_ids is None:
            # Steps not listed as a dependency of any other step are exits
            all_deps: set = set()
            for s in steps:
                all_deps.update(s.dependencies)
            exit_ids = [sid for sid in step_ids if sid not in all_deps] or step_ids[-1:]
        else:
            exit_ids = exit_step_ids

        return cls(
            definition_id        = definition_id or f"{PREFIX_DEFINITION}{uuid.uuid4().hex[:12]}",
            name                 = name,
            description          = description,
            workflow_type        = workflow_type,
            steps                = tuple(steps),
            entry_step_id        = entry_step_id or "",
            exit_step_ids        = tuple(exit_ids),
            version              = version,
            max_retries          = max_retries,
            timeout_seconds      = timeout_seconds,
            enable_checkpointing = enable_checkpointing,
            enable_compensation  = enable_compensation,
            metadata             = dict(metadata or {}),
            created_at           = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ── Introspection ─────────────────────────────────────────────────────────

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def step_map(self) -> Dict[str, WorkflowStep]:
        return {s.step_id: s for s in self.steps}

    @property
    def step_ids(self) -> List[str]:
        return [s.step_id for s in self.steps]

    def get_step(self, step_id: str) -> WorkflowStep:
        for s in self.steps:
            if s.step_id == step_id:
                return s
        from .exceptions import WorkflowDefinitionError
        raise WorkflowDefinitionError(f"Step not found in definition: {step_id!r}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "definition_id":        self.definition_id,
            "name":                 self.name,
            "description":          self.description,
            "workflow_type":        self.workflow_type.value,
            "step_count":           self.step_count,
            "entry_step_id":        self.entry_step_id,
            "exit_step_ids":        list(self.exit_step_ids),
            "version":              self.version,
            "max_retries":          self.max_retries,
            "timeout_seconds":      self.timeout_seconds,
            "enable_checkpointing": self.enable_checkpointing,
            "enable_compensation":  self.enable_compensation,
            "created_at":           self.created_at,
        }


@dataclass(frozen=True)
class WorkflowExecutionRequest:
    """
    Immutable input to the orchestration engine.

    Carries the approved workflow definition reference, context data,
    and execution configuration.
    """
    request_id:     str
    workflow_id:    str     # logical workflow instance identifier
    definition_id:  str     # which definition to execute
    context_data:   Dict[str, Any]
    execution_config: Dict[str, Any]
    priority:       int
    created_at:     str

    @classmethod
    def create(
        cls,
        workflow_id:    str,
        definition_id:  str,
        *,
        context_data:   Optional[Dict[str, Any]] = None,
        execution_config: Optional[Dict[str, Any]] = None,
        priority:       int                      = 5,
        request_id:     Optional[str]            = None,
    ) -> "WorkflowExecutionRequest":
        return cls(
            request_id      = request_id or f"wreq-{uuid.uuid4().hex[:10]}",
            workflow_id     = workflow_id,
            definition_id   = definition_id,
            context_data    = dict(context_data or {}),
            execution_config = dict(execution_config or {}),
            priority        = priority,
            created_at      = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id":     self.request_id,
            "workflow_id":    self.workflow_id,
            "definition_id":  self.definition_id,
            "priority":       self.priority,
            "created_at":     self.created_at,
        }
