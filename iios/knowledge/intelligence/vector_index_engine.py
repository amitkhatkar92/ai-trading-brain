"""
vector_index_engine.py — iios.knowledge.intelligence
------------------------------------------------------
VectorSearchResult, VectorIndex, and VectorIndexEngine.

The VectorIndexEngine is adapter-agnostic:
  - In stub mode:  in-memory linear cosine search (no external DB)
  - With adapter:  delegates to an injected VectorStoreAdapter

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_VECTORS, DEFAULT_TOP_K

_log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Domain value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VectorSearchResult:
    """A single result from a vector similarity search."""
    artifact_id: str
    score:       float          # similarity score [0.0 – 1.0]
    metadata:    Dict[str, Any]
    rank:        int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "score":       self.score,
            "metadata":    self.metadata,
            "rank":        self.rank,
        }


# ---------------------------------------------------------------------------
# Pluggable adapter Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class VectorStoreAdapter(Protocol):
    """
    Protocol for pluggable vector database backends
    (Pinecone, Weaviate, Qdrant, pgvector, Chroma, etc.).
    """
    def upsert(
        self,
        artifact_id: str,
        vector:      List[float],
        metadata:    Dict[str, Any],
    ) -> None: ...

    def search(
        self,
        query_vector: List[float],
        top_k:        int,
    ) -> List[VectorSearchResult]: ...

    def delete(self, artifact_id: str) -> bool: ...
    def count(self) -> int: ...


# ---------------------------------------------------------------------------
# In-memory vector index (linear cosine similarity)
# ---------------------------------------------------------------------------


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


class VectorIndex:
    """
    Thread-safe in-memory vector index with linear cosine similarity search.

    Used in stub mode when no VectorStoreAdapter is injected.
    """

    def __init__(self, max_vectors: int = DEFAULT_MAX_VECTORS) -> None:
        self._max_vectors = max_vectors
        self._store:      Dict[str, tuple] = {}   # artifact_id → (vector, metadata)
        self._lock        = threading.Lock()

    def upsert(
        self,
        artifact_id: str,
        vector:      List[float],
        metadata:    Dict[str, Any],
    ) -> None:
        with self._lock:
            if len(self._store) >= self._max_vectors and artifact_id not in self._store:
                from .exceptions import IntelligenceCapacityError
                raise IntelligenceCapacityError(limit=self._max_vectors)
            self._store[artifact_id] = (list(vector), dict(metadata))

    def search(
        self,
        query_vector: List[float],
        top_k:        int = DEFAULT_TOP_K,
    ) -> List[VectorSearchResult]:
        with self._lock:
            items = list(self._store.items())

        scored = [
            (aid, _cosine_similarity(query_vector, v), meta)
            for aid, (v, meta) in items
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            VectorSearchResult(
                artifact_id = aid,
                score       = max(0.0, min(1.0, score)),
                metadata    = meta,
                rank        = i + 1,
            )
            for i, (aid, score, meta) in enumerate(scored[:top_k])
        ]

    def delete(self, artifact_id: str) -> bool:
        with self._lock:
            if artifact_id in self._store:
                del self._store[artifact_id]
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# ---------------------------------------------------------------------------
# Vector Index Engine
# ---------------------------------------------------------------------------


class VectorIndexEngine:
    """
    Orchestrates vector upsert and search operations.

    In stub mode:   uses VectorIndex (in-memory linear search).
    With adapter:   delegates to an injected VectorStoreAdapter.
    """

    def __init__(
        self,
        adapter:     Optional[VectorStoreAdapter] = None,
        max_vectors: int                          = DEFAULT_MAX_VECTORS,
    ) -> None:
        self._adapter     = adapter
        self._index       = VectorIndex(max_vectors=max_vectors) if not adapter else None

    @property
    def has_adapter(self) -> bool:
        return self._adapter is not None

    def upsert(
        self,
        artifact_id: str,
        vector:      List[float],
        metadata:    Dict[str, Any] = None,
    ) -> None:
        meta = dict(metadata or {})
        if self._adapter:
            self._adapter.upsert(artifact_id, vector, meta)
        else:
            self._index.upsert(artifact_id, vector, meta)
        _log.debug(f"Vector upserted: artifact_id={artifact_id!r}")

    def search(
        self,
        query_vector: List[float],
        top_k:        int = DEFAULT_TOP_K,
    ) -> List[VectorSearchResult]:
        if self._adapter:
            return self._adapter.search(query_vector, top_k)
        return self._index.search(query_vector, top_k)

    def delete(self, artifact_id: str) -> bool:
        if self._adapter:
            return self._adapter.delete(artifact_id)
        return self._index.delete(artifact_id)

    def count(self) -> int:
        if self._adapter:
            return self._adapter.count()
        return self._index.count()

    def set_adapter(self, adapter: VectorStoreAdapter) -> None:
        """Swap the vector store adapter at runtime."""
        self._adapter = adapter
        self._index   = None
        _log.info("Vector store adapter registered")
