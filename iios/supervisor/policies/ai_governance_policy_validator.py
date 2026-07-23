"""
ai_governance_policy_validator.py — iios.supervisor.policies
--------------------------------------------------------------
Structural validation for AI governance policies and evaluation requests.

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .constants import AIGovernanceValidationCode
from .ai_governance_policy import AIGovernancePolicy
from .ai_governance_policy_request import AIGovernancePolicyRequest


# ---------------------------------------------------------------------------
# Validation result types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AIGovernanceValidationCheckResult:
    """Result of a single validation check."""
    code:    AIGovernanceValidationCode
    passed:  bool
    message: str = ""


@dataclass(frozen=True)
class AIGovernancePolicyValidationResult:
    """Aggregated validation outcome."""
    is_valid:      bool
    checks:        Tuple[AIGovernanceValidationCheckResult, ...]
    failed_checks: Tuple[AIGovernanceValidationCheckResult, ...]
    passed_count:  int
    failed_count:  int

    @property
    def failure_messages(self) -> List[str]:
        return [c.message for c in self.failed_checks if c.message]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class AIGovernancePolicyValidator:
    """
    Validates :class:`AIGovernancePolicyRequest` and
    :class:`AIGovernancePolicy` structural integrity before evaluation.
    """

    def validate_request(
        self, request: AIGovernancePolicyRequest
    ) -> AIGovernancePolicyValidationResult:
        checks: List[AIGovernanceValidationCheckResult] = [
            self._check_request_completeness(request),
            self._check_context_consistency(request),
        ]
        return self._build_result(checks)

    def validate_policy(
        self, policy: AIGovernancePolicy
    ) -> AIGovernancePolicyValidationResult:
        checks: List[AIGovernanceValidationCheckResult] = [
            self._check_policy_integrity(policy),
            self._check_rule_integrity(policy),
            self._check_condition_integrity(policy),
            self._check_conflict_resolution_integrity(policy),
        ]
        return self._build_result(checks)

    # ------------------------------------------------------------------
    # Request checks
    # ------------------------------------------------------------------

    def _check_request_completeness(
        self, request: AIGovernancePolicyRequest
    ) -> AIGovernanceValidationCheckResult:
        ok = bool(request.request_id) and bool(request.supervision_id)
        return AIGovernanceValidationCheckResult(
            code    = AIGovernanceValidationCode.REQUEST_COMPLETENESS,
            passed  = ok,
            message = "" if ok else "request_id and supervision_id must be non-empty",
        )

    def _check_context_consistency(
        self, request: AIGovernancePolicyRequest
    ) -> AIGovernanceValidationCheckResult:
        ok = request.context is not None and bool(request.context.supervision_id)
        return AIGovernanceValidationCheckResult(
            code    = AIGovernanceValidationCode.CONTEXT_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "Request context must have a valid supervision_id",
        )

    # ------------------------------------------------------------------
    # Policy checks
    # ------------------------------------------------------------------

    def _check_policy_integrity(
        self, policy: AIGovernancePolicy
    ) -> AIGovernanceValidationCheckResult:
        ok = bool(policy.policy_id) and bool(policy.name)
        return AIGovernanceValidationCheckResult(
            code    = AIGovernanceValidationCode.POLICY_INTEGRITY,
            passed  = ok,
            message = "" if ok else "policy_id and name must be non-empty",
        )

    def _check_rule_integrity(
        self, policy: AIGovernancePolicy
    ) -> AIGovernanceValidationCheckResult:
        ok = all(bool(r.rule_id) and bool(r.name) for r in policy.rules)
        return AIGovernanceValidationCheckResult(
            code    = AIGovernanceValidationCode.RULE_INTEGRITY,
            passed  = ok,
            message = "" if ok else "All rules must have non-empty rule_id and name",
        )

    def _check_condition_integrity(
        self, policy: AIGovernancePolicy
    ) -> AIGovernanceValidationCheckResult:
        for rule in policy.rules:
            for cond in rule.conditions:
                if not cond.condition_id or not cond.field_path:
                    return AIGovernanceValidationCheckResult(
                        code    = AIGovernanceValidationCode.CONDITION_INTEGRITY,
                        passed  = False,
                        message = "All conditions must have non-empty condition_id and field_path",
                    )
        return AIGovernanceValidationCheckResult(
            code   = AIGovernanceValidationCode.CONDITION_INTEGRITY,
            passed = True,
        )

    def _check_conflict_resolution_integrity(
        self, policy: AIGovernancePolicy
    ) -> AIGovernanceValidationCheckResult:
        """Verify that no rule has an undefined action value."""
        from .constants import AIGovernancePolicyAction
        valid_actions = set(AIGovernancePolicyAction)
        ok = all(r.action in valid_actions for r in policy.rules)
        return AIGovernanceValidationCheckResult(
            code    = AIGovernanceValidationCode.CONFLICT_RESOLUTION_INTEGRITY,
            passed  = ok,
            message = "" if ok else "All rules must prescribe a valid AIGovernancePolicyAction",
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _build_result(
        checks: List[AIGovernanceValidationCheckResult],
    ) -> AIGovernancePolicyValidationResult:
        failed = tuple(c for c in checks if not c.passed)
        return AIGovernancePolicyValidationResult(
            is_valid      = len(failed) == 0,
            checks        = tuple(checks),
            failed_checks = failed,
            passed_count  = len(checks) - len(failed),
            failed_count  = len(failed),
        )
