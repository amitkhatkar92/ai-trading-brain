"""
vector_store.py -- iios.ai.memory_knowledge.vector
===================================================
:class:`VectorStore` — provider-independent ABC for vector storage.

Concrete implementations integrate FAISS, Chroma, Pinecone, Weaviate,
pgvector etc. without changing the A4 interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


Vector = List[float]


class VectorStore(ABC):
    """
    Abstract vector storage backend.

    Implementors must provide CRUD operations on (id, vector, metadata)
    triples plus nearest-neighbour search.
    """

    @abstractmethod
    def upsert(self, vector_id: str, vector: Vector, metadata: Dict[str, Any]) -> None:
        """Insert or update a vector with associated metadata."""

    @abstractmethod
    def delete(self, vector_id: str) -> bool:
        """Remove a vector by ID; return True if it existed."""

    @abstractmethod
    def get(self, vector_id: str) -> Optional[Tuple[Vector, Dict[str, Any]]]:
        """Return (vector, metadata) or None if absent."""

    @abstractmethod
    def search(
        self, query_vector: Vector, top_k: int = 10
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Return up to ``top_k`` nearest neighbours as
        ``[(vector_id, similarity_score, metadata), ...]`` sorted descending.
        """

    @abstractmethod
    def count(self) -> int:
        """Return total stored vector count."""

    @abstractmethod
    def clear(self) -> None:
        """Delete all vectors."""
