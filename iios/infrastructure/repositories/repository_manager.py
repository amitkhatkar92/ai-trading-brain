"""
iios/infrastructure/repositories/repository_manager.py
=======================================================
Orchestrates the repository registry, factory and unit of work.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Generator, Optional

from .base_repository import BaseRepository
from .repository_factory import RepositoryFactory
from .repository_registry import RepositoryRegistry
from .unit_of_work import InMemoryUnitOfWork

__all__ = ["RepositoryManager", "get_repository_manager", "reset_repository_manager"]

_lock = threading.Lock()
_manager: Optional["RepositoryManager"] = None


class RepositoryManager:
    """Combines registry, factory and unit-of-work into one façade."""

    def __init__(self) -> None:
        self.registry = RepositoryRegistry()
        self.factory = RepositoryFactory()
        self._uow: Optional[InMemoryUnitOfWork] = None
        self._lock = threading.RLock()

    @contextmanager
    def unit_of_work(self) -> Generator[InMemoryUnitOfWork, None, None]:
        """Obtain a new InMemoryUnitOfWork context."""
        uow = InMemoryUnitOfWork()
        with uow.begin() as ctx:
            yield ctx

    def get_repository(self, name: str) -> BaseRepository:
        return self.registry.get(name)

    def create_repository(self, name: str, **kwargs: Any) -> BaseRepository:
        return self.factory.create(name, **kwargs)

    def reset(self) -> None:
        self.registry.clear()


def get_repository_manager() -> RepositoryManager:
    global _manager
    with _lock:
        if _manager is None:
            _manager = RepositoryManager()
        return _manager


def reset_repository_manager() -> None:
    global _manager
    with _lock:
        if _manager is not None:
            _manager.reset()
        _manager = None
