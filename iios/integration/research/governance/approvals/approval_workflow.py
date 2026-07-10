"""approvals/approval_workflow.py — Approval workflow state machine."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from iios.integration.research.governance.governance_constants import (
    ApprovalStatus,
    ReviewDecision,
    ReviewStage,
)
from iios.integration.research.governance.governance_exceptions import (
    ApprovalStateError,
)
from iios.integration.research.governance.approvals.approval_result import ApprovalResult


@dataclass
class ApprovalWorkflow:
    """
    Multi-stage approval workflow.

    The workflow advances through ``stages`` sequentially. Each stage produces
    an ``ApprovalResult``. The workflow completes when all required stages
    are approved (or fails immediately on any rejection).
    """
    workflow_id:   str
    entity_id:     str
    entity_type:   str
    status:        ApprovalStatus
    stages:        list[ReviewStage]             # ordered required stages
    stage_results: dict[str, ApprovalResult]     # stage.value → result
    submitter:     str
    notes:         str
    created_at:    float
    updated_at:    float
    completed_at:  Optional[float]

    @classmethod
    def create(
        cls,
        entity_id:   str,
        entity_type: str,
        submitter:   str,
        stages:      list[ReviewStage],
        *,
        workflow_id: Optional[str] = None,
        notes:       str           = "",
    ) -> "ApprovalWorkflow":
        now = time.time()
        return cls(
            workflow_id   = workflow_id or f"wf_{uuid.uuid4().hex[:10]}",
            entity_id     = entity_id,
            entity_type   = entity_type,
            status        = ApprovalStatus.PENDING,
            stages        = list(stages),
            stage_results = {},
            submitter     = submitter,
            notes         = notes,
            created_at    = now,
            updated_at    = now,
            completed_at  = None,
        )

    @property
    def current_stage(self) -> Optional[ReviewStage]:
        for stage in self.stages:
            if stage.value not in self.stage_results:
                return stage
        return None

    def advance(
        self,
        decision:  ReviewDecision,
        reviewer:  str,
        comments:  str = "",
    ) -> bool:
        """
        Record a decision for the current stage.

        Returns ``True`` if the workflow is now fully approved.
        Raises ``ApprovalStateError`` if the workflow is already terminal.
        """
        if self.is_terminal():
            raise ApprovalStateError(
                f"Workflow '{self.workflow_id}' is already in terminal state {self.status.value}"
            )
        stage = self.current_stage
        if stage is None:
            raise ApprovalStateError(
                f"Workflow '{self.workflow_id}' has no pending stage"
            )
        result = ApprovalResult.create(
            self.workflow_id, stage, decision, reviewer, comments=comments
        )
        self.stage_results[stage.value] = result
        self.updated_at = time.time()
        if decision == ReviewDecision.APPROVED:
            if self.current_stage is None:  # all stages done
                self.status       = ApprovalStatus.APPROVED
                self.completed_at = self.updated_at
                return True
        elif decision in (ReviewDecision.REJECTED, ReviewDecision.REVISE):
            self.status       = ApprovalStatus.REJECTED
            self.completed_at = self.updated_at
        return False

    def reject(self, reviewer: str, reason: str = "") -> None:
        if self.is_terminal():
            raise ApprovalStateError(
                f"Workflow '{self.workflow_id}' is already terminal"
            )
        stage = self.current_stage or (self.stages[0] if self.stages else ReviewStage.PEER_REVIEW)
        result = ApprovalResult.create(
            self.workflow_id, stage, ReviewDecision.REJECTED, reviewer, comments=reason
        )
        self.stage_results[stage.value] = result
        self.status       = ApprovalStatus.REJECTED
        self.completed_at = time.time()
        self.updated_at   = self.completed_at

    def withdraw(self) -> None:
        if self.is_terminal():
            raise ApprovalStateError(
                f"Workflow '{self.workflow_id}' is already terminal"
            )
        self.status       = ApprovalStatus.WITHDRAWN
        self.completed_at = time.time()
        self.updated_at   = self.completed_at

    def is_terminal(self) -> bool:
        return self.status in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.WITHDRAWN,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id":   self.workflow_id,
            "entity_id":     self.entity_id,
            "entity_type":   self.entity_type,
            "status":        self.status.value,
            "stages":        [s.value for s in self.stages],
            "stage_results": {k: v.to_dict() for k, v in self.stage_results.items()},
            "submitter":     self.submitter,
            "notes":         self.notes,
            "created_at":    self.created_at,
            "updated_at":    self.updated_at,
            "completed_at":  self.completed_at,
        }
