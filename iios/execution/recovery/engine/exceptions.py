"""
iios/execution/recovery/engine/exceptions.py
============================================
Exception hierarchy for the Execution Recovery Engine.

Error codes: RE-000 … RE-010

C7 Execution Recovery & Resilience — Phase 1, Module 2
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class RecoveryEngineError(IIOSError):
    """Base exception for the Execution Recovery Engine."""

    error_code = "RE-000"

    def __init__(
        self,
        message: str = "Recovery engine error",
        *,
        context=None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=self.error_code,
            context=context,
            correlation_id=correlation_id,
        )


class RecoveryEngineNotRunningError(RecoveryEngineError):
    """Raised when an operation requires the engine to be running."""

    error_code = "RE-001"

    def __init__(self) -> None:
        super().__init__("Recovery engine is not running")


class RecoveryEngineAlreadyRunningError(RecoveryEngineError):
    """Raised when the engine is started while already running."""

    error_code = "RE-002"

    def __init__(self) -> None:
        super().__init__("Recovery engine is already running")


class RecoveryRequestNotFoundError(RecoveryEngineError):
    """Raised when a recovery request cannot be located."""

    error_code = "RE-003"

    def __init__(self, request_id: str) -> None:
        super().__init__(f"Recovery request not found: {request_id!r}")
        self.request_id = request_id


class RecoveryRequestValidationError(RecoveryEngineError):
    """Raised when a recovery request fails validation."""

    error_code = "RE-004"

    def __init__(self, message: str, *, errors: tuple = ()) -> None:
        super().__init__(message)
        self.errors = errors


class RecoveryDispatchError(RecoveryEngineError):
    """Raised when the dispatcher cannot dispatch a recovery workflow."""

    error_code = "RE-005"

    def __init__(self, message: str, *, request_id: str = "") -> None:
        super().__init__(message)
        self.request_id = request_id


class RecoverySchedulerError(RecoveryEngineError):
    """Raised by the recovery scheduler."""

    error_code = "RE-006"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class RecoveryPipelineError(RecoveryEngineError):
    """Raised when a pipeline stage fails."""

    error_code = "RE-007"

    def __init__(self, message: str, *, stage: str = "") -> None:
        super().__init__(message)
        self.stage = stage


class RecoverySessionManagerError(RecoveryEngineError):
    """Raised by the recovery session manager."""

    error_code = "RE-008"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class RecoverySnapshotError(RecoveryEngineError):
    """Raised when a recovery snapshot cannot be created or published."""

    error_code = "RE-009"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class RecoveryContextValidationError(RecoveryEngineError):
    """Raised when recovery context fails validation."""

    error_code = "RE-010"

    def __init__(self, message: str, *, errors: tuple = ()) -> None:
        super().__init__(message)
        self.errors = errors
