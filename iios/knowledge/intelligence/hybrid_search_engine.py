"""
hybrid_search_engine.py — iios.knowledge.intelligence
------------------------------------------------------
Hybrid search: combines semantic (vector) and keyword (token overlap) scores.

Final score = alpha * semantic_score + (1 - alpha) * keyword_score

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, List

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_TOP_K, RetrievalMode
from .embedding_engine import EmbeddingEngine
from .knowledge_intelligence_response import (
    KnowledgeRetrievalItem,
    KnowledgeRetrievalResult,
)
from .vector_store_manager import VectorStoreManager

_log = get_logger(__name__)


def _keyword_score(query: str, metadata: Dict[str, Any]) -> float:
    """
    Rough token-overlap score between query and artifact metadata text.
    """
    q_tokens = set(re.split(r"\W+", query.lower())) - {""}
    if not q_tokens:
        return 0.0
    m_text = " ".join(str(v) for v in metadata.values() if v)
    m_tokens = set(re.split(r"\W+", m_text.lower())) - {""}
    if not m_tokens:
        return 0.0
    overlap = len(q_tokens & m_tokens)
    return overlap / len(q_tokens | m_tokens)   # Jaccard


class HybridSearchEngine:
    """
    Combined semantic + keyword search.

    Weights:
      alpha * semantic_score + (1 - alpha) * keyword_score
    """

    def __init__(
        self,
        embedding_engine: EmbeddingEngine,
        vector_store:     VectorStoreManager,
        alpha:            float = 0.7,
        top_k:            int   = DEFAULT_TOP_K,
    ) -> None:
        self._embedding_engine = embedding_engine
        self._vector_store     = vector_store
        self._alpha            = max(0.0, min(1.0, alpha))
        self._top_k            = top_k

    def search(
        self,
        query: str,
        top_k: int = 0,
    ) -> KnowledgeRetrievalResult:
        """Perform hybrid search and return top-K results."""
        k       = top_k or self._top_k
        t_start = time.monotonic()

        # Fetch more candidates to re-score; cap at 5×k
        fetch_k = min(k * 5, 500)
        try:
            query_emb   = self._embedding_engine.generate("query", query)
            sem_results = self._vector_store.search(query_emb, fetch_k)
        except Exception as exc:
            _log.warning(f"Hybrid search embedding failed: {exc!r}")
            sem_results = []

        scored: List[tuple] = []
        for r in sem_results:
            kw_score  = _keyword_score(query, r.metadata)
            combined  = self._alpha * r.score + (1.0 - self._alpha) * kw_score
            scored.append((r.artifact_id, combined, r.metadata))

        scored.sort(key=lambda x: x[1], reverse=True)
        top     = scored[:k]
        retrieval_ms = (time.monotonic() - t_start) * 1_000

        items = [
            KnowledgeRetrievalItem(
                item_id     = f"hs-{aid[:8]}",
                artifact_id = aid,
                score       = round(score, 6),
                metadata    = meta,
                rank        = rank + 1,
            )
            for rank, (aid, score, meta) in enumerate(top)
        ]
        return KnowledgeRetrievalResult.create(
            query        = query,
            items        = items,
            mode         = RetrievalMode.HYBRID,
            retrieval_ms = retrieval_ms,
        )
