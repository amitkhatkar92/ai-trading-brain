"""iios/execution/execution_exceptions.py"""
from __future__ import annotations


class ExecutionError(Exception):
    """EX-000  Base exception for the Execution Engine."""

    code: str = "EX-000"

    def __init__(self, message: str = "", *, code: str = "") -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}" if self.message else f"[{self.code}]"


# ── Request errors ─────────────────────────────────────────────────────────────

class ExecutionRequestError(ExecutionError):
    """EX-010  Base for execution-request errors."""
    code = "EX-010"


class ExecutionNotFoundError(ExecutionRequestError):
    """EX-011  Execution not found in registry/store."""
    code = "EX-011"

    def __init__(self, message: str = "", *, execution_id: str = "") -> None:
        super().__init__(message)
        self.execution_id = execution_id


class ExecutionAlreadyExistsError(ExecutionRequestError):
    """EX-012  Duplicate execution ID."""
    code = "EX-012"

    def __init__(self, message: str = "", *, execution_id: str = "") -> None:
        super().__init__(message)
        self.execution_id = execution_id


class ExecutionInvalidError(ExecutionRequestError):
    """EX-013  Request fields fail validation."""
    code = "EX-013"

    def __init__(self, message: str = "", *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors or []


class ExecutionStateError(ExecutionRequestError):
    """EX-014  Invalid state transition attempted."""
    code = "EX-014"

    def __init__(self, message: str = "", *, from_status: str = "", to_status: str = "") -> None:
        super().__init__(message)
        self.from_status = from_status
        self.to_status   = to_status


class ExecutionExpiredError(ExecutionRequestError):
    """EX-015  Execution request has expired."""
    code = "EX-015"

    def __init__(self, message: str = "", *, execution_id: str = "") -> None:
        super().__init__(message)
        self.execution_id = execution_id


# ── Workflow errors ────────────────────────────────────────────────────────────

class WorkflowError(ExecutionError):
    """EX-020  Base for workflow errors."""
    code = "EX-020"


class WorkflowValidationError(WorkflowError):
    """EX-021  Workflow validation failed."""
    code = "EX-021"

    def __init__(self, message: str = "", *, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors: list[str] = errors or []


class WorkflowExecutionError(WorkflowError):
    """EX-022  Error during workflow step execution."""
    code = "EX-022"

    def __init__(self, message: str = "", *, step_name: str = "") -> None:
        super().__init__(message)
        self.step_name = step_name


class WorkflowCancelledError(WorkflowError):
    """EX-023  Workflow was cancelled before completion."""
    code = "EX-023"

    def __init__(self, message: str = "", *, execution_id: str = "") -> None:
        super().__init__(message)
        self.execution_id = execution_id


# ── Session errors ─────────────────────────────────────────────────────────────

class SessionError(ExecutionError):
    """EX-030  Base for session errors."""
    code = "EX-030"


class SessionNotFoundError(SessionError):
    """EX-031  Session not found."""
    code = "EX-031"

    def __init__(self, message: str = "", *, session_id: str = "") -> None:
        super().__init__(message)
        self.session_id = session_id


class SessionAlreadyExistsError(SessionError):
    """EX-032  Duplicate session ID."""
    code = "EX-032"

    def __init__(self, message: str = "", *, session_id: str = "") -> None:
        super().__init__(message)
        self.session_id = session_id


class SessionExpiredError(SessionError):
    """EX-033  Session has exceeded its TTL."""
    code = "EX-033"

    def __init__(self, message: str = "", *, session_id: str = "") -> None:
        super().__init__(message)
        self.session_id = session_id


# ── Engine lifecycle errors ────────────────────────────────────────────────────

class EngineError(ExecutionError):
    """EX-040  Base for engine lifecycle errors."""
    code = "EX-040"


class EngineNotInitializedError(EngineError):
    """EX-041  Operation attempted before engine.initialize()."""
    code = "EX-041"


class EngineAlreadyRunningError(EngineError):
    """EX-042  initialize() called on an already-running engine."""
    code = "EX-042"


class EngineShutdownError(EngineError):
    """EX-043  Operation attempted on a shut-down engine."""
    code = "EX-043"


# ── Registry errors ────────────────────────────────────────────────────────────

class RegistryError(ExecutionError):
    """EX-050  Base for registry errors."""
    code = "EX-050"


class RegistryOverflowError(RegistryError):
    """EX-051  Registry has reached its capacity limit."""
    code = "EX-051"

    def __init__(self, message: str = "", *, capacity: int = 0, current: int = 0) -> None:
        super().__init__(message)
        self.capacity = capacity
        self.current  = current


class RegistryItemNotFoundError(RegistryError):
    """EX-052  Item not found in registry."""
    code = "EX-052"

    def __init__(self, message: str = "", *, item_id: str = "") -> None:
        super().__init__(message)
        self.item_id = item_id


class RegistryItemAlreadyExistsError(RegistryError):
    """EX-053  Item with this ID already exists in registry."""
    code = "EX-053"

    def __init__(self, message: str = "", *, item_id: str = "") -> None:
        super().__init__(message)
        self.item_id = item_id
