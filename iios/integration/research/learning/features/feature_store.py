"""features/feature_store.py — In-memory feature store for pre-computed feature vectors."""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

from iios.integration.research.learning.learning_exceptions import FeatureNotFoundError


class FeatureStore:
    """
    In-memory store of pre-computed feature vectors keyed by entity ID.

    Enables offline feature serving: features are computed once, stored here,
    and fetched during training / inference without recomputation.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._ttl:   dict[str, float]          = {}
        self._lock   = threading.RLock()

    def put(self, entity_id: str, features: dict[str, Any], *, ttl_sec: Optional[float] = None) -> None:
        with self._lock:
            self._store[entity_id] = dict(features)
            if ttl_sec is not None:
                self._ttl[entity_id] = time.time() + ttl_sec
            else:
                self._ttl.pop(entity_id, None)

    def get(self, entity_id: str) -> dict[str, Any]:
        with self._lock:
            self._evict_expired()
            vec = self._store.get(entity_id)
        if vec is None:
            raise FeatureNotFoundError(f"No feature vector for entity '{entity_id}'")
        return dict(vec)

    def has(self, entity_id: str) -> bool:
        with self._lock:
            self._evict_expired()
            return entity_id in self._store

    def delete(self, entity_id: str) -> None:
        with self._lock:
            self._store.pop(entity_id, None)
            self._ttl.pop(entity_id, None)

    def put_batch(self, batch: dict[str, dict[str, Any]], *, ttl_sec: Optional[float] = None) -> None:
        with self._lock:
            for eid, features in batch.items():
                self._store[eid] = dict(features)
                if ttl_sec is not None:
                    self._ttl[eid] = time.time() + ttl_sec
                else:
                    self._ttl.pop(eid, None)

    def get_batch(self, entity_ids: list[str]) -> dict[str, dict[str, Any]]:
        result = {}
        for eid in entity_ids:
            if self.has(eid):
                result[eid] = self.get(eid)
        return result

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [eid for eid, exp in self._ttl.items() if now >= exp]
        for eid in expired:
            self._store.pop(eid, None)
            self._ttl.pop(eid, None)

    def count(self) -> int:
        with self._lock:
            self._evict_expired()
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._ttl.clear()
