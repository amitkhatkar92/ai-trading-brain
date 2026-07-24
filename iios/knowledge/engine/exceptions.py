"""
exceptions.py — iios.knowledge.engine
----------------------------------------
Typed exception hierarchy for the Knowledge Engine subsystem.

Error code prefix: KNE (KNowledge Engine)

C14 Enterprise Knowledge Intelligence — Phase 1, Module 2
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class KnowledgeEngineError(IIOSError):
    """Base for all Knowledge Engine errors."""
    error_code = "KNE-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


# ---------------------------------------------------------------------------
# Specific errors
# ---------------------------------------------------------------------------


class KnowledgeEngineNotRunningError(KnowledgeEngineError):
    """Raised when a method requires the engine to be running."""
    error_code = "KNE-001"

    def __init__(self, message: str = "Knowledge Engine is not running") -> None:
        super().__init__(message)


class KnowledgeEngineValidationError(KnowledgeEngineError):
    """Raised when engine-level validation fails."""
    error_code = "KNE-002"


class KnowledgeSessionError(KnowledgeEngineError):
    """Raised when a session management operation fails."""
    error_code = "KNE-003"


class KnowledgeCollectionError(KnowledgeEngineError):
    """Raised when knowledge collection fails."""
    error_code = "KNE-004"

    def __init__(
        self,
        message: str = "",
        source: str = "",
        code: str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.source = source


class KnowledgePipelineError(KnowledgeEngineError):
    """Raised when a pipeline operation fails."""
    error_code = "KNE-005"

    def __init__(
        self,
        message: str = "",
        pipeline_id: str = "",
        code: str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.pipeline_id = pipeline_id


class KnowledgeDispatchError(KnowledgeEngineError):
    """Raised when dispatching to a downstream framework fails."""
    error_code = "KNE-006"


class KnowledgePublicationError(KnowledgeEngineError):
    """Raised when snapshot publication fails."""
    error_code = "KNE-007"


class KnowledgeSchedulerError(KnowledgeEngineError):
    """Raised when a scheduler operation fails."""
    error_code = "KNE-008"


class KnowledgeCapacityError(KnowledgeEngineError):
    """Raised when the engine exceeds its capacity limit."""
    error_code = "KNE-009"

    def __init__(
        self,
        message: str = "",
        limit: int = 0,
        code: str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.limit = limit
