"""
iios/infrastructure/dependency_injection/provider.py
=====================================================
Provider protocol and concrete provider implementations.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, Optional, TypeVar

T = TypeVar("T")

__all__ = [
    "Provider",
    "SingletonProvider",
    "TransientProvider",
    "FactoryProvider",
    "InstanceProvider",
    "LazyProvider",
]


class Provider(ABC, Generic[T]):
    """Abstract provider that produces a service instance."""

    @abstractmethod
    def get(self) -> T:
        """Return (or create) the service instance."""

    def reset(self) -> None:
        """Reset any cached state. No-op by default."""


class SingletonProvider(Provider[T]):
    """Creates exactly one instance, shared on every call."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._instance: Optional[T] = None
        self._lock = threading.Lock()

    def get(self) -> T:
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = self._factory()
        return self._instance

    def reset(self) -> None:
        with self._lock:
            self._instance = None


class TransientProvider(Provider[T]):
    """Creates a new instance on every call."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory

    def get(self) -> T:
        return self._factory()


class FactoryProvider(Provider[T]):
    """Delegates to an arbitrary callable with optional args."""

    def __init__(self, factory: Callable[..., T], *args: Any, **kwargs: Any) -> None:
        self._factory = factory
        self._args = args
        self._kwargs = kwargs

    def get(self) -> T:
        return self._factory(*self._args, **self._kwargs)


class InstanceProvider(Provider[T]):
    """Wraps a pre-built instance (always returns the same object)."""

    def __init__(self, instance: T) -> None:
        self._instance = instance

    def get(self) -> T:
        return self._instance


class LazyProvider(Provider[T]):
    """Defers construction until first access (thread-safe singleton)."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._instance: Optional[T] = None
        self._lock = threading.Lock()
        self._initialised = False

    def get(self) -> T:
        if not self._initialised:
            with self._lock:
                if not self._initialised:
                    self._instance = self._factory()
                    self._initialised = True
        return self._instance  # type: ignore[return-value]

    def reset(self) -> None:
        with self._lock:
            self._instance = None
            self._initialised = False
