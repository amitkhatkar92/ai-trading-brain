"""iios/decision_governance/approval/approval_engine.py

ApprovalEngine: orchestrates ad-hoc policy evaluation OR workflow execution.
"""
from __future__ import annotations

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
from iios.decision_governance.approval.approval_workflow import ApprovalWorkflow


class ApprovalEngine:
    """
    Runs approval evaluation.

    Usage:
    - ``evaluate(subject, policies)``   → runs each policy independently; ANDs all results
    - ``run_workflow(subject, workflow)`` → delegates to the workflow's execute()
    """

    def evaluate(
        self,
        subject:  GovernanceSubject,
        policies: list[ApprovalPolicy],
    ) -> ApprovalResult:
        """Evaluate a list of policies against the subject (no workflow ordering)."""
        records:     list[ApprovalRecord] = []
        escalations: int                  = 0
        rejected     = False
        escalated    = False
        current_level: ApprovalLevel      = ApprovalLevel.AUTO

        for policy in policies:
            record = policy.evaluate(subject)
            records.append(record)
            current_level = record.level

            if record.status == ApprovalStatus.REJECTED:
                rejected = True
            elif record.status == ApprovalStatus.ESCALATED:
                escalations += 1
                escalated = True

        if rejected:
            final_status = ApprovalStatus.REJECTED
        elif escalated:
            final_status = ApprovalStatus.ESCALATED
        else:
            final_status = ApprovalStatus.APPROVED

        return ApprovalResult(
            decision_id=subject.decision_id,
            status=final_status,
            approved=(final_status == ApprovalStatus.APPROVED),
            records=records,
            escalations=escalations,
            current_level=current_level,
        )

    def run_workflow(
        self,
        subject:  GovernanceSubject,
        workflow: ApprovalWorkflow,
    ) -> ApprovalResult:
        """Execute an ApprovalWorkflow against the subject."""
        return workflow.execute(subject)

    def approve_manual(
        self,
        existing: ApprovalResult,
        approver: str,
        reason:   str = "",
    ) -> ApprovalResult:
        """
        Record a manual approval decision on an existing (escalated) result.
        Returns a new ApprovalResult with status APPROVED.
        """
        record = ApprovalRecord(
            decision_id=existing.decision_id,
            policy_id="manual_override",
            policy_name="Manual Override",
            level=ApprovalLevel.MULTI,
            mode=__import__(
                "iios.decision_governance.governance_constants",
                fromlist=["ApprovalMode"],
            ).ApprovalMode.MANUAL,
            status=ApprovalStatus.APPROVED,
            approver=approver,
            reason=reason,
        )
        records = list(existing.records) + [record]
        return ApprovalResult(
            decision_id=existing.decision_id,
            status=ApprovalStatus.APPROVED,
            approved=True,
            records=records,
            escalations=existing.escalations,
            current_level=ApprovalLevel.MULTI,
        )

    def reject_manual(
        self,
        existing: ApprovalResult,
        approver: str,
        reason:   str = "",
    ) -> ApprovalResult:
        """Record a manual rejection on an existing (escalated) result."""
        from iios.decision_governance.governance_constants import ApprovalMode  # noqa: PLC0415
        record = ApprovalRecord(
            decision_id=existing.decision_id,
            policy_id="manual_override",
            policy_name="Manual Override",
            level=ApprovalLevel.MULTI,
            mode=ApprovalMode.MANUAL,
            status=ApprovalStatus.REJECTED,
            approver=approver,
            reason=reason,
        )
        records = list(existing.records) + [record]
        return ApprovalResult(
            decision_id=existing.decision_id,
            status=ApprovalStatus.REJECTED,
            approved=False,
            records=records,
            escalations=existing.escalations,
            current_level=ApprovalLevel.MULTI,
        )
