"""
embedding_registry.py — iios.knowledge.intelligence
----------------------------------------------------
Thread-safe registry of EmbeddingVector objects keyed by artifact_id.

C14 Enterprise Knowledge Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_MAX_EMBEDDINGS
from .embedding_engine import EmbeddingVector

_log = get_logger(__name__)


class EmbeddingRegistry:
    """Thread-safe store for EmbeddingVector objects."""

    def __init__(self, max_embeddings: int = DEFAULT_MAX_EMBEDDINGS) -> None:
        self._max_embeddings = max_embeddings
        self._store: Dict[str, EmbeddingVector] = {}
        self._lock  = threading.Lock()

    def store(self, embedding: EmbeddingVector) -> None:
        with self._lock:
            if (
                len(self._store) >= self._max_embeddings
                and embedding.artifact_id not in self._store
            ):
                from .exceptions import IntelligenceCapacityError
                raise IntelligenceCapacityError(limit=self._max_embeddings)
            self._store[embedding.artifact_id] = embedding

    def get(self, artifact_id: str) -> Optional[EmbeddingVector]:
        with self._lock:
            return self._store.get(artifact_id)

    def has(self, artifact_id: str) -> bool:
        with self._lock:
            return artifact_id in self._store

    def remove(self, artifact_id: str) -> bool:
        with self._lock:
            if artifact_id in self._store:
                del self._store[artifact_id]
                return True
            return False

    def all_artifact_ids(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
