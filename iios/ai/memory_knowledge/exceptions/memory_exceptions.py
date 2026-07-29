"""
memory_exceptions.py -- iios.ai.memory_knowledge.exceptions
============================================================
A4 exception hierarchy.  All exceptions extend :class:`AIException` from A1.

Error code range: AI-900 – AI-950
"""
from __future__ import annotations

from iios.ai.foundation.exceptions import AIException


# ── Memory exceptions  ────────────────────────────────────────────────────────

class AIMemoryException(AIException):
    """Base for all A4 memory exceptions (AI-900)."""
    def __init__(self, message: str = "Memory error", code: str = "AI-900", **kw):
        super().__init__(message, code=code, **kw)


class AIMemoryNotFoundError(AIMemoryException):
    """Requested memory entry does not exist (AI-901)."""
    def __init__(self, entry_id: str = "", **kw):
        super().__init__(
            f"Memory entry not found: {entry_id!r}" if entry_id else "Memory entry not found",
            code="AI-901", **kw,
        )


class AIMemoryAlreadyExistsError(AIMemoryException):
    """Memory entry with that ID already exists (AI-902)."""
    def __init__(self, entry_id: str = "", **kw):
        super().__init__(
            f"Memory entry already exists: {entry_id!r}" if entry_id else "Memory entry already exists",
            code="AI-902", **kw,
        )


class AIMemoryExpiredError(AIMemoryException):
    """Memory entry has expired (AI-903)."""
    def __init__(self, entry_id: str = "", **kw):
        super().__init__(
            f"Memory entry has expired: {entry_id!r}" if entry_id else "Memory entry has expired",
            code="AI-903", **kw,
        )


class AIMemoryStorageError(AIMemoryException):
    """Low-level storage operation failed (AI-904)."""
    def __init__(self, message: str = "Memory storage error", **kw):
        super().__init__(message, code="AI-904", **kw)


class AIMemoryCapacityError(AIMemoryException):
    """Memory store has reached capacity (AI-905)."""
    def __init__(self, message: str = "Memory store capacity exceeded", **kw):
        super().__init__(message, code="AI-905", **kw)


# ── Knowledge exceptions  ─────────────────────────────────────────────────────

class AIKnowledgeException(AIException):
    """Base for all A4 knowledge exceptions (AI-910)."""
    def __init__(self, message: str = "Knowledge error", code: str = "AI-910", **kw):
        super().__init__(message, code=code, **kw)


class AIKnowledgeNotFoundError(AIKnowledgeException):
    """Requested knowledge item does not exist (AI-911)."""
    def __init__(self, item_id: str = "", **kw):
        super().__init__(
            f"Knowledge item not found: {item_id!r}" if item_id else "Knowledge item not found",
            code="AI-911", **kw,
        )


class AIKnowledgeAlreadyExistsError(AIKnowledgeException):
    """Knowledge item with that ID already exists (AI-912)."""
    def __init__(self, item_id: str = "", **kw):
        super().__init__(
            f"Knowledge item already exists: {item_id!r}" if item_id else "Knowledge item already exists",
            code="AI-912", **kw,
        )


class AIKnowledgeValidationError(AIKnowledgeException):
    """Knowledge item failed validation (AI-913)."""
    def __init__(self, message: str = "Knowledge validation failed", **kw):
        super().__init__(message, code="AI-913", **kw)


# ── Retrieval exceptions  ─────────────────────────────────────────────────────

class AIRetrievalException(AIException):
    """Base for all A4 retrieval exceptions (AI-920)."""
    def __init__(self, message: str = "Retrieval error", code: str = "AI-920", **kw):
        super().__init__(message, code=code, **kw)


class AIRetrievalFailedError(AIRetrievalException):
    """Retrieval operation failed (AI-921)."""
    def __init__(self, message: str = "Retrieval failed", **kw):
        super().__init__(message, code="AI-921", **kw)


class AINoResultsError(AIRetrievalException):
    """No results found for the retrieval request (AI-922)."""
    def __init__(self, message: str = "No results found", **kw):
        super().__init__(message, code="AI-922", **kw)


# ── Vector exceptions  ────────────────────────────────────────────────────────

class AIVectorStoreException(AIException):
    """Base for all A4 vector store exceptions (AI-930)."""
    def __init__(self, message: str = "Vector store error", code: str = "AI-930", **kw):
        super().__init__(message, code=code, **kw)


class AIVectorStoreNotReadyError(AIVectorStoreException):
    """Vector store is not ready or unavailable (AI-931)."""
    def __init__(self, message: str = "Vector store not ready", **kw):
        super().__init__(message, code="AI-931", **kw)


class AIEmbeddingServiceException(AIException):
    """Embedding service error (AI-940)."""
    def __init__(self, message: str = "Embedding service error", code: str = "AI-940", **kw):
        super().__init__(message, code=code, **kw)


# ── Policy exceptions  ────────────────────────────────────────────────────────

class AIMemoryPolicyViolationError(AIException):
    """Memory or knowledge policy was violated (AI-950)."""
    def __init__(self, message: str = "Memory policy violation", **kw):
        super().__init__(message, code="AI-950", **kw)
