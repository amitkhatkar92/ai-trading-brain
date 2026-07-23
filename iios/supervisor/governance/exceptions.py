"""
exceptions.py — iios.supervisor.governance
-------------------------------------------
Exception hierarchy for the Autonomous Governance Framework.

Error-code prefix: AGF (Autonomous Governance Framework).

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 4
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class AutonomousGovernanceError(IIOSError):
    """Base exception for the Autonomous Governance Framework (AGF-000)."""
    error_code: str = "AGF-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class AutonomousGovernanceEngineNotRunningError(AutonomousGovernanceError):
    """Engine is not running — call start() first (AGF-001)."""
    error_code = "AGF-001"

    def __init__(self) -> None:
        super().__init__(
            "Autonomous Governance Engine is not running — call start() first",
            code=self.error_code,
        )


class AutonomousGovernanceSessionError(AutonomousGovernanceError):
    """Session lifecycle error (AGF-002)."""
    error_code = "AGF-002"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Autonomous governance session error: {message}",
            code=self.error_code,
        )


class AutonomousGovernanceContextError(AutonomousGovernanceError):
    """Invalid or incomplete governance context (AGF-003)."""
    error_code = "AGF-003"

    def __init__(self, message: str = "", *, supervision_id: str = "") -> None:
        detail = f" (supervision_id={supervision_id!r})" if supervision_id else ""
        super().__init__(
            f"Autonomous governance context error{detail}: {message}",
            code=self.error_code,
        )
        self.supervision_id: str = supervision_id


class AutonomousGovernanceValidationError(AutonomousGovernanceError):
    """Validation failure (AGF-004)."""
    error_code = "AGF-004"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Autonomous governance validation error: {message}",
            code=self.error_code,
        )


class AutonomousGovernanceAssessmentError(AutonomousGovernanceError):
    """Enterprise assessment failure (AGF-005)."""
    error_code = "AGF-005"

    def __init__(self, message: str = "", *, request_id: str = "") -> None:
        detail = f" (request_id={request_id!r})" if request_id else ""
        super().__init__(
            f"Autonomous governance assessment error{detail}: {message}",
            code=self.error_code,
        )
        self.request_id: str = request_id


class AutonomousGovernanceReasoningError(AutonomousGovernanceError):
    """Enterprise reasoning failure (AGF-006)."""
    error_code = "AGF-006"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Autonomous governance reasoning error: {message}",
            code=self.error_code,
        )


class AutonomousGovernanceRegistryError(AutonomousGovernanceError):
    """Registry constraint violation (AGF-007)."""
    error_code = "AGF-007"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Autonomous governance registry error: {message}",
            code=self.error_code,
        )


class AutonomousGovernanceCapacityError(AutonomousGovernanceError):
    """Session registry capacity exceeded (AGF-008)."""
    error_code = "AGF-008"

    def __init__(self, limit: int = 0) -> None:
        super().__init__(
            f"Autonomous governance capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit: int = limit


class AutonomousGovernancePublicationError(AutonomousGovernanceError):
    """Governance result publication failure (AGF-009)."""
    error_code = "AGF-009"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Autonomous governance publication error: {message}",
            code=self.error_code,
        )
