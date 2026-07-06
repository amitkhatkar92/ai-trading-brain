"""
iios/infrastructure/repositories/repository_registry.py
=======================================================
Registry for BaseRepository instances.
"""

from __future__ import annotations

import threading
from typing import Any, Optional, Type

from ..infrastructure_exceptions import RepositoryError
from .base_repository import BaseRepository

__all__ = ["RepositoryRegistry", "get_repository_registry", "reset_repository_registry"]

_lock = threading.Lock()
_registry: Optional["RepositoryRegistry"] = None


class RepositoryRegistry:
    """Maintains a catalogue of named repository instances."""

    def __init__(self) -> None:
        self._repos: dict[str, BaseRepository] = {}
        self._lock = threading.RLock()

    def register(self, name: str, repo: BaseRepository, allow_override: bool = False) -> None:
        with self._lock:
            if name in self._repos and not allow_override:
                raise RepositoryError(
                    f"Repository '{name}' already registered",
                    code="INF-REPO-001",
                    context={"name": name},
                )
            self._repos[name] = repo

    def get(self, name: str) -> BaseRepository:
        with self._lock:
            r = self._repos.get(name)
        if r is None:
            raise RepositoryError(
                f"Repository '{name}' not found",
                code="INF-REPO-002",
                context={"name": name},
            )
        return r

    def get_optional(self, name: str) -> Optional[BaseRepository]:
        with self._lock:
            return self._repos.get(name)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._repos

    def names(self) -> list[str]:
        with self._lock:
            return list(self._repos.keys())

    def unregister(self, name: str) -> bool:
        with self._lock:
            return self._repos.pop(name, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._repos.clear()


def get_repository_registry() -> RepositoryRegistry:
    global _registry
    with _lock:
        if _registry is None:
            _registry = RepositoryRegistry()
        return _registry


def reset_repository_registry() -> None:
    global _registry
    with _lock:
        _registry = None
