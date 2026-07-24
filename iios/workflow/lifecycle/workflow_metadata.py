"""
workflow_metadata.py — iios.workflow.lifecycle
-----------------------------------------------
WorkflowMetadata — operational and configuration metadata
for a workflow session.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .constants import (
    DEFAULT_VERSION,
    WorkflowPriority,
    WorkflowType,
)


@dataclass(frozen=True)
class WorkflowMetadata:
    """
    Immutable metadata describing the characteristics of a workflow session.

    Records workflow type, priority, owning enterprise, version and tags.
    """
    workflow_type:     WorkflowType
    workflow_priority: WorkflowPriority
    enterprise_id:     str
    owner_id:          str
    workflow_version:  str
    tags:              tuple   # Tuple[str, ...]
    custom:            Dict[str, Any]

    @classmethod
    def create(
        cls,
        workflow_type:     WorkflowType     = WorkflowType.SEQUENTIAL,
        workflow_priority: WorkflowPriority = WorkflowPriority.NORMAL,
        *,
        enterprise_id:    str = "iios",
        owner_id:         str = "system",
        workflow_version: str = DEFAULT_VERSION,
        tags:             Optional[List[str]]     = None,
        custom:           Optional[Dict[str, Any]] = None,
    ) -> "WorkflowMetadata":
        return cls(
            workflow_type     = workflow_type,
            workflow_priority = workflow_priority,
            enterprise_id     = enterprise_id,
            owner_id          = owner_id,
            workflow_version  = workflow_version,
            tags              = tuple(tags or []),
            custom            = dict(custom or {}),
        )

    @classmethod
    def default(cls) -> "WorkflowMetadata":
        return cls.create()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_type":     self.workflow_type.value,
            "workflow_priority": self.workflow_priority.value,
            "enterprise_id":     self.enterprise_id,
            "owner_id":          self.owner_id,
            "workflow_version":  self.workflow_version,
            "tags":              list(self.tags),
            "custom":            self.custom,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WorkflowMetadata":
        return cls(
            workflow_type     = WorkflowType(
                d.get("workflow_type", WorkflowType.SEQUENTIAL.value)
            ),
            workflow_priority = WorkflowPriority(
                d.get("workflow_priority", WorkflowPriority.NORMAL.value)
            ),
            enterprise_id    = d.get("enterprise_id", "iios"),
            owner_id         = d.get("owner_id", "system"),
            workflow_version = d.get("workflow_version", DEFAULT_VERSION),
            tags             = tuple(d.get("tags", [])),
            custom           = d.get("custom", {}),
        )
