"""
iios/infrastructure/repositories/repository_factory.py
=======================================================
Factory for creating repository instances.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional, Type

from ..infrastructure_exceptions import RepositoryError
from .base_repository import BaseRepository, InMemoryRepository

__all__ = ["RepositoryFactory"]


class RepositoryFactory:
    """Creates BaseRepository instances from registered builder functions.

    Usage::

        factory = RepositoryFactory()
        factory.register("trade", lambda: InMemoryRepository(key_fn=lambda e: e.id))
        repo = factory.create("trade")
    """

    def __init__(self) -> None:
        self._builders: dict[str, Callable[..., BaseRepository]] = {}
        self._lock = threading.RLock()

    def register(self, name: str, builder: Callable[..., BaseRepository]) -> None:
        with self._lock:
            self._builders[name] = builder

    def register_class(self, name: str, cls: Type[BaseRepository], **kwargs: Any) -> None:
        """Register a repository class; it will be instantiated with *kwargs*."""
        with self._lock:
            self._builders[name] = lambda: cls(**kwargs)

    def create(self, name: str, **override: Any) -> BaseRepository:
        with self._lock:
            builder = self._builders.get(name)
        if builder is None:
            raise RepositoryError(
                f"No repository builder for '{name}'",
                code="INF-REPO-003",
                context={"name": name},
            )
        return builder(**override) if override else builder()

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._builders

    def names(self) -> list[str]:
        with self._lock:
            return list(self._builders.keys())
