"""
risk_policy_validator.py — iios.risk.policies
===============================================
Policy and request validation for the Risk Policy Framework.

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import dataclasses
from typing import List, Optional, Tuple

from .constants import (
    VERSION,
    ConditionOperator,
    EvaluationMode,
    PolicyPriority,
    PolicyType,
    ValidationCode,
)
from .risk_policy import RiskPolicy
from .risk_policy_request import RiskPolicyRequest


# ---------------------------------------------------------------------------
# Validation result primitives
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class RiskPolicyValidationCheckResult:
    """Result of a single validation check."""
    code:       ValidationCode
    passed:     bool
    message:    str = ""


@dataclasses.dataclass(frozen=True)
class RiskPolicyValidationResult:
    """Aggregated result of all validation checks for a policy or request."""
    is_valid:       bool
    failed_checks:  Tuple[RiskPolicyValidationCheckResult, ...]
    passed_checks:  Tuple[RiskPolicyValidationCheckResult, ...]
    policy_id:      str = ""
    request_id:     str = ""
    framework_version: str = VERSION

    @property
    def failure_messages(self) -> List[str]:
        return [c.message for c in self.failed_checks]

    @property
    def failure_codes(self) -> List[ValidationCode]:
        return [c.code for c in self.failed_checks]


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class RiskPolicyValidator:
    """
    Validates :class:`~.risk_policy.RiskPolicy` and
    :class:`~.risk_policy_request.RiskPolicyRequest` objects.

    Checks
    ------
    Policy validation:
      1. ``POLICY_CONSISTENCY``           — required fields present and coherent
      2. ``RULE_CONSISTENCY``             — rules are non-empty; weight > 0
      3. ``CONDITION_VALIDITY``           — conditions have valid field_path & operator
      4. ``PRIORITY_INTEGRITY``           — priority is a valid PolicyPriority value
      5. ``CONFLICT_RESOLUTION_INTEGRITY`` — evaluation_mode enum is valid
      6. ``EVALUATION_COMPLETENESS``      — at least one rule or a default_action set
      7. ``AUDIT_COMPLETENESS``           — policy_id and version are non-empty

    Request validation:
      8. ``REQUEST_VALIDITY``             — required request fields present
    """

    def validate_policy(self, policy: RiskPolicy) -> RiskPolicyValidationResult:
        checks: List[RiskPolicyValidationCheckResult] = []

        # 1. Policy consistency
        checks.append(self._check_policy_consistency(policy))
        # 2. Rule consistency
        checks.append(self._check_rule_consistency(policy))
        # 3. Condition validity
        checks.append(self._check_condition_validity(policy))
        # 4. Priority integrity
        checks.append(self._check_priority_integrity(policy))
        # 5. Conflict resolution integrity
        checks.append(self._check_conflict_resolution_integrity(policy))
        # 6. Evaluation completeness
        checks.append(self._check_evaluation_completeness(policy))
        # 7. Audit completeness
        checks.append(self._check_audit_completeness(policy))

        failed = tuple(c for c in checks if not c.passed)
        passed = tuple(c for c in checks if c.passed)
        return RiskPolicyValidationResult(
            is_valid       = len(failed) == 0,
            failed_checks  = failed,
            passed_checks  = passed,
            policy_id      = policy.policy_id,
        )

    def validate_request(self, request: RiskPolicyRequest) -> RiskPolicyValidationResult:
        check = self._check_request_validity(request)
        failed = (check,) if not check.passed else ()
        passed = (check,) if check.passed else ()
        return RiskPolicyValidationResult(
            is_valid       = check.passed,
            failed_checks  = failed,
            passed_checks  = passed,
            request_id     = request.request_id,
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_policy_consistency(policy: RiskPolicy) -> RiskPolicyValidationCheckResult:
        code = ValidationCode.POLICY_CONSISTENCY
        if not policy.policy_id:
            return RiskPolicyValidationCheckResult(code, False, "policy_id is empty")
        if not policy.name:
            return RiskPolicyValidationCheckResult(code, False, "name is empty")
        if not isinstance(policy.policy_type, PolicyType):
            return RiskPolicyValidationCheckResult(code, False, "policy_type is invalid")
        return RiskPolicyValidationCheckResult(code, True)

    @staticmethod
    def _check_rule_consistency(policy: RiskPolicy) -> RiskPolicyValidationCheckResult:
        code = ValidationCode.RULE_CONSISTENCY
        for rule in policy.rules:
            if not rule.rule_id:
                return RiskPolicyValidationCheckResult(code, False, f"rule_id empty in rule '{rule.name}'")
            if rule.weight <= 0:
                return RiskPolicyValidationCheckResult(code, False, f"rule weight <= 0 in '{rule.name}'")
        return RiskPolicyValidationCheckResult(code, True)

    @staticmethod
    def _check_condition_validity(policy: RiskPolicy) -> RiskPolicyValidationCheckResult:
        code = ValidationCode.CONDITION_VALIDITY
        for rule in policy.rules:
            for cond in rule.conditions:
                if not cond.field_path:
                    return RiskPolicyValidationCheckResult(
                        code, False,
                        f"condition '{cond.name}' has empty field_path",
                    )
                if not isinstance(cond.operator, ConditionOperator):
                    return RiskPolicyValidationCheckResult(
                        code, False,
                        f"condition '{cond.name}' has invalid operator",
                    )
        return RiskPolicyValidationCheckResult(code, True)

    @staticmethod
    def _check_priority_integrity(policy: RiskPolicy) -> RiskPolicyValidationCheckResult:
        code = ValidationCode.PRIORITY_INTEGRITY
        if not isinstance(policy.priority, PolicyPriority):
            return RiskPolicyValidationCheckResult(code, False, "priority is not a PolicyPriority")
        if policy.priority.value not in (p.value for p in PolicyPriority):
            return RiskPolicyValidationCheckResult(code, False, f"unknown priority value {policy.priority}")
        return RiskPolicyValidationCheckResult(code, True)

    @staticmethod
    def _check_conflict_resolution_integrity(policy: RiskPolicy) -> RiskPolicyValidationCheckResult:
        code = ValidationCode.CONFLICT_RESOLUTION_INTEGRITY
        if not isinstance(policy.evaluation_mode, EvaluationMode):
            return RiskPolicyValidationCheckResult(code, False, "evaluation_mode is not an EvaluationMode")
        return RiskPolicyValidationCheckResult(code, True)

    @staticmethod
    def _check_evaluation_completeness(policy: RiskPolicy) -> RiskPolicyValidationCheckResult:
        code = ValidationCode.EVALUATION_COMPLETENESS
        if not policy.rules and policy.default_action is None:
            return RiskPolicyValidationCheckResult(
                code, False, "policy has no rules and no default_action",
            )
        return RiskPolicyValidationCheckResult(code, True)

    @staticmethod
    def _check_audit_completeness(policy: RiskPolicy) -> RiskPolicyValidationCheckResult:
        code = ValidationCode.AUDIT_COMPLETENESS
        if not policy.policy_id:
            return RiskPolicyValidationCheckResult(code, False, "policy_id missing — not auditable")
        if not policy.version:
            return RiskPolicyValidationCheckResult(code, False, "version missing — not auditable")
        return RiskPolicyValidationCheckResult(code, True)

    @staticmethod
    def _check_request_validity(request: RiskPolicyRequest) -> RiskPolicyValidationCheckResult:
        code = ValidationCode.REQUEST_VALIDITY
        if not request.request_id:
            return RiskPolicyValidationCheckResult(code, False, "request_id is empty")
        if not request.evaluation_id:
            return RiskPolicyValidationCheckResult(code, False, "evaluation_id is empty")
        if not request.portfolio_id:
            return RiskPolicyValidationCheckResult(code, False, "portfolio_id is empty")
        if not request.risk_id:
            return RiskPolicyValidationCheckResult(code, False, "risk_id is empty")
        if request.context is None:
            return RiskPolicyValidationCheckResult(code, False, "context is None")
        return RiskPolicyValidationCheckResult(code, True)
