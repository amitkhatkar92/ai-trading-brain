"""
exceptions.py — iios.market.policies
======================================
Exception hierarchy for the Market Policy Framework.

Error-code prefix: MP (Market Policy).

C12 Market Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class MarketPolicyError(IIOSError):
    """Base exception for the Market Policy Framework (MP-000)."""
    error_code: str = "MP-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class MarketPolicyEngineNotRunningError(MarketPolicyError):
    """Engine operation attempted before start() (MP-001)."""
    error_code = "MP-001"

    def __init__(self) -> None:
        super().__init__(
            "Market policy engine is not running — call start() first",
            code=self.error_code,
        )


class MarketPolicyNotFoundError(MarketPolicyError):
    """Referenced policy not found in the registry (MP-002)."""
    error_code = "MP-002"

    def __init__(self, policy_id: str) -> None:
        super().__init__(
            f"Market policy not found: {policy_id!r}",
            code=self.error_code,
        )
        self.policy_id = policy_id


class MarketPolicyValidationError(MarketPolicyError):
    """Policy configuration fails validation (MP-003)."""
    error_code = "MP-003"

    def __init__(
        self,
        message: str = "",
        *,
        failed_checks: tuple = (),
        policy_id: str = "",
    ) -> None:
        detail = f" (policy_id={policy_id!r})" if policy_id else ""
        super().__init__(
            f"Market policy validation failed{detail}: {message}",
            code=self.error_code,
        )
        self.failed_checks = failed_checks
        self.policy_id = policy_id


class MarketPolicyEvaluationError(MarketPolicyError):
    """Error during policy evaluation (MP-004)."""
    error_code = "MP-004"

    def __init__(self, message: str = "", *, policy_id: str = "") -> None:
        detail = f" (policy_id={policy_id!r})" if policy_id else ""
        super().__init__(
            f"Market policy evaluation error{detail}: {message}",
            code=self.error_code,
        )
        self.policy_id = policy_id


class MarketPolicyConflictError(MarketPolicyError):
    """Irresolvable conflict between policy outcomes (MP-005)."""
    error_code = "MP-005"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Market policy conflict: {message}",
            code=self.error_code,
        )


class MarketPolicyRegistryError(MarketPolicyError):
    """Registry operation error (MP-006)."""
    error_code = "MP-006"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Market policy registry error: {message}",
            code=self.error_code,
        )


class MarketPolicyConfigurationError(MarketPolicyError):
    """Invalid policy configuration (MP-007)."""
    error_code = "MP-007"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Market policy configuration error: {message}",
            code=self.error_code,
        )


class MarketPolicyAuditError(MarketPolicyError):
    """Audit trail generation error (MP-008)."""
    error_code = "MP-008"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Market policy audit error: {message}",
            code=self.error_code,
        )


class MarketPolicyCapacityError(MarketPolicyError):
    """Registry capacity exhausted (MP-009)."""
    error_code = "MP-009"

    def __init__(self, limit: int) -> None:
        super().__init__(
            f"Market policy registry capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit = limit
