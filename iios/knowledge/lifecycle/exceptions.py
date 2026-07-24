"""
exceptions.py — iios.knowledge.lifecycle
------------------------------------------
Typed exception hierarchy for the Knowledge Lifecycle subsystem.

Error code prefix: KNL (KNowledge Lifecycle)

C14 Enterprise Knowledge Intelligence — Phase 1, Module 1
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class KnowledgeLifecycleError(IIOSError):
    """Base for all Knowledge Lifecycle errors."""
    error_code = "KNL-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


# ---------------------------------------------------------------------------
# Specific errors
# ---------------------------------------------------------------------------


class KnowledgeSessionNotFoundError(KnowledgeLifecycleError):
    """Raised when the requested knowledge session cannot be found."""
    error_code = "KNL-001"

    def __init__(
        self,
        message: str = "",
        session_id: str = "",
        code: str | None = None,
    ) -> None:
        super().__init__(message or f"Knowledge session not found: {session_id!r}", code=code)
        self.session_id = session_id


class KnowledgeInvalidTransitionError(KnowledgeLifecycleError):
    """Raised when a requested state transition is not permitted."""
    error_code = "KNL-002"

    def __init__(
        self,
        message: str = "",
        from_state: str = "",
        to_state: str = "",
        code: str | None = None,
    ) -> None:
        super().__init__(
            message or f"Invalid transition {from_state!r} → {to_state!r}",
            code=code,
        )
        self.from_state = from_state
        self.to_state   = to_state


class KnowledgeSessionTerminatedError(KnowledgeLifecycleError):
    """Raised when an operation is attempted on a terminal session."""
    error_code = "KNL-003"


class KnowledgeValidationError(KnowledgeLifecycleError):
    """Raised when lifecycle validation fails."""
    error_code = "KNL-004"


class KnowledgeRegistryError(KnowledgeLifecycleError):
    """Raised when a registry operation fails."""
    error_code = "KNL-005"


class KnowledgeCapacityError(KnowledgeLifecycleError):
    """Raised when the session registry exceeds its capacity limit."""
    error_code = "KNL-006"

    def __init__(
        self,
        message: str = "",
        limit: int = 0,
        code: str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.limit = limit


class KnowledgeLifecycleNotRunningError(KnowledgeLifecycleError):
    """Raised when a method requires the lifecycle engine to be running."""
    error_code = "KNL-007"

    def __init__(self, message: str = "Knowledge Lifecycle is not running") -> None:
        super().__init__(message)


class KnowledgeHistoryError(KnowledgeLifecycleError):
    """Raised when a history operation fails."""
    error_code = "KNL-008"
