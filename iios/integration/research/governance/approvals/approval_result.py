"""approvals/approval_result.py — Per-stage approval decision record."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import ReviewDecision, ReviewStage


@dataclass
class ApprovalResult:
    """
    Records the decision made for a single review stage.
    """
    result_id:   str
    workflow_id: str
    stage:       ReviewStage
    decision:    ReviewDecision
    reviewer:    str
    comments:    str
    decided_at:  float

    @classmethod
    def create(
        cls,
        workflow_id: str,
        stage:       ReviewStage,
        decision:    ReviewDecision,
        reviewer:    str,
        *,
        comments:   str           = "",
        result_id:  Optional[str] = None,
    ) -> "ApprovalResult":
        return cls(
            result_id   = result_id or f"ar_{uuid.uuid4().hex[:10]}",
            workflow_id = workflow_id,
            stage       = stage,
            decision    = decision,
            reviewer    = reviewer,
            comments    = comments,
            decided_at  = time.time(),
        )

    def is_approved(self) -> bool:
        return self.decision == ReviewDecision.APPROVED

    def is_rejected(self) -> bool:
        return self.decision in (ReviewDecision.REJECTED, ReviewDecision.REVISE)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id":   self.result_id,
            "workflow_id": self.workflow_id,
            "stage":       self.stage.value,
            "decision":    self.decision.value,
            "reviewer":    self.reviewer,
            "comments":    self.comments,
            "decided_at":  self.decided_at,
        }
