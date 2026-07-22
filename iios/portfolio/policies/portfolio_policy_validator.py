"""
portfolio_policy_validator.py — iios.portfolio.policies
========================================================
Policy and request validation for the Portfolio Policy Framework.

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .constants import PolicyStatus


@dataclass(frozen=True)
class PolicyValidationCheckResult:
    """Result of a single validation check."""
    code:    str
    passed:  bool
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "passed": self.passed, "message": self.message}


@dataclass(frozen=True)
class PolicyValidationResult:
    """
    Aggregate result of validating a policy or request.

    Fields
    ------
    is_valid :      True iff all checks passed.
    checks :        Tuple of all individual check results.
    failed_checks : Subset of checks that failed.
    passed_count :  Number of passed checks.
    failed_count :  Number of failed checks.
    """
    is_valid:      bool
    checks:        tuple   # Tuple[PolicyValidationCheckResult, ...]
    failed_checks: tuple   # Tuple[PolicyValidationCheckResult, ...]
    passed_count:  int
    failed_count:  int

    @property
    def error_messages(self) -> List[str]:
        return [c.message for c in self.failed_checks if c.message]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid":     self.is_valid,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "checks":       [c.to_dict() for c in self.checks],
        }


def _result_from_checks(checks: List[PolicyValidationCheckResult]) -> PolicyValidationResult:
    failed = tuple(c for c in checks if not c.passed)
    return PolicyValidationResult(
        is_valid      = len(failed) == 0,
        checks        = tuple(checks),
        failed_checks = failed,
        passed_count  = sum(1 for c in checks if c.passed),
        failed_count  = len(failed),
    )


class PortfolioPolicyValidator:
    """
    Validates PortfolioPolicy configurations and PortfolioPolicyRequest objects.

    Policy validation checks (6):
        POLICY_IDENTITY   — policy_id and name must be non-empty.
        POLICY_TYPE       — policy_type must be a valid PolicyType.
        POLICY_PRIORITY   — priority must be a valid PolicyPriority.
        POLICY_STATUS     — status must be a valid PolicyStatus.
        POLICY_RULES      — at least one rule or explicitly a rule-less policy.
        POLICY_VERSION    — version must be a non-empty string.

    Request validation checks (6):
        REQUEST_IDENTITY  — request_id must be non-empty.
        REQUEST_PORTFOLIO — portfolio_id must be non-empty.
        REQUEST_CONTEXT   — context must not be None.
        REQUEST_PRIORITY  — priority must be a valid PolicyPriority.
        REQUEST_POLICY_TYPES — if present, policy_types must contain valid types.
        REQUEST_INPUTS    — inputs must be a dict.
    """

    # ------------------------------------------------------------------
    # Policy validation
    # ------------------------------------------------------------------

    def validate_policy(self, policy: Any) -> PolicyValidationResult:
        """Validate a PortfolioPolicy's configuration."""
        checks: List[PolicyValidationCheckResult] = []

        # POLICY_IDENTITY
        has_id   = bool(getattr(policy, "policy_id", ""))
        has_name = bool(getattr(policy, "name", ""))
        checks.append(PolicyValidationCheckResult(
            "POLICY_IDENTITY",
            has_id and has_name,
            "" if (has_id and has_name) else "policy_id and name must be non-empty",
        ))

        # POLICY_TYPE
        from .constants import PolicyType
        pt = getattr(policy, "policy_type", None)
        valid_type = isinstance(pt, PolicyType)
        checks.append(PolicyValidationCheckResult(
            "POLICY_TYPE",
            valid_type,
            "" if valid_type else f"invalid policy_type: {pt!r}",
        ))

        # POLICY_PRIORITY
        from .constants import PolicyPriority
        pri = getattr(policy, "priority", None)
        valid_pri = isinstance(pri, PolicyPriority)
        checks.append(PolicyValidationCheckResult(
            "POLICY_PRIORITY",
            valid_pri,
            "" if valid_pri else f"invalid priority: {pri!r}",
        ))

        # POLICY_STATUS
        status = getattr(policy, "status", None)
        valid_status = isinstance(status, PolicyStatus)
        checks.append(PolicyValidationCheckResult(
            "POLICY_STATUS",
            valid_status,
            "" if valid_status else f"invalid status: {status!r}",
        ))

        # POLICY_RULES — rule_count >= 0 (0-rule policies are allowed)
        rule_count = getattr(policy, "rule_count", None)
        valid_rules = isinstance(rule_count, int) and rule_count >= 0
        checks.append(PolicyValidationCheckResult(
            "POLICY_RULES",
            valid_rules,
            "" if valid_rules else "rule_count must be a non-negative integer",
        ))

        # POLICY_VERSION
        version = getattr(policy, "version", "")
        valid_ver = bool(version)
        checks.append(PolicyValidationCheckResult(
            "POLICY_VERSION",
            valid_ver,
            "" if valid_ver else "version must be a non-empty string",
        ))

        return _result_from_checks(checks)

    # ------------------------------------------------------------------
    # Request validation
    # ------------------------------------------------------------------

    def validate_request(self, request: Any) -> PolicyValidationResult:
        """Validate a PortfolioPolicyRequest."""
        checks: List[PolicyValidationCheckResult] = []

        # REQUEST_IDENTITY
        has_rid = bool(getattr(request, "request_id", ""))
        checks.append(PolicyValidationCheckResult(
            "REQUEST_IDENTITY",
            has_rid,
            "" if has_rid else "request_id must be non-empty",
        ))

        # REQUEST_PORTFOLIO
        has_pid = bool(getattr(request, "portfolio_id", ""))
        checks.append(PolicyValidationCheckResult(
            "REQUEST_PORTFOLIO",
            has_pid,
            "" if has_pid else "portfolio_id must be non-empty",
        ))

        # REQUEST_CONTEXT
        ctx = getattr(request, "context", None)
        has_ctx = ctx is not None
        checks.append(PolicyValidationCheckResult(
            "REQUEST_CONTEXT",
            has_ctx,
            "" if has_ctx else "context must not be None",
        ))

        # REQUEST_PRIORITY
        from .constants import PolicyPriority
        pri = getattr(request, "priority", None)
        valid_pri = isinstance(pri, PolicyPriority)
        checks.append(PolicyValidationCheckResult(
            "REQUEST_PRIORITY",
            valid_pri,
            "" if valid_pri else f"invalid priority: {pri!r}",
        ))

        # REQUEST_POLICY_TYPES
        from .constants import PolicyType
        pts = getattr(request, "policy_types", ())
        valid_pts = all(isinstance(pt, PolicyType) for pt in pts)
        checks.append(PolicyValidationCheckResult(
            "REQUEST_POLICY_TYPES",
            valid_pts,
            "" if valid_pts else "policy_types must contain valid PolicyType values",
        ))

        # REQUEST_INPUTS
        inputs = getattr(request, "inputs", None)
        valid_inputs = isinstance(inputs, dict)
        checks.append(PolicyValidationCheckResult(
            "REQUEST_INPUTS",
            valid_inputs,
            "" if valid_inputs else "inputs must be a dict",
        ))

        return _result_from_checks(checks)
