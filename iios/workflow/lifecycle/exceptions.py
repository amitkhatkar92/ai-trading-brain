"""
exceptions.py — iios.workflow.lifecycle
-----------------------------------------
Exception hierarchy for the Workflow Lifecycle module.

Error code prefix: WLC

C16 Enterprise Workflow & Process Orchestration — Phase 1, Module 1
"""
from __future__ import annotations

from typing import Optional

from iios.common.errors.exceptions import IIOSError


class WorkflowLifecycleError(IIOSError):
    """WLC-000 — Base exception for all Workflow Lifecycle errors."""
    error_code = "WLC-000"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class WorkflowSessionNotFoundError(WorkflowLifecycleError):
    """WLC-001 — No workflow session found for the given session_id."""
    error_code = "WLC-001"

    def __init__(
        self,
        session_id: str,
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Workflow session not found: {session_id!r}",
            code=code,
        )
        self.session_id = session_id


class WorkflowInvalidTransitionError(WorkflowLifecycleError):
    """WLC-002 — Attempted state transition is not permitted by the state machine."""
    error_code = "WLC-002"

    def __init__(
        self,
        from_state: str,
        to_state:   str,
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Invalid transition: {from_state!r} → {to_state!r}",
            code=code,
        )
        self.from_state = from_state
        self.to_state   = to_state


class WorkflowSessionTerminatedError(WorkflowLifecycleError):
    """WLC-003 — Operation attempted on an archived (terminated) session."""
    error_code = "WLC-003"

    def __init__(
        self,
        session_id: str,
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Workflow session is archived (terminated): {session_id!r}",
            code=code,
        )
        self.session_id = session_id


class WorkflowValidationError(WorkflowLifecycleError):
    """WLC-004 — Lifecycle validation check failed."""
    error_code = "WLC-004"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code)


class WorkflowCapacityError(WorkflowLifecycleError):
    """WLC-005 — Registry capacity limit exceeded."""
    error_code = "WLC-005"

    def __init__(
        self,
        limit: int,
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Workflow registry capacity exceeded: limit={limit}",
            code=code,
        )
        self.limit = limit


class WorkflowHistoryError(WorkflowLifecycleError):
    """WLC-006 — History integrity or lookup failure."""
    error_code = "WLC-006"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code)
