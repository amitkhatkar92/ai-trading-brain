"""
iios/knowledge/versioning/version_exceptions.py
================================================
Exception hierarchy for the Knowledge Versioning & Evolution Engine.

All exceptions derive from VersionError which itself extends the existing
KnowledgeVersionError so callers that catch the base exception continue to
work after this engine is introduced.
"""

from __future__ import annotations

from ..knowledge_exceptions import KnowledgeVersionError

__all__ = [
    "VersionError",
    "VersionNotFoundError",
    "VersionAlreadyExistsError",
    "VersionConflictError",
    "VersionRollbackError",
    "VersionValidationError",
    "BranchError",
    "BranchNotFoundError",
    "BranchAlreadyExistsError",
    "BranchMergeError",
    "BranchConflictError",
    "DiffError",
    "ProvenanceError",
    "LineageError",
    "LineageCycleError",
    "AuditError",
    "VersionEngineError",
]


class VersionError(KnowledgeVersionError):
    """Base for all versioning engine errors."""

    def __init__(self, message: str, code: str = "VE-000") -> None:
        super().__init__(message, code=code)


class VersionNotFoundError(VersionError):
    """Requested version does not exist."""

    def __init__(self, message: str, code: str = "VE-001") -> None:
        super().__init__(message, code=code)


class VersionAlreadyExistsError(VersionError):
    """Version with this ID already exists."""

    def __init__(self, message: str, code: str = "VE-002") -> None:
        super().__init__(message, code=code)


class VersionConflictError(VersionError):
    """Concurrent modification conflict on a version."""

    def __init__(self, message: str, code: str = "VE-003") -> None:
        super().__init__(message, code=code)


class VersionRollbackError(VersionError):
    """Rollback to target version failed."""

    def __init__(self, message: str, code: str = "VE-004") -> None:
        super().__init__(message, code=code)


class VersionValidationError(VersionError):
    """Version data failed validation."""

    def __init__(self, message: str, violations: list[str] | None = None,
                 code: str = "VE-005") -> None:
        super().__init__(message, code=code)
        self.violations: list[str] = violations or []


class BranchError(VersionError):
    """Base for branch-related errors."""

    def __init__(self, message: str, code: str = "VE-100") -> None:
        super().__init__(message, code=code)


class BranchNotFoundError(BranchError):
    """Requested branch does not exist."""

    def __init__(self, message: str, code: str = "VE-101") -> None:
        super().__init__(message, code=code)


class BranchAlreadyExistsError(BranchError):
    """Branch with this name already exists for the knowledge item."""

    def __init__(self, message: str, code: str = "VE-102") -> None:
        super().__init__(message, code=code)


class BranchMergeError(BranchError):
    """Merge operation failed."""

    def __init__(self, message: str, code: str = "VE-103") -> None:
        super().__init__(message, code=code)


class BranchConflictError(BranchMergeError):
    """Merge strategy is MANUAL and conflicts were detected."""

    def __init__(self, message: str, conflict_fields: list[str] | None = None,
                 code: str = "VE-104") -> None:
        super().__init__(message, code=code)
        self.conflict_fields: list[str] = conflict_fields or []


class DiffError(VersionError):
    """Diff computation failed."""

    def __init__(self, message: str, code: str = "VE-200") -> None:
        super().__init__(message, code=code)


class ProvenanceError(VersionError):
    """Provenance tracking error."""

    def __init__(self, message: str, code: str = "VE-300") -> None:
        super().__init__(message, code=code)


class LineageError(VersionError):
    """Lineage graph error."""

    def __init__(self, message: str, code: str = "VE-400") -> None:
        super().__init__(message, code=code)


class LineageCycleError(LineageError):
    """Adding this lineage edge would create a cycle."""

    def __init__(self, message: str, code: str = "VE-401") -> None:
        super().__init__(message, code=code)


class AuditError(VersionError):
    """Audit log error."""

    def __init__(self, message: str, code: str = "VE-500") -> None:
        super().__init__(message, code=code)


class VersionEngineError(VersionError):
    """High-level versioning engine error."""

    def __init__(self, message: str, code: str = "VE-900") -> None:
        super().__init__(message, code=code)
