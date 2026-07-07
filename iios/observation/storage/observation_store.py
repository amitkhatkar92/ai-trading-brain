"""
iios/observation/storage/observation_store.py
=============================================
ObservationStore — durable persistence façade.

Wraps the in-memory repository with an abstraction that could be
swapped for a SQL/NoSQL backend.  For now delegates to the
ObservationRepository singleton.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from ..observation_constants import ObservationStatus, SYSTEM_OBSERVER
from ..models.observation import Observation
from ..repositories.observation_repository import (
    ObservationRepository,
    get_observation_repository,
)
from ..repositories.observation_query import ObservationQuery

__all__ = ["ObservationStore", "get_observation_store", "reset_observation_store"]

_LOG  = logging.getLogger("iios.observation.store")
_lock = threading.Lock()
_store: Optional["ObservationStore"] = None


class ObservationStore:
    """High-level durable store with TTL expiry housekeeping."""

    def __init__(self, repo: Optional[ObservationRepository] = None) -> None:
        self._repo        = repo or get_observation_repository()
        self._lock        = threading.RLock()
        self._last_expiry = 0.0

    # ── Delegate CRUD ─────────────────────────────────────────────────────────

    def save(self, obs: Observation) -> Observation:
        return self._repo.save(obs)

    def get(self, obs_id: str) -> Observation:
        return self._repo.get(obs_id)

    def get_or_none(self, obs_id: str) -> Optional[Observation]:
        return self._repo.get_or_none(obs_id)

    def update(self, obs: Observation) -> Observation:
        return self._repo.update(obs)

    def upsert(self, obs: Observation) -> Observation:
        return self._repo.upsert(obs)

    def delete(self, obs_id: str) -> Observation:
        return self._repo.delete(obs_id)

    def exists(self, obs_id: str) -> bool:
        return self._repo.exists(obs_id)

    def find(self, query: ObservationQuery) -> list[Observation]:
        return self._repo.find(query)

    def list_accepted(self) -> list[Observation]:
        return self._repo.list_accepted()

    def list_pending(self) -> list[Observation]:
        return self._repo.list_pending()

    def save_batch(self, observations: list[Observation]) -> list[str]:
        return self._repo.save_batch(observations)

    # ── TTL housekeeping ──────────────────────────────────────────────────────

    def expire_stale(self, actor: str = SYSTEM_OBSERVER) -> list[str]:
        """Transition all expired ACCEPTED observations to EXPIRED status."""
        expired_ids: list[str] = []
        accepted    = self._repo.list_accepted()
        for obs in accepted:
            if obs.metadata.is_expired:
                try:
                    obs.expire(actor)
                    self._repo.update(obs)
                    expired_ids.append(obs.id)
                except Exception as exc:
                    _LOG.warning("Could not expire '%s': %s", obs.id[:24], exc)
        self._last_expiry = time.time()
        return expired_ids

    # ── Statistics ────────────────────────────────────────────────────────────

    def statistics(self) -> dict[str, Any]:
        return {
            "repository":    self._repo.statistics(),
            "last_expiry_at": self._last_expiry,
        }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_store() -> ObservationStore:
    global _store
    if _store is None:
        with _lock:
            if _store is None:
                _store = ObservationStore()
    return _store


def reset_observation_store() -> None:
    global _store
    with _lock:
        _store = None
