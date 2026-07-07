"""
iios/observation/repositories/observation_repository.py
=======================================================
Primary CRUD repository for observations.

Wraps the storage and cache layers and provides the standard
read/write interface used by all higher-level services.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from ..observation_constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    SYSTEM_OBSERVER,
    ObservationStatus,
)
from ..observation_exceptions import ObservationNotFoundError
from ..models.observation import Observation
from .observation_storage import ObservationStorage, get_observation_storage
from .observation_cache   import ObservationCache, get_observation_cache
from .observation_query   import ObservationQuery

__all__ = [
    "ObservationRepository",
    "get_observation_repository",
    "reset_observation_repository",
]

_LOG  = logging.getLogger("iios.observation.repository")
_lock = threading.Lock()
_repo: Optional["ObservationRepository"] = None


class ObservationRepository:
    """High-level repository combining storage + cache."""

    def __init__(
        self,
        storage: Optional[ObservationStorage] = None,
        cache:   Optional[ObservationCache]   = None,
    ) -> None:
        self._storage = storage or get_observation_storage()
        self._cache   = cache   or get_observation_cache()
        self._lock    = threading.RLock()

    # ── Create ────────────────────────────────────────────────────────────────

    def save(self, obs: Observation) -> Observation:
        self._storage.store(obs)
        self._cache.put(obs)
        _LOG.debug("Saved: %s (%s)", obs.id[:32], obs.status.value)
        return obs

    def save_batch(self, observations: list[Observation]) -> list[str]:
        ids = self._storage.bulk_store(observations)
        for obs in observations:
            if obs.id in ids:
                self._cache.put(obs)
        return ids

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, obs_id: str) -> Observation:
        cached = self._cache.get(obs_id)
        if cached is not None:
            return cached
        obs = self._storage.get(obs_id)    # raises ObservationNotFoundError if missing
        self._cache.put(obs)
        return obs

    def get_or_none(self, obs_id: str, include_deleted: bool = False) -> Optional[Observation]:
        try:
            obs = self.get(obs_id)
        except ObservationNotFoundError:
            return None
        if obs.is_deleted and not include_deleted:
            return None
        return obs

    def exists(self, obs_id: str) -> bool:
        if self._cache.contains(obs_id):
            return True
        return self._storage.exists(obs_id)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, obs: Observation) -> Observation:
        self._storage.update(obs)
        self._cache.put(obs)
        return obs

    def upsert(self, obs: Observation) -> Observation:
        self._storage.upsert(obs)
        self._cache.put(obs)
        return obs

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, obs_id: str) -> Observation:
        obs = self._storage.delete(obs_id)
        self._cache.invalidate(obs_id)
        return obs

    def soft_delete(self, obs_id: str, actor: str = SYSTEM_OBSERVER) -> Observation:
        obs = self.get(obs_id)
        obs.soft_delete(actor)
        return self.update(obs)

    # ── Query ─────────────────────────────────────────────────────────────────

    def find(self, query: ObservationQuery) -> list[Observation]:
        """Execute *query* against the storage layer."""
        all_obs = self._storage.list_all(include_deleted=query.include_deleted)

        # Filter
        matched = [o for o in all_obs if query.matches(o)]

        # Sort
        reverse = query.sort_order.value == "desc"
        try:
            matched.sort(
                key=lambda o: getattr(o, query.sort_field, o.created_at) or 0,
                reverse=reverse,
            )
        except (AttributeError, TypeError):
            matched.sort(key=lambda o: o.created_at, reverse=reverse)

        # Paginate
        start = query.page_offset
        end   = start + query.page_size
        return matched[start:end]

    def count(self, query: Optional[ObservationQuery] = None) -> int:
        if query is None:
            return self._storage.count()
        all_obs = self._storage.list_all(include_deleted=query.include_deleted)
        return sum(1 for o in all_obs if query.matches(o))

    def find_by_status(self, status: ObservationStatus) -> list[Observation]:
        return self._storage.list_by_status(status)

    def list_accepted(self) -> list[Observation]:
        return self.find_by_status(ObservationStatus.ACCEPTED)

    def list_pending(self) -> list[Observation]:
        """Return all observations not yet in a terminal state."""
        terminal = {
            ObservationStatus.ACCEPTED,
            ObservationStatus.REJECTED,
            ObservationStatus.ARCHIVED,
            ObservationStatus.EXPIRED,
            ObservationStatus.DELETED,
        }
        return [o for o in self._storage.list_all() if o.status not in terminal]

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        return {
            "storage": self._storage.statistics(),
            "cache":   self._cache.statistics(),
        }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_repository() -> ObservationRepository:
    global _repo
    if _repo is None:
        with _lock:
            if _repo is None:
                _repo = ObservationRepository()
    return _repo


def reset_observation_repository() -> None:
    global _repo
    with _lock:
        _repo = None
