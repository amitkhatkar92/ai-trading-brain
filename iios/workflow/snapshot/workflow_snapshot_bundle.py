"""
workflow_snapshot_bundle.py — iios.workflow.snapshot
-----------------------------------------------------
WorkflowSnapshotBundle — immutable collection of related snapshots
aggregated for multi-workflow or enterprise-level reporting.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 5
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .constants import PREFIX_BUNDLE
from .workflow_snapshot import WorkflowSnapshot


@dataclass(frozen=True)
class WorkflowSnapshotBundle:
    """
    Immutable bundle of related WorkflowSnapshot objects.

    Represents a logical grouping — for example, all snapshots for a
    batch job, saga, or enterprise workflow session.
    """
    bundle_id:         str
    bundle_name:       str
    enterprise_id:     str
    snapshots:         tuple          # Tuple[WorkflowSnapshot, ...]
    correlation_id:    str
    tags:              Dict[str, str]
    extra:             Dict[str, Any]
    created_at:        str

    @classmethod
    def create(
        cls,
        bundle_name:   str,
        snapshots:     List[WorkflowSnapshot],
        *,
        enterprise_id: str                     = "",
        correlation_id: str                    = "",
        tags:          Optional[Dict[str, str]] = None,
        extra:         Optional[Dict[str, Any]] = None,
        bundle_id:     Optional[str]            = None,
    ) -> "WorkflowSnapshotBundle":
        return cls(
            bundle_id      = bundle_id or f"{PREFIX_BUNDLE}{uuid.uuid4().hex[:12]}",
            bundle_name    = bundle_name,
            enterprise_id  = enterprise_id,
            snapshots      = tuple(snapshots),
            correlation_id = correlation_id or uuid.uuid4().hex,
            tags           = dict(tags or {}),
            extra          = dict(extra or {}),
            created_at     = datetime.now(tz=timezone.utc).isoformat(),
        )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def snapshot_count(self) -> int:
        return len(self.snapshots)

    @property
    def workflow_ids(self) -> List[str]:
        return [s.workflow_id for s in self.snapshots]

    @property
    def snapshot_ids(self) -> List[str]:
        return [s.snapshot_id for s in self.snapshots]

    def get_snapshot(self, snapshot_id: str) -> Optional[WorkflowSnapshot]:
        for s in self.snapshots:
            if s.snapshot_id == snapshot_id:
                return s
        return None

    def get_by_workflow(self, workflow_id: str) -> List[WorkflowSnapshot]:
        return [s for s in self.snapshots if s.workflow_id == workflow_id]

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id":      self.bundle_id,
            "bundle_name":    self.bundle_name,
            "enterprise_id":  self.enterprise_id,
            "correlation_id": self.correlation_id,
            "snapshot_count": self.snapshot_count,
            "workflow_ids":   self.workflow_ids,
            "snapshot_ids":   self.snapshot_ids,
            "tags":           dict(self.tags),
            "created_at":     self.created_at,
        }
