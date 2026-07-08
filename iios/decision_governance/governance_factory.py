"""iios/decision_governance/governance_factory.py

Factory helpers for creating governance objects without boilerplate.
"""
from __future__ import annotations

from typing import Callable

from iios.decision_governance.governance_context import GovernanceSubject
from iios.decision_governance.governance_constants import (
    DEFAULT_GOVERNANCE_MODE,
    GovernanceMode,
    PolicyType,
    PolicyViolationSeverity,
)
from iios.decision_governance.policies.governance_policy import (
    CompositePolicy,
    GovernancePolicy,
    PredicatePolicy,
    ScoreThresholdPolicy,
)
from iios.decision_governance.approval.approval_policy import (
    AutoApprovalPolicy,
    ConditionalApprovalPolicy,
    EscalationApprovalPolicy,
    ScoreThresholdApprovalPolicy,
)
from iios.decision_governance.approval.approval_workflow import ApprovalWorkflow
from iios.decision_governance.governance_manager import GovernanceRequest


class GovernanceFactory:

    @staticmethod
    def make_subject(
        decision_id: str = "",
        score:       float = 0.5,
        **payload,
    ) -> GovernanceSubject:
        return GovernanceSubject(decision_id=decision_id, score=score, payload=payload)

    @staticmethod
    def make_score_policy(
        policy_id:   str,
        name:        str,
        threshold:   float,
        blocking:    bool = True,
        policy_type: PolicyType = PolicyType.GOVERNANCE,
    ) -> ScoreThresholdPolicy:
        return ScoreThresholdPolicy(
            policy_id=policy_id,
            name=name,
            threshold=threshold,
            blocking=blocking,
            policy_type=policy_type,
        )

    @staticmethod
    def make_predicate_policy(
        policy_id:         str,
        name:              str,
        predicate:         Callable[[GovernanceSubject], bool],
        violation_message: str = "Predicate failed",
        blocking:          bool = True,
    ) -> PredicatePolicy:
        return PredicatePolicy(
            policy_id=policy_id,
            name=name,
            predicate=predicate,
            violation_message=violation_message,
            blocking=blocking,
        )

    @staticmethod
    def make_auto_approval(
        policy_id: str = "_auto",
        name:      str = "Auto Approve",
    ) -> AutoApprovalPolicy:
        return AutoApprovalPolicy(policy_id=policy_id, name=name)

    @staticmethod
    def make_threshold_approval(
        policy_id:  str,
        name:       str,
        threshold:  float,
    ) -> ScoreThresholdApprovalPolicy:
        return ScoreThresholdApprovalPolicy(
            policy_id=policy_id, name=name, threshold=threshold
        )

    @staticmethod
    def make_escalation_approval(
        policy_id: str,
        name:      str,
        reason:    str = "Manual review required",
    ) -> EscalationApprovalPolicy:
        return EscalationApprovalPolicy(policy_id=policy_id, name=name, escalation_reason=reason)

    @staticmethod
    def make_workflow(workflow_id: str = "", name: str = "") -> ApprovalWorkflow:
        return ApprovalWorkflow(workflow_id=workflow_id, name=name)

    @staticmethod
    def make_request(
        subject:             GovernanceSubject | None = None,
        governance_policies: list | None = None,
        approval_policies:   list | None = None,
        workflow:            ApprovalWorkflow | None = None,
        mode:                GovernanceMode = DEFAULT_GOVERNANCE_MODE,
    ) -> GovernanceRequest:
        return GovernanceRequest(
            subject=subject or GovernanceSubject(),
            governance_policies=governance_policies or [],
            approval_policies=approval_policies or [],
            workflow=workflow,
            mode=mode,
        )
