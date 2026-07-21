"""
exceptions.py — iios.decision.policies
========================================
Exception hierarchy for the Decision Policy Framework.

Error codes: DP-000 through DP-008

C9 Decision Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class DecisionPolicyError(IIOSError):
    """Base exception for all decision policy errors.  DP-000"""
    error_code = "DP-000"

    def __init__(self, message: str = "Decision policy error", **_kw: object) -> None:
        super().__init__(message, code=self.error_code)


class PolicyNotFoundError(DecisionPolicyError):
    """Raised when a policy is not found in the registry.  DP-001"""
    error_code = "DP-001"

    def __init__(self, policy_id: str = "") -> None:
        self.policy_id = policy_id
        super().__init__(f"Policy not found: {policy_id!r}")


class PolicyConfigurationError(DecisionPolicyError):
    """Raised when a policy is misconfigured.  DP-002"""
    error_code = "DP-002"

    def __init__(self, message: str = "Policy configuration error", policy_id: str = "") -> None:
        self.policy_id = policy_id
        super().__init__(message)


class PolicyEvaluationError(DecisionPolicyError):
    """Raised when a policy evaluation fails unexpectedly.  DP-003"""
    error_code = "DP-003"

    def __init__(self, message: str = "Policy evaluation error", policy_id: str = "") -> None:
        self.policy_id = policy_id
        super().__init__(message or f"Policy evaluation error: {policy_id!r}")


class PolicyConflictError(DecisionPolicyError):
    """Raised when unresolvable policy conflicts are detected.  DP-004"""
    error_code = "DP-004"

    def __init__(self, message: str = "Unresolvable policy conflict") -> None:
        super().__init__(message)


class PolicyValidationError(DecisionPolicyError):
    """Raised when policy validation fails.  DP-005"""
    error_code = "DP-005"

    def __init__(
        self,
        message: str = "Policy validation failed",
        failed_checks: tuple[str, ...] = (),
    ) -> None:
        self.failed_checks = tuple(failed_checks)
        super().__init__(message)


class PolicyChainError(DecisionPolicyError):
    """Raised when a policy chain configuration or execution fails.  DP-006"""
    error_code = "DP-006"

    def __init__(self, message: str = "Policy chain error", chain_id: str = "") -> None:
        self.chain_id = chain_id
        super().__init__(message)


class PolicyRegistryError(DecisionPolicyError):
    """Raised when the policy registry operation fails.  DP-007"""
    error_code = "DP-007"

    def __init__(self, message: str = "Policy registry error") -> None:
        super().__init__(message)


class PolicyEngineNotRunningError(DecisionPolicyError):
    """Raised when an operation is attempted on a stopped engine.  DP-008"""
    error_code = "DP-008"

    def __init__(self, message: str = "Decision policy engine is not running") -> None:
        super().__init__(message)
