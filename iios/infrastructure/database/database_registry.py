"""
iios/infrastructure/database/database_registry.py
==================================================
Registry of named DatabaseEngine instances.
"""

from __future__ import annotations

import threading
from typing import Optional

from .database_engine import DatabaseEngine
from .database_exceptions import EngineNotFoundError, DatabaseError

__all__ = ["DatabaseRegistry", "get_database_registry", "reset_database_registry"]

_lock = threading.Lock()
_registry: Optional["DatabaseRegistry"] = None


class DatabaseRegistry:
    """Maintains a catalogue of named ``DatabaseEngine`` instances.

    Usage::

        reg = get_database_registry()
        reg.register("trades", engine)
        engine = reg.get("trades")
    """

    def __init__(self) -> None:
        self._engines: dict[str, DatabaseEngine] = {}
        self._default: Optional[str] = None
        self._lock = threading.RLock()

    def register(
        self,
        name: str,
        engine: DatabaseEngine,
        *,
        as_default: bool = False,
        allow_override: bool = False,
    ) -> None:
        with self._lock:
            if name in self._engines and not allow_override:
                raise DatabaseError(
                    f"Engine '{name}' is already registered",
                    code="DB-REG-001",
                    context={"name": name},
                )
            self._engines[name] = engine
            if as_default or self._default is None:
                self._default = name

    def get(self, name: str) -> DatabaseEngine:
        with self._lock:
            eng = self._engines.get(name)
        if eng is None:
            raise EngineNotFoundError(name)
        return eng

    def get_optional(self, name: str) -> Optional[DatabaseEngine]:
        with self._lock:
            return self._engines.get(name)

    def default(self) -> DatabaseEngine:
        """Return the default engine (first registered or explicitly set)."""
        with self._lock:
            if self._default is None:
                raise EngineNotFoundError("<default>")
            return self.get(self._default)

    def set_default(self, name: str) -> None:
        with self._lock:
            if name not in self._engines:
                raise EngineNotFoundError(name)
            self._default = name

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._engines

    def names(self) -> list[str]:
        with self._lock:
            return list(self._engines.keys())

    def unregister(self, name: str, close: bool = True) -> bool:
        with self._lock:
            eng = self._engines.pop(name, None)
            if eng is None:
                return False
            if close:
                eng.close()
            if self._default == name:
                self._default = next(iter(self._engines), None)
        return True

    def close_all(self) -> None:
        with self._lock:
            for eng in self._engines.values():
                try:
                    eng.close()
                except Exception:
                    pass
            self._engines.clear()
            self._default = None

    def __len__(self) -> int:
        return len(self._engines)


def get_database_registry() -> DatabaseRegistry:
    global _registry
    with _lock:
        if _registry is None:
            _registry = DatabaseRegistry()
        return _registry


def reset_database_registry() -> None:
    global _registry
    with _lock:
        if _registry is not None:
            _registry.close_all()
        _registry = None
