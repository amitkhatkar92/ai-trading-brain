"""
iios/execution/recovery/policies/exceptions.py
==============================================
Exception hierarchy for the Execution Recovery Policy Framework.

Error codes: RP-000 … RP-008

C7 Execution Recovery & Resilience — Phase 1, Module 3
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class RecoveryPolicyError(IIOSError):
    """Base exception for the Recovery Policy Framework."""
    error_code = "RP-000"
    def __init__(self, message: str = "Recovery policy error", *,
                 context=None, correlation_id: str = "") -> None:
        super().__init__(message, code=self.error_code,
                         context=context, correlation_id=correlation_id)


class RecoveryPolicyNotRunningError(RecoveryPolicyError):
    """Raised when an operation requires the policy engine to be running."""
    error_code = "RP-001"
    def __init__(self) -> None:
        super().__init__("Recovery policy engine is not running")


class RecoveryPolicyNotFoundError(RecoveryPolicyError):
    """Raised when a named policy cannot be found."""
    error_code = "RP-002"
    def __init__(self, policy_name: str) -> None:
        super().__init__(f"Recovery policy not found: {policy_name!r}")
        self.policy_name = policy_name


class RecoveryPolicyValidationError(RecoveryPolicyError):
    """Raised when a policy fails validation."""
    error_code = "RP-003"
    def __init__(self, message: str, *, errors: tuple = ()) -> None:
        super().__init__(message)
        self.errors = errors


class RecoveryRuleValidationError(RecoveryPolicyError):
    """Raised when a rule fails validation."""
    error_code = "RP-004"
    def __init__(self, message: str, *, rule_id: str = "") -> None:
        super().__init__(message)
        self.rule_id = rule_id


class RecoveryStrategyNotFoundError(RecoveryPolicyError):
    """Raised when a required recovery strategy is not available."""
    error_code = "RP-005"
    def __init__(self, strategy_type: str) -> None:
        super().__init__(f"Recovery strategy not found: {strategy_type!r}")
        self.strategy_type = strategy_type


class RecoveryPolicyEvaluationError(RecoveryPolicyError):
    """Raised when policy evaluation encounters an unrecoverable error."""
    error_code = "RP-006"
    def __init__(self, message: str, *, policy_name: str = "") -> None:
        super().__init__(message)
        self.policy_name = policy_name


class RecoveryPolicyConflictError(RecoveryPolicyError):
    """Raised when two policies produce conflicting decisions."""
    error_code = "RP-007"
    def __init__(self, policy_a: str, policy_b: str) -> None:
        super().__init__(f"Policy conflict between {policy_a!r} and {policy_b!r}")
        self.policy_a = policy_a
        self.policy_b = policy_b


class RecoveryPolicyRegistryError(RecoveryPolicyError):
    """Raised by the policy registry."""
    error_code = "RP-008"
    def __init__(self, message: str) -> None:
        super().__init__(message)
