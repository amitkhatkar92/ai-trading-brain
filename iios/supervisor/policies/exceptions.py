"""
exceptions.py — iios.supervisor.policies
------------------------------------------
Exception hierarchy for the AI Governance Policy Framework.

Error-code prefix: AGP (AI Governance Policy).

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 3
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class AIGovernancePolicyError(IIOSError):
    """Base exception for the AI Governance Policy Framework (AGP-000)."""
    error_code: str = "AGP-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class AIGovernancePolicyEngineNotRunningError(AIGovernancePolicyError):
    """Engine is not running — call start() first (AGP-001)."""
    error_code = "AGP-001"

    def __init__(self) -> None:
        super().__init__(
            "AI Governance Policy Engine is not running — call start() first",
            code=self.error_code,
        )


class AIGovernancePolicyNotFoundError(AIGovernancePolicyError):
    """Policy ID lookup failed (AGP-002)."""
    error_code = "AGP-002"

    def __init__(self, policy_id: str = "") -> None:
        detail = f" (policy_id={policy_id!r})" if policy_id else ""
        super().__init__(
            f"AI governance policy not found{detail}",
            code=self.error_code,
        )
        self.policy_id: str = policy_id


class AIGovernancePolicyRegistryError(AIGovernancePolicyError):
    """Registry constraint violation (AGP-003)."""
    error_code = "AGP-003"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"AI governance policy registry error: {message}",
            code=self.error_code,
        )


class AIGovernancePolicyCapacityError(AIGovernancePolicyError):
    """Policy registry capacity exceeded (AGP-004)."""
    error_code = "AGP-004"

    def __init__(self, limit: int = 0) -> None:
        super().__init__(
            f"AI governance policy capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit: int = limit


class AIGovernancePolicyEvaluationError(AIGovernancePolicyError):
    """Structural policy evaluation failure (AGP-005)."""
    error_code = "AGP-005"

    def __init__(self, message: str = "", *, request_id: str = "") -> None:
        detail = f" (request_id={request_id!r})" if request_id else ""
        super().__init__(
            f"AI governance policy evaluation error{detail}: {message}",
            code=self.error_code,
        )
        self.request_id: str = request_id


class AIGovernancePolicyValidationError(AIGovernancePolicyError):
    """Policy structural validation failure (AGP-006)."""
    error_code = "AGP-006"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"AI governance policy validation error: {message}",
            code=self.error_code,
        )


class AIGovernancePolicyConditionError(AIGovernancePolicyError):
    """Condition evaluation failure (AGP-007)."""
    error_code = "AGP-007"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"AI governance policy condition error: {message}",
            code=self.error_code,
        )


class AIGovernancePolicyRuleError(AIGovernancePolicyError):
    """Rule evaluation failure (AGP-008)."""
    error_code = "AGP-008"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"AI governance policy rule error: {message}",
            code=self.error_code,
        )


class AIGovernancePolicyHistoryError(AIGovernancePolicyError):
    """History access or capacity failure (AGP-009)."""
    error_code = "AGP-009"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"AI governance policy history error: {message}",
            code=self.error_code,
        )


class AIGovernancePolicyAuditError(AIGovernancePolicyError):
    """Audit generation or storage failure (AGP-010)."""
    error_code = "AGP-010"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"AI governance policy audit error: {message}",
            code=self.error_code,
        )


class AIGovernancePolicyConflictError(AIGovernancePolicyError):
    """Policy conflict that cannot be resolved by the configured strategy (AGP-011)."""
    error_code = "AGP-011"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"AI governance policy conflict error: {message}",
            code=self.error_code,
        )
