"""
market_policy_validator.py — iios.market.policies
===================================================
Policy and request validation for the Market Policy Framework.

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

import dataclasses
from typing import List, Optional, Tuple

from .constants import (
    VERSION,
    ConditionOperator,
    EvaluationMode,
    MarketPolicyType,
    PolicyPriority,
    ValidationCode,
)
from .market_policy import MarketPolicy
from .market_policy_request import MarketPolicyRequest


# ---------------------------------------------------------------------------
# Validation result primitives
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class MarketPolicyValidationCheckResult:
    """Result of a single validation check."""
    code:    ValidationCode
    passed:  bool
    message: str = ""


@dataclasses.dataclass(frozen=True)
class MarketPolicyValidationResult:
    """Aggregated result of all validation checks for a policy or request."""
    is_valid:          bool
    failed_checks:     Tuple[MarketPolicyValidationCheckResult, ...]
    passed_checks:     Tuple[MarketPolicyValidationCheckResult, ...]
    policy_id:         str = ""
    request_id:        str = ""
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

class MarketPolicyValidator:
    """
    Validates :class:`~.market_policy.MarketPolicy` and
    :class:`~.market_policy_request.MarketPolicyRequest` objects.

    Policy checks:
      1. POLICY_CONSISTENCY            — required fields present and coherent
      2. RULE_CONSISTENCY              — rules have weight > 0
      3. CONDITION_VALIDITY            — conditions have valid field_path & operator
      4. PRIORITY_INTEGRITY            — priority is a valid PolicyPriority value
      5. CONFLICT_RESOLUTION_INTEGRITY — evaluation_mode enum is valid
      6. EVALUATION_COMPLETENESS       — at least one rule or a default_action set
      7. AUDIT_COMPLETENESS            — policy_id and version are non-empty

    Request checks:
      8. REQUEST_VALIDITY              — required request fields present
    """

    def validate_policy(self, policy: MarketPolicy) -> MarketPolicyValidationResult:
        checks: List[MarketPolicyValidationCheckResult] = [
            self._check_policy_consistency(policy),
            self._check_rule_consistency(policy),
            self._check_condition_validity(policy),
            self._check_priority_integrity(policy),
            self._check_conflict_resolution_integrity(policy),
            self._check_evaluation_completeness(policy),
            self._check_audit_completeness(policy),
        ]
        failed = tuple(c for c in checks if not c.passed)
        passed = tuple(c for c in checks if c.passed)
        return MarketPolicyValidationResult(
            is_valid      = len(failed) == 0,
            failed_checks = failed,
            passed_checks = passed,
            policy_id     = policy.policy_id,
        )

    def validate_request(
        self, request: MarketPolicyRequest
    ) -> MarketPolicyValidationResult:
        check = self._check_request_validity(request)
        failed = (check,) if not check.passed else ()
        passed = (check,) if check.passed else ()
        return MarketPolicyValidationResult(
            is_valid      = check.passed,
            failed_checks = failed,
            passed_checks = passed,
            request_id    = request.request_id,
        )

    def validate_or_raise(self, policy: MarketPolicy) -> None:
        """Validate and raise :exc:`~.exceptions.MarketPolicyValidationError` if invalid."""
        from .exceptions import MarketPolicyValidationError
        result = self.validate_policy(policy)
        if not result.is_valid:
            raise MarketPolicyValidationError(
                "; ".join(result.failure_messages),
                failed_checks=tuple(result.failed_checks),
                policy_id=policy.policy_id,
            )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_policy_consistency(
        policy: MarketPolicy,
    ) -> MarketPolicyValidationCheckResult:
        ok = (
            bool(policy.policy_id)
            and bool(policy.name)
            and isinstance(policy.policy_type, MarketPolicyType)
        )
        return MarketPolicyValidationCheckResult(
            code    = ValidationCode.POLICY_CONSISTENCY,
            passed  = ok,
            message = "" if ok else "policy_id, name, and policy_type are required",
        )

    @staticmethod
    def _check_rule_consistency(
        policy: MarketPolicy,
    ) -> MarketPolicyValidationCheckResult:
        for rule in policy.rules:
            if rule.weight <= 0:
                return MarketPolicyValidationCheckResult(
                    code    = ValidationCode.RULE_CONSISTENCY,
                    passed  = False,
                    message = f"Rule '{rule.rule_id}' has weight <= 0",
                )
        return MarketPolicyValidationCheckResult(
            code=ValidationCode.RULE_CONSISTENCY, passed=True
        )

    @staticmethod
    def _check_condition_validity(
        policy: MarketPolicy,
    ) -> MarketPolicyValidationCheckResult:
        for rule in policy.rules:
            for cond in rule.conditions:
                if not cond.field_path:
                    return MarketPolicyValidationCheckResult(
                        code    = ValidationCode.CONDITION_VALIDITY,
                        passed  = False,
                        message = f"Condition '{cond.condition_id}' has empty field_path",
                    )
                if not isinstance(cond.operator, ConditionOperator):
                    return MarketPolicyValidationCheckResult(
                        code    = ValidationCode.CONDITION_VALIDITY,
                        passed  = False,
                        message = f"Condition '{cond.condition_id}' has invalid operator",
                    )
        return MarketPolicyValidationCheckResult(
            code=ValidationCode.CONDITION_VALIDITY, passed=True
        )

    @staticmethod
    def _check_priority_integrity(
        policy: MarketPolicy,
    ) -> MarketPolicyValidationCheckResult:
        ok = isinstance(policy.priority, PolicyPriority)
        return MarketPolicyValidationCheckResult(
            code    = ValidationCode.PRIORITY_INTEGRITY,
            passed  = ok,
            message = "" if ok else f"Invalid priority: {policy.priority!r}",
        )

    @staticmethod
    def _check_conflict_resolution_integrity(
        policy: MarketPolicy,
    ) -> MarketPolicyValidationCheckResult:
        ok = isinstance(policy.evaluation_mode, EvaluationMode)
        return MarketPolicyValidationCheckResult(
            code    = ValidationCode.CONFLICT_RESOLUTION_INTEGRITY,
            passed  = ok,
            message = "" if ok else f"Invalid evaluation_mode: {policy.evaluation_mode!r}",
        )

    @staticmethod
    def _check_evaluation_completeness(
        policy: MarketPolicy,
    ) -> MarketPolicyValidationCheckResult:
        ok = len(policy.rules) > 0 or policy.default_action is not None
        return MarketPolicyValidationCheckResult(
            code    = ValidationCode.EVALUATION_COMPLETENESS,
            passed  = ok,
            message = "" if ok else "Policy has no rules and no default_action",
        )

    @staticmethod
    def _check_audit_completeness(
        policy: MarketPolicy,
    ) -> MarketPolicyValidationCheckResult:
        ok = bool(policy.policy_id) and bool(policy.version)
        return MarketPolicyValidationCheckResult(
            code    = ValidationCode.AUDIT_COMPLETENESS,
            passed  = ok,
            message = "" if ok else "policy_id and version are required for auditability",
        )

    @staticmethod
    def _check_request_validity(
        request: MarketPolicyRequest,
    ) -> MarketPolicyValidationCheckResult:
        ok = (
            bool(request.request_id)
            and bool(request.evaluation_id)
            and bool(request.market_analysis_id)
            and bool(request.exchange)
        )
        return MarketPolicyValidationCheckResult(
            code    = ValidationCode.REQUEST_VALIDITY,
            passed  = ok,
            message = (
                "" if ok else
                "request_id, evaluation_id, market_analysis_id, and exchange are required"
            ),
        )
