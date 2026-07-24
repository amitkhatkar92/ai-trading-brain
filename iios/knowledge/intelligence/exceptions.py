"""
exceptions.py — iios.knowledge.intelligence
---------------------------------------------
Typed exception hierarchy for the Knowledge Intelligence Framework.

Error code prefix: KIF (Knowledge Intelligence Framework)

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

from iios.common.errors.exceptions import IIOSError


class KnowledgeIntelligenceError(IIOSError):
    """Base for all Knowledge Intelligence Framework errors."""
    error_code = "KIF-000"

    def __init__(self, message: str = "", code: str | None = None) -> None:
        super().__init__(message, code=code or self.error_code)


class IntelligenceNotRunningError(KnowledgeIntelligenceError):
    """Raised when an operation requires the intelligence engine to be running."""
    error_code = "KIF-001"

    def __init__(
        self, message: str = "Knowledge Intelligence Engine is not running",
    ) -> None:
        super().__init__(message)


class IntelligenceValidationError(KnowledgeIntelligenceError):
    """Raised when intelligence-level validation fails."""
    error_code = "KIF-002"


class KnowledgeGraphError(KnowledgeIntelligenceError):
    """Raised when a knowledge graph operation fails."""
    error_code = "KIF-003"

    def __init__(
        self,
        message:  str = "",
        graph_id: str = "",
        code:     str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.graph_id = graph_id


class EntityResolutionError(KnowledgeIntelligenceError):
    """Raised when entity resolution fails."""
    error_code = "KIF-004"

    def __init__(
        self,
        message:   str = "",
        entity_id: str = "",
        code:      str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.entity_id = entity_id


class EmbeddingError(KnowledgeIntelligenceError):
    """Raised when embedding generation fails."""
    error_code = "KIF-005"

    def __init__(
        self,
        message:     str = "",
        artifact_id: str = "",
        code:        str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.artifact_id = artifact_id


class VectorIndexError(KnowledgeIntelligenceError):
    """Raised when vector indexing or retrieval fails."""
    error_code = "KIF-006"

    def __init__(
        self,
        message:  str = "",
        index_id: str = "",
        code:     str | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.index_id = index_id


class RetrievalError(KnowledgeIntelligenceError):
    """Raised when knowledge retrieval fails."""
    error_code = "KIF-007"


class EnrichmentError(KnowledgeIntelligenceError):
    """Raised when knowledge enrichment fails."""
    error_code = "KIF-008"


class IntelligenceCapacityError(KnowledgeIntelligenceError):
    """Raised when an intelligence store capacity is exceeded."""
    error_code = "KIF-009"

    def __init__(
        self,
        message: str = "",
        limit:   int = 0,
        code:    str | None = None,
    ) -> None:
        super().__init__(message or f"Capacity limit reached: {limit}", code=code)
        self.limit = limit
