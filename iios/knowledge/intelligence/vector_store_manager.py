"""
vector_store_manager.py — iios.knowledge.intelligence
------------------------------------------------------
Manages the lifecycle of the active VectorIndexEngine and provides
a store-level API to the rest of the framework.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_VECTORS, DEFAULT_TOP_K
from .embedding_engine import EmbeddingVector
from .vector_index_engine import VectorIndexEngine, VectorSearchResult, VectorStoreAdapter

_log = get_logger(__name__)


class VectorStoreManager:
    """
    Thin management wrapper over a VectorIndexEngine.

    Exposes upsert/search/count and allows adapter injection.
    """

    def __init__(
        self,
        adapter:     Optional[VectorStoreAdapter] = None,
        max_vectors: int                          = DEFAULT_MAX_VECTORS,
    ) -> None:
        self._engine = VectorIndexEngine(adapter=adapter, max_vectors=max_vectors)
        self._lock   = threading.Lock()

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index_embedding(
        self,
        embedding: EmbeddingVector,
        metadata:  Dict[str, Any] = None,
    ) -> None:
        with self._lock:
            self._engine.upsert(
                artifact_id = embedding.artifact_id,
                vector      = list(embedding.vector),
                metadata    = metadata or {},
            )

    def index_batch(
        self,
        embeddings: List[EmbeddingVector],
        metadata:   List[Dict[str, Any]] = None,
    ) -> int:
        indexed = 0
        meta_list = metadata or [{}] * len(embeddings)
        for emb, meta in zip(embeddings, meta_list):
            try:
                self.index_embedding(emb, meta)
                indexed += 1
            except Exception as exc:
                _log.debug(f"Skipped indexing {emb.artifact_id!r}: {exc!r}")
        return indexed

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def search(
        self,
        query_embedding: EmbeddingVector,
        top_k:           int = DEFAULT_TOP_K,
    ) -> List[VectorSearchResult]:
        with self._lock:
            return self._engine.search(list(query_embedding.vector), top_k)

    def search_by_vector(
        self,
        query_vector: List[float],
        top_k:        int = DEFAULT_TOP_K,
    ) -> List[VectorSearchResult]:
        with self._lock:
            return self._engine.search(query_vector, top_k)

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def delete(self, artifact_id: str) -> bool:
        with self._lock:
            return self._engine.delete(artifact_id)

    def count(self) -> int:
        return self._engine.count()

    def set_adapter(self, adapter: VectorStoreAdapter) -> None:
        with self._lock:
            self._engine.set_adapter(adapter)
        _log.info("VectorStoreAdapter registered in VectorStoreManager")
