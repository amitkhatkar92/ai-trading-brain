"""
exceptions.py — iios.portfolio.policies
========================================
Exception hierarchy for the Institutional Portfolio Policy Framework.

Error-code prefix: PP (Portfolio Policies)

C10 Portfolio Intelligence — Phase 1, Module 3
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class PortfolioPolicyError(IIOSError):
    """
    Base error for the Institutional Portfolio Policy Framework.

    All policy exceptions derive from this class so callers can catch
    the entire family with a single ``except PortfolioPolicyError``.
    """
    error_code: str = "PP-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class PortfolioPolicyNotFoundError(PortfolioPolicyError):
    """Raised when a policy_id lookup fails in the registry."""
    error_code = "PP-001"

    def __init__(self, policy_id: str = "") -> None:
        self.policy_id = policy_id
        detail = f" (policy_id={policy_id!r})" if policy_id else ""
        super().__init__(f"Policy not found{detail}", code=self.error_code)


class PortfolioPolicyNotRunningError(PortfolioPolicyError):
    """Raised when the engine is called before it has been started."""
    error_code = "PP-002"

    def __init__(self) -> None:
        super().__init__("Portfolio policy engine is not running", code=self.error_code)


class PortfolioPolicyConfigurationError(PortfolioPolicyError):
    """Raised when a policy or rule is misconfigured."""
    error_code = "PP-003"

    def __init__(self, message: str, *, field: str = "") -> None:
        self.field = field
        super().__init__(message, code=self.error_code)


class PortfolioPolicyEvaluationError(PortfolioPolicyError):
    """Raised when an evaluation run fails unrecoverably."""
    error_code = "PP-004"

    def __init__(self, message: str, *, evaluation_id: str = "") -> None:
        self.evaluation_id = evaluation_id
        super().__init__(message, code=self.error_code)


class PortfolioPolicyConflictError(PortfolioPolicyError):
    """Raised when conflicting policy outcomes cannot be resolved."""
    error_code = "PP-005"

    def __init__(self, message: str, *, conflicting_policies: tuple = ()) -> None:
        self.conflicting_policies = conflicting_policies
        super().__init__(message, code=self.error_code)


class PortfolioPolicyValidationError(PortfolioPolicyError):
    """Raised when a policy or request fails configuration validation."""
    error_code = "PP-006"

    def __init__(self, message: str, *, failed_checks: tuple = ()) -> None:
        self.failed_checks = failed_checks
        super().__init__(message, code=self.error_code)


class PortfolioPolicyAuditError(PortfolioPolicyError):
    """Raised when the audit subsystem encounters an error."""
    error_code = "PP-007"

    def __init__(self, message: str) -> None:
        super().__init__(message, code=self.error_code)


class PortfolioPolicyCapacityError(PortfolioPolicyError):
    """Raised when the policy registry is at capacity."""
    error_code = "PP-008"

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(
            f"Policy registry capacity exceeded (limit={limit})",
            code=self.error_code,
        )


class PortfolioPolicyChainError(PortfolioPolicyError):
    """Raised when a policy chain encounters an error."""
    error_code = "PP-009"

    def __init__(self, message: str, *, chain_id: str = "") -> None:
        self.chain_id = chain_id
        super().__init__(message, code=self.error_code)
