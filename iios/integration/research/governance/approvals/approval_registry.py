"""approvals/approval_registry.py — Thread-safe workflow store."""
from __future__ import annotations

import threading
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import ApprovalStatus
from iios.integration.research.governance.governance_exceptions import (
    ApprovalNotFoundError,
    LineageCapacityError,
)


class ApprovalRegistry:
    """Thread-safe store for ApprovalWorkflow objects."""

    def __init__(self, max_workflows: int = 50_000) -> None:
        self._workflows: dict  = {}
        self._max     = max_workflows
        self._lock    = threading.RLock()

    def register(self, workflow: Any) -> None:
        with self._lock:
            if len(self._workflows) >= self._max:
                raise LineageCapacityError(f"Approval registry capacity ({self._max}) reached")
            self._workflows[workflow.workflow_id] = workflow

    def get(self, workflow_id: str) -> Any:
        with self._lock:
            wf = self._workflows.get(workflow_id)
        if wf is None:
            raise ApprovalNotFoundError(f"Approval workflow '{workflow_id}' not found")
        return wf

    def has(self, workflow_id: str) -> bool:
        with self._lock:
            return workflow_id in self._workflows

    def by_entity(self, entity_id: str) -> list:
        with self._lock:
            return [w for w in self._workflows.values() if w.entity_id == entity_id]

    def by_status(self, status: ApprovalStatus) -> list:
        with self._lock:
            return [w for w in self._workflows.values() if w.status == status]

    def count(self) -> int:
        with self._lock:
            return len(self._workflows)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            by_status: dict[str, int] = {}
            for wf in self._workflows.values():
                k = wf.status.value
                by_status[k] = by_status.get(k, 0) + 1
            return {
                "total":     len(self._workflows),
                "by_status": by_status,
                "capacity":  self._max,
            }
