"""
workflow_priority.py — iios.workflow.engine
--------------------------------------------
Priority-aware queue item and comparison logic for workflow scheduling.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 2
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .constants import DEFAULT_PRIORITY, WorkflowQueuePriority
from .workflow_request import WorkflowEngineRequest


@dataclass(order=True)
class PriorityWorkflowItem:
    """
    Priority-ordered wrapper for a WorkflowEngineRequest.

    Implements comparison by (priority, sequence) so that the heap
    returns lower priority numbers (higher urgency) first.
    Ties are broken by insertion sequence (FIFO).
    """
    priority:  int
    sequence:  int
    item_id:   str = field(compare=False)
    request:   WorkflowEngineRequest = field(compare=False)
    queued_at: str = field(compare=False)

    @classmethod
    def create(
        cls,
        request:  WorkflowEngineRequest,
        sequence: int,
        *,
        priority: Optional[int] = None,
    ) -> "PriorityWorkflowItem":
        prio = priority if priority is not None else request.priority
        prio = max(0, min(3, prio))   # clamp to [0, 3]
        return cls(
            priority  = prio,
            sequence  = sequence,
            item_id   = f"wqi-{uuid.uuid4().hex[:10]}",
            request   = request,
            queued_at = datetime.now(tz=timezone.utc).isoformat(),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id":    self.item_id,
            "request_id": self.request.request_id,
            "priority":   self.priority,
            "sequence":   self.sequence,
            "queued_at":  self.queued_at,
        }


def priority_label(priority: int) -> str:
    """Return a human-readable label for an integer priority."""
    try:
        return WorkflowQueuePriority(priority).name
    except ValueError:
        return "UNKNOWN"
