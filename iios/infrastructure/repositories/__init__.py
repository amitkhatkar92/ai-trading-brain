"""
iios/infrastructure/repositories/__init__.py
"""

from __future__ import annotations

from .base_repository import BaseRepository, InMemoryRepository
from .unit_of_work import InMemoryUnitOfWork
from .transaction_manager import TransactionManager
from .repository_registry import (
    RepositoryRegistry,
    get_repository_registry,
    reset_repository_registry,
)
from .repository_factory import RepositoryFactory
from .repository_manager import (
    RepositoryManager,
    get_repository_manager,
    reset_repository_manager,
)

__all__ = [
    "BaseRepository", "InMemoryRepository",
    "InMemoryUnitOfWork",
    "TransactionManager",
    "RepositoryRegistry", "get_repository_registry", "reset_repository_registry",
    "RepositoryFactory",
    "RepositoryManager", "get_repository_manager", "reset_repository_manager",
]
