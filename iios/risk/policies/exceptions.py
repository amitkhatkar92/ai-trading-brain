"""
exceptions.py — iios.risk.policies
=====================================
Exception hierarchy for the Risk Policy Framework.

Error-code prefix: RP (Risk Policy).

C11 Risk Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class RiskPolicyError(IIOSError):
    """Base exception for the Risk Policy Framework (RP-000)."""
    error_code: str = "RP-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class RiskPolicyEngineNotRunningError(RiskPolicyError):
    """Engine operation attempted before start() (RP-001)."""
    error_code = "RP-001"

    def __init__(self) -> None:
        super().__init__(
            "Risk policy engine is not running — call start() first",
            code=self.error_code,
        )


class RiskPolicyNotFoundError(RiskPolicyError):
    """Referenced policy not found in the registry (RP-002)."""
    error_code = "RP-002"

    def __init__(self, policy_id: str) -> None:
        super().__init__(
            f"Policy not found: {policy_id!r}",
            code=self.error_code,
        )
        self.policy_id = policy_id


class RiskPolicyValidationError(RiskPolicyError):
    """Policy configuration fails validation (RP-003)."""
    error_code = "RP-003"

    def __init__(
        self,
        message: str = "",
        *,
        failed_checks: tuple = (),
        policy_id: str = "",
    ) -> None:
        detail = f" (policy_id={policy_id!r})" if policy_id else ""
        super().__init__(
            f"Policy validation failed{detail}: {message}",
            code=self.error_code,
        )
        self.failed_checks = failed_checks
        self.policy_id = policy_id


class RiskPolicyEvaluationError(RiskPolicyError):
    """Error during policy evaluation (RP-004)."""
    error_code = "RP-004"

    def __init__(self, message: str = "", *, policy_id: str = "") -> None:
        detail = f" (policy_id={policy_id!r})" if policy_id else ""
        super().__init__(
            f"Policy evaluation error{detail}: {message}",
            code=self.error_code,
        )
        self.policy_id = policy_id


class RiskPolicyConflictError(RiskPolicyError):
    """Irresolvable conflict between policy outcomes (RP-005)."""
    error_code = "RP-005"

    def __init__(self, message: str = "", *, conflicting_policies: tuple = ()) -> None:
        super().__init__(
            f"Policy conflict: {message}",
            code=self.error_code,
        )
        self.conflicting_policies = conflicting_policies


class RiskPolicyRegistryError(RiskPolicyError):
    """Registry operation failed (RP-006)."""
    error_code = "RP-006"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Policy registry error: {message}",
            code=self.error_code,
        )


class RiskPolicyConfigurationError(RiskPolicyError):
    """Invalid policy configuration (RP-007)."""
    error_code = "RP-007"

    def __init__(self, message: str = "", *, field: str = "") -> None:
        detail = f" (field={field!r})" if field else ""
        super().__init__(
            f"Policy configuration error{detail}: {message}",
            code=self.error_code,
        )
        self.field = field


class RiskPolicyAuditError(RiskPolicyError):
    """Audit trail operation failed (RP-008)."""
    error_code = "RP-008"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Policy audit error: {message}",
            code=self.error_code,
        )


class RiskPolicyCapacityError(RiskPolicyError):
    """Policy registry capacity exceeded (RP-009)."""
    error_code = "RP-009"

    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Policy registry capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit = limit
