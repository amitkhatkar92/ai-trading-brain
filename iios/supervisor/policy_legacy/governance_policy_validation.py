"""
governance_policy_validation.py — iios.supervisor.policy
----------------------------------------------------------
Structural validation for governance policies and evaluation requests.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .constants import GovernanceValidationCode
from .governance_policy import GovernancePolicy
from .governance_policy_request import GovernancePolicyRequest


@dataclass(frozen=True)
class GovernanceValidationCheckResult:
    """Result of a single validation check."""
    code:    GovernanceValidationCode
    passed:  bool
    message: str = ""


@dataclass(frozen=True)
class GovernanceValidationResult:
    """Aggregated validation outcome."""
    is_valid:      bool
    checks:        Tuple[GovernanceValidationCheckResult, ...]
    failed_checks: Tuple[GovernanceValidationCheckResult, ...]
    passed_count:  int
    failed_count:  int

    @property
    def failure_messages(self) -> List[str]:
        return [c.message for c in self.failed_checks if c.message]


class GovernancePolicyValidator:
    """
    Validates :class:`GovernancePolicyRequest` and :class:`GovernancePolicy`
    structural integrity.
    """

    def validate_request(
        self, request: GovernancePolicyRequest
    ) -> GovernanceValidationResult:
        checks: List[GovernanceValidationCheckResult] = [
            self._check_request_completeness(request),
            self._check_context_consistency(request),
        ]
        failed = tuple(c for c in checks if not c.passed)
        return GovernanceValidationResult(
            is_valid      = len(failed) == 0,
            checks        = tuple(checks),
            failed_checks = failed,
            passed_count  = len(checks) - len(failed),
            failed_count  = len(failed),
        )

    def validate_policy(
        self, policy: GovernancePolicy
    ) -> GovernanceValidationResult:
        checks: List[GovernanceValidationCheckResult] = [
            self._check_policy_integrity(policy),
            self._check_rule_integrity(policy),
            self._check_condition_integrity(policy),
        ]
        failed = tuple(c for c in checks if not c.passed)
        return GovernanceValidationResult(
            is_valid      = len(failed) == 0,
            checks        = tuple(checks),
            failed_checks = failed,
            passed_count  = len(checks) - len(failed),
            failed_count  = len(failed),
        )

    # ------------------------------------------------------------------
    # Request checks
    # ------------------------------------------------------------------

    def _check_request_completeness(
        self, request: GovernancePolicyRequest
    ) -> GovernanceValidationCheckResult:
        ok = bool(request.request_id) and bool(request.supervision_id)
        return GovernanceValidationCheckResult(
            code    = GovernanceValidationCode.REQUEST_COMPLETENESS,
            passed  = ok,
            message = "" if ok else "request_id and supervision_id must be non-empty",
        )

    def _check_context_consistency(
        self, request: GovernancePolicyRequest
    ) -> GovernanceValidationCheckResult:
        ok = request.context is not None and bool(request.context.supervision_id)
        return GovernanceValidationCheckResult(
            code    = GovernanceValidationCode.CONTEXT_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "Request context must have a valid supervision_id",
        )

    # ------------------------------------------------------------------
    # Policy checks
    # ------------------------------------------------------------------

    def _check_policy_integrity(
        self, policy: GovernancePolicy
    ) -> GovernanceValidationCheckResult:
        ok = bool(policy.policy_id) and bool(policy.name)
        return GovernanceValidationCheckResult(
            code    = GovernanceValidationCode.POLICY_INTEGRITY,
            passed  = ok,
            message = "" if ok else "policy_id and name must be non-empty",
        )

    def _check_rule_integrity(
        self, policy: GovernancePolicy
    ) -> GovernanceValidationCheckResult:
        ok = all(bool(r.rule_id) and bool(r.name) for r in policy.rules)
        return GovernanceValidationCheckResult(
            code    = GovernanceValidationCode.RULE_INTEGRITY,
            passed  = ok,
            message = "" if ok else "All rules must have non-empty rule_id and name",
        )

    def _check_condition_integrity(
        self, policy: GovernancePolicy
    ) -> GovernanceValidationCheckResult:
        for rule in policy.rules:
            for cond in rule.conditions:
                if not cond.condition_id or not cond.field_path:
                    return GovernanceValidationCheckResult(
                        code    = GovernanceValidationCode.CONDITION_INTEGRITY,
                        passed  = False,
                        message = "All conditions must have non-empty condition_id and field_path",
                    )
        return GovernanceValidationCheckResult(
            code   = GovernanceValidationCode.CONDITION_INTEGRITY,
            passed = True,
        )
