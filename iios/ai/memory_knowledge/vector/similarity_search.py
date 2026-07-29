"""
similarity_search.py -- iios.ai.memory_knowledge.vector
========================================================
:class:`SimilaritySearch` — provider-independent ABC for similarity queries.

Separates the *search algorithm* from the *storage backend*, allowing
algorithms such as ANN or exact k-NN to be swapped independently.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


Vector = List[float]
SearchResult = Tuple[str, float, Dict[str, Any]]  # (id, score, metadata)


class SimilaritySearch(ABC):
    """Abstract similarity search algorithm."""

    @abstractmethod
    def search(
        self,
        query_vector: Vector,
        top_k:        int  = 10,
        min_score:    float = 0.0,
    ) -> List[SearchResult]:
        """
        Return the top-k most similar items.

        :param query_vector: Dense query embedding.
        :param top_k:        Maximum number of results.
        :param min_score:    Minimum similarity threshold [0, 1].
        :returns: List of (id, score, metadata) sorted by score descending.
        """
