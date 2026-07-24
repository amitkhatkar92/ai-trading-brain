"""
retrieval_engine.py — iios.knowledge.intelligence
--------------------------------------------------
Semantic retrieval over the vector index.

Converts a text query to an embedding, searches the vector store,
and wraps results as KnowledgeRetrievalResult.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import time
from typing import List

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_TOP_K, RetrievalMode
from .embedding_engine import EmbeddingEngine
from .knowledge_intelligence_response import (
    KnowledgeRetrievalItem,
    KnowledgeRetrievalResult,
)
from .vector_store_manager import VectorStoreManager

_log = get_logger(__name__)


class RetrievalEngine:
    """
    Semantic retrieval via embedding + vector index.

    Generates a query embedding, searches the VectorStoreManager,
    and returns a typed KnowledgeRetrievalResult.
    """

    def __init__(
        self,
        embedding_engine: EmbeddingEngine,
        vector_store:     VectorStoreManager,
        top_k:            int = DEFAULT_TOP_K,
    ) -> None:
        self._embedding_engine = embedding_engine
        self._vector_store     = vector_store
        self._top_k            = top_k

    def retrieve(
        self,
        query: str,
        top_k: int = 0,
    ) -> KnowledgeRetrievalResult:
        """Retrieve top-K knowledge artifacts by semantic similarity."""
        k       = top_k or self._top_k
        t_start = time.monotonic()
        try:
            query_emb = self._embedding_engine.generate("query", query)
            results   = self._vector_store.search(query_emb, k)
        except Exception as exc:
            _log.warning(f"Retrieval failed: {exc!r}")
            results = []

        retrieval_ms = (time.monotonic() - t_start) * 1_000
        items = [
            KnowledgeRetrievalItem(
                item_id     = f"ri-{r.artifact_id[:8]}",
                artifact_id = r.artifact_id,
                score       = r.score,
                metadata    = r.metadata,
                rank        = r.rank,
            )
            for r in results
        ]
        return KnowledgeRetrievalResult.create(
            query        = query,
            items        = items,
            mode         = RetrievalMode.SEMANTIC,
            retrieval_ms = retrieval_ms,
        )
