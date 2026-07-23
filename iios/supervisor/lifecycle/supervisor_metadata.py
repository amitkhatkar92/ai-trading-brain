"""
supervisor_metadata.py — iios.supervisor.lifecycle
---------------------------------------------------
Immutable supplementary metadata for a supervisor session.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 1
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .constants import VERSION


@dataclass(frozen=True)
class SupervisorMetadata:
    """
    Immutable supplementary metadata attached to a supervisor session.

    Fields
    ------
    supervisor_id :     Supervised entity identifier.
    source :            System or component that initiated the session.
    workflow_id :       Workflow routing context.
    tags :              Free-form key/value tags for filtering.
    notes :             Optional human-readable notes.
    framework_version : Framework version string.
    """
    supervisor_id:     str            = ""
    source:            str            = ""
    workflow_id:       str            = ""
    tags:              Dict[str, str] = field(default_factory=dict)
    notes:             str            = ""
    framework_version: str            = VERSION

    @classmethod
    def create(
        cls,
        *,
        supervisor_id: str                      = "",
        source:        str                      = "",
        workflow_id:   str                      = "",
        tags:          Optional[Dict[str, str]] = None,
        notes:         str                      = "",
    ) -> "SupervisorMetadata":
        return cls(
            supervisor_id = supervisor_id,
            source        = source,
            workflow_id   = workflow_id,
            tags          = dict(tags or {}),
            notes         = notes,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supervisor_id":    self.supervisor_id,
            "source":           self.source,
            "workflow_id":      self.workflow_id,
            "tags":             dict(self.tags),
            "notes":            self.notes,
            "framework_version": self.framework_version,
        }
