"""
exceptions.py — iios.integration.lifecycle
-------------------------------------------
Exception hierarchy for the Integration Lifecycle module.

Error code prefix: ILC

C15 Enterprise Integration & Connectivity — Phase 1, Module 1
"""
from __future__ import annotations

from typing import Optional

from iios.common.errors.exceptions import IIOSError


class IntegrationLifecycleError(IIOSError):
    """ILC-000 — Base exception for all Integration Lifecycle errors."""
    error_code = "ILC-000"

    def __init__(self, message: str, *, code: Optional[str] = None) -> None:
        super().__init__(message, code=code or self.error_code)


class IntegrationSessionNotFoundError(IntegrationLifecycleError):
    """ILC-001 — No integration session found for the given session_id."""
    error_code = "ILC-001"

    def __init__(
        self,
        session_id: str,
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Integration session not found: {session_id!r}",
            code=code,
        )
        self.session_id = session_id


class IntegrationInvalidTransitionError(IntegrationLifecycleError):
    """ILC-002 — Attempted state transition is not permitted by the state machine."""
    error_code = "ILC-002"

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


class IntegrationSessionTerminatedError(IntegrationLifecycleError):
    """ILC-003 — Operation attempted on an archived (terminated) session."""
    error_code = "ILC-003"

    def __init__(
        self,
        session_id: str,
        *,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            f"Session is terminated (archived): {session_id!r}",
            code=code,
        )
        self.session_id = session_id


class IntegrationValidationError(IntegrationLifecycleError):
    """ILC-004 — Lifecycle validation check failed."""
    error_code = "ILC-004"

    def __init__(
        self,
        message: str,
        *,
        failed_checks: Optional[list] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message, code=code)
        self.failed_checks = failed_checks or []


class IntegrationCapacityError(IntegrationLifecycleError):
    """ILC-005 — Registry or history storage capacity exceeded."""
    error_code = "ILC-005"

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        limit: Optional[int] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(
            message or f"Capacity limit reached: {limit}",
            code=code,
        )
        self.limit = limit


class IntegrationHistoryError(IntegrationLifecycleError):
    """ILC-006 — Error accessing or recording lifecycle history."""
    error_code = "ILC-006"
