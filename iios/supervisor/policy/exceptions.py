"""
exceptions.py — iios.supervisor.policy
========================================
Exception hierarchy for the AI Governance Policy Framework.

Error-code prefix: GP (Governance Policy).

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class GovernancePolicyError(IIOSError):
    """Base error for the AI Governance Policy Framework (GP-000)."""
    error_code: str = "GP-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class GovernancePolicyEngineNotRunningError(GovernancePolicyError):
    """Raised when an operation requires the engine to be running (GP-001)."""
    error_code = "GP-001"

    def __init__(self) -> None:
        super().__init__(
            "Governance policy engine is not running — call start() first",
            code=self.error_code,
        )


class GovernancePolicyNotFoundError(GovernancePolicyError):
    """Raised when a policy_id lookup fails (GP-002)."""
    error_code = "GP-002"

    def __init__(self, policy_id: str = "") -> None:
        detail = f" (policy_id={policy_id!r})" if policy_id else ""
        super().__init__(
            f"Governance policy not found{detail}",
            code=self.error_code,
        )
        self.policy_id = policy_id


class GovernancePolicyRegistryError(GovernancePolicyError):
    """Raised on registry constraint violations (GP-003)."""
    error_code = "GP-003"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Governance policy registry error: {message}",
            code=self.error_code,
        )


class GovernancePolicyCapacityError(GovernancePolicyError):
    """Raised when the policy registry capacity is exceeded (GP-004)."""
    error_code = "GP-004"

    def __init__(self, limit: int = 0) -> None:
        super().__init__(
            f"Governance policy capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit = limit


class GovernancePolicyEvaluationError(GovernancePolicyError):
    """Raised when a policy evaluation fails structurally (GP-005)."""
    error_code = "GP-005"

    def __init__(self, message: str = "", *, request_id: str = "") -> None:
        detail = f" (request_id={request_id!r})" if request_id else ""
        super().__init__(
            f"Governance policy evaluation error{detail}: {message}",
            code=self.error_code,
        )
        self.request_id = request_id


class GovernancePolicyValidationError(GovernancePolicyError):
    """Raised when policy structural validation fails (GP-006)."""
    error_code = "GP-006"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Governance policy validation failed: {message}",
            code=self.error_code,
        )


class GovernancePolicyConditionError(GovernancePolicyError):
    """Raised when a policy condition is structurally invalid (GP-007)."""
    error_code = "GP-007"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Governance policy condition error: {message}",
            code=self.error_code,
        )


class GovernancePolicyRuleError(GovernancePolicyError):
    """Raised when a policy rule is structurally invalid (GP-008)."""
    error_code = "GP-008"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Governance policy rule error: {message}",
            code=self.error_code,
        )


class GovernancePolicyHistoryError(GovernancePolicyError):
    """Raised on history access/integrity failures (GP-009)."""
    error_code = "GP-009"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Governance policy history error: {message}",
            code=self.error_code,
        )
