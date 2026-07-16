"""iios/execution/engine/exceptions.py
==================================================
Exception hierarchy for the IIOS Execution Engine.

All exceptions inherit from IIOSError.

Error Codes
-----------
EX-000  ExecutionEngineError         — base
EX-001  ExecutionRequestError        — malformed request
EX-002  ExecutionValidationError     — validation failure
EX-003  ExecutionPreparationError    — context preparation failure
EX-004  ExecutionRegistryError       — registry operation failure
EX-005  ExecutionNotFoundError       — execution not in registry
EX-006  DuplicateExecutionError      — duplicate execution_id
EX-007  ExecutionCapacityError       — max_executions exceeded
EX-008  ExecutionEngineNotRunningError — engine not started
EX-009  ExecutionStateError          — invalid state transition
EX-010  ExecutionCancelledError      — execution was cancelled

C6 Execution Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class ExecutionEngineError(IIOSError):
    """Base for all Execution Engine errors."""
    DEFAULT_CODE = "EX-000"


class ExecutionRequestError(ExecutionEngineError):
    """Malformed or incomplete execution request."""
    DEFAULT_CODE = "EX-001"


class ExecutionValidationError(ExecutionEngineError):
    """One or more validation checks failed."""
    DEFAULT_CODE = "EX-002"

    def __init__(
        self,
        message:        str,
        *,
        code:           str             = "EX-002",
        errors:         tuple[str, ...]  = (),
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str             = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.errors = errors


class ExecutionPreparationError(ExecutionEngineError):
    """Context preparation failed."""
    DEFAULT_CODE = "EX-003"


class ExecutionRegistryError(ExecutionEngineError):
    """Generic registry operation failure."""
    DEFAULT_CODE = "EX-004"


class ExecutionNotFoundError(ExecutionEngineError):
    """Requested execution_id is not in the registry."""
    DEFAULT_CODE = "EX-005"

    def __init__(
        self,
        execution_id:   str,
        *,
        code:           str             = "EX-005",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str             = "",
    ) -> None:
        super().__init__(
            f"Execution not found: {execution_id!r}",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.execution_id = execution_id


class DuplicateExecutionError(ExecutionEngineError):
    """An execution with this ID is already registered."""
    DEFAULT_CODE = "EX-006"

    def __init__(
        self,
        execution_id:   str,
        *,
        code:           str             = "EX-006",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str             = "",
    ) -> None:
        super().__init__(
            f"Duplicate execution_id: {execution_id!r}",
            code=code, context=context, correlation_id=correlation_id,
        )
        self.execution_id = execution_id


class ExecutionCapacityError(ExecutionEngineError):
    """Registry has reached its max_executions limit."""
    DEFAULT_CODE = "EX-007"


class ExecutionEngineNotRunningError(ExecutionEngineError):
    """Operation attempted before engine.start() was called."""
    DEFAULT_CODE = "EX-008"


class ExecutionStateError(ExecutionEngineError):
    """Requested state transition is not valid."""
    DEFAULT_CODE = "EX-009"

    def __init__(
        self,
        from_state:     str,
        to_state:       str,
        execution_id:   str             = "",
        *,
        code:           str             = "EX-009",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str             = "",
    ) -> None:
        super().__init__(
            f"Invalid engine state transition {from_state!r} → {to_state!r}"
            + (f" (execution: {execution_id!r})" if execution_id else ""),
            code=code, context=context, correlation_id=correlation_id,
        )
        self.from_state   = from_state
        self.to_state     = to_state
        self.execution_id = execution_id


class ExecutionCancelledError(ExecutionEngineError):
    """The execution was cancelled before completion."""
    DEFAULT_CODE = "EX-010"
