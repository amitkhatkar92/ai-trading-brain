"""
iios/infrastructure/repositories/base_repository.py
====================================================
Generic repository ABC with CRUD operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Iterable, Optional, TypeVar

__all__ = ["BaseRepository", "InMemoryRepository"]

T = TypeVar("T")
K = TypeVar("K")


class BaseRepository(ABC, Generic[T, K]):
    """Abstract repository for entity type *T* with key type *K*.

    Implementations must be thread-safe.
    """

    @abstractmethod
    def get(self, key: K) -> Optional[T]:
        """Return entity by *key*, or None if absent."""

    @abstractmethod
    def get_all(self) -> list[T]:
        """Return all entities."""

    @abstractmethod
    def save(self, entity: T) -> T:
        """Persist *entity* (insert or update). Returns saved entity."""

    @abstractmethod
    def save_all(self, entities: Iterable[T]) -> list[T]:
        """Persist a batch. Returns saved entities."""

    @abstractmethod
    def delete(self, key: K) -> bool:
        """Delete entity by *key*. Returns True if it existed."""

    @abstractmethod
    def delete_all(self) -> int:
        """Delete all entities. Returns count deleted."""

    @abstractmethod
    def exists(self, key: K) -> bool:
        """Return True if *key* exists in the repository."""

    @abstractmethod
    def count(self) -> int:
        """Return total number of stored entities."""

    def find(self, **criteria: Any) -> list[T]:
        """Filter entities by attribute criteria (default: full scan)."""
        results = []
        for entity in self.get_all():
            match = all(
                getattr(entity, attr, None) == value
                for attr, value in criteria.items()
            )
            if match:
                results.append(entity)
        return results


class InMemoryRepository(BaseRepository[T, K]):
    """Simple thread-safe in-memory repository backed by a dict.

    Requires entities to have a ``key`` property or that you supply
    a *key_fn* callable that extracts the key from an entity.

    Usage::

        repo = InMemoryRepository(key_fn=lambda e: e.id)
        repo.save(my_entity)
        entity = repo.get(42)
    """

    def __init__(self, key_fn: Any = None) -> None:
        import threading
        self._store: dict[Any, T] = {}
        self._key_fn = key_fn
        self._lock = threading.RLock()

    def _extract_key(self, entity: T) -> K:
        if self._key_fn is not None:
            return self._key_fn(entity)  # type: ignore[return-value]
        # Fall back to entity.key attribute
        if hasattr(entity, "key"):
            return entity.key  # type: ignore[return-value]
        if hasattr(entity, "id"):
            return entity.id  # type: ignore[return-value]
        raise ValueError(f"Cannot extract key from {entity!r} — provide a key_fn")

    def get(self, key: K) -> Optional[T]:
        with self._lock:
            return self._store.get(key)  # type: ignore[arg-type]

    def get_all(self) -> list[T]:
        with self._lock:
            return list(self._store.values())

    def save(self, entity: T) -> T:
        key = self._extract_key(entity)
        with self._lock:
            self._store[key] = entity  # type: ignore[index]
        return entity

    def save_all(self, entities: Iterable[T]) -> list[T]:
        saved = []
        for entity in entities:
            saved.append(self.save(entity))
        return saved

    def delete(self, key: K) -> bool:
        with self._lock:
            return self._store.pop(key, None) is not None  # type: ignore[arg-type]

    def delete_all(self) -> int:
        with self._lock:
            count = len(self._store)
            self._store.clear()
            return count

    def exists(self, key: K) -> bool:
        with self._lock:
            return key in self._store  # type: ignore[operator]

    def count(self) -> int:
        with self._lock:
            return len(self._store)
