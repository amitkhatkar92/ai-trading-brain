"""iios/decision_governance/governance_registry.py

Master registry: governance policies + approval policies + workflows.
"""
from __future__ import annotations

import threading

from iios.decision_governance.governance_constants import MAX_REGISTRY_SIZE
from iios.decision_governance.governance_exceptions import (
    PolicyAlreadyExistsError,
    PolicyNotFoundError,
    RegistryOverflowError,
)
from iios.decision_governance.policies.governance_policy import GovernancePolicy
from iios.decision_governance.approval.approval_policy import ApprovalPolicy
from iios.decision_governance.approval.approval_workflow import ApprovalWorkflow


class GovernanceRegistry:
    """Thread-safe master registry for all governance artefacts."""

    def __init__(self, max_size: int = MAX_REGISTRY_SIZE) -> None:
        self._lock:       threading.RLock                 = threading.RLock()
        self._policies:   dict[str, GovernancePolicy]     = {}
        self._approval:   dict[str, ApprovalPolicy]       = {}
        self._workflows:  dict[str, ApprovalWorkflow]     = {}
        self._max:        int                             = max_size

    # ── governance policies ───────────────────────────────────────────────────

    def register_policy(
        self, policy: GovernancePolicy, *, overwrite: bool = False
    ) -> None:
        with self._lock:
            if policy.policy_id in self._policies and not overwrite:
                raise PolicyAlreadyExistsError(policy.policy_id)
            if policy.policy_id not in self._policies and len(self._policies) >= self._max:
                raise RegistryOverflowError(self._max)
            self._policies[policy.policy_id] = policy

    def get_policy(self, policy_id: str) -> GovernancePolicy:
        with self._lock:
            p = self._policies.get(policy_id)
        if p is None:
            raise PolicyNotFoundError(policy_id)
        return p

    def has_policy(self, policy_id: str) -> bool:
        with self._lock:
            return policy_id in self._policies

    def all_policies(self, policy_type: str | None = None) -> list[GovernancePolicy]:
        with self._lock:
            policies = list(self._policies.values())
        if policy_type:
            policies = [p for p in policies if p.policy_type.value == policy_type]
        return policies

    def policies_by_tag(self, tag: str) -> list[GovernancePolicy]:
        with self._lock:
            return [p for p in self._policies.values() if tag in p.tags]

    # ── approval policies ─────────────────────────────────────────────────────

    def register_approval(
        self, policy: ApprovalPolicy, *, overwrite: bool = False
    ) -> None:
        with self._lock:
            if policy.policy_id in self._approval and not overwrite:
                raise PolicyAlreadyExistsError(f"approval:{policy.policy_id}")
            self._approval[policy.policy_id] = policy

    def get_approval(self, policy_id: str) -> ApprovalPolicy:
        with self._lock:
            p = self._approval.get(policy_id)
        if p is None:
            raise PolicyNotFoundError(f"approval:{policy_id}")
        return p

    def has_approval(self, policy_id: str) -> bool:
        with self._lock:
            return policy_id in self._approval

    def all_approvals(self) -> list[ApprovalPolicy]:
        with self._lock:
            return list(self._approval.values())

    # ── workflows ─────────────────────────────────────────────────────────────

    def register_workflow(
        self, workflow: ApprovalWorkflow, *, overwrite: bool = False
    ) -> None:
        with self._lock:
            if workflow.workflow_id in self._workflows and not overwrite:
                raise PolicyAlreadyExistsError(f"workflow:{workflow.workflow_id}")
            self._workflows[workflow.workflow_id] = workflow

    def get_workflow(self, workflow_id: str) -> ApprovalWorkflow:
        with self._lock:
            w = self._workflows.get(workflow_id)
        if w is None:
            raise PolicyNotFoundError(f"workflow:{workflow_id}")
        return w

    def has_workflow(self, workflow_id: str) -> bool:
        with self._lock:
            return workflow_id in self._workflows

    def all_workflows(self) -> list[ApprovalWorkflow]:
        with self._lock:
            return list(self._workflows.values())

    # ── stats ─────────────────────────────────────────────────────────────────

    def statistics(self) -> dict:
        with self._lock:
            return {
                "governance_policies": len(self._policies),
                "approval_policies":   len(self._approval),
                "workflows":           len(self._workflows),
            }


# ── singleton ─────────────────────────────────────────────────────────────────

_singleton_lock: threading.Lock         = threading.Lock()
_instance:       GovernanceRegistry | None = None


def get_governance_registry() -> GovernanceRegistry:
    global _instance  # noqa: PLW0603
    if _instance is None:
        with _singleton_lock:
            if _instance is None:
                _instance = GovernanceRegistry()
    return _instance


def reset_governance_registry() -> None:
    global _instance  # noqa: PLW0603
    with _singleton_lock:
        _instance = None
