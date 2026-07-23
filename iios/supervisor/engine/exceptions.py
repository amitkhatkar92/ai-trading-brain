"""
exceptions.py — iios.supervisor.engine
========================================
Exception hierarchy for the Institutional AI Supervisor Engine subsystem.

Error-code prefix: SE (Supervisor Engine).

C13 AI Supervisor & Autonomous Governance — Phase 1, Module 2
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class SupervisorEngineError(IIOSError):
    """Base error for the AI Supervisor Engine subsystem (SE-000)."""
    error_code: str = "SE-000"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class SupervisorEngineNotRunningError(SupervisorEngineError):
    """Raised when an operation is attempted before the engine is started (SE-001)."""
    error_code = "SE-001"

    def __init__(self) -> None:
        super().__init__(
            "Supervisor engine is not running — call start() first",
            code=self.error_code,
        )


class SupervisorSessionError(SupervisorEngineError):
    """Raised when a supervisor session operation fails (SE-002)."""
    error_code = "SE-002"

    def __init__(self, message: str = "", *, session_id: str = "") -> None:
        detail = f" (session_id={session_id!r})" if session_id else ""
        super().__init__(
            f"Supervisor session error{detail}: {message}",
            code=self.error_code,
        )
        self.session_id = session_id


class SupervisorPipelineError(SupervisorEngineError):
    """Raised when a supervisor pipeline operation fails (SE-003)."""
    error_code = "SE-003"

    def __init__(self, message: str = "", *, pipeline_id: str = "") -> None:
        detail = f" (pipeline_id={pipeline_id!r})" if pipeline_id else ""
        super().__init__(
            f"Supervisor pipeline error{detail}: {message}",
            code=self.error_code,
        )
        self.pipeline_id = pipeline_id


class SupervisorDispatchError(SupervisorEngineError):
    """Raised when dispatching a supervisor workflow fails (SE-004)."""
    error_code = "SE-004"

    def __init__(self, message: str = "", *, workflow_type: str = "") -> None:
        detail = f" (workflow={workflow_type!r})" if workflow_type else ""
        super().__init__(
            f"Supervisor dispatch error{detail}: {message}",
            code=self.error_code,
        )
        self.workflow_type = workflow_type


class SupervisorCollectionError(SupervisorEngineError):
    """Raised when collecting subsystem snapshots fails (SE-005)."""
    error_code = "SE-005"

    def __init__(self, message: str = "", *, missing_inputs: tuple = ()) -> None:
        super().__init__(
            f"Supervisor collection error: {message}",
            code=self.error_code,
        )
        self.missing_inputs = missing_inputs


class SupervisorPublicationError(SupervisorEngineError):
    """Raised when publishing a supervisor snapshot fails (SE-006)."""
    error_code = "SE-006"

    def __init__(self, message: str = "", *, supervision_id: str = "") -> None:
        detail = f" (supervision_id={supervision_id!r})" if supervision_id else ""
        super().__init__(
            f"Supervisor publication error{detail}: {message}",
            code=self.error_code,
        )
        self.supervision_id = supervision_id


class SupervisorEngineValidationError(SupervisorEngineError):
    """Raised when supervisor engine validation checks fail (SE-007)."""
    error_code = "SE-007"

    def __init__(self, message: str = "", *, failed_checks: tuple = ()) -> None:
        super().__init__(
            f"Supervisor engine validation failed: {message}",
            code=self.error_code,
        )
        self.failed_checks = failed_checks


class SupervisorSchedulerError(SupervisorEngineError):
    """Raised when the supervisor scheduler encounters an error (SE-008)."""
    error_code = "SE-008"

    def __init__(self, message: str = "") -> None:
        super().__init__(
            f"Supervisor scheduler error: {message}",
            code=self.error_code,
        )


class SupervisorEngineCapacityError(SupervisorEngineError):
    """Raised when an engine capacity limit is exceeded (SE-009)."""
    error_code = "SE-009"

    def __init__(self, limit: int = 0) -> None:
        super().__init__(
            f"Supervisor engine capacity exceeded (limit={limit})",
            code=self.error_code,
        )
        self.limit = limit
