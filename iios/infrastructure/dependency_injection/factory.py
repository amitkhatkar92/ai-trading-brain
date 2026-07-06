"""
iios/infrastructure/dependency_injection/factory.py
====================================================
Factory helpers for creating services with complex construction logic.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Generic, Optional, Type, TypeVar

__all__ = [
    "ServiceFactory",
    "AbstractFactory",
    "ConcreteFactory",
    "FactoryRegistry",
]

T = TypeVar("T")


class ServiceFactory(Generic[T]):
    """A callable factory that creates instances of a specific type.

    Usage::

        factory = ServiceFactory(MyService, arg1="value")
        svc = factory.create()
        svc2 = factory.create()  # independent new instance
    """

    def __init__(self, cls: Type[T], *args: Any, **kwargs: Any) -> None:
        self._cls = cls
        self._args = args
        self._kwargs = kwargs

    def create(self, **override: Any) -> T:
        """Create a new instance, optionally overriding constructor kwargs."""
        kw = dict(self._kwargs)
        kw.update(override)
        return self._cls(*self._args, **kw)

    def __call__(self, **override: Any) -> T:
        return self.create(**override)

    @property
    def target_type(self) -> Type[T]:
        return self._cls


class AbstractFactory(Generic[T]):
    """Registry-backed factory that creates objects by type key."""

    def __init__(self) -> None:
        self._builders: dict[str, Callable[..., T]] = {}
        self._lock = threading.Lock()

    def register(self, key: str, builder: Callable[..., T]) -> None:
        with self._lock:
            self._builders[key] = builder

    def create(self, key: str, **kwargs: Any) -> T:
        with self._lock:
            builder = self._builders.get(key)
        if builder is None:
            raise KeyError(f"No builder registered for key '{key}'")
        return builder(**kwargs)

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._builders.keys())

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._builders


class ConcreteFactory(Generic[T]):
    """A factory backed by a single callable, with optional caching."""

    def __init__(
        self,
        callable_: Callable[..., T],
        cache: bool = False,
    ) -> None:
        self._callable = callable_
        self._cache = cache
        self._cached: Optional[T] = None
        self._lock = threading.Lock()

    def __call__(self, **kwargs: Any) -> T:
        if self._cache:
            with self._lock:
                if self._cached is None:
                    self._cached = self._callable(**kwargs)
                return self._cached
        return self._callable(**kwargs)

    def invalidate(self) -> None:
        with self._lock:
            self._cached = None


class FactoryRegistry:
    """Global registry of named ``AbstractFactory`` instances."""

    def __init__(self) -> None:
        self._factories: dict[str, AbstractFactory] = {}
        self._lock = threading.Lock()

    def register_factory(self, name: str, factory: AbstractFactory) -> None:
        with self._lock:
            self._factories[name] = factory

    def get(self, name: str) -> AbstractFactory:
        with self._lock:
            f = self._factories.get(name)
        if f is None:
            raise KeyError(f"No factory named '{name}'")
        return f

    def create(self, factory_name: str, key: str, **kwargs: Any) -> Any:
        return self.get(factory_name).create(key, **kwargs)

    def names(self) -> list[str]:
        with self._lock:
            return list(self._factories.keys())
