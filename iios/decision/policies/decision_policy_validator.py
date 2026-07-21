"""
decision_policy_validator.py — iios.decision.policies
=======================================================
Structural and consistency validation for policy objects.

Six validation checks
----------------------
1. POLICY_IDENTITY    — policy_id / name are non-empty
2. RULE_CONSISTENCY   — every rule has at least one condition
3. CONDITION_VALIDITY — every condition has a non-empty field_path
4. PRIORITY_INTEGRITY — priority is a recognised PolicyPriority value
5. CONFLICT_INTEGRITY — policy has at least one rule or an explicit default
6. AUDIT_COMPLETENESS — policy_type and default_action are set

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from iios.common.logging.logging_manager import get_logger

from .constants import PolicyPriority, PolicyValidationCode
from .decision_policy import DecisionPolicy
from .decision_policy_request import PolicyEvaluationRequest

_log = get_logger(__name__)


@dataclass(frozen=True)
class PolicyValidationCheckResult:
    """Outcome of a single validation check."""
    code:    PolicyValidationCode
    passed:  bool
    message: str


@dataclass(frozen=True)
class PolicyValidationResult:
    """Aggregated outcome of all validation checks."""
    is_valid:      bool
    checks:        Tuple[PolicyValidationCheckResult, ...]
    failed_checks: Tuple[PolicyValidationCode, ...]
    passed_count:  int
    failed_count:  int

    @property
    def error_messages(self) -> Tuple[str, ...]:
        return tuple(c.message for c in self.checks if not c.passed)


class DecisionPolicyValidator:
    """
    Validates :class:`DecisionPolicy` and :class:`PolicyEvaluationRequest`
    objects for structural correctness.

    Validation does not raise; it always returns a
    :class:`PolicyValidationResult`.  The caller decides how to act on
    failed checks.
    """

    # ------------------------------------------------------------------
    # Policy validation
    # ------------------------------------------------------------------

    def validate_policy(self, policy: DecisionPolicy) -> PolicyValidationResult:
        """Run all six checks against *policy*."""
        checks: List[PolicyValidationCheckResult] = [
            self._check_identity(policy),
            self._check_rule_consistency(policy),
            self._check_condition_validity(policy),
            self._check_priority_integrity(policy),
            self._check_conflict_integrity(policy),
            self._check_audit_completeness(policy),
        ]
        return self._build(checks)

    def _check_identity(self, policy: DecisionPolicy) -> PolicyValidationCheckResult:
        ok = bool(policy.policy_id and policy.name)
        return PolicyValidationCheckResult(
            code    = PolicyValidationCode.POLICY_IDENTITY,
            passed  = ok,
            message = "" if ok else "policy_id and name must be non-empty",
        )

    def _check_rule_consistency(self, policy: DecisionPolicy) -> PolicyValidationCheckResult:
        bad = [r for r in policy.rules if not r.conditions]
        ok  = len(bad) == 0
        return PolicyValidationCheckResult(
            code    = PolicyValidationCode.RULE_CONSISTENCY,
            passed  = ok,
            message = "" if ok else (
                f"{len(bad)} rule(s) have no conditions: "
                f"{[r.name for r in bad]}"
            ),
        )

    def _check_condition_validity(self, policy: DecisionPolicy) -> PolicyValidationCheckResult:
        empty_path: List[str] = []
        for rule in policy.rules:
            for cond in rule.conditions:
                if not cond.field_path:
                    empty_path.append(cond.condition_id)
        ok = len(empty_path) == 0
        return PolicyValidationCheckResult(
            code    = PolicyValidationCode.CONDITION_VALIDITY,
            passed  = ok,
            message = "" if ok else (
                f"{len(empty_path)} condition(s) have empty field_path: {empty_path}"
            ),
        )

    def _check_priority_integrity(self, policy: DecisionPolicy) -> PolicyValidationCheckResult:
        try:
            _ = PolicyPriority(int(policy.priority))
            ok = True
        except (ValueError, TypeError):
            ok = False
        return PolicyValidationCheckResult(
            code    = PolicyValidationCode.PRIORITY_INTEGRITY,
            passed  = ok,
            message = "" if ok else (
                f"priority value {policy.priority!r} is not a valid PolicyPriority"
            ),
        )

    def _check_conflict_integrity(self, policy: DecisionPolicy) -> PolicyValidationCheckResult:
        # Policy is coherent if it has at least one rule OR a default action
        ok = bool(policy.rules) or (policy.default_action is not None)
        return PolicyValidationCheckResult(
            code    = PolicyValidationCode.CONFLICT_INTEGRITY,
            passed  = ok,
            message = "" if ok else "policy has no rules and no default_action",
        )

    def _check_audit_completeness(self, policy: DecisionPolicy) -> PolicyValidationCheckResult:
        ok = policy.policy_type is not None and policy.default_action is not None
        return PolicyValidationCheckResult(
            code    = PolicyValidationCode.AUDIT_COMPLETENESS,
            passed  = ok,
            message = "" if ok else "policy_type and default_action must be set",
        )

    # ------------------------------------------------------------------
    # Request validation
    # ------------------------------------------------------------------

    def validate_request(self, request: PolicyEvaluationRequest) -> PolicyValidationResult:
        """Light-weight structural check on an evaluation request."""
        checks: List[PolicyValidationCheckResult] = []

        rid_ok = bool(request.request_id)
        checks.append(PolicyValidationCheckResult(
            code    = PolicyValidationCode.POLICY_IDENTITY,
            passed  = rid_ok,
            message = "" if rid_ok else "request_id must be non-empty",
        ))

        ctx_ok = request.context is not None
        checks.append(PolicyValidationCheckResult(
            code    = PolicyValidationCode.AUDIT_COMPLETENESS,
            passed  = ctx_ok,
            message = "" if ctx_ok else "request context must not be None",
        ))

        return self._build(checks)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build(checks: List[PolicyValidationCheckResult]) -> PolicyValidationResult:
        failed = [c for c in checks if not c.passed]
        return PolicyValidationResult(
            is_valid      = len(failed) == 0,
            checks        = tuple(checks),
            failed_checks = tuple(c.code for c in failed),
            passed_count  = len(checks) - len(failed),
            failed_count  = len(failed),
        )
