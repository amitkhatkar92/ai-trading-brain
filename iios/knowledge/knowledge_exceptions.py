"""
iios/knowledge/knowledge_exceptions.py
=======================================
Exception hierarchy for the IIOS Knowledge Engine.
All exceptions carry a human-readable message, an error code, and
optional structured context.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    # Base
    "KnowledgeError",
    # Identity
    "KnowledgeNotFoundError",
    "KnowledgeAlreadyExistsError",
    "KnowledgeIdentityError",
    # Validation
    "KnowledgeValidationError",
    "KnowledgeSchemaError",
    "KnowledgeConstraintError",
    "KnowledgeConsistencyError",
    "KnowledgeIntegrityError",
    # Versioning
    "KnowledgeVersionError",
    "KnowledgeVersionNotFoundError",
    "KnowledgeRollbackError",
    # Storage
    "KnowledgeStorageError",
    "KnowledgeSerializationError",
    # Query / Search
    "KnowledgeQueryError",
    "KnowledgeSearchError",
    # Graph
    "KnowledgeGraphError",
    "KnowledgeRelationshipError",
    "KnowledgeCycleError",
    # Engine
    "KnowledgeEngineError",
    "KnowledgeEngineNotInitializedError",
    "KnowledgeRegistryError",
    # Security
    "KnowledgeAccessDeniedError",
    # State
    "KnowledgeStateError",
    "KnowledgeArchivedError",
    "KnowledgeDeprecatedError",
]


class KnowledgeError(Exception):
    """Base exception for all IIOS Knowledge Engine errors."""

    def __init__(
        self,
        message: str = "",
        code: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.context: dict[str, Any] = context or {}

    def __str__(self) -> str:
        base = self.message or repr(self)
        return f"[{self.code}] {base}" if self.code else base


# ── Identity ──────────────────────────────────────────────────────────────────

class KnowledgeNotFoundError(KnowledgeError):
    """Requested knowledge item does not exist."""


class KnowledgeAlreadyExistsError(KnowledgeError):
    """A knowledge item with the same ID already exists."""


class KnowledgeIdentityError(KnowledgeError):
    """Identity (ID, namespace, slug) is invalid or malformed."""


# ── Validation ────────────────────────────────────────────────────────────────

class KnowledgeValidationError(KnowledgeError):
    """General validation failure."""
    def __init__(self, message: str = "", code: str = "", context: dict[str, Any] | None = None,
                 violations: list[str] | None = None) -> None:
        super().__init__(message, code, context)
        self.violations: list[str] = violations or []


class KnowledgeSchemaError(KnowledgeValidationError):
    """Knowledge item does not match expected schema."""


class KnowledgeConstraintError(KnowledgeValidationError):
    """A hard constraint was violated."""


class KnowledgeConsistencyError(KnowledgeValidationError):
    """Knowledge item is internally inconsistent or conflicts with existing items."""


class KnowledgeIntegrityError(KnowledgeValidationError):
    """Structural integrity check failed (e.g. tamper detection)."""


# ── Versioning ────────────────────────────────────────────────────────────────

class KnowledgeVersionError(KnowledgeError):
    """General versioning error."""


class KnowledgeVersionNotFoundError(KnowledgeVersionError):
    """Requested version does not exist."""


class KnowledgeRollbackError(KnowledgeVersionError):
    """Rollback operation failed."""


# ── Storage ───────────────────────────────────────────────────────────────────

class KnowledgeStorageError(KnowledgeError):
    """Persistence / storage operation failed."""


class KnowledgeSerializationError(KnowledgeError):
    """Serialization or deserialization failed."""


# ── Query / Search ────────────────────────────────────────────────────────────

class KnowledgeQueryError(KnowledgeError):
    """Query construction or execution failed."""


class KnowledgeSearchError(KnowledgeError):
    """Search operation failed."""


# ── Graph ─────────────────────────────────────────────────────────────────────

class KnowledgeGraphError(KnowledgeError):
    """Knowledge graph operation failed."""


class KnowledgeRelationshipError(KnowledgeGraphError):
    """Relationship operation failed."""


class KnowledgeCycleError(KnowledgeGraphError):
    """Cycle detected in the knowledge graph."""


# ── Engine ────────────────────────────────────────────────────────────────────

class KnowledgeEngineError(KnowledgeError):
    """Engine-level failure."""


class KnowledgeEngineNotInitializedError(KnowledgeEngineError):
    """Operation attempted before engine was initialized."""


class KnowledgeRegistryError(KnowledgeError):
    """Knowledge registry operation failed."""


# ── Security ──────────────────────────────────────────────────────────────────

class KnowledgeAccessDeniedError(KnowledgeError):
    """Principal does not have permission to perform this operation."""


# ── State ─────────────────────────────────────────────────────────────────────

class KnowledgeStateError(KnowledgeError):
    """Operation is not valid for the current state of the knowledge item."""


class KnowledgeArchivedError(KnowledgeStateError):
    """Item is archived and cannot be modified."""


class KnowledgeDeprecatedError(KnowledgeStateError):
    """Item is deprecated."""
