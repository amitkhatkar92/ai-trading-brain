"""approvals/approval_engine.py — Approval orchestrator."""
from __future__ import annotations

from typing import Any, Optional

from iios.integration.research.governance.governance_constants import ApprovalStatus, ReviewDecision, ReviewStage
from iios.integration.research.governance.approvals.approval_policy   import ApprovalPolicy
from iios.integration.research.governance.approvals.approval_registry import ApprovalRegistry
from iios.integration.research.governance.approvals.approval_result   import ApprovalResult
from iios.integration.research.governance.approvals.approval_workflow  import ApprovalWorkflow


class ApprovalEngine:
    """Facade for all approval workflow operations."""

    def __init__(self) -> None:
        self._registry = ApprovalRegistry()
        self._policies: dict[str, ApprovalPolicy] = {}

    # ── Policy management ─────────────────────────────────────────────────────

    def register_policy(self, policy: ApprovalPolicy) -> None:
        self._policies[policy.policy_id] = policy

    def get_policy(self, policy_id: str) -> Optional[ApprovalPolicy]:
        return self._policies.get(policy_id)

    # ── Workflow lifecycle ─────────────────────────────────────────────────────

    def submit(
        self,
        entity_id:   str,
        entity_type: str,
        submitter:   str,
        stages:      list[ReviewStage],
        *,
        notes: str = "",
    ) -> ApprovalWorkflow:
        wf = ApprovalWorkflow.create(entity_id, entity_type, submitter, stages, notes=notes)
        self._registry.register(wf)
        return wf

    def review(
        self,
        workflow_id: str,
        stage:       ReviewStage,
        decision:    ReviewDecision,
        reviewer:    str,
        comments:    str = "",
    ) -> ApprovalResult:
        wf = self._registry.get(workflow_id)
        wf.advance(decision, reviewer, comments)
        result_key = stage.value
        return wf.stage_results.get(result_key) or list(wf.stage_results.values())[-1]

    def reject_workflow(
        self,
        workflow_id: str,
        reviewer:    str,
        reason:      str = "",
    ) -> None:
        wf = self._registry.get(workflow_id)
        wf.reject(reviewer, reason)

    def withdraw_workflow(self, workflow_id: str) -> None:
        wf = self._registry.get(workflow_id)
        wf.withdraw()

    def get_workflow(self, workflow_id: str) -> ApprovalWorkflow:
        return self._registry.get(workflow_id)

    def pending_workflows(self) -> list[ApprovalWorkflow]:
        return self._registry.by_status(ApprovalStatus.PENDING)

    def workflows_for_entity(self, entity_id: str) -> list[ApprovalWorkflow]:
        return self._registry.by_entity(entity_id)

    def stats(self) -> dict[str, Any]:
        return self._registry.stats()
