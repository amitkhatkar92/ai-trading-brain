"""
iios/infrastructure/database/orm/model_registry.py
===================================================
Registry of BaseModel subclasses — enables introspection and bulk table creation.
"""

from __future__ import annotations

import threading
from typing import Optional, Type

from .base_model import BaseModel
from ..database_session import DatabaseSession

__all__ = ["ModelRegistry", "get_model_registry", "reset_model_registry"]

_lock = threading.Lock()
_registry: Optional["ModelRegistry"] = None


class ModelRegistry:
    """Tracks all registered BaseModel subclasses.

    BaseModel auto-registers itself on class creation.
    Call ``create_all(session)`` to materialise all tables at once.
    """

    def __init__(self) -> None:
        self._models: dict[str, Type[BaseModel]] = {}
        self._lock = threading.RLock()

    def register(self, cls: Type[BaseModel]) -> None:
        with self._lock:
            name = getattr(cls, "__tablename__", None)
            if name:
                self._models[name] = cls

    def get(self, table_name: str) -> Optional[Type[BaseModel]]:
        with self._lock:
            return self._models.get(table_name)

    def all_models(self) -> list[Type[BaseModel]]:
        with self._lock:
            return list(self._models.values())

    def table_names(self) -> list[str]:
        with self._lock:
            return list(self._models.keys())

    def create_all(self, session: DatabaseSession) -> None:
        """Create all registered tables if they don't exist."""
        with self._lock:
            models = list(self._models.values())
        for model_cls in models:
            model_cls.create_table(session)

    def drop_all(self, session: DatabaseSession) -> None:
        """Drop all registered tables (destructive — test use only)."""
        with self._lock:
            names = list(self._models.keys())
        for name in reversed(names):  # reverse for FK safety
            session.execute(f"DROP TABLE IF EXISTS {name}")

    def __len__(self) -> int:
        return len(self._models)


def get_model_registry() -> ModelRegistry:
    global _registry
    with _lock:
        if _registry is None:
            _registry = ModelRegistry()
        return _registry


def reset_model_registry() -> None:
    global _registry
    with _lock:
        _registry = None
