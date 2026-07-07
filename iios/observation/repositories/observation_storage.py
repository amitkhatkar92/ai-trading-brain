"""
iios/observation/repositories/observation_storage.py
=====================================================
In-memory storage backend for observations.

Provides thread-safe CRUD operations over a dict-backed store.
In production this would be backed by SQLite / Redis / PostgreSQL —
the repository layer provides that abstraction.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

from ..observation_constants import MAX_OBSERVATIONS_IN_MEMORY, ObservationStatus
from ..observation_exceptions import (
    ObservationAlreadyExistsError,
    ObservationCapacityError,
    ObservationNotFoundError,
    ObservationStorageError,
)
from ..models.observation import Observation

__all__ = ["ObservationStorage", "get_observation_storage", "reset_observation_storage"]

_LOG   = logging.getLogger("iios.observation.storage")
_lock  = threading.Lock()
_store: Optional["ObservationStorage"] = None


class ObservationStorage:
    """Thread-safe in-memory observation store.

    Supports full CRUD + bulk operations.  Indexed by ``obs.id`` (full
    namespace/uid string).
    """

    def __init__(self, capacity: int = MAX_OBSERVATIONS_IN_MEMORY) -> None:
        self._lock     = threading.RLock()
        self._capacity = capacity
        self._data:    dict[str, Observation] = {}
        # Secondary indices
        self._by_type: dict[str, set[str]] = {}  # obs_type.value → {obs_id}
        self._by_status: dict[str, set[str]] = {}  # status.value → {obs_id}

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _index_add(self, obs: Observation) -> None:
        t = obs.obs_type.value
        s = obs.status.value
        self._by_type.setdefault(t, set()).add(obs.id)
        self._by_status.setdefault(s, set()).add(obs.id)

    def _index_remove(self, obs: Observation) -> None:
        t = obs.obs_type.value
        s = obs.status.value
        self._by_type.get(t, set()).discard(obs.id)
        self._by_status.get(s, set()).discard(obs.id)

    def _index_update(self, old: Observation, new: Observation) -> None:
        self._index_remove(old)
        self._index_add(new)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def store(self, obs: Observation) -> None:
        with self._lock:
            if obs.id in self._data:
                raise ObservationAlreadyExistsError(
                    f"Observation '{obs.id}' already exists.", code="OBS-002"
                )
            if len(self._data) >= self._capacity:
                raise ObservationCapacityError(
                    f"Storage capacity ({self._capacity}) exceeded.", code="OBS-091"
                )
            self._data[obs.id] = obs
            self._index_add(obs)

    def update(self, obs: Observation) -> None:
        with self._lock:
            old = self._data.get(obs.id)
            if old is None:
                raise ObservationNotFoundError(
                    f"Cannot update: observation '{obs.id}' not found.", code="OBS-001"
                )
            self._index_update(old, obs)
            self._data[obs.id] = obs

    def upsert(self, obs: Observation) -> None:
        with self._lock:
            old = self._data.get(obs.id)
            if old is not None:
                self._index_update(old, obs)
            else:
                if len(self._data) >= self._capacity:
                    raise ObservationCapacityError(
                        f"Storage capacity ({self._capacity}) exceeded.", code="OBS-091"
                    )
                self._index_add(obs)
            self._data[obs.id] = obs

    def get(self, obs_id: str) -> Observation:
        with self._lock:
            obs = self._data.get(obs_id)
        if obs is None:
            raise ObservationNotFoundError(
                f"Observation '{obs_id}' not found.", code="OBS-001"
            )
        return obs

    def get_or_none(self, obs_id: str) -> Optional[Observation]:
        with self._lock:
            return self._data.get(obs_id)

    def delete(self, obs_id: str) -> Observation:
        with self._lock:
            obs = self._data.pop(obs_id, None)
        if obs is None:
            raise ObservationNotFoundError(
                f"Cannot delete: observation '{obs_id}' not found.", code="OBS-001"
            )
        self._index_remove(obs)
        return obs

    def exists(self, obs_id: str) -> bool:
        with self._lock:
            return obs_id in self._data

    # ── Bulk ──────────────────────────────────────────────────────────────────

    def bulk_store(self, observations: list[Observation]) -> list[str]:
        stored: list[str] = []
        for obs in observations:
            try:
                self.store(obs)
                stored.append(obs.id)
            except (ObservationAlreadyExistsError, ObservationCapacityError) as exc:
                _LOG.warning("bulk_store skipped '%s': %s", obs.id[:24], exc)
        return stored

    def bulk_update(self, observations: list[Observation]) -> list[str]:
        updated: list[str] = []
        for obs in observations:
            try:
                self.update(obs)
                updated.append(obs.id)
            except ObservationNotFoundError as exc:
                _LOG.warning("bulk_update skipped '%s': %s", obs.id[:24], exc)
        return updated

    # ── Query helpers ─────────────────────────────────────────────────────────

    def list_all(self, include_deleted: bool = False) -> list[Observation]:
        with self._lock:
            items = list(self._data.values())
        if not include_deleted:
            items = [o for o in items if not o.is_deleted]
        return items

    def list_by_status(self, status: ObservationStatus) -> list[Observation]:
        with self._lock:
            ids = set(self._by_status.get(status.value, set()))
            return [self._data[i] for i in ids if i in self._data]

    def list_by_type(self, obs_type: Any) -> list[Observation]:
        with self._lock:
            ids = set(self._by_type.get(obs_type.value, set()))
            return [self._data[i] for i in ids if i in self._data]

    def count(self) -> int:
        with self._lock:
            return len(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._by_type.clear()
            self._by_status.clear()

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            by_status = {k: len(v) for k, v in self._by_status.items() if v}
            by_type   = {k: len(v) for k, v in self._by_type.items()   if v}
        return {
            "total":      self.count(),
            "capacity":   self._capacity,
            "by_status":  by_status,
            "by_type":    by_type,
        }


# ── Singleton helpers ─────────────────────────────────────────────────────────

def get_observation_storage() -> ObservationStorage:
    global _store
    if _store is None:
        with _lock:
            if _store is None:
                _store = ObservationStorage()
    return _store


def reset_observation_storage() -> None:
    global _store
    with _lock:
        _store = None
