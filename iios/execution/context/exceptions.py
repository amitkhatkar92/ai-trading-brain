"""iios/execution/context/exceptions.py
==================================================
Exception hierarchy for the IIOS Execution Context package.

All exceptions inherit from IIOSError.

Error Codes
-----------
ECX-000  ExecutionContextError        — base
ECX-001  ContextBuildError            — builder failure
ECX-002  ContextValidationError       — validation failure
ECX-003  ContextNotFoundError         — context_id not in registry
ECX-004  DuplicateContextError        — duplicate context_id
ECX-005  ContextCapacityError         — registry full
ECX-006  ContextRegistryNotRunning    — registry not started
ECX-007  ContextIncompleteError       — required fields missing
ECX-008  ContextInconsistencyError    — snapshot / identifier mismatch
ECX-009  ContextSerializationError    — cannot serialize/deserialize
ECX-010  ContextHistoryError          — history operation failure

C6 Execution Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from iios.common.errors.exceptions import IIOSError


class ExecutionContextError(IIOSError):
    """Base for all Execution Context errors."""
    DEFAULT_CODE = "ECX-000"


class ContextBuildError(ExecutionContextError):
    """Builder failed to assemble the context."""
    DEFAULT_CODE = "ECX-001"


class ContextValidationError(ExecutionContextError):
    """Context validation failed."""
    DEFAULT_CODE = "ECX-002"

    def __init__(
        self,
        message:        str,
        *,
        code:           str = "ECX-002",
        errors:         tuple[str, ...] = (),
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.errors = errors


class ContextNotFoundError(ExecutionContextError):
    """No context registered under the given context_id."""
    DEFAULT_CODE = "ECX-003"

    def __init__(
        self,
        context_id: str,
        *,
        code:           str = "ECX-003",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"ExecutionContext not found: '{context_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.context_id = context_id


class DuplicateContextError(ExecutionContextError):
    """A context with this ID is already registered."""
    DEFAULT_CODE = "ECX-004"

    def __init__(
        self,
        context_id: str,
        *,
        code:           str = "ECX-004",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(
            f"ExecutionContext already registered: '{context_id}'",
            code=code,
            context=context,
            correlation_id=correlation_id,
        )
        self.context_id = context_id


class ContextCapacityError(ExecutionContextError):
    """Registry has reached maximum context capacity."""
    DEFAULT_CODE = "ECX-005"


class ContextRegistryNotRunning(ExecutionContextError):
    """Registry was not started before use."""
    DEFAULT_CODE = "ECX-006"


class ContextIncompleteError(ExecutionContextError):
    """Required fields are missing from the context."""
    DEFAULT_CODE = "ECX-007"

    def __init__(
        self,
        message:       str,
        *,
        missing_fields: tuple[str, ...] = (),
        code:           str = "ECX-007",
        context:        Optional[Dict[str, Any]] = None,
        correlation_id: str = "",
    ) -> None:
        super().__init__(message, code=code, context=context,
                         correlation_id=correlation_id)
        self.missing_fields = missing_fields


class ContextInconsistencyError(ExecutionContextError):
    """Snapshot or identifier mismatch detected."""
    DEFAULT_CODE = "ECX-008"


class ContextSerializationError(ExecutionContextError):
    """Cannot serialize or deserialize the context."""
    DEFAULT_CODE = "ECX-009"


class ContextHistoryError(ExecutionContextError):
    """History operation failed."""
    DEFAULT_CODE = "ECX-010"
