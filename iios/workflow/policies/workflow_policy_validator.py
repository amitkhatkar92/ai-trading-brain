"""
workflow_policy_validator.py — iios.workflow.policies
------------------------------------------------------
WorkflowPolicyValidator — validates governance policy configuration
before registration or evaluation.

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .exceptions import WorkflowPolicyValidationError
from .workflow_policy import WorkflowPolicy

_log = get_logger(__name__)


@dataclass(frozen=True)
class PolicyValidationResult:
    """Result of validating a single WorkflowPolicy."""
    policy_id: str
    valid:     bool
    issues:    tuple   # Tuple[str, ...]

    @property
    def issue_list(self) -> List[str]:
        return list(self.issues)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "valid":     self.valid,
            "issues":    self.issue_list,
        }


class WorkflowPolicyValidator:
    """
    Validates governance policy configuration.

    Thread-safe — stateless.
    """

    def validate(self, policy: WorkflowPolicy) -> PolicyValidationResult:
        """
        Validate a WorkflowPolicy.

        Returns:
            PolicyValidationResult with validation outcome.
        """
        issues: List[str] = []

        # 1. Policy must have a non-empty ID
        if not policy.policy_id:
            issues.append("policy_id is empty")

        # 2. Policy must have a non-empty name
        if not policy.name:
            issues.append("policy name is empty")

        # 3. Policy type must be valid (always valid if it's an enum)

        # 4. Domain must be valid (always valid if it's an enum)

        # 5. Rules: each rule must have a non-empty ID and name
        for rule in policy.rules:
            if not rule.rule_id:
                issues.append(f"Rule has empty rule_id in policy {policy.policy_id!r}")
            if not rule.name:
                issues.append(f"Rule has empty name in policy {policy.policy_id!r}")
            # Each condition must have a non-empty field
            for cond in rule.conditions:
                if not cond.field:
                    issues.append(
                        f"Condition {cond.condition_id!r} has empty field "
                        f"in rule {rule.rule_id!r}"
                    )

        # 6. Policy must have a valid default_action (always valid if enum)

        # 7. Version must be non-empty
        if not policy.version:
            issues.append("policy version is empty")

        valid = len(issues) == 0
        result = PolicyValidationResult(
            policy_id = policy.policy_id,
            valid     = valid,
            issues    = tuple(issues),
        )
        if not valid:
            _log.warning(
                f"Policy validation failed: policy={policy.policy_id!r} "
                f"issues={issues}"
            )
        return result

    def validate_or_raise(self, policy: WorkflowPolicy) -> None:
        """Validate and raise WorkflowPolicyValidationError if invalid."""
        result = self.validate(policy)
        if not result.valid:
            raise WorkflowPolicyValidationError(
                f"Policy {policy.policy_id!r} failed validation",
                issues=result.issue_list,
            )
