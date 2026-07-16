"""iios/execution/positions/engine/exceptions.py
==================================================
Exception hierarchy for the IIOS Position Engine.

Error Codes
-----------
PE2-000  PositionEngineError            — base
PE2-001  PositionEngineNotRunningError  — engine is not started
PE2-002  PositionOperationError         — generic operation failure
PE2-003  PositionCreationError          — create operation failed
PE2-004  PositionUpdateError            — update operation failed
PE2-005  PositionCloseError             — close operation failed
PE2-006  PositionSyncError              — sync operation failed
PE2-007  PositionArchiveError           — archive operation failed
PE2-008  PositionQueryError             — query operation failed
PE2-009  PositionEngineValidationError  — request validation failure
PE2-010  PositionEngineStateError       — engine in unexpected state

C6 Execution Intelligence — Phase 3, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class PositionEngineError(IIOSError):
    """Base for all Position Engine errors."""
    DEFAULT_CODE = "PE2-000"


class PositionEngineNotRunningError(PositionEngineError):
    """The engine or manager is not in the RUNNING state."""
    DEFAULT_CODE = "PE2-001"

    def __init__(
        self,
        *,
        code:           str = "PE2-001",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            "PositionEngine is not running",
            code=code, context=context, correlation_id=correlation_id,
        )


class PositionOperationError(PositionEngineError):
    """A position operation failed for an unspecified reason."""
    DEFAULT_CODE = "PE2-002"

    def __init__(
        self,
        message: str,
        *,
        operation: str = "",
        code:           str = "PE2-002",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {"operation": operation},
            correlation_id=correlation_id,
        )
        self.operation = operation


class PositionCreationError(PositionEngineError):
    """The CREATE_POSITION operation failed."""
    DEFAULT_CODE = "PE2-003"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PE2-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class PositionUpdateError(PositionEngineError):
    """The UPDATE_POSITION operation failed."""
    DEFAULT_CODE = "PE2-004"

    def __init__(
        self,
        position_id: str,
        message: str = "",
        *,
        code:           str = "PE2-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message or f"Update failed for position '{position_id}'",
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id


class PositionCloseError(PositionEngineError):
    """The CLOSE_POSITION operation failed."""
    DEFAULT_CODE = "PE2-005"

    def __init__(
        self,
        position_id: str,
        message: str = "",
        *,
        code:           str = "PE2-005",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message or f"Close failed for position '{position_id}'",
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id


class PositionSyncError(PositionEngineError):
    """The SYNC_POSITION operation failed."""
    DEFAULT_CODE = "PE2-006"

    def __init__(
        self,
        position_id: str,
        message: str = "",
        *,
        code:           str = "PE2-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message or f"Sync failed for position '{position_id}'",
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id


class PositionArchiveError(PositionEngineError):
    """The ARCHIVE_POSITION operation failed."""
    DEFAULT_CODE = "PE2-007"

    def __init__(
        self,
        position_id: str,
        message: str = "",
        *,
        code:           str = "PE2-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message or f"Archive failed for position '{position_id}'",
            code=code,
            context=context or {"position_id": position_id},
            correlation_id=correlation_id,
        )
        self.position_id = position_id


class PositionQueryError(PositionEngineError):
    """The QUERY_POSITION operation failed."""
    DEFAULT_CODE = "PE2-008"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PE2-008",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)


class PositionEngineValidationError(PositionEngineError):
    """Request validation failed before the operation could execute."""
    DEFAULT_CODE = "PE2-009"

    def __init__(
        self,
        message: str,
        *,
        errors:         tuple[str, ...] = (),
        code:           str = "PE2-009",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            message,
            code=code,
            context=context or {"errors": list(errors)},
            correlation_id=correlation_id,
        )
        self.errors = errors


class PositionEngineStateError(PositionEngineError):
    """The engine is in an unexpected operational state."""
    DEFAULT_CODE = "PE2-010"

    def __init__(
        self,
        message: str,
        *,
        code:           str = "PE2-010",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context, correlation_id=correlation_id)
