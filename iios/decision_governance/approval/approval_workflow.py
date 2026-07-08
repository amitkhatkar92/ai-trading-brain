"""iios/decision_governance/approval/approval_workflow.py

ApprovalWorkflow: ordered sequence of ApprovalPolicy steps.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from iios.decision_governance.governance_constants import (
    ApprovalLevel,
    ApprovalStatus,
)
from iios.decision_governance.governance_context import GovernanceSubject
from iios.decision_governance.approval.approval_policy import ApprovalPolicy
from iios.decision_governance.approval.approval_result import (
    ApprovalRecord,
    ApprovalResult,
)


@dataclass
class WorkflowStep:
    """One step in an approval workflow."""

    step_id:  str           = field(default_factory=lambda: str(uuid.uuid4()))
    policy:   ApprovalPolicy | None = None
    order:    int           = 0
    required: bool          = True   # If False, failure is logged but not blocking


class ApprovalWorkflow:
    """
    Sequential multi-step approval workflow.

    Steps are sorted by `order` (ascending) at execution time.
    The overall result is APPROVED only when all required steps approve.
    Any required REJECTED step terminates the workflow immediately.
    Any ESCALATED record increments the escalation counter.
    """

    def __init__(self, workflow_id: str = "", name: str = "") -> None:
        self.workflow_id: str = workflow_id or str(uuid.uuid4())
        self.name:        str = name
        self._steps:      list[WorkflowStep] = []

    def add_step(
        self,
        policy:   ApprovalPolicy,
        order:    int  = 0,
        required: bool = True,
    ) -> "ApprovalWorkflow":
        self._steps.append(WorkflowStep(policy=policy, order=order, required=required))
        return self  # fluent

    @property
    def steps(self) -> list[WorkflowStep]:
        return sorted(self._steps, key=lambda s: s.order)

    def execute(self, subject: GovernanceSubject) -> ApprovalResult:
        """Run all steps and return an aggregate ApprovalResult."""
        records:      list[ApprovalRecord] = []
        escalations:  int                  = 0
        final_status: ApprovalStatus       = ApprovalStatus.APPROVED
        current_level: ApprovalLevel       = ApprovalLevel.AUTO

        for step in self.steps:
            if step.policy is None:
                continue

            record = step.policy.evaluate(subject)
            records.append(record)
            current_level = record.level

            if record.status == ApprovalStatus.ESCALATED:
                escalations += 1
                if step.required:
                    final_status = ApprovalStatus.ESCALATED
                    # Continue evaluation — don't short-circuit on escalation

            elif record.status == ApprovalStatus.REJECTED and step.required:
                final_status = ApprovalStatus.REJECTED
                break  # required rejection → stop immediately

        approved = final_status == ApprovalStatus.APPROVED

        return ApprovalResult(
            decision_id=subject.decision_id,
            status=final_status,
            approved=approved,
            records=records,
            escalations=escalations,
            current_level=current_level,
        )
