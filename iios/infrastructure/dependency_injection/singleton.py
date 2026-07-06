"""
iios/infrastructure/dependency_injection/singleton.py
======================================================
Singleton base class and registry helpers.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional, TypeVar

__all__ = ["Singleton", "SingletonMeta", "singleton_registry"]

T = TypeVar("T")

# Global registry: class → instance
_registry: dict[type, Any] = {}
_registry_lock = threading.Lock()


class SingletonMeta(type):
    """Metaclass that enforces the Singleton pattern at class level.

    Usage::

        class MyService(metaclass=SingletonMeta):
            def __init__(self): ...

        a = MyService()
        b = MyService()
        assert a is b
    """

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        with _registry_lock:
            if cls not in _registry:
                _registry[cls] = super().__call__(*args, **kwargs)
            return _registry[cls]


class Singleton:
    """Convenience base class using ``SingletonMeta``.

    Subclasses are automatically singletons::

        class Config(Singleton):
            def __init__(self): self.value = 42

        assert Config() is Config()
    """

    _instance_lock: threading.Lock

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Patch the subclass to use SingletonMeta behaviour
        cls._instance_lock = threading.Lock()
        cls._singleton_instance: Optional[Any] = None
        original_new = cls.__new__

        def __new__(klass: type, *args: Any, **kwargs: Any) -> Any:
            with _registry_lock:
                if klass not in _registry:
                    if original_new is object.__new__:
                        instance = object.__new__(klass)
                    else:
                        instance = original_new(klass, *args, **kwargs)
                    _registry[klass] = instance
                return _registry[klass]

        cls.__new__ = __new__  # type: ignore[method-assign]


def singleton_registry() -> dict[type, Any]:
    """Return a copy of the current singleton registry (for inspection)."""
    with _registry_lock:
        return dict(_registry)


def clear_singleton_registry() -> None:
    """Clear all cached singletons (for testing only)."""
    with _registry_lock:
        _registry.clear()
