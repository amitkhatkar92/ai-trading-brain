"""iios/decision_governance/policies/policy_executor.py

Executes a list of GovernancePolicies against a GovernanceSubject and
produces a PolicyExecutionResult.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from iios.decision_governance.governance_context import GovernanceSubject
from iios.decision_governance.policies.governance_policy import (
    GovernancePolicy,
    PolicyViolation,
)


@dataclass
class PolicyExecutionResult:
    """Aggregate outcome of running all policies against one subject."""

    result_id:          str                 = field(default_factory=lambda: str(uuid.uuid4()))
    subject_id:         str                 = ""
    policies_evaluated: int                 = 0
    violations:         list[PolicyViolation] = field(default_factory=list)
    passed:             bool                = True   # False if any blocking violation exists
    generated_at:       float               = field(default_factory=time.time)

    @property
    def blocking_violations(self) -> int:
        return sum(1 for v in self.violations if v.is_blocking)

    @property
    def warning_violations(self) -> int:
        return sum(1 for v in self.violations if not v.is_blocking)

    def to_dict(self) -> dict:
        return {
            "result_id":           self.result_id,
            "subject_id":          self.subject_id,
            "policies_evaluated":  self.policies_evaluated,
            "violations":          [v.to_dict() for v in self.violations],
            "blocking_violations": self.blocking_violations,
            "warning_violations":  self.warning_violations,
            "passed":              self.passed,
            "generated_at":        self.generated_at,
        }


class PolicyExecutor:
    """Executes governance policies against a subject."""

    def execute(
        self,
        subject: GovernanceSubject,
        policies: list[GovernancePolicy],
    ) -> PolicyExecutionResult:
        """Run all policies; collect violations. passed=False on any blocking violation."""
        violations: list[PolicyViolation] = []
        for policy in policies:
            try:
                violation = policy.validate(subject)
            except Exception as exc:  # noqa: BLE001
                # Treat execution failure as a blocking violation
                from iios.decision_governance.policies.governance_policy import (  # noqa: PLC0415
                    PolicyViolation as _PV,
                    PolicyViolationSeverity as _PVS,
                )
                violation = _PV(
                    policy_id=policy.policy_id,
                    policy_name=policy.name,
                    severity=_PVS.CRITICAL,
                    message=f"Policy execution error: {exc}",
                    is_blocking=True,
                )
            if violation is not None:
                violations.append(violation)

        blocking = any(v.is_blocking for v in violations)
        return PolicyExecutionResult(
            subject_id=subject.subject_id,
            policies_evaluated=len(policies),
            violations=violations,
            passed=not blocking,
        )
