"""
vector_index.py -- iios.ai.memory_knowledge.vector
===================================================
:class:`VectorIndex` — ABC that combines a :class:`VectorStore` with a
:class:`SimilaritySearch` algorithm into a single indexable unit.

Implementations may wrap FAISS IndexFlatL2, Annoy, HNSWlib, etc.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


Vector = List[float]


class VectorIndex(ABC):
    """
    Abstract composite: storage + search algorithm.

    Higher-level components (e.g. :class:`SemanticRankingStrategy`) depend
    only on this ABC — the backend provider is injected at wire-up time.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable index name."""

    @abstractmethod
    def add(self, item_id: str, vector: Vector, metadata: Dict[str, Any]) -> None:
        """Index an item."""

    @abstractmethod
    def remove(self, item_id: str) -> bool:
        """Remove an item; return True if found."""

    @abstractmethod
    def query(
        self,
        vector:    Vector,
        top_k:     int    = 10,
        min_score: float  = 0.0,
    ) -> List[Any]:
        """Return top-k results as implementation-defined objects."""

    @abstractmethod
    def size(self) -> int:
        """Return current index size."""

    @abstractmethod
    def rebuild(self) -> None:
        """Trigger an index rebuild / optimisation if applicable."""
